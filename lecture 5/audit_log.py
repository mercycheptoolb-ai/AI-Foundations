from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
AUDIT_LOG_PATH = OUTPUT_DIR / "audit_log.json"


def append_turn(prompt: str, reply: str, tool_events: list[dict[str, str]] | None, last_shot: dict[str, str] | None) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
        "reply": reply,
        "tool_events": tool_events or [],
        "last_shot": last_shot,
    }

    existing: list[dict[str, Any]] = []
    if AUDIT_LOG_PATH.exists():
        try:
            existing = json.loads(AUDIT_LOG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []

    existing.append(entry)
    AUDIT_LOG_PATH.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
