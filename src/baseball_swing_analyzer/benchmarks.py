from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkClip:
    id: str
    path: str
    expected_swing_count: int
    expected_rejections: list[str] | None = None
    contact_frame_min_ratio: float | None = None
    contact_frame_max_ratio: float | None = None


def load_benchmarks(manifest_path: Path) -> list[BenchmarkClip]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [BenchmarkClip(**clip) for clip in payload["clips"]]
