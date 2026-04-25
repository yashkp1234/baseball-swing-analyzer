"""Tests for pose estimation and smoothing."""

import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from numpy.typing import NDArray

from baseball_swing_analyzer.pose import extract_pose, pose_device, smooth_keypoints


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


def test_pose_device_falls_back_to_cpu_when_cuda_init_fails() -> None:
    fake_ort = MagicMock()
    fake_ort.get_available_providers.return_value = [
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    fake_ort.preload_dlls = MagicMock()
    cpu_model = MagicMock()
    cpu_model.det_model.session.get_providers.return_value = ["CPUExecutionProvider"]
    cpu_model.pose_model.session.get_providers.return_value = ["CPUExecutionProvider"]

    with patch("baseball_swing_analyzer.pose._pose_model", None), \
         patch("baseball_swing_analyzer.pose._pose_device", "cpu"), \
         patch("baseball_swing_analyzer.pose._ort_preloaded", False), \
         patch("baseball_swing_analyzer.pose._build_pose_model", side_effect=[RuntimeError("cuda broke"), cpu_model]), \
         patch.dict("os.environ", {"SWING_POSE_DEVICE": "auto"}, clear=False), \
         patch.dict(sys.modules, {"onnxruntime": fake_ort}):
        assert pose_device() == "cpu"


def test_pose_device_falls_back_to_cpu_when_cuda_inference_fails() -> None:
    fake_ort = MagicMock()
    fake_ort.get_available_providers.return_value = [
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    fake_ort.preload_dlls = MagicMock()

    cuda_model = MagicMock()
    cuda_model.det_model.session.get_providers.return_value = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    cuda_model.pose_model.session.get_providers.return_value = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    cuda_model.side_effect = RuntimeError("cudnn blew up")

    cpu_model = MagicMock()
    cpu_model.det_model.session.get_providers.return_value = ["CPUExecutionProvider"]
    cpu_model.pose_model.session.get_providers.return_value = ["CPUExecutionProvider"]
    cpu_model.return_value = (np.zeros((17, 2), dtype=np.float32), np.zeros(17, dtype=np.float32))

    with patch("baseball_swing_analyzer.pose._pose_model", None), \
         patch("baseball_swing_analyzer.pose._pose_device", "cpu"), \
         patch("baseball_swing_analyzer.pose._ort_preloaded", False), \
         patch("baseball_swing_analyzer.pose._build_pose_model", side_effect=[cuda_model, cpu_model]), \
         patch.dict("os.environ", {"SWING_POSE_DEVICE": "auto"}, clear=False), \
         patch.dict(sys.modules, {"onnxruntime": fake_ort}):
        assert pose_device() == "cpu"


def test_register_nvidia_dll_dirs_prepends_path(tmp_path) -> None:
    user_site = tmp_path / "usersite"
    cudnn_bin = user_site / "nvidia" / "cudnn" / "bin"
    cublas_bin = user_site / "nvidia" / "cublas" / "bin"
    cudnn_bin.mkdir(parents=True)
    cublas_bin.mkdir(parents=True)

    with patch("baseball_swing_analyzer.pose._dll_handles", []), \
         patch("baseball_swing_analyzer.pose.site.getusersitepackages", return_value=str(user_site)), \
         patch("baseball_swing_analyzer.pose.site.getsitepackages", return_value=[]), \
         patch("baseball_swing_analyzer.pose.os.add_dll_directory", side_effect=lambda path: path), \
         patch.dict("os.environ", {"PATH": "C:\\existing"}, clear=False):
        from baseball_swing_analyzer.pose import _register_nvidia_dll_dirs

        _register_nvidia_dll_dirs()

        path_parts = os.environ["PATH"].split(os.pathsep)
        assert str(cudnn_bin) in path_parts
        assert str(cublas_bin) in path_parts
        assert path_parts[-1] == "C:\\existing"
