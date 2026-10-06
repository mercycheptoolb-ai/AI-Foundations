"""Boss agent — owns the chat and delegates to book specialists.

Every action lands on one asyncio.Queue through BossDeps.emit():
  boss_thinking      the run starts
  agent_step         one PydanticAI loop node (boss or specialist), or a retrieval
  specialist_started the boss delegated to a book (dashboard edge lights up)
  specialist_done    that book reported back
  spend              a model call was priced; carries that agent's running total + project total
  budget_exceeded    project spend hit the budget — the run is cancelled (💥)
  final / error      last event; data matches ChatResponse
run_boss_chat_stream() drains the queue for SSE; run_boss_chat() returns the final dict.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from pydantic_ai import Agent, RunContext

from agents.config import BOSS_NAME, build_model
from agents.events import clip, run_traced
from agents.specialists import run_specialist, specialist_name
from models import BOOK_TITLES, Delegation
from pricing import DEFAULT_MODEL, cost_usd, fmt_usd

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "boss.md").read_text(encoding="utf-8")
MAX_DELEGATIONS = 12  # guard rail on Portkey spend per question


@dataclass
class BossDeps:
    queue: asyncio.Queue
    model: str = DEFAULT_MODEL
    budget_usd: float = 1.0
    delegations: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    specialist_usage: list[dict] = field(default_factory=list)
    spend: dict[str, dict] = field(default_factory=dict)  # agent name → running tally
    total_usd: float = 0.0
    over_budget: bool = False
    task: asyncio.Task | None = None
    started: float = field(default_factory=time.perf_counter)
    seq: int = 0

    def emit(self, event_type: str, **data: Any) -> None:
        self._push(event_type, data)
        # Every model response (boss or specialist) passes through here, so this is
        # the one place to price tokens and enforce the budget.
        if event_type == "agent_step" and data.get("kind") == "model_response":
            self._charge(data)

    def _charge(self, step: dict) -> None:
        u = step.get("usage") or {}
        cost = cost_usd(self.model, u.get("input_tokens", 0), u.get("output_tokens", 0), u.get("cache_read_tokens", 0))
        agent = step["agent"]
        row = self.spend.setdefault(
            agent,
            {
                "agent": agent,
                "book_number": step.get("book_number"),
                "requests": 0,
                "input_tokens": 0,
                "cached_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            },
        )
        row["requests"] += 1
        row["input_tokens"] += u.get("input_tokens", 0)
        row["cached_tokens"] += u.get("cache_read_tokens", 0)
        row["output_tokens"] += u.get("output_tokens", 0)
        row["cost_usd"] += cost
        self.total_usd += cost
        self._push(
            "spend",
            {
                "agent": agent,
                "book_number": step.get("book_number"),
                "call_cost_usd": cost,
                "row": dict(row),
                "total_usd": self.total_usd,
                "budget_usd": self.budget_usd,
            },
        )
        if self.total_usd >= self.budget_usd and not self.over_budget:
            self.over_budget = True
            self._push(
                "budget_exceeded",
                {"agent": agent, "total_usd": self.total_usd, "budget_usd": self.budget_usd},
            )
            if self.task:  # stop the boss and every in-flight specialist
                self.task.cancel()

    def _push(self, event_type: str, data: dict) -> None:
        self.seq += 1
        data = {
            "seq": self.seq,
            "t_ms": round((time.perf_counter() - self.started) * 1000),
            "ts": time.time(),
            **data,
        }
        event = {"type": event_type, "data": data}
        if event_type not in ("final", "error"):
            self.trace.append(event)
        self.queue.put_nowait(event)


boss_agent = Agent(deps_type=BossDeps, output_type=str, instructions=PROMPT, name="boss")


@boss_agent.tool
async def ask_book_specialist(ctx: RunContext[BossDeps], book_number: int, question: str) -> dict:
    """Delegate a question to the specialist for one Harry Potter book.

    Args:
        book_number: 1 Sorcerer's Stone, 2 Chamber of Secrets, 3 Prisoner of Azkaban,
            4 Goblet of Fire, 5 Order of the Phoenix, 6 Half-Blood Prince, 7 Deathly Hallows.
        question: A specific question for that book, with concrete names/objects/places
            so the specialist's keyword search finds the right passages.
    """
    d = ctx.deps
    if book_number not in BOOK_TITLES:
        return {"status": "error", "reply": "book_number must be between 1 and 7."}
    if len(d.delegations) >= MAX_DELEGATIONS:
        return {"status": "error", "reply": "Delegation limit reached; answer from the reports you have."}

    index = len(d.delegations)
    delegation = Delegation(
        agent=specialist_name(book_number),
        book_number=book_number,
        book_title=BOOK_TITLES[book_number],
        question=question,
        status="running",
    ).model_dump()
    d.delegations.append(delegation)
    d.emit(
        "specialist_started",
        index=index,
        from_agent=BOSS_NAME,
        tool_call_id=ctx.tool_call_id,
        **{k: delegation[k] for k in ("agent", "book_number", "book_title", "question")},
    )

    result = await run_specialist(book_number, question, emit=d.emit, model_name=d.model)

    delegation.update(reply=result["reply"], status=result["status"])
    if result.get("usage"):
        d.specialist_usage.append(result["usage"])
    d.emit("specialist_done", index=index, to_agent=BOSS_NAME, question=question, **result)
    return {k: result.get(k) for k in ("agent", "book_number", "book_title", "status", "passages_used", "reply")}


def _total_usage(boss: dict | None, specialists: list[dict]) -> dict:
    parts = ([boss] if boss else []) + specialists
    keys = ("requests", "input_tokens", "output_tokens")
    total = {k: sum(p.get(k, 0) for p in parts) for k in keys}
    return {"boss": boss, "specialists": {k: sum(p.get(k, 0) for p in specialists) for k in keys}, "total": total}


def _final_data(deps: BossDeps, boss_usage: dict | None) -> dict:
    return {
        "delegations": deps.delegations,
        "trace": list(deps.trace),
        "boss_name": BOSS_NAME,
        "usage": _total_usage(boss_usage, deps.specialist_usage),
        "spend": list(deps.spend.values()),
        "total_usd": deps.total_usd,
        "budget_usd": deps.budget_usd,
        "budget_exceeded": deps.over_budget,
        "model": deps.model,
    }


async def run_boss_chat_stream(
    message: str, model: str = DEFAULT_MODEL, budget_usd: float = 1.0
) -> AsyncIterator[dict]:
    """Yield every queued event as it happens, ending with `final` or `error`."""
    queue: asyncio.Queue = asyncio.Queue()
    deps = BossDeps(queue=queue, model=model, budget_usd=budget_usd)

    async def work() -> None:
        boss_usage = None
        try:
            deps.emit("boss_thinking", agent=BOSS_NAME, message=message, model=model, budget_usd=budget_usd)
            answer, boss_usage = await run_traced(
                boss_agent, message, emit=deps.emit, agent_name=BOSS_NAME, deps=deps, model=build_model(model)
            )
            deps.emit("final", answer=answer, **_final_data(deps, boss_usage))
        except asyncio.CancelledError:
            if not deps.over_budget:  # client hung up — just stop
                raise
            asyncio.current_task().uncancel()
            deps.emit(
                "error",
                answer=(
                    f"💥 BOOM! The castle blew its budget: {fmt_usd(deps.total_usd)} spent of "
                    f"{fmt_usd(deps.budget_usd)} on {model}. Every agent was stopped mid-spell."
                ),
                error="budget exceeded",
                **_final_data(deps, boss_usage),
            )
        except Exception as exc:
            deps.emit(
                "error",
                answer=f"The Headmaster's spell fizzled: {clip(exc, 400)}",
                error=clip(exc, 1000),
                **_final_data(deps, boss_usage),
            )
        finally:
            queue.put_nowait(None)

    task = asyncio.create_task(work())
    deps.task = task
    try:
        while (event := await queue.get()) is not None:
            yield event
    finally:
        if not task.done():  # client hung up mid-run: stop spending tokens
            task.cancel()


async def run_boss_chat(message: str, model: str = DEFAULT_MODEL, budget_usd: float = 1.0) -> dict:
    final: dict = {"answer": "No answer produced.", "delegations": [], "boss_name": BOSS_NAME}
    async for event in run_boss_chat_stream(message, model, budget_usd):
        if event["type"] in ("final", "error"):
            final = event["data"]
    return final
