"""Tests for multi-swing session analysis."""

import numpy as np
import pytest

from baseball_swing_analyzer.session import (
    build_session_report,
    dtw_distance,
    pairwise_dtw,
    session_consistency,
)


def test_dtw_identical():
    seq = np.zeros((10, 17, 3), dtype=float)
    assert dtw_distance(seq, seq) == pytest.approx(0.0, abs=1e-5)


def test_dtw_different():
    a = np.zeros((10, 17, 3), dtype=float)
    b = np.ones((10, 17, 3), dtype=float)
    d = dtw_distance(a, b)
    assert d > 0.0


def test_dtw_mismatched_shapes():
    a = np.zeros((10, 17, 3), dtype=float)
    b = np.zeros((8, 17, 3), dtype=float)
    d = dtw_distance(a, b)
    assert d >= 0.0


def test_session_consistency():
    reports = [
        {"stride_plant_frame": 10, "wrist_peak_velocity_px_s": 2000.0},
        {"stride_plant_frame": 12, "wrist_peak_velocity_px_s": 2100.0},
        {"stride_plant_frame": 11, "wrist_peak_velocity_px_s": 1900.0},
    ]
    summary = session_consistency(reports)
    assert "stride_plant_frame" in summary
    assert "wrist_peak_velocity_px_s" in summary
    assert summary["stride_plant_frame"]["mean"] == pytest.approx(11.0)
    assert summary["stride_plant_frame"]["std"] == pytest.approx(1.0)


def test_session_consistency_empty():
    assert session_consistency([]) == {}


def test_pairwise_dtw():
    swings = [
        np.zeros((10, 17, 3), dtype=float),
        np.ones((10, 17, 3), dtype=float),
        np.ones((10, 17, 3), dtype=float) * 2,
    ]
    matrix = pairwise_dtw(swings)
    assert matrix.shape == (3, 3)
    assert matrix[0, 0] == pytest.approx(0.0)
    assert matrix[0, 1] > 0.0
    assert matrix[0, 2] > matrix[0, 1]  # diverges further
    np.testing.assert_allclose(np.diag(matrix), 0.0)


def test_pairwise_dtw_single_swing():
    assert pairwise_dtw([np.zeros((5, 17, 3))]).shape == (1, 1)


def test_build_session_report():
    reports = [
        {
            "stride_plant_frame": 10,
            "wrist_peak_velocity_px_s": 2000.0,
            "flags": {
                "front_shoulder_closed_load": True,
                "hip_casting": False,
                "arm_slot_at_contact": "middle",
                "leg_action": "toe_tap",
                "finish_height": "high",
            },
        },
        {
            "stride_plant_frame": 12,
            "wrist_peak_velocity_px_s": 1900.0,
            "flags": {
                "front_shoulder_closed_load": True,
                "hip_casting": False,
                "arm_slot_at_contact": "middle",
                "leg_action": "leg_kick",
                "finish_height": "high",
            },
        },
    ]
    session = build_session_report(reports)
    assert session["swing_count"] == 2
    assert "metric_consistency" in session
    assert "flag_trends" in session
    assert "leg_action" in session["flag_trends"]
    assert session["flag_trends"]["front_shoulder_closed_load"]["true_pct"] == 100.0
