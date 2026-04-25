"""Tests for the main analyzer pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from baseball_swing_analyzer.analyzer import _analysis_budget, _subsample_indices, analyze_swing


def test_analyze_swing_on_dummy_video(tmp_path: Path) -> None:
    video = Path("tests/fixtures/swing_dummy.mp4")
    out_dir = tmp_path / "output"

    fake_bbox = (200, 100, 440, 380)
    fake_kpts = np.zeros((60, 17, 3), dtype=np.float32)
    # Simulate right-wrist swing arc
    fake_kpts[:, 10, 0] = np.linspace(200, 400, 60)
    fake_kpts[:, 10, 1] = 300 - 100 * np.sin(np.linspace(0, np.pi, 60))
    fake_kpts[:, 10, 2] = 0.95

    call_idx = {"n": 0}

    def _fake_pose(frame, bbox=None):
        idx = call_idx["n"]
        call_idx["n"] += 1
        return fake_kpts[idx % 60]

    with patch("baseball_swing_analyzer.analyzer.detect_person", return_value=fake_bbox), \
         patch("baseball_swing_analyzer.analyzer.extract_pose", side_effect=_fake_pose), \
         patch("baseball_swing_analyzer.analyzer.get_video_properties", return_value=MagicMock(width=640, height=480, fps=30.0, total_frames=60)), \
         patch("baseball_swing_analyzer.analyzer.load_video", return_value=(np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(60))):
        result = analyze_swing(video, output_dir=out_dir, annotate=True)

    assert isinstance(result, dict)
    assert "phase_durations" in result
    assert "contact_frame" in result
    assert (out_dir / "annotated.mp4").exists()


def test_analysis_budget_uses_gpu_settings() -> None:
    with patch("baseball_swing_analyzer.analyzer.pose_device", return_value="cuda"), \
         patch.dict("os.environ", {}, clear=False):
        target_fps, max_frames = _analysis_budget()

    assert target_fps == 15.0
    assert max_frames == 48


def test_subsample_indices_respect_max_frames() -> None:
    indices = _subsample_indices(300, 30.0, 15.0, 48)
    assert len(indices) == 48
