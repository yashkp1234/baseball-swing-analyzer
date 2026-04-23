"""Tests for visualization helpers."""

import numpy as np
import pytest

from baseball_swing_analyzer.visualizer import (
    COCO_SKELETON,
    annotate_frame,
    draw_bbox,
    draw_skeleton,
)


def test_draw_skeleton() -> None:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    keypoints = np.zeros((17, 3), dtype=np.float32)
    keypoints[5] = (100.0, 100.0, 0.9)
    keypoints[7] = (120.0, 120.0, 0.9)
    keypoints[9] = (140.0, 140.0, 0.9)
    out = draw_skeleton(frame, keypoints)
    assert out.shape == frame.shape
    assert out.dtype == frame.dtype


def test_draw_bbox() -> None:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_bbox(frame, (50, 50, 150, 150))
    assert out.shape == frame.shape
    assert out.dtype == frame.dtype


def test_annotate_frame() -> None:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    keypoints = np.zeros((17, 3), dtype=np.float32)
    keypoints[5] = (100.0, 100.0, 0.9)
    keypoints[7] = (120.0, 120.0, 0.9)
    out = annotate_frame(frame, keypoints, (50, 50, 150, 150), "test_phase")
    assert out.shape == frame.shape
    assert out.dtype == frame.dtype


def test_draw_skeleton_skips_low_score() -> None:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    keypoints = np.zeros((17, 3), dtype=np.float32)
    keypoints[5] = (100.0, 100.0, 0.0)
    keypoints[7] = (120.0, 120.0, 0.0)
    out = draw_skeleton(frame, keypoints)
    # Should be identical to input because nothing is drawn
    np.testing.assert_array_equal(out, frame)
