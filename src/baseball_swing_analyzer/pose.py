"""Pose estimation with RTMLib and temporal smoothing."""

import numpy as np
from numpy.typing import NDArray

from rtmlib import Body

_pose_model: Body | None = None


def _get_pose_model() -> Body:
    global _pose_model
    if _pose_model is None:
        _pose_model = Body(mode='balanced')
    return _pose_model


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
