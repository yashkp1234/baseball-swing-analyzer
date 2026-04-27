from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BatCue:
    visible: bool
    confidence: float
    center_x: float | None = None
    center_y: float | None = None


def empty_bat_cue() -> BatCue:
    return BatCue(visible=False, confidence=0.0)
