"""Pose estimation with RTMLib and temporal smoothing."""

import numpy as np
from numpy.typing import NDArray

from rtmlib import Wholebody

_pose_model: Wholebody | None = None


def _get_pose_model() -> Wholebody:
    global _pose_model
    if _pose_model is None:
        _pose_model = Wholebody()
    return _pose_model


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
        keypoints = keypoints.copy()
        scores = scores.copy()
        keypoints[:, 0] += x1
        keypoints[:, 1] += y1
    else:
        keypoints, scores = model(frame)

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
