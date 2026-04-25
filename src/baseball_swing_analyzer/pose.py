"""Pose estimation with RTMLib and temporal smoothing."""

import logging
import os
import site
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from rtmlib import Body

logger = logging.getLogger(__name__)

_pose_model: Body | None = None
_pose_device = "cpu"
_ort_preloaded = False
_dll_handles: list[object] = []


def _requested_device() -> str:
    requested = os.environ.get("SWING_POSE_DEVICE", "auto").strip().lower()
    return requested if requested in {"auto", "cpu", "cuda"} else "auto"


def _nvidia_bin_dirs() -> list[Path]:
    roots = [Path(site.getusersitepackages()), *(Path(p) for p in site.getsitepackages())]
    bin_dirs: list[Path] = []
    for root in roots:
        nvidia_dir = root / "nvidia"
        if not nvidia_dir.exists():
            continue
        for bin_dir in sorted(nvidia_dir.glob("*/bin")):
            if bin_dir not in bin_dirs:
                bin_dirs.append(bin_dir)
    return bin_dirs


def _preload_onnxruntime_dlls() -> None:
    global _ort_preloaded
    if _ort_preloaded:
        return

    try:
        import onnxruntime as ort
    except ImportError:
        return

    preload = os.environ.get("SWING_ORT_PRELOAD_DLLS", "1").strip().lower()
    if preload in {"0", "false", "no"} or not hasattr(ort, "preload_dlls"):
        _ort_preloaded = True
        return

    directory = os.environ.get("SWING_ORT_DLL_DIRECTORY")
    try:
        _register_nvidia_dll_dirs()
        ort.preload_dlls(directory=directory if directory is not None else "")
        logger.info("Preloaded ONNX Runtime CUDA/cuDNN DLLs")
    except Exception as exc:
        logger.warning("ONNX Runtime DLL preload failed: %s", exc)
    finally:
        _ort_preloaded = True


def _build_pose_model(device: str) -> Body:
    return Body(mode="lightweight", backend="onnxruntime", device=device)


def _register_nvidia_dll_dirs() -> None:
    bin_dirs = _nvidia_bin_dirs()
    if not bin_dirs:
        return

    current_path = os.environ.get("PATH", "")
    path_parts = [part for part in current_path.split(os.pathsep) if part]
    new_parts = [str(bin_dir) for bin_dir in bin_dirs if str(bin_dir) not in path_parts]
    if new_parts:
        os.environ["PATH"] = os.pathsep.join([*new_parts, *path_parts])

    if not hasattr(os, "add_dll_directory"):
        return

    for bin_dir in bin_dirs:
        try:
            _dll_handles.append(os.add_dll_directory(str(bin_dir)))
        except OSError:
            continue


def _model_uses_cuda(model: Body) -> bool:
    sessions = []
    for attr in ("det_model", "pose_model"):
        component = getattr(model, attr, None)
        session = getattr(component, "session", None)
        if session is not None:
            sessions.append(session)

    if not sessions:
        return False

    return all("CUDAExecutionProvider" in session.get_providers() for session in sessions)


def _validate_pose_runtime(model: Body) -> None:
    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
    model(dummy)


def _get_pose_model() -> Body:
    global _pose_model, _pose_device
    if _pose_model is None:
        requested = _requested_device()

        if requested in {"auto", "cuda"}:
            try:
                import onnxruntime as ort

                _preload_onnxruntime_dlls()
                providers = ort.get_available_providers()
                if "CUDAExecutionProvider" in providers:
                    candidate = _build_pose_model("cuda")
                    if _model_uses_cuda(candidate):
                        _validate_pose_runtime(candidate)
                        _pose_model = candidate
                        _pose_device = "cuda"
                    elif requested == "cuda":
                        raise RuntimeError("CUDAExecutionProvider fell back to CPU")
                elif requested == "cuda":
                    raise RuntimeError("CUDAExecutionProvider is not available")
            except Exception as exc:
                if requested == "cuda":
                    raise RuntimeError(f"Failed to initialize CUDA pose model: {exc}") from exc
                logger.warning("CUDA pose init failed, falling back to CPU: %s", exc)
                _pose_model = None

        if _pose_model is None:
            _pose_model = _build_pose_model("cpu")
            _pose_device = "cpu"

        logger.info("Pose model initialized on %s", _pose_device)

    return _pose_model


def pose_device() -> str:
    _get_pose_model()
    return _pose_device


def _select_dominant(keypoints: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Select single person with highest average score.

    Handles multi-person output from rtmlib Body:
      - keypoints (N, K, 2) and scores (N, K) when N > 1
      - keypoints (K, 2) and scores (K,) when N == 1
      - empty arrays when N == 0
    """
    # Empty (no detections)
    if keypoints.size == 0 or scores.size == 0:
        empty_kp = np.zeros((17, 2), dtype=np.float32)
        empty_s = np.zeros(17, dtype=np.float32)
        return empty_kp, empty_s

    if keypoints.ndim == 2 and scores.ndim == 1:
        return keypoints.astype(np.float32), scores.astype(np.float32)

    if keypoints.ndim == 3 and scores.ndim == 2:
        mean_scores = scores.mean(axis=1)
        dominant = int(np.argmax(mean_scores))
        return keypoints[dominant].astype(np.float32), scores[dominant].astype(np.float32)

    raise ValueError(
        f"Unexpected keypoints/scores shape: {keypoints.shape} / {scores.shape}"
    )


def extract_pose(
    frame: NDArray[np.uint8],
    bbox: tuple[int, int, int, int] | None = None,
) -> NDArray[np.float32]:
    """Estimate COCO body keypoints for a single frame.

    Returns an array of shape ``(17, 3)`` where each row is ``(x, y, score)``.
    """
    model = _get_pose_model()

    if bbox is not None:
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        crop = frame[y1:y2, x1:x2]
        keypoints, scores = model(crop)
        keypoints, scores = _select_dominant(keypoints, scores)
        keypoints = keypoints.copy()
        keypoints[:, 0] += x1
        keypoints[:, 1] += y1
    else:
        keypoints, scores = model(frame)
        keypoints, scores = _select_dominant(keypoints, scores)

    out = np.zeros((17, 3), dtype=np.float32)
    out[:, :2] = keypoints.astype(np.float32)
    out[:, 2] = scores.astype(np.float32)
    return out


def smooth_keypoints(keypoints: NDArray[np.float32], window: int = 3) -> NDArray[np.float32]:
    """Apply a simple moving-average filter across the time axis.

    *keypoints* should have shape ``(T, 17, 3)``.
    """
    if keypoints.ndim != 3 or keypoints.shape[1] != 17 or keypoints.shape[2] != 3:
        raise ValueError("keypoints must have shape (T, 17, 3)")

    if keypoints.shape[0] < window:
        return keypoints.copy()

    half = window // 2
    smoothed = np.zeros_like(keypoints)
    for t in range(keypoints.shape[0]):
        start = max(0, t - half)
        end = min(keypoints.shape[0], t + half + 1)
        smoothed[t] = keypoints[start:end].mean(axis=0)
    return smoothed
