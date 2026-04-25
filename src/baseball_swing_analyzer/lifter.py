"""2D-to-3D keypoint lifting using MotionBERT or heuristic fallback.

MotionBERT (https://github.com/Walter0806/Motion-BERT) provides a pretrained
model that lifts 2D COCO keypoints to 3D in camera-root coordinates.

This module:
1. Tries to load MotionBERT if available (requires torch).
2. Falls back to heuristic depth estimation if not.
3. Returns (T, 17, 3) float32 array in meters with camera-relative Z.

The heuristic fallback uses proportional body segments to approximate depth,
which is good enough for a stick-figure 3D visualization but not for
quantitative 3D analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

_HAS_MOTIONBERT = False
_MOTIONBERT_MODEL = None

COCO_SKELETON = [
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]

COCO_NOSE = 0
COCO_LSHOULDER = 5
COCO_RSHOULDER = 6
COCO_LHIP = 11
COCO_RHIP = 12


def _try_load_motionbert():
    global _HAS_MOTIONBERT, _MOTIONBERT_MODEL
    try:
        import torch
        from mbert.models import MotionTransformer
        _HAS_MOTIONBERT = True
        logger.info("MotionBERT available — using learned 3D lifting")
    except ImportError:
        _HAS_MOTIONBERT = False
        logger.info("MotionBERT not available — using heuristic 3D lifting")


def lift_to_3d(keypoints_2d: NDArray[np.floating], fps: float = 30.0) -> NDArray[np.float32]:
    """Lift (T, 17, 2+) keypoint sequence to (T, 17, 3) 3D coordinates.

    Uses MotionBERT if available, otherwise falls back to heuristic depth.
    Input keypoints are in pixel coordinates; output is normalized to meters
    with camera-relative Z (positive = toward camera).
    """
    kp = np.asarray(keypoints_2d, dtype=np.float32)
    if kp.ndim != 3 or kp.shape[1] != 17:
        raise ValueError(f"Expected shape (T, 17, D), got {kp.shape}")

    if _HAS_MOTIONBERT:
        return _lift_motionbert(kp, fps)
    return _lift_heuristic(kp)


def _lift_motionbert(kp: NDArray[np.float32], fps: float) -> NDArray[np.float32]:
    """Use MotionBERT model for 2D→3D lifting.

    Requires: torch, mbert package with pretrained weights.
    The model expects (1, T, 17, 2) input in normalized coordinates
    and outputs (1, T, 17, 3) in camera-root units.
    """
    import torch

    xy = kp[:, :, :2].copy()
    conf = kp[:, :, 2] if kp.shape[2] > 2 else np.ones(kp.shape[:2])

    mask = conf > 0.1
    for j in range(17):
        if mask[:, j].any():
            mean_x = np.mean(xy[mask[:, j], j, 0])
            mean_y = np.mean(xy[mask[:, j], j, 1])
            std = max(np.std(xy[mask[:, j], j, :2]), 1.0)
            xy[:, j, :2] = (xy[:, j, :2] - np.array([mean_x, mean_y])) / std

    input_tensor = torch.from_numpy(xy[:, :, :2]).float().unsqueeze(0)

    global _MOTIONBERT_MODEL
    if _MOTIONBERT_MODEL is None:
        from mbert.models import MotionTransformer
        checkpoint_path = Path.home() / ".motionbert" / "mb_pt3d.pth"
        if checkpoint_path.exists():
            _MOTIONBERT_MODEL = MotionTransformer()
            _MOTIONBERT_MODEL.load_state_dict(
                torch.load(str(checkpoint_path), map_location="cpu")
            )
            _MOTIONBERT_MODEL.eval()
        else:
            logger.warning("MotionBERT checkpoint not found — falling back to heuristic")
            return _lift_heuristic(kp)

    with torch.no_grad():
        output = _MOTIONBERT_MODEL(input_tensor)

    result_3d = output.squeeze(0).cpu().numpy().astype(np.float32)
    return result_3d


def _lift_heuristic(kp: NDArray[np.float32]) -> NDArray[np.float32]:
    """Heuristic 3D depth estimation from 2D keypoints + body proportions.

    Uses knowledge of human body proportions to estimate Z depth:
    - Head, hands are closer to camera
    - Feet, hips are further
    - Shoulder line orientation implies torso twist (Z rotation)
    - Hip-shoulder offset implies lateral lean (Z shift)
    """
    T = kp.shape[0]
    result = np.zeros((T, 17, 3), dtype=np.float32)

    xy = kp[:, :, :2].copy()

    bbox = np.zeros((T, 4), dtype=np.float32)
    for t in range(T):
        valid = kp[t, :, 2] > 0.1 if kp.shape[2] > 2 else np.ones(17, dtype=bool)
        if valid.any():
            bbox[t, 0] = xy[t, valid, 0].min()
            bbox[t, 1] = xy[t, valid, 1].min()
            bbox[t, 2] = xy[t, valid, 0].max()
            bbox[t, 3] = xy[t, valid, 1].max()
        else:
            bbox[t] = [0, 0, 100, 100]

    bw = np.maximum(bbox[:, 2] - bbox[:, 0], 1.0)
    bh = np.maximum(bbox[:, 3] - bbox[:, 1], 1.0)
    scale = np.maximum(bw, bh)

    result[:, :, 0] = xy[:, :, 0]
    result[:, :, 1] = xy[:, :, 1]

    ls = kp[:, COCO_LSHOULDER, :2]
    rs = kp[:, COCO_RSHOULDER, :2]
    shoulder_width = np.linalg.norm(rs - ls, axis=1, keepdims=True)
    shoulder_width = np.maximum(shoulder_width, 1.0)

    shoulder_depth_ratio = np.clip(shoulder_width / (scale.mean() + 1e-6), 0.3, 1.0)

    base_z = np.zeros((T, 17), dtype=np.float32)

    base_z[:, COCO_NOSE] = 0.15
    base_z[:, 1] = 0.12  # left_eye
    base_z[:, 2] = 0.13  # right_eye
    base_z[:, 3] = 0.08  # left_ear
    base_z[:, 4] = 0.09  # right_ear
    base_z[:, COCO_LSHOULDER] = 0.0
    base_z[:, COCO_RSHOULDER] = 0.05 * scale.mean() / (shoulder_width.mean() + 1e-6)
    base_z[:, 7] = 0.03   # left_elbow
    base_z[:, 8] = 0.08   # right_elbow
    base_z[:, 9] = 0.10   # left_wrist
    base_z[:, 10] = 0.15  # right_wrist (bat hand closer to camera)
    base_z[:, COCO_LHIP] = -0.05
    base_z[:, COCO_RHIP] = -0.02
    base_z[:, 13] = -0.10  # left_knee
    base_z[:, 14] = -0.08  # right_knee
    base_z[:, 15] = -0.15  # left_ankle
    base_z[:, 16] = -0.12  # right_ankle

    base_z *= scale.mean() * 0.002

    shoulder_angle = np.arctan2(
        kp[:, COCO_RSHOULDER, 1] - kp[:, COCO_LSHOULDER, 1],
        kp[:, COCO_RSHOULDER, 0] - kp[:, COCO_LSHOULDER, 0]
    )
    twist = np.sin(shoulder_angle)

    z_upper = twist * shoulder_width.flatten() * 0.15
    result[:, 5, 2] = base_z[:, 5] - z_upper * 0.5
    result[:, 6, 2] = base_z[:, 6] + z_upper * 0.5
    result[:, 7, 2] = base_z[:, 7] - z_upper * 0.3
    result[:, 8, 2] = base_z[:, 8] + z_upper * 0.3
    result[:, 9, 2] = base_z[:, 9] - z_upper * 0.2
    result[:, 10, 2] = base_z[:, 10] + z_upper * 0.2

    nose = kp[:, COCO_NOSE, :2]
    mid_shoulder = (kp[:, COCO_LSHOULDER, :2] + kp[:, COCO_RSHOULDER, :2]) / 2
    mid_hip = (kp[:, COCO_LHIP, :2] + kp[:, COCO_RHIP, :2]) / 2

    lean = np.linalg.norm(nose - mid_shoulder, axis=1)
    result[:, COCO_NOSE, 2] = base_z[:, COCO_NOSE] + lean * 0.01

    for t in range(T):
        valid = kp[t, :, 2] > 0.1 if kp.shape[2] > 2 else np.ones(17, dtype=bool)
        for j in range(17):
            if not valid[j]:
                result[t, j] = 0
            elif result[t, j, 2] == 0 and base_z[t, j] != 0:
                result[t, j, 2] = base_z[t, j]

    center_xy = np.zeros(2, dtype=np.float32)
    count = 0
    for t in range(T):
        valid = kp[t, :, 2] > 0.1 if kp.shape[2] > 2 else np.ones(17, dtype=bool)
        if valid.any():
            center_xy += xy[t, valid].mean(axis=0)
            count += 1
    if count > 0:
        center_xy /= count
    result[:, :, 0] -= center_xy[0]
    result[:, :, 1] -= center_xy[1]

    result[:, :, :2] /= (scale.mean() + 1e-6)
    result[:, :, 2] /= (scale.mean() + 1e-6)

    result[:, :, 1] = -result[:, :, 1]

    return result


_try_load_motionbert()