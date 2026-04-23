"""Tests for pose estimation and smoothing."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from numpy.typing import NDArray

from baseball_swing_analyzer.pose import extract_pose, smooth_keypoints


def test_extract_pose_with_bbox() -> None:
    fake_keypoints = np.arange(34).reshape(17, 2).astype(np.float32)
    fake_scores = np.ones(17, dtype=np.float32)
    mock_model = MagicMock()
    mock_model.return_value = (fake_keypoints, fake_scores)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    bbox = (10, 20, 110, 220)

    with patch("baseball_swing_analyzer.pose._get_pose_model", return_value=mock_model):
        result = extract_pose(frame, bbox)

    assert result.shape == (17, 3)
    assert result.dtype == np.float32
    # Verify translation back to original coordinates
    np.testing.assert_array_equal(result[:, 0], fake_keypoints[:, 0] + 10)
    np.testing.assert_array_equal(result[:, 1], fake_keypoints[:, 1] + 20)
    np.testing.assert_array_equal(result[:, 2], fake_scores)


def test_extract_pose_without_bbox() -> None:
    fake_keypoints = np.zeros((17, 2), dtype=np.float32)
    fake_scores = np.zeros(17, dtype=np.float32)
    mock_model = MagicMock()
    mock_model.return_value = (fake_keypoints, fake_scores)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    with patch("baseball_swing_analyzer.pose._get_pose_model", return_value=mock_model):
        result = extract_pose(frame)

    assert result.shape == (17, 3)
    np.testing.assert_array_equal(result[:, 0], fake_keypoints[:, 0])
    np.testing.assert_array_equal(result[:, 1], fake_keypoints[:, 1])
    np.testing.assert_array_equal(result[:, 2], fake_scores)


def test_smooth_keypoints_shape_validation() -> None:
    bad = np.zeros((5, 18, 3), dtype=np.float32)
    with pytest.raises(ValueError):
        smooth_keypoints(bad)


def test_smooth_keypoints_small_time() -> None:
    # T < window >= 3 case
    kp = np.zeros((2, 17, 3), dtype=np.float32)
    smoothed = smooth_keypoints(kp, window=3)
    np.testing.assert_array_equal(smoothed, kp)


def test_smooth_keypoints_averaging() -> None:
    # Simple case: flat line should remain flat
    kp = np.ones((5, 17, 3), dtype=np.float32)
    smoothed = smooth_keypoints(kp, window=3)
    # Because of 'same' mode and constant line, output should still be ones
    np.testing.assert_allclose(smoothed, kp, atol=1e-5)
