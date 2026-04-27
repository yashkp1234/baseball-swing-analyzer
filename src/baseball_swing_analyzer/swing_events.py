from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SwingEvents:
    load_start: int | None
    stride_start: int | None
    swing_start: int | None
    contact_frame: int | None
    follow_through_start: int | None
    confidence: float


def localize_swing_events(num_frames: int) -> SwingEvents:
    if num_frames < 8:
        return SwingEvents(None, None, None, None, None, 0.0)

    contact = max(2, int(num_frames * 0.55))
    return SwingEvents(
        load_start=0,
        stride_start=max(1, contact - 6),
        swing_start=max(2, contact - 3),
        contact_frame=contact,
        follow_through_start=min(num_frames - 1, contact + 1),
        confidence=0.4,
    )
