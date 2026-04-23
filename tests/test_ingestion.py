"""Tests for video ingestion utilities."""

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from baseball_swing_analyzer.ingestion import (
    VideoProperties,
    get_video_properties,
    is_blurry,
    load_video,
)


def _write_dummy_video(path: Path, width: int = 640, height: int = 480, fps: float = 30.0, frames: int = 5) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    try:
        for _ in range(frames):
            frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def test_load_video(tmp_path: Path) -> None:
    video_path = tmp_path / "dummy.mp4"
    _write_dummy_video(video_path)
    frames = list(load_video(video_path))
    assert len(frames) == 5
    for f in frames:
        assert f.shape == (480, 640, 3)


def test_get_video_properties(tmp_path: Path) -> None:
    video_path = tmp_path / "dummy.mp4"
    _write_dummy_video(video_path, width=640, height=480, fps=30.0, frames=10)
    props = get_video_properties(video_path)
    assert props == VideoProperties(width=640, height=480, fps=30.0, total_frames=10)


def test_is_blurry() -> None:
    # Create a perfectly sharp synthetic image (gradient)
    np.random.seed(0)
    sharp = (np.random.rand(100, 256, 3) * 255).astype(np.uint8)
    assert is_blurry(sharp, threshold=50.0) == False

    # Blurred image
    blurred = cv2.GaussianBlur(sharp, (21, 21), 5)
    assert is_blurry(blurred, threshold=1000.0) == True
