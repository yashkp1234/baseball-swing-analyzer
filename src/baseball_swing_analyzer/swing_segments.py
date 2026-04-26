"""Detect active swing windows inside longer pose sequences."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

from .metrics import wrist_velocity


@dataclass(frozen=True)
class SwingSegment:
    start_frame: int
    end_frame: int
    contact_frame: int
    duration_s: float
    confidence: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def detect_swing_segments(
    keypoints_seq: NDArray[np.floating],
    fps: float,
    min_duration_s: float = 0.25,
    merge_gap_s: float = 0.18,
    pre_context_s: float = 0.55,
    post_context_s: float = 0.25,
) -> list[SwingSegment]:
    """Return active swing windows based on hand/wrist speed."""
    seq = np.asarray(keypoints_seq, dtype=float)
    if seq.ndim != 3 or seq.shape[0] < 4:
        return []

    speeds = wrist_velocity(seq, fps).max(axis=1)
    peak = float(speeds.max(initial=0.0))
    if peak <= 0:
        return []

    nonzero = speeds[speeds > 0]
    if nonzero.size == 0:
        return []
    threshold = max(float(np.percentile(nonzero, 25)), float(np.median(nonzero)) * 0.5)
    active = speeds >= threshold
    runs = _merge_runs(_active_runs(active), max_gap=max(1, round(merge_gap_s * fps)))

    pre_context = max(1, round(pre_context_s * fps))
    post_context = max(1, round(post_context_s * fps))
    min_len = max(3, round(min_duration_s * fps))
    average = float(np.mean(speeds))
    deviation = float(np.std(speeds))
    segments: list[SwingSegment] = []

    for start, end in runs:
        if end - start + 1 < min_len:
            continue
        window_start = max(0, start - pre_context)
        window_end = min(len(speeds) - 1, end + post_context)
        contact = int(window_start + np.argmax(speeds[window_start:window_end + 1]))
        confidence = min(1.0, peak / (average + deviation + 1e-6) / 2.0)
        segments.append(
            SwingSegment(
                start_frame=window_start,
                end_frame=window_end,
                contact_frame=contact,
                duration_s=round((window_end - window_start + 1) / fps, 3),
                confidence=round(confidence, 3),
            )
        )

    return segments


def best_swing_segment(segments: list[SwingSegment]) -> SwingSegment | None:
    if not segments:
        return None
    return max(segments, key=lambda segment: (segment.confidence, segment.duration_s))


def _active_runs(active: NDArray[np.bool_]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    index = 0
    while index < len(active):
        if not bool(active[index]):
            index += 1
            continue
        start = index
        while index + 1 < len(active) and bool(active[index + 1]):
            index += 1
        runs.append((start, index))
        index += 1
    return runs


def _merge_runs(runs: list[tuple[int, int]], max_gap: int) -> list[tuple[int, int]]:
    if not runs:
        return []
    merged = [runs[0]]
    for start, end in runs[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= max_gap:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged
