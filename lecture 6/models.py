from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DunkVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["dunk"] = "dunk"
    clip_label: str
    scores: dict[str, float] = Field(default_factory=dict)
    total: float
    play_by_play: str
    rationale: str
    frame_paths: list[str]


class FoulVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["foul"] = "foul"
    clip_label: str
    call: Literal["foul", "flop", "no_call"]
    confidence: float = Field(ge=0.0, le=1.0)
    play_by_play: str
    rationale: str
    frame_paths: list[str]
