"""Yale SOM course-explorer agent.

main.py calls run_agent(message) -> {"reply": str, "tools_used": [str]}.
Every run is appended to output/audit_trail.json.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, UsageLimits, capture_run_messages
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    NativeToolCallPart,
    NativeToolReturnPart,
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

import tools
from models import AgentResult, AuditEntry, SearchResult, ToolCallRecord

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"

for env_path in [ROOT / ".env", ROOT.parent / ".env"]:
    if env_path.exists():
        load_dotenv(env_path, override=False)

API_KEY = os.getenv("PORTKEY_API_KEY", "").strip()
if not API_KEY:
    raise RuntimeError(f"PORTKEY_API_KEY is missing from {ROOT / '.env'} or {ROOT.parent / '.env'}")

MODEL_NAME = "gpt-5.6-luna"

client = AsyncOpenAI(
    api_key=API_KEY,
    base_url="https://api.portkey.ai/v1",
    default_headers={"x-portkey-provider": "openai"},
)
provider = OpenAIProvider(openai_client=client)
# Responses API model: required for OpenAI's native web_search tool.
model = OpenAIResponsesModel(MODEL_NAME, provider=provider)

agent = Agent(
    model,
    instructions=PROMPT_PATH.read_text(encoding="utf-8"),
    capabilities=[tools.web_search],
)

USAGE_LIMITS = UsageLimits(request_limit=8)


@agent.tool_plain(name="search_courses")
def search_courses_tool(
    query: str = "",
    faculty: str = "",
    category: str = "",
    day: str = "",
    session: str = "",
    limit: int = tools.MAX_RESULTS,
) -> SearchResult:
    """Search the Yale SOM course catalog (data/yale_som_classes.json). All filters are optional.

    Args:
        query: Keywords; every word must appear in the title, course number, description, faculty, category, or type.
        faculty: Part of an instructor's name, e.g. "Simonsohn".
        category: Part of a category or type, e.g. "Finance", "Core", "Marketing", "elective", "EMBA".
        day: Meeting day as written in Daytimes, e.g. "M", "Tu", "W", "Th", "F" (or a full weekday name).
        session: "fall" (full term), "fall-1", or "fall-2".
        limit: Max rows to return (1-15).
    """
    return tools.search_courses(query=query, faculty=faculty, category=category, day=day, session=session, limit=limit)


# ---------------------------------------------------------------- audit trail

_audit_lock = threading.Lock()


def _short(value: Any, limit: int = 240) -> str:
    if isinstance(value, SearchResult):
        titles = "; ".join(f"{c.number} {c.title}" for c in value.courses[:5])
        more = " …" if value.returned > 5 else ""
        return f"{value.total_matches} match(es), returned {value.returned}: {titles}{more}"
    if not isinstance(value, str):
        try:
            value = json.dumps(value, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            value = str(value)
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _tool_label(name: str) -> str:
    return "web_search" if "web_search" in name or name == "web-search" else name


def _args(part: ToolCallPart | NativeToolCallPart) -> dict[str, Any] | str | None:
    try:
        return part.args_as_dict()
    except Exception:  # noqa: BLE001 - malformed args are still worth logging
        return part.args if isinstance(part.args, (str, dict)) else None


def _parse_messages(messages: list[ModelMessage]) -> tuple[list[str], list[ToolCallRecord], list[str], str | None]:
    thoughts: list[str] = []
    calls: dict[str, ToolCallRecord] = {}
    tools_used: list[str] = []
    finish_reason: str | None = None

    for msg in messages:
        if isinstance(msg, ModelResponse):
            finish_reason = msg.finish_reason or finish_reason
            has_calls = any(isinstance(p, (ToolCallPart, NativeToolCallPart)) for p in msg.parts)
            for part in msg.parts:
                if isinstance(part, ThinkingPart) and part.content.strip():
                    thoughts.append(_short(part.content, 600))
                elif isinstance(part, TextPart) and has_calls and part.content.strip():
                    thoughts.append(_short(part.content, 600))
                elif isinstance(part, (ToolCallPart, NativeToolCallPart)):
                    label = _tool_label(part.tool_name)
                    calls[part.tool_call_id] = ToolCallRecord(name=label, args=_args(part))
                    if label not in tools_used:
                        tools_used.append(label)
                elif isinstance(part, NativeToolReturnPart) and part.tool_call_id in calls:
                    calls[part.tool_call_id].result = _short(part.content)
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                    calls[part.tool_call_id].result = _short(part.content)
                elif isinstance(part, RetryPromptPart) and part.tool_call_id in calls:
                    calls[part.tool_call_id].result = "retry: " + _short(part.content)

    return thoughts, list(calls.values()), tools_used, finish_reason


def _append_audit(entry: AuditEntry) -> None:
    """Append one row; never wipe earlier rows (an unreadable file is left untouched)."""
    with _audit_lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        rows: list[Any] = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
            try:
                rows = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"[audit] {AUDIT_PATH} is not valid JSON; skipping write so nothing is lost.")
                return
            if not isinstance(rows, list):
                rows = [rows]
        rows.append(entry.model_dump(mode="json"))
        AUDIT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------- public API


def run_agent(message: str) -> dict:
    """Run one agent loop. FastAPI runs sync endpoints in a worker thread, so run_sync is safe here."""
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    reply = ""
    stop_reason = ""

    with capture_run_messages() as messages:
        try:
            result = agent.run_sync(message, usage_limits=USAGE_LIMITS)
            reply = str(result.output)
            stop_reason = "completed: model returned a final answer"
        except Exception as exc:  # noqa: BLE001 - surface a friendly reply, keep the audit row
            reply = "Sorry — the course agent hit an error and couldn't finish. Please try again."
            stop_reason = f"error: {type(exc).__name__}: {_short(str(exc), 200)}"

    thoughts, tool_calls, tools_used, finish_reason = _parse_messages(list(messages))
    if finish_reason:
        stop_reason += f" (finish_reason={finish_reason})"

    _append_audit(
        AuditEntry(
            time=started,
            user_message=message,
            thoughts=thoughts,
            tool_calls=tool_calls,
            tools_used=tools_used,
            reply=reply,
            stop_reason=stop_reason,
        )
    )
    return AgentResult(reply=reply, tools_used=tools_used).model_dump()
