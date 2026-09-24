from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import DunkVerdict, FoulVerdict
from video_tools import call_foul, describe_video, resolve_video_path, sample_frames, score_dunk

ROOT = Path(__file__).resolve().parent
for env_path in [ROOT / ".env", ROOT.parent / ".env"]:
    if env_path.exists():
        load_dotenv(env_path, override=False)

API_KEY = os.getenv("PORTKEY_API_KEY", "").strip()
if not API_KEY:
    raise RuntimeError(f"PORTKEY_API_KEY is missing from {ROOT / '.env'} or {ROOT.parent / '.env'}")

PROMPT_PATH = ROOT / "prompts" / "prompt.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else "You are a sports video judge."

client = AsyncOpenAI(
    api_key=API_KEY,
    base_url="https://api.portkey.ai/v1",
    default_headers={"x-portkey-provider": "openai"},
)
provider = OpenAIProvider(openai_client=client)
model = OpenAIChatModel("gpt-5.6-luna", provider=provider)

agent = Agent(
    model,
    deps_type=dict[str, Any],
    system_prompt=SYSTEM_PROMPT,
    output_type=DunkVerdict | FoulVerdict,
)


@agent.tool
async def sample_frames_tool(ctx: RunContext[dict[str, Any]], video_path: str, every_n_sec: float = 0.5, max_frames: int = 16) -> dict[str, Any]:
    on_tool = ctx.deps.get("on_tool")
    if on_tool:
        on_tool("sample_frames")
    return sample_frames(video_path, every_n_sec=every_n_sec, max_frames=max_frames)


@agent.tool
async def describe_video_tool(ctx: RunContext[dict[str, Any]], frame_paths: list[str], clip_label: str) -> dict[str, Any]:
    on_tool = ctx.deps.get("on_tool")
    if on_tool:
        on_tool("describe_video")
    return describe_video(frame_paths, clip_label)


@agent.tool
async def score_dunk_tool(ctx: RunContext[dict[str, Any]], frame_paths: list[str], description: str, clip_label: str) -> DunkVerdict:
    on_tool = ctx.deps.get("on_tool")
    if on_tool:
        on_tool("score_dunk")
    payload = score_dunk(frame_paths, description, clip_label)
    return DunkVerdict(**payload)


@agent.tool
async def call_foul_tool(ctx: RunContext[dict[str, Any]], frame_paths: list[str], description: str, clip_label: str) -> FoulVerdict:
    on_tool = ctx.deps.get("on_tool")
    if on_tool:
        on_tool("call_foul")
    payload = call_foul(frame_paths, description, clip_label)
    return FoulVerdict(**payload)


async def _run_agent(video_path: str, on_tool: Callable[[str], None] | None = None) -> dict[str, Any]:
    resolved = resolve_video_path(video_path)
    clip_label = resolved.name
    deps = {"on_tool": on_tool or (lambda _: None)}

    sampled = sample_frames(str(resolved), every_n_sec=0.5, max_frames=16)
    frame_paths = sampled["frame_paths"]
    if on_tool:
        on_tool("sample_frames")

    description = describe_video(frame_paths, clip_label)
    if on_tool:
        on_tool("describe_video")

    prompt = (
        f"Judge this sports clip: {clip_label}.\n"
        f"Sampled frames: {frame_paths}\n"
        f"Summary: {description}\n"
        "Always prefer observable evidence from the sampled frames and text description over filename guesses.\n"
        "Pick exactly one verdict: dunk OR foul. Use the available tool to produce the evidence-based verdict.\n"
        "If the clip is clearly a dunk, emit a DunkVerdict. If it is a foul/flop/no-call situation, emit a FoulVerdict.\n"
        "For foul decisions, give a real probability between 0 and 1, not 0.5 unless the evidence really supports it."
    )

    result = await agent.run(prompt, deps=deps)
    verdict = result.output

    if isinstance(verdict, DunkVerdict):
        if on_tool:
            on_tool("score_dunk")
        return {
            "verdict": verdict.model_dump(),
            "tool_events": [{"name": "sample_frames"}, {"name": "describe_video"}, {"name": "score_dunk"}],
        }

    if isinstance(verdict, FoulVerdict):
        if on_tool:
            on_tool("call_foul")
        return {
            "verdict": verdict.model_dump(),
            "tool_events": [{"name": "sample_frames"}, {"name": "describe_video"}, {"name": "call_foul"}],
        }

    fallback = (
        score_dunk(frame_paths, str(description), clip_label)
        if "dunk" in str(description).lower() or "dunk" in clip_label.lower()
        else call_foul(frame_paths, str(description), clip_label)
    )
    return {
        "verdict": fallback,
        "tool_events": [{"name": "sample_frames"}, {"name": "describe_video"}, {"name": "score_dunk" if "kind" in fallback and fallback.get("kind") == "dunk" else "call_foul"}],
    }


def run_agent(video_path: str, on_tool: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Public API expected by app.py.

    This wrapper is resilient to being called multiple times in the same Python process.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run_agent(video_path, on_tool=on_tool))

    result: dict[str, Any] | None = None
    error: BaseException | None = None

    def runner() -> None:
        nonlocal result, error
        try:
            result = asyncio.run(_run_agent(video_path, on_tool=on_tool))
        except BaseException as exc:  # pragma: no cover - defensive only
            error = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if error is not None:
        raise error
    if result is None:
        raise RuntimeError("Agent execution did not return a result.")
    return result


if __name__ == "__main__":
    sample = "videos/dunks/howard_1.mp4"
    print(run_agent(sample))
