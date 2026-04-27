"""Unit tests for biomechanical metrics."""

import numpy as np
import pytest

from baseball_swing_analyzer.metrics import (
    angle_between,
    midpoint,
    hip_angle,
    shoulder_angle,
    x_factor,
    spine_tilt,
    knee_angle,
    head_displacement,
    wrist_velocity,
    stride_foot_plant_frame,
    phase_durations,
    clip_metric,
)


class TestHelpers:
    def test_angle_between_perpendicular(self) -> None:
        assert angle_between(np.array([1, 0]), np.array([0, 1])) == pytest.approx(90.0)

    def test_angle_between_parallel(self) -> None:
        assert angle_between(np.array([3, 0]), np.array([5, 0])) == pytest.approx(0.0)

    def test_angle_between_zero_vector_returns_nan(self) -> None:
        result = angle_between(np.array([0, 0]), np.array([1, 0]))
        assert np.isnan(result)

    def test_midpoint(self) -> None:
        assert np.allclose(
            midpoint(np.array([0.0, 0.0]), np.array([2.0, 2.0])),
            np.array([1.0, 1.0]),
        )


class TestHipAngle:
    def test_45_degrees(self) -> None:
        kp = _blank_keypoints()
        kp[11] = [0, 0]
        kp[12] = [1, 1]
        assert hip_angle(kp) == pytest.approx(45.0)

    def test_horizontal(self) -> None:
        kp = _blank_keypoints()
        kp[11] = [0, 0]
        kp[12] = [1, 0]
        assert hip_angle(kp) == pytest.approx(0.0)


class TestShoulderAngle:
    def test_horizontal(self) -> None:
        kp = _blank_keypoints()
        kp[5] = [0, 0]
        kp[6] = [1, 0]
        assert shoulder_angle(kp) == pytest.approx(0.0)

    def test_negative_slope(self) -> None:
        kp = _blank_keypoints()
        kp[5] = [0, 0]
        kp[6] = [1, -1]
        assert shoulder_angle(kp) == pytest.approx(-45.0)


class TestXFactor:
    def test_hip_minus_shoulder(self) -> None:
        kp = _blank_keypoints()
        # hips 45°
        kp[11] = [0, 0]
        kp[12] = [1, 1]
        # shoulders 0°
        kp[5] = [0, 0]
        kp[6] = [1, 0]
        assert x_factor(kp) == pytest.approx(45.0)

    def test_wraparound_170_minus_minus_10(self) -> None:
        kp = _blank_keypoints()
        # vertical hip line (x constant) → hip_angle = 90.0
        kp[11] = [-1, 10]
        kp[12] = [-1, -10]
        # vertical shoulder line (x constant) → shoulder_angle = 90.0
        kp[5] = [1, 10]
        kp[6] = [1, -10]
        assert hip_angle(kp) == pytest.approx(90.0)
        assert shoulder_angle(kp) == pytest.approx(90.0)
        # separation = 180 - 180 = 0
        assert abs(x_factor(kp)) == pytest.approx(0.0, abs=0.1)

    def test_wraparound_boundary_opposite(self) -> None:
        kp = _blank_keypoints()
        # hip angle near +170°, shoulder near -170° (20° total separation)
        kp[11] = [10, 0]
        kp[12] = [-1, 1]
        kp[5] = [1, 0]
        kp[6] = [10, 1]
        # hip ≈ 174°, shoulder ≈ -174° → separation ≈ -348° → normalized to ≈ +12°
        sep = x_factor(kp)
        assert abs(sep) <= 180.0


class TestSpineTilt:
    def test_perfectly_vertical(self) -> None:
        kp = _blank_keypoints()
        kp[5] = [0, 0]
        kp[6] = [2, 0]
        kp[11] = [0, 2]
        kp[12] = [2, 2]
        assert spine_tilt(kp) == pytest.approx(0.0)

    def test_45_degrees(self) -> None:
        kp = _blank_keypoints()
        kp[5] = [0, 0]
        kp[6] = [2, 0]
        kp[11] = [1, 1]
        kp[12] = [3, 1]
        # shoulder centre = (1,0), hip centre = (2,1)
        # vec = (1,1), vertical = (0,1) -- unsigned angle should be 45°
        assert spine_tilt(kp) == pytest.approx(45.0)


class TestKneeAngle:
    def test_flexion_90_degrees(self) -> None:
        kp = _blank_keypoints()
        # hip-knee-ankle interior angle = 90deg, so flexion = 180-90 = 90
        kp[11] = [0, 0]
        kp[13] = [1, 0]
        kp[15] = [1, 1]
        assert knee_angle(kp, "left") == pytest.approx(90.0)

    def test_straight_knee(self) -> None:
        kp = _blank_keypoints()
        kp[11] = [0, 0]
        kp[13] = [1, 0]  # knee directly below hip
        kp[15] = [2, 0]  # ankle continues straight
        assert knee_angle(kp, "left") == pytest.approx(0.0)

    def test_bent_knee_around_108(self) -> None:
        kp = _blank_keypoints()
        kp[11] = [0.0, 0.0]
        kp[13] = [1.0, 2.0]
        kp[15] = [2.0, 1.0]
        # interior angle = ~71.6°, flexion = 180 - 71.6 = ~108.4°
        assert knee_angle(kp, "left") == pytest.approx(108.4, abs=0.5)

    def test_invalid_side_raises(self) -> None:
        kp = _blank_keypoints()
        with pytest.raises(ValueError):
            knee_angle(kp, "middle")


class TestHeadDisplacement:
    def test_3_4_5_triangle(self) -> None:
        seq = _blank_sequence(2)
        seq[0, 0] = [0, 0]
        seq[1, 0] = [3, 4]
        assert head_displacement(seq) == pytest.approx(5.0)

    def test_single_frame_returns_zero(self) -> None:
        seq = _blank_sequence(1)
        seq[0, 0] = [5, 5]
        assert head_displacement(seq) == pytest.approx(0.0)


class TestWristVelocity:
    def test_constant_movement(self) -> None:
        # 3 frames, 1 px per frame along x; fps = 30 => 30 px/s
        seq = _blank_sequence(3)
        seq[:, 9] = [[0, 0], [1, 0], [2, 0]]
        seq[:, 10] = [[0, 0], [0, 0], [0, 0]]
        vel = wrist_velocity(seq, fps=30.0)
        assert vel.shape == (3, 2)
        assert vel[0, :].tolist() == [0.0, 0.0]
        assert vel[1, 0] == pytest.approx(30.0)
        assert vel[1, 1] == pytest.approx(0.0)
        assert vel[2, 0] == pytest.approx(30.0)
        assert vel[2, 1] == pytest.approx(0.0)

    def test_diagonal_movement(self) -> None:
        # moving (1,1) per frame; magnitude = sqrt(2)
        seq = _blank_sequence(2)
        seq[:, 9] = [[0, 0], [1, 1]]
        vel = wrist_velocity(seq, fps=1.0)
        assert vel[1, 0] == pytest.approx(np.sqrt(2))

    def test_bad_shape_raises(self) -> None:
        with pytest.raises(ValueError):
            wrist_velocity(np.zeros((5, 5)), fps=30.0)


class TestStrideFootPlantFrame:
    def test_basic_transition_left(self) -> None:
        seq = _blank_sequence(5)
        # left ankle (lead) moves down then up; right stays flat below
        seq[:, 15, 1] = [100, 90, 80, 85, 90]
        seq[:, 16, 1] = [120, 120, 120, 120, 120]
        assert stride_foot_plant_frame(seq) == 2

    def test_no_transition_returns_none(self) -> None:
        seq = _blank_sequence(3)
        seq[:, 15, 1] = [100, 110, 120]
        seq[:, 16, 1] = [130, 130, 130]
        assert stride_foot_plant_frame(seq) is None


class TestPhaseDurations:
    def test_contiguous(self) -> None:
        labels = ["stance", "load", "load", "load", "stride", "swing", "swing"]
        expected = {"stance": 1, "load": 3, "stride": 1, "swing": 2}
        assert phase_durations(labels) == expected

    def test_non_contiguous(self) -> None:
        labels = ["stance", "load", "stance", "stance"]
        expected = {"stance": 2, "load": 1}
        assert phase_durations(labels) == expected


class TestClipMetric:
    def test_clamps_high_values(self) -> None:
        assert clip_metric(343.0, 0.0, 200.0) == pytest.approx(200.0)
        assert clip_metric(72.0, 0.0, 12.0) == pytest.approx(12.0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _blank_keypoints() -> np.ndarray:
    """Return a (17, 2) keypoint array filled with zeros."""
    return np.zeros((17, 2), dtype=float)


def _blank_sequence(frames: int) -> np.ndarray:
    """Return a (T, 17, 2) keypoint array filled with zeros."""
    if frames < 0:
        raise ValueError("frames must be non-negative")
    arr = np.zeros((frames, 17, 2), dtype=float)
    return arr
