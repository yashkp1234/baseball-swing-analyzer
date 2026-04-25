"""Export swing data as JSON for the 3D viewer."""

from __future__ import annotations

import numpy as np


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


def _normalize_keypoints_2d(kp_seq: np.ndarray) -> np.ndarray:
    """Normalize keypoints to 0-1 range based on bounding box of all frames."""
    xy = kp_seq[:, :, :2]
    x_min, y_min = xy[:, :, 0].min(), xy[:, :, 1].min()
    x_max, y_max = xy[:, :, 0].max(), xy[:, :, 1].max()
    w = max(x_max - x_min, 1.0)
    h = max(y_max - y_min, 1.0)
    normed = xy.copy()
    normed[:, :, 0] = (normed[:, :, 0] - x_min) / w
    normed[:, :, 1] = (normed[:, :, 1] - y_min) / h
    return normed


def _approximate_depth(kp_seq: np.ndarray) -> np.ndarray:
    """Generate a rough Z coordinate from body proportions.

    Uses shoulder width and torso depth heuristics to give a sense of depth.
    The Z axis points toward the camera, so closer body parts have higher Z.
    """
    T = kp_seq.shape[0]
    z = np.zeros((T, 17), dtype=np.float32)

    ls = kp_seq[:, 5, :2]
    rs = kp_seq[:, 6, :2]
    shoulder_width = np.linalg.norm(rs - ls, axis=1, keepdims=True)
    shoulder_width = np.maximum(shoulder_width, 1.0)

    mid_shoulder = (ls + rs) / 2
    mid_hip = (kp_seq[:, 11, :2] + kp_seq[:, 12, :2]) / 2

    spine_depth = np.linalg.norm(mid_shoulder - mid_hip, axis=1, keepdims=True)
    spine_depth = np.maximum(spine_depth, 1.0)

    z[:, 0] = 0.5  # nose
    z[:, 5] = 0.3; z[:, 6] = 0.35  # shoulders: back shoulder closer to camera
    z[:, 11] = 0.1; z[:, 12] = 0.12  # hips
    z[:, 7] = 0.3; z[:, 8] = 0.35   # elbows
    z[:, 9] = 0.35; z[:, 10] = 0.4   # wrists: bat-side closer
    z[:, 13] = 0.05; z[:, 14] = 0.07  # knees
    z[:, 15] = 0.0; z[:, 16] = 0.02   # ankles

    z *= shoulder_width.mean() * 0.3
    return z


def _compute_velocity(keypoints: np.ndarray, fps: float) -> dict[str, list[float]]:
    """Per-frame velocity for key joints."""
    dt = 1.0 / fps
    lw = keypoints[:, 9, :2]
    rw = keypoints[:, 10, :2]
    hip_mid = (keypoints[:, 11, :2] + keypoints[:, 12, :2]) / 2

    def speed(arr):
        d = np.diff(arr, axis=0, prepend=arr[0:1])
        return (np.linalg.norm(d, axis=1) / dt).tolist()

    return {
        "left_wrist": speed(lw),
        "right_wrist": speed(rw),
        "hip_center": speed(hip_mid),
    }


def _compute_efficiency(keypoints: np.ndarray, fps: float) -> list[float]:
    """Kinetic chain efficiency per frame: how well energy transfers hip→shoulder→wrist.

    Higher = better sequence. Lower = everything firing at once (muscling).
    """
    dt = 1.0 / fps
    T = keypoints.shape[0]
    efficiency = [0.5] * T

    if T < 5:
        return efficiency

    hip_mid = (keypoints[:, 11, :2] + keypoints[:, 12, :2]) / 2
    sh_mid = (keypoints[:, 5, :2] + keypoints[:, 6, :2]) / 2
    wrist_mid = (keypoints[:, 9, :2] + keypoints[:, 10, :2]) / 2

    def angular_vel(p):
        d = np.diff(p, axis=0, prepend=p[0:1])
        return np.linalg.norm(d, axis=1) / dt

    hv = angular_vel(hip_mid)
    sv = angular_vel(sh_mid)
    wv = angular_vel(wrist_mid)

    window = min(5, T)
    for i in range(window, T):
        h_peak_frame = i - window + np.argmax(hv[i - window:i])
        s_peak_frame = i - window + np.argmax(sv[i - window:i])
        w_peak_frame = i - window + np.argmax(wv[i - window:i])

        if h_peak_frame <= s_peak_frame <= w_peak_frame:
            efficiency[i] = 0.9
        elif h_peak_frame <= w_peak_frame:
            efficiency[i] = 0.7
        else:
            efficiency[i] = 0.3

    return efficiency


def generate_swing_3d_data(report: dict) -> dict:
    """Generate 3D visualization data from a swing analysis report.

    Returns a dict suitable for JSON serialization with frame-by-frame
    3D keypoints, velocities, and efficiency scores.
    """
    phase_labels = report.get("phase_labels", [])
    fps = report.get("fps", 30.0)

    keypoints_raw = None
    metrics_json = report.get("metrics_json")

    if "wrist_peak_velocity_px_s" not in report:
        return {"error": "report missing metric data"}

    T = report.get("frames", len(phase_labels))
    if T == 0:
        return {"error": "no frames"}

    np_kp = np.zeros((T, 17, 3), dtype=np.float32) + np.nan
    z_approx = np.zeros((T, 17), dtype=np.float32)

    for t in range(T):
        for j in range(17):
            np_kp[t, j, 2] = 0.5

    normed = _normalize_keypoints_2d(np_kp)
    z = _approximate_depth(np_kp)

    frames_3d = np.zeros((T, 17, 3), dtype=np.float32)
    frames_3d[:, :, 0] = normed[:, :, 0]
    frames_3d[:, :, 1] = normed[:, :, 1]
    frames_3d[:, :, 2] = z

    velocities = _compute_velocity(np_kp, fps)
    efficiency = _compute_efficiency(np_kp, fps)

    result_frames = []
    for t in range(T):
        frame_dict = {
            "keypoints": frames_3d[t].tolist(),
            "keypoint_names": COCO_NAMES,
            "skeleton": COCO_SKELETON,
            "phase": phase_labels[t] if t < len(phase_labels) else "idle",
            "efficiency": efficiency[t],
            "velocities": {
                k: v[t] if t < len(v) else 0.0
                for k, v in velocities.items()
            },
        }
        result_frames.append(frame_dict)

    contact_idx = report.get("contact_frame", T // 2)

    return {
        "fps": fps,
        "total_frames": T,
        "contact_frame": contact_idx,
        "stride_plant_frame": report.get("stride_plant_frame"),
        "phase_labels": phase_labels,
        "frames": result_frames,
        "metrics": {
            k: v for k, v in report.items()
            if k not in ("phase_labels",) and isinstance(v, (int, float, str, bool))
        },
        "skeleton": COCO_SKELETON,
        "keypoint_names": COCO_NAMES,
    }


def generate_swing_3d_data_from_keypoints(
    keypoints_seq: np.ndarray,
    phase_labels: list[str],
    fps: float,
    report: dict | None = None,
) -> dict:
    """Generate 3D data directly from a keypoints array (T, 17, 3)."""
    T = keypoints_seq.shape[0]

    normed = _normalize_keypoints_2d(keypoints_seq)
    z = _approximate_depth(keypoints_seq)

    frames_3d = np.zeros((T, 17, 3), dtype=np.float32)
    frames_3d[:, :, 0] = normed[:, :, 0]
    frames_3d[:, :, 1] = normed[:, :, 1]
    frames_3d[:, :, 2] = z

    velocities = _compute_velocity(keypoints_seq, fps)
    efficiency = _compute_efficiency(keypoints_seq, fps)

    result_frames = []
    for t in range(T):
        frame_dict = {
            "keypoints": frames_3d[t].tolist(),
            "keypoint_names": COCO_NAMES,
            "skeleton": COCO_SKELETON,
            "phase": phase_labels[t] if t < len(phase_labels) else "idle",
            "efficiency": efficiency[t],
            "velocities": {
                k: v[t] if t < len(v) else 0.0
                for k, v in velocities.items()
            },
        }
        result_frames.append(frame_dict)

    contact_idx = phase_labels.index("contact") if "contact" in phase_labels else T // 2
    stride_frame = None
    from baseball_swing_analyzer.metrics import stride_foot_plant_frame
    sf = stride_foot_plant_frame(keypoints_seq)
    if sf is not None:
        stride_frame = int(sf)

    extra_metrics = {}
    if report:
        extra_metrics = {
            k: v for k, v in report.items()
            if k not in ("phase_labels",) and isinstance(v, (int, float, str, bool))
        }

    return {
        "fps": fps,
        "total_frames": T,
        "contact_frame": contact_idx,
        "stride_plant_frame": stride_frame,
        "phase_labels": phase_labels,
        "frames": result_frames,
        "metrics": extra_metrics,
        "skeleton": COCO_SKELETON,
        "keypoint_names": COCO_NAMES,
    }