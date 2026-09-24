from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import mss
from PIL import Image

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def capture_window_screenshot(region: str = "window") -> dict[str, str]:
    """Capture a screenshot of the current desktop window and save it to output/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
    path = OUTPUT_DIR / f"screen-{ts}.png"

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRA")
        image.save(path)

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "region": region,
        "path": str(path),
    }


if __name__ == "__main__":
    result = capture_window_screenshot()
    print(result)
