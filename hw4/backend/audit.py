"""Append-only audit trail of the agent loop (Problem 12).

Every chat message runs one agent loop. AuditTrail is a PydanticAI capability (lifecycle
hooks) that records what happened in that loop, one JSON object per event, in
output/audit_trail.json:

    run_start     who is chatting (guest / user id), page, message length, model, limits
    model_step    one model call: the provider's stop reason, which tools it asked for, what
                  the loop does next (run_tools / check_reply), tokens, time
    tool          one tool call: name, short args, short result (or why it failed), time
    output_check  the grounding check on the reply: passed, or sent back to the model (why)
    run_end       why the loop stopped, plus totals (model calls, tool calls, tokens, time)
    fallback_reply  (written by main.py) which canned reply the shopper got when the loop
                  didn't produce one: crisis / blocked / declined / usage_limit / gave_up

The file is a JSON array with one entry per line. A new entry only overwrites the closing
"]", so earlier entries are never rewritten, and the file is never cleared between runs or
server restarts. If it was cut off (e.g. a crash mid-write), the complete entries are kept,
the damaged original is saved next to it, and appending carries on.

Privacy: the shopper's message and the reply are stored only as lengths, never as text, and
there are no names or emails from accounts, passwords, session tokens, or API keys. Guests are
recorded as "guest". Tool arguments are written by the model and can contain words the shopper
typed (e.g. a search term), so they are clipped, with emails and phone/card-like numbers masked;
search_chat_history queries (drawn from the shopper's own past chats) are stored as a length only.

Read it with any JSON tool, or print the latest runs:  python audit.py [N]
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
import sys
import threading
import time
import uuid
from dataclasses import KW_ONLY, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import fcntl  # file lock so two processes can't interleave writes (macOS / Linux)
except ImportError:  # pragma: no cover - Windows
    fcntl = None

from pydantic import BaseModel, ValidationError
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.exceptions import (
    ContentFilterError,
    ModelHTTPError,
    ToolRetryError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import TextPart, ToolCallPart

from models import (
    Alternatives,
    CatalogueOverview,
    ChatHistorySearch,
    CustomerProfileInfo,
    PriceInfo,
    PriceQuote,
    ProductDescription,
    SearchResults,
    ShopDeps,
    StockInfo,
)

logger = logging.getLogger("campus_customs.audit")

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
TAIL_BYTES = 4096  # how much of the file end to read when appending
OUTPUT_TOOL_PREFIX = "final_result"  # PydanticAI's name for the "here is my answer" tool
_lock = threading.Lock()


def audit_path() -> Path:
    """output/audit_trail.json, or AUDIT_TRAIL_PATH (used by tests so they don't touch the real file)."""
    return Path(os.getenv("AUDIT_TRAIL_PATH") or DEFAULT_PATH)


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


# ---------- the append-only file ----------

def append(entry: dict) -> None:
    """Add one entry to the end of the trail. Never raises: auditing must not break the chat."""
    try:
        line = _dumps(entry)
        path = audit_path()
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)  # never O_TRUNC
            with os.fdopen(fd, "r+b") as f:
                if fcntl:
                    fcntl.flock(f, fcntl.LOCK_EX)
                _append_locked(f, path, line)
    except Exception:
        logger.warning("could not write to the audit trail", exc_info=True)


def _finite(value: Any) -> Any:
    """NaN / Infinity aren't valid JSON: store them as strings."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite(v) for v in value]
    return value


def _dumps(entry: dict) -> bytes:
    return json.dumps(_finite(entry), ensure_ascii=False, default=str, allow_nan=False).encode()


def _append_locked(f, path: Path, line: bytes) -> None:
    end = f.seek(0, os.SEEK_END)
    if end == 0:
        f.write(b"[\n" + line + b"\n]\n")
        return
    start = max(0, end - TAIL_BYTES)
    f.seek(start)
    tail = f.read().rstrip()
    if tail.endswith(b"]"):
        before = tail[:-1].rstrip()
        cut = start + len(before)
        if before.endswith(b"}"):  # ...last entry} ]  ->  ...last entry},\n new\n]
            f.seek(cut)
            f.write(b",\n" + line + b"\n]\n")
            f.truncate()
            return
        if before == b"[" and start == 0:  # an empty array
            f.seek(cut)
            f.write(b"\n" + line + b"\n]\n")
            f.truncate()
            return
    _repair(f, path, line)


def _repair(f, path: Path, line: bytes) -> None:
    """The file doesn't end like a JSON array (cut off mid-write?). Keep every complete
    entry, save the original next to it, and continue. Nothing is thrown away."""
    f.seek(0)
    raw = f.read()
    kept = []
    for chunk in raw.splitlines():
        text = chunk.strip().rstrip(b",")
        if text.startswith(b"{"):
            try:
                obj = json.loads(text)
            except ValueError:
                continue
            if isinstance(obj, dict):
                kept.append(_dumps(obj))
    backup = path.with_name(f"{path.stem}.damaged-{datetime.now():%Y%m%d-%H%M%S-%f}{path.suffix}")
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # owner-only, like the trail
    with os.fdopen(fd, "wb") as b:
        b.write(raw)
    note = _dumps({
        "time": now(),
        "event": "trail_repaired",
        "detail": f"file did not end in ']'; kept {len(kept)} complete entries; original saved as {backup.name}",
    })
    f.seek(0)
    f.write(b"[\n" + b",\n".join([*kept, note, line]) + b"\n]\n")
    f.truncate()


def read_entries(path: Path | None = None) -> list[dict]:
    """All entries, oldest first (for tests and the command line)."""
    p = path or audit_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


# ---------- short, privacy-safe summaries ----------

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
LONG_DIGITS_RE = re.compile(r"\+?\(?\d(?:[\s().\/-]{0,3}\d){6,}")  # phone or card-like numbers


def clip(value: Any, limit: int = 80) -> str:
    """One line, emails and long digit runs masked, at most `limit` characters."""
    text = " ".join(str(value).split())
    text = LONG_DIGITS_RE.sub("[number]", EMAIL_RE.sub("[email]", text))
    return text if len(text) <= limit else text[: limit - 1] + "…"


PRIVATE_ARGS = {("search_chat_history", "query")}  # words from the shopper's own past chats


def short_args(args: Any, tool: str = "") -> dict:
    """Tool arguments without empty values; long values clipped; private ones reduced to a length."""
    if isinstance(args, BaseModel):
        args = args.model_dump()
    if not isinstance(args, dict):
        return {"args": clip(args)}
    out: dict[str, Any] = {}
    for k, v in args.items():
        if isinstance(v, BaseModel):
            v = v.model_dump()
        elif isinstance(v, list):
            v = [x.model_dump() if isinstance(x, BaseModel) else x for x in v]
        if v is None or v == "" or v == [] or v == {}:
            continue
        if (tool, k) in PRIVATE_ARGS:
            out[k] = f"[{len(str(v))} chars]"
        elif isinstance(v, (bool, int, float)):
            out[k] = v
        elif isinstance(v, str):
            out[k] = clip(v)
        else:
            out[k] = clip(json.dumps(v, ensure_ascii=False), 120)
    return out


def _ids(ids: list[str], n: int = 3) -> str:
    more = f" +{len(ids) - n} more" if len(ids) > n else ""
    return ", ".join(ids[:n]) + more


def short_result(result: Any) -> str:
    """One line saying what a tool found. Customer tools report counts only (no name or email)."""
    r = result
    if isinstance(r, SearchResults):
        s = f"{len(r.matches)} shown of {r.total_found} found"
        if r.in_size_found is not None:
            s += f" ({r.in_size_found} in the size)"
        return s + (f": {_ids([m.product_id for m in r.matches])}" if r.matches else "")
    if isinstance(r, PriceInfo):
        return f"{r.product_id} = {r.price_display} (matched by {r.matched_by})"
    if isinstance(r, StockInfo):
        return clip(f"{r.product_id} (matched by {r.matched_by}): {r.summary}", 200)
    if isinstance(r, ProductDescription):
        desc = "has description" if r.description else "no description"
        return f"{r.product_id}: {r.garment_color or 'color not listed'}, {desc}"
    if isinstance(r, PriceQuote):
        s = f"{len(r.lines)} line(s), total {r.total_display}"
        if r.remaining_budget is not None:
            s += f", ${r.remaining_budget:.2f} left of ${r.budget:.2f}"
        return s
    if isinstance(r, Alternatives):
        return f"{len(r.matches)} in-stock alternative(s) in {r.size or 'any size'}" + (
            f": {_ids([m.product_id for m in r.matches])}" if r.matches else ""
        )
    if isinstance(r, CatalogueOverview):
        return f"{r.total_products} products in {len(r.categories)} categories"
    if isinstance(r, CustomerProfileInfo):
        return f"logged_in={str(r.logged_in).lower()}, saved_messages={r.saved_messages}"
    if isinstance(r, ChatHistorySearch):
        return f"logged_in={str(r.logged_in).lower()}, {len(r.matches)} past message(s)"
    return clip(f"{type(r).__name__}: {r}", 120)


def stop_reason_for(error: BaseException) -> tuple[str, str]:
    """Why the loop stopped early, and a short detail."""
    if is_content_filter(error):
        return "blocked_by_content_filter", "the model provider's content filter blocked the request or the reply"
    if isinstance(error, UsageLimitExceeded):
        return "usage_limit", clip(str(error).split(". ")[0], 160)  # "The next request would exceed the request_limit of 8"
    if isinstance(error, UnexpectedModelBehavior):
        return "gave_up_after_retries", clip(error, 160)
    if isinstance(error, asyncio.CancelledError):
        return "cancelled", "the request was cancelled (e.g. the shopper closed the page)"
    if isinstance(error, ModelHTTPError):
        return "model_error", f"{type(error).__name__} (HTTP {error.status_code})"
    return "error", type(error).__name__


def is_content_filter(error: BaseException) -> bool:
    """True when the provider's content filter stopped the run: Azure OpenAI (behind Portkey)
    refused the prompt (HTTP 400, code content_filter), or filtered the reply (ContentFilterError)."""
    if isinstance(error, ContentFilterError):
        return True
    body = getattr(error, "body", None)
    return isinstance(error, ModelHTTPError) and isinstance(body, dict) and body.get("code") == "content_filter"


def new_run_id() -> str:
    return uuid.uuid4().hex[:8]


def _is_output_tool(name: str) -> bool:
    return name.startswith(OUTPUT_TOOL_PREFIX)


# ---------- the capability that records the loop ----------

@dataclass
class AuditTrail(AbstractCapability[ShopDeps]):
    """Records each agent run into the audit trail. One fresh copy per run (for_run)."""

    _: KW_ONLY
    id: str | None = "audit_trail"
    run: str = ""
    seq: int = 0
    steps: int = 0
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    started: float = 0.0
    tools_used: list[str] = field(default_factory=list)

    async def for_run(self, ctx: RunContext[ShopDeps]) -> AuditTrail:
        return AuditTrail(run=(ctx.metadata or {}).get("run") or new_run_id())

    def _log(self, event: str, **fields: Any) -> None:
        self.seq += 1
        entry = {"time": now(), "run": self.run, "seq": self.seq, "event": event}
        entry.update({k: v for k, v in fields.items() if v is not None})
        append(entry)  # never raises

    def _safe(self, fn, *args) -> Any:
        """Run a summary helper; a bug in the audit code must never break the chat."""
        try:
            return fn(*args)
        except Exception as e:
            logger.warning("audit summary failed: %s", type(e).__name__)
            return f"(summary unavailable: {type(e).__name__})"

    def _ms(self, since: float) -> int:
        return round((time.perf_counter() - since) * 1000)

    # --- the whole run ---
    async def wrap_run(self, ctx: RunContext[ShopDeps], *, handler):
        self.started = time.perf_counter()
        self._safe(self._start, ctx)
        try:
            result = await handler()
        except BaseException as e:  # includes cancellation; always re-raised
            self._safe(lambda: self._end(*stop_reason_for(e)))
            raise
        self._safe(lambda: self._end("final_answer", None, **_reply_fields(result.output)))
        return result

    def _start(self, ctx: RunContext[ShopDeps]) -> None:
        deps, meta = ctx.deps, ctx.metadata or {}
        page = deps.page.page_type if deps else None
        if deps and deps.page.product:
            page += f" ({deps.page.product.product_id})"
        limits = ctx.usage_limits
        self._log(
            "run_start",
            customer=f"user:{deps.customer.user_id}" if deps and deps.customer else "guest",
            page=page,
            message_chars=meta.get("message_chars"),
            history_messages=meta.get("history_messages"),
            redacted_sensitive=meta.get("redacted_sensitive") or None,
            model=getattr(ctx.model, "model_name", None),
            limits={"model_requests": limits.request_limit, "tool_calls": limits.tool_calls_limit} if limits else None,
        )

    def _end(self, reason: str, detail: str | None = None, **fields: Any) -> None:
        self._log(
            "run_end",
            stop_reason=reason,
            detail=detail,
            model_requests=self.steps,
            tool_calls=self.tool_calls,
            tools_used=sorted(set(self.tools_used)) or None,
            tokens={"in": self.tokens_in, "out": self.tokens_out},
            ms=self._ms(self.started),
            **fields,
        )

    # --- one model call ---
    async def wrap_model_request(self, ctx: RunContext[ShopDeps], *, request_context, handler):
        self.steps += 1
        step, t0 = self.steps, time.perf_counter()
        try:
            response = await handler(request_context)
        except Exception as e:
            reason = "content_filter" if is_content_filter(e) else "error"
            self._log("model_step", step=step, stop_reason=reason, error=type(e).__name__, ms=self._ms(t0))
            raise
        self._safe(self._log_step, step, t0, response, request_context)
        return response

    def _log_step(self, step: int, t0: float, response, request_context) -> None:
        calls = [p.tool_name for p in response.parts if isinstance(p, ToolCallPart)]
        wrote_text = any(isinstance(p, TextPart) and p.content.strip() for p in response.parts)
        if any(not _is_output_tool(c) for c in calls):
            then = "run_tools"
        elif calls or wrote_text:
            then = "check_reply"
        elif response.finish_reason in ("content_filter", "length"):
            then = "stop"  # PydanticAI ends the run (no reply to retry)
        else:
            then = "retry"  # empty response
        usage = response.usage
        self.tokens_in += usage.input_tokens or 0
        self.tokens_out += usage.output_tokens or 0
        self._log(
            "model_step",
            step=step,
            stop_reason=response.finish_reason,
            asked_for=["(final answer)" if _is_output_tool(c) else c for c in calls] or None,
            then=then,
            tokens={"in": usage.input_tokens, "out": usage.output_tokens},
            ms=self._ms(t0),
        )
        # A tool name the agent doesn't have never reaches the tool hooks: PydanticAI sends it
        # straight back to the model. Record it here so every requested call shows up.
        params = request_context.model_request_parameters
        known = {t.name for t in [*params.function_tools, *params.output_tools]}
        for c in calls:
            if known and c not in known:
                self._log("tool", tool=c, ok=False, result="unknown tool, sent back to model")

    # --- one tool call ---
    async def wrap_tool_execute(self, ctx: RunContext[ShopDeps], *, call, tool_def, args, handler):
        t0 = time.perf_counter()
        self.tool_calls += 1
        self.tools_used.append(call.tool_name)
        try:
            result = await handler(args)
        except Exception as e:
            # ModelRetry (e.g. "several products match 'football tee'") goes back to the model.
            retry = isinstance(e, (ModelRetry, ToolRetryError))
            self._log(
                "tool",
                tool=call.tool_name,
                args=self._safe(short_args, args, call.tool_name),
                ok=False,
                result=("sent back to model: " if retry else f"error {type(e).__name__}: ")
                + self._safe(lambda: clip(_retry_text(e), 160)),
                ms=self._ms(t0),
            )
            raise
        self._log("tool", tool=call.tool_name, args=self._safe(short_args, args, call.tool_name), ok=True, result=self._safe(short_result, result), ms=self._ms(t0))
        return result

    async def wrap_tool_validate(self, ctx: RunContext[ShopDeps], *, call, tool_def, args, handler):
        try:
            return await handler(args)
        except (ValidationError, ModelRetry, ToolRetryError) as e:
            if not _is_output_tool(call.tool_name):
                self._log("tool", tool=call.tool_name, args=self._safe(short_args, args, call.tool_name), ok=False,
                          result="invalid arguments: " + self._safe(lambda: clip(_retry_text(e), 160)))
            raise

    # --- the reply: format check, then the grounding check (agent.check_grounding) ---
    async def wrap_output_validate(self, ctx: RunContext[ShopDeps], *, output_context, output, handler):
        try:
            return await handler(output)
        except (ValidationError, ModelRetry, ToolRetryError) as e:
            self._log("output_check", outcome="bad_format", reason=self._safe(lambda: clip(_retry_text(e), 160)))
            raise

    async def wrap_output_process(self, ctx: RunContext[ShopDeps], *, output_context, output, handler):
        if ctx.partial_output:
            return await handler(output)
        try:
            result = await handler(output)
        except ModelRetry as e:
            self._log("output_check", outcome="sent_back", reason=self._safe(lambda: clip(_retry_text(e), 200)))
            raise
        self._log("output_check", outcome="passed")
        return result


def _reply_fields(out: Any) -> dict:
    """What run_end keeps about the reply: its length, plus the product ids and page filters the
    model chose (written by the model, so clipped and masked like tool arguments)."""
    page_search = out.page_search.model_dump(exclude_defaults=True) if getattr(out, "page_search", None) else None
    return {
        "reply_chars": len(out.message),
        "product_ids": [clip(x, 100) for x in out.product_ids] or None,
        "page_search": short_args(page_search) if page_search else None,
    }


def _retry_text(e: BaseException) -> str:
    """The message of a ModelRetry / ToolRetryError / ValidationError, without boilerplate."""
    if isinstance(e, ValidationError):
        return "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:3])
    msg = e.message if isinstance(e, ModelRetry) else str(e)
    return msg.removeprefix("Please fix your reply: ")


# ---------- command line: print the latest runs ----------

def _print_latest(n: int) -> None:
    entries = read_entries()
    runs: list[str] = []
    for e in entries:
        if e.get("run") and e["run"] not in runs:
            runs.append(e["run"])
    keep = set(runs[-n:])
    first = next((i for i, e in enumerate(entries) if e.get("run") in keep), len(entries))
    print(f"{audit_path()}: {len(entries)} entries, {len(runs)} runs (showing the last {len(keep)})")
    for e in entries[first:]:
        if e.get("run") and e["run"] not in keep:
            continue
        ev = e["event"]
        detail = {k: v for k, v in e.items() if k not in ("time", "run", "seq", "event")}
        print(f"{e['time'][11:23]}  {e.get('run', '-'):<8}  {ev:<14}  {json.dumps(detail, ensure_ascii=False)}")


if __name__ == "__main__":
    _print_latest(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
