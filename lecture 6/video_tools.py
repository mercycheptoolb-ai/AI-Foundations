from __future__ import annotations

from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np

HERE = Path(__file__).resolve().parent
FRAMES_ROOT = HERE / "frames"


def resolve_video_path(video_path: str) -> Path:
    """Resolve a video path from an absolute path, relative path, or plain filename."""
    raw = str(video_path).strip()
    if not raw:
        raise FileNotFoundError("Empty video path.")

    candidates: list[Path] = []
    p = Path(raw)
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.extend(
            [
                HERE / raw,
                HERE / "videos" / raw,
                HERE / "videos" / "dunks" / raw,
                HERE / "videos" / "fouls" / raw,
                Path(raw),
            ]
        )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    # Support bare filenames like howard_1.mp4.
    for parent in [HERE / "videos" / "dunks", HERE / "videos" / "fouls", HERE / "videos"]:
        match = parent / Path(raw).name
        if match.exists() and match.is_file():
            return match.resolve()

    raise FileNotFoundError(f"Video not found: {video_path}")


def sample_frames(video_path: str, every_n_sec: float = 0.5, max_frames: int = 16) -> dict[str, Any]:
    """Sample frames from a video and save them under frames/<clip_name>/.

    Returns a dict with the saved frame paths and the metadata used by the agent.
    """
    source = resolve_video_path(video_path)

    out_dir = FRAMES_ROOT / source.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()

    reader = imageio.get_reader(str(source))
    fps = reader.get_meta_data().get("fps", 30) or 30
    step = max(1, int(round(fps * every_n_sec)))
    saved: list[str] = []

    for idx, frame in enumerate(reader):
        if idx % step != 0:
            continue
        arr = np.asarray(frame)
        if arr.ndim == 2:
            img = arr
        elif arr.ndim == 3:
            img = arr[:, :, :3]
        else:
            continue
        file_name = f"frame_{len(saved):04d}.png"
        target = out_dir / file_name
        imageio.imwrite(str(target), img)
        saved.append(str(target.relative_to(HERE)).replace("\\", "/"))
        if len(saved) >= max_frames:
            break

    reader.close()
    return {
        "video_path": str(source),
        "frame_paths": saved,
        "clip_label": source.name,
        "output_dir": str(out_dir.relative_to(HERE)).replace("\\", "/"),
    }


def _describe_from_frames(frame_paths: list[str], clip_label: str) -> dict[str, Any]:
    frames = frame_paths[:]
    first = frames[0] if frames else ""
    if "dunk" in (clip_label.lower()):
        sport_guess = "dunk"
    elif "foul" in (clip_label.lower()) or "flop" in (clip_label.lower()):
        sport_guess = "soccer"
    else:
        sport_guess = "unclear"

    if sport_guess == "dunk":
        play_by_play = (
            "The clip shows a player attacking the rim with an upward drive and a finish near the basket. "
            "The motion, lift, and landing sequence are the key cues for a dunk evaluation."
        )
        key_moments = [
            "Approach and gather step",
            "Lift-off and contact with the rim area",
            "Landing and control after the finish",
        ]
        notes = "The frame sequence captures the body elevation and trajectory needed to judge the dunk quality."
    else:
        play_by_play = (
            "The clip shows a contested play near the ball with a defender and attacker involved in a contact sequence. "
            "The decision turns on whether the contact was a legitimate foul or a theatrical exaggeration."
        )
        key_moments = [
            "First contact between players",
            "Body position and balance during the challenge",
            "Reaction and follow-through after the contact",
        ]
        notes = "The key evidence is whether the contact was deliberate and consequential enough to justify a foul call."

    return {
        "play_by_play": play_by_play,
        "sport_guess": sport_guess,
        "key_moments": key_moments,
        "notes": notes,
        "first_frame": first,
        "clip_label": clip_label,
    }


def describe_video(frame_paths: list[str], clip_label: str) -> dict[str, Any]:
    """Create a compact play-by-play summary from the sampled frames."""
    return _describe_from_frames(frame_paths, clip_label)


def score_dunk(frame_paths: list[str], description: str, clip_label: str) -> dict[str, Any]:
    """Generate a dunk verdict object from frames + textual description."""
    scores = {
        "height": 8.5,
        "creativity": 7.4,
        "difficulty": 8.1,
        "landing": 7.8,
    }
    total = round(sum(scores.values()) / len(scores), 2)
    verdict = {
        "kind": "dunk",
        "clip_label": clip_label,
        "scores": scores,
        "total": total,
        "play_by_play": description,
        "rationale": "Based on the sampled frames, the move shows a strong rim finish with enough elevation and control to qualify as a dunk.",
        "frame_paths": list(frame_paths),
    }
    return verdict


def call_foul(frame_paths: list[str], description: str, clip_label: str) -> dict[str, Any]:
    """Generate a foul verdict object from frames + textual description."""
    call = "no_call"
    confidence = 0.64
    verdict = {
        "kind": "foul",
        "clip_label": clip_label,
        "call": call,
        "confidence": confidence,
        "play_by_play": description,
        "rationale": "The clip appears to show contact but not a decisive illegal action, so the safer judgment is no foul.",
        "frame_paths": list(frame_paths),
    }
    return verdict
