"""Export swing data as JSON for the 3D viewer.

Orchestrates the 2D→3D lifting and energy analysis, producing a single
JSON blob that the frontend Three.js visualization consumes.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .lifter import lift_to_3d
from .energy import (
    compute_velocities,
    compute_speeds,
    compute_kinetic_chain_scores,
    detect_energy_loss_events,
)


COCO_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

COCO_SKELETON = [
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]


def generate_swing_3d_data(report: dict) -> dict:
    """Generate 3D visualization data from a swing analysis report.

    Uses the report's internal keypoints if available (stored by the
    build_report function). Falls back to zeros if raw keypoints
    aren't embedded in the report dict.
    """
    phase_labels = report.get("phase_labels", [])
    fps = report.get("fps", 30.0)
    T = report.get("frames", len(phase_labels))
    if T == 0:
        return _empty_result(fps)

    keypoints_2d = report.get("_keypoints_seq")
    if keypoints_2d is not None:
        kp = np.asarray(keypoints_2d, dtype=np.float32)
    else:
        kp = np.zeros((T, 17, 3), dtype=np.float32)

    return _build_3d_data(kp, fps, phase_labels, report)


def generate_swing_3d_data_from_keypoints(
    keypoints_seq: NDArray[np.floating],
    phase_labels: list[str],
    fps: float,
    report: dict | None = None,
) -> dict:
    """Generate 3D data directly from a keypoints array (T, 17, 3)."""
    kp = np.asarray(keypoints_seq, dtype=np.float32)
    return _build_3d_data(kp, fps, phase_labels, report or {})


def _build_3d_data(
    keypoints_seq: NDArray[np.floating],
    fps: float,
    phase_labels: list[str],
    report: dict,
) -> dict:
    """Core builder: lift to 3D, compute energy, serialize."""
    T = keypoints_seq.shape[0]

    keypoints_3d = lift_to_3d(keypoints_seq, fps)

    velocities = compute_velocities(keypoints_3d, fps)
    speeds = compute_speeds(velocities)
    chain_scores = compute_kinetic_chain_scores(keypoints_3d, fps)
    energy_events = detect_energy_loss_events(keypoints_3d, fps, phase_labels)

    normed = _normalize_3d(keypoints_3d)

    frames_list = []
    contact_idx = phase_labels.index("contact") if "contact" in phase_labels else T // 2

    for t in range(T):
        frame = {
            "keypoints": normed[t].tolist(),
            "keypoint_names": COCO_NAMES,
            "skeleton": COCO_SKELETON,
            "phase": phase_labels[t] if t < len(phase_labels) else "idle",
            "bat": _estimate_bat(normed[t]),
            "efficiency": _frame_efficiency(speeds, t),
            "velocities": {
                name: round(float(speeds[name][t]), 2)
                for name in speeds
            },
            "velocity_vectors": {
                name: [round(float(v), 4) for v in velocities[name][t]]
                for name in velocities
            },
        }
        frames_list.append(frame)

    stride_frame = report.get("stride_plant_frame")

    return {
        "fps": fps,
        "total_frames": T,
        "contact_frame": contact_idx,
        "stride_plant_frame": stride_frame,
        "phase_labels": phase_labels,
        "frames": frames_list,
        "swing_segments": report.get("swing_segments", []),
        "primary_swing_segment": report.get("primary_swing_segment"),
        "ball": _estimate_ball(frames_list, contact_idx),
        "kinetic_chain_scores": chain_scores,
        "energy_loss_events": energy_events,
        "depth_disclaimer": "Depth is estimated from 2D heuristics — quantitative depth metrics are not available. View this as a stylized rendering of the 2D pose.",
        "metrics": {
            k: v for k, v in report.items()
            if k not in ("phase_labels", "_keypoints_seq", "flags") and isinstance(v, (int, float, str, bool))
        },
        "skeleton": COCO_SKELETON,
        "keypoint_names": COCO_NAMES,
    }


def _estimate_bat(frame_points: NDArray[np.float32]) -> dict:
    """Estimate bat handle and barrel from wrist/forearm pose points."""
    left_wrist = frame_points[9]
    right_wrist = frame_points[10]
    left_elbow = frame_points[7]
    right_elbow = frame_points[8]
    handle = (left_wrist + right_wrist) / 2.0
    hand_axis = right_wrist - left_wrist
    forearm_axis = ((left_wrist - left_elbow) + (right_wrist - right_elbow)) / 2.0
    direction = hand_axis + forearm_axis
    length = float(np.linalg.norm(direction))
    if not np.isfinite(length) or length < 1e-6:
        direction = np.array([0.45, 0.0, 0.0], dtype=np.float32)
        length = float(np.linalg.norm(direction))
    unit = direction / length
    barrel = handle + unit * 0.55
    return {
        "handle": [round(float(v), 4) for v in handle],
        "barrel": [round(float(v), 4) for v in barrel],
        "confidence": 0.45,
        "estimate_basis": "wrist_forearm_proxy",
    }


def _estimate_ball(frames_list: list[dict], contact_idx: int) -> dict:
    bat = frames_list[contact_idx].get("bat") if frames_list and 0 <= contact_idx < len(frames_list) else None
    position = bat["barrel"] if bat else [0.0, 0.0, 0.0]
    return {
        "contact_frame": contact_idx,
        "contact_position": position,
        "confidence": 0.35,
        "estimate_basis": "contact_frame_barrel_proxy",
    }


def _normalize_3d(kp_3d: NDArray[np.float32]) -> NDArray[np.float32]:
    """Normalize 3D keypoints to [-1, 1] range for visualization."""
    result = kp_3d.copy()
    flat = result.reshape(-1, 3)
    mins = flat.min(axis=0)
    maxs = flat.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1.0
    result = (result - mins) / ranges * 2 - 1
    return result


def _frame_efficiency(speeds: dict[str, NDArray[np.float32]], t: int) -> float:
    """Compute a per-frame kinetic chain efficiency score (0-1)."""
    hip_s = speeds.get("hip_center", np.zeros(1))
    sh_s = speeds.get("shoulder_center", np.zeros(1))
    wr_s = speeds.get("right_wrist", np.zeros(1))

    wi = 0.6
    if t >= len(wr_s) or t >= len(sh_s) or t >= len(hip_s):
        return 0.5

    chain_score = 0.5
    if hip_s[t] > 0 and sh_s[t] > 0:
        ratio = min(sh_s[t] / (hip_s[t] + 1e-6), 2.0)
        chain_score = min(1.0, max(0.0, 0.3 + ratio * 0.4))

    return float(chain_score)


def _empty_result(fps: float) -> dict:
    return {
        "fps": fps,
        "total_frames": 0,
        "contact_frame": 0,
        "stride_plant_frame": None,
        "phase_labels": [],
        "frames": [],
        "swing_segments": [],
        "primary_swing_segment": None,
        "ball": {"contact_frame": 0, "contact_position": [0.0, 0.0, 0.0], "confidence": 0.0, "estimate_basis": "contact_frame_barrel_proxy"},
        "kinetic_chain_scores": {"hip_to_shoulder": {"lag_frames": 0, "direction": "synced"}, "shoulder_to_hand": {"lag_frames": 0, "direction": "synced"}},
        "energy_loss_events": [],
        "metrics": {},
        "skeleton": COCO_SKELETON,
        "keypoint_names": COCO_NAMES,
    }
