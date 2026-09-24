from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from audit_log import append_turn
from screen_tools import capture_window_screenshot

ROOT = Path(__file__).resolve().parent
ROOT_ENV = ROOT.parent / ".env"
load_dotenv(ROOT_ENV)

API_KEY = os.getenv("PORTKEY_API_KEY")
if not API_KEY:
    raise RuntimeError(f"PORTKEY_API_KEY is missing from {ROOT_ENV}")

PROMPT_PATH = ROOT / "prompts" / "prompt.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else "You are a helpful screen-aware assistant."

client = AsyncOpenAI(
    api_key=API_KEY,
    base_url="https://api.portkey.ai/v1",
    default_headers={"x-portkey-provider": "openai"},
)
provider = OpenAIProvider(openai_client=client)
model = OpenAIChatModel("gpt-5.6-luna", provider=provider)

message_history: list[dict[str, Any]] = []


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_history(role: str, content: str, **extra: Any) -> None:
    message_history.append({"role": role, "content": content, **extra})
    max_items = 20
    if len(message_history) > max_items:
        del message_history[:-max_items]


def _history_context() -> str:
    if not message_history:
        return ""
    context_parts: list[str] = []
    for item in message_history:
        if item.get("image_path"):
            context_parts.append(f"[{item['role']}] image_path={item['image_path']}")
        text = item.get("content")
        if text:
            context_parts.append(f"[{item['role']}] {text}")
    if not context_parts:
        return ""
    return "Earlier in this session:\n" + "\n".join(context_parts) + "\n\n"


agent = Agent(model, system_prompt=SYSTEM_PROMPT, output_type=str)


@agent.tool
async def look_at_screen(ctx: RunContext[None], reason: str | None = None) -> dict[str, Any]:
    """Capture the current screen so the agent can answer questions about what is visible."""
    shot = capture_window_screenshot(region="window")
    _append_history(
        "tool",
        reason or "The user asked about what is visible on screen.",
        image_path=shot["path"],
        captured_at=shot["captured_at"],
        region=shot["region"],
    )
    return shot


async def _run(prompt: str) -> dict[str, Any]:
    history_context = _history_context()
    user_prompt = f"{history_context}User message: {prompt}".strip()
    result = await agent.run(user_prompt)

    screenshot_event = None
    if message_history:
        for item in reversed(message_history):
            if item.get("image_path"):
                screenshot_event = {
                    "captured_at": item.get("captured_at", _iso_now()),
                    "region": item.get("region", "window"),
                    "path": item["image_path"],
                }
                break

    tool_events: list[dict[str, str]] = []
    if screenshot_event:
        tool_events.append({"name": "Look at screen"})

    final_reply = str(result.output)
    _append_history("assistant", final_reply, tool_events=tool_events, last_shot=screenshot_event)

    if screenshot_event:
        last_shot = {
            "captured_at": screenshot_event["captured_at"],
            "region": screenshot_event["region"],
        }
    else:
        last_shot = None

    append_turn(prompt, final_reply, tool_events, last_shot)

    return {
        "text": final_reply,
        "tool_events": tool_events,
        "last_shot": last_shot,
    }


def run_agent(prompt: str) -> dict[str, Any]:
    return asyncio.run(_run(prompt))


if __name__ == "__main__":
    print(json.dumps(run_agent("Describe what is on screen and what I should do next."), indent=2))
