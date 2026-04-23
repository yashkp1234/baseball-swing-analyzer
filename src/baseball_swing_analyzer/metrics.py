import numpy as np


COCO_NOSE = 0
COCO_LS = 5
COCO_RS = 6
COCO_LE = 7
COCO_RE = 8
COCO_LW = 9
COCO_RW = 10
COCO_LH = 11
COCO_RH = 12
COCO_LK = 13
COCO_RK = 14
COCO_LA = 15
COCO_RA = 16


def angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    """Return the unsigned angle between two 2-D vectors in degrees."""
    v1 = np.asarray(v1, dtype=float).flatten()
    v2 = np.asarray(v2, dtype=float).flatten()
    dot = float(np.dot(v1, v2))
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 == 0 or n2 == 0:
        return float(np.nan)
    cosang = dot / (n1 * n2)
    cosang = max(-1.0, min(1.0, cosang))
    return float(np.degrees(np.arccos(cosang)))


def midpoint(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Return the midpoint of two points."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return (a + b) / 2


def hip_angle(keypoints: np.ndarray) -> float:
    """Angle of LH->RH line vs horizontal, degrees.

    Note: Valid for **frontal/back view** only (transverse-plane rotation).
    In a side view this measures sagittal tilt, not rotation.
    """
    keypoints = np.asarray(keypoints, dtype=float)
    lh = keypoints[COCO_LH]
    rh = keypoints[COCO_RH]
    dx = float(rh[0] - lh[0])
    dy = float(rh[1] - lh[1])
    if dx == 0:
        return -90.0 if dy > 0 else 90.0
    ang = np.degrees(np.arctan2(dy, dx))
    return float(ang)


def shoulder_angle(keypoints: np.ndarray) -> float:
    """Angle of LS->RS line vs horizontal, degrees.

    Note: Valid for **frontal/back view** only (transverse-plane rotation).
    """
    keypoints = np.asarray(keypoints, dtype=float)
    ls = keypoints[COCO_LS]
    rs = keypoints[COCO_RS]
    dx = float(rs[0] - ls[0])
    dy = float(rs[1] - ls[1])
    if dx == 0:
        return -90.0 if dy > 0 else 90.0
    ang = np.degrees(np.arctan2(dy, dx))
    return float(ang)


def _normalize_angle_diff(a: float, b: float) -> float:
    """Return the smallest signed difference between two angles in degrees."""
    diff = a - b
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    return float(diff)


def x_factor(keypoints: np.ndarray) -> float:
    """Hip-shoulder separation in degrees.

    Computed as hip_angle - shoulder_angle. This is a valid proxy
    **only for frontal/back camera views** (transverse plane).
    """
    return _normalize_angle_diff(hip_angle(keypoints), shoulder_angle(keypoints))


def lateral_spine_tilt(keypoints: np.ndarray) -> float:
    """Lateral side-bend: angle of shoulder-midpoint → hip-midpoint vs vertical."""
    keypoints = np.asarray(keypoints, dtype=float)
    shoulders = midpoint(keypoints[COCO_LS], keypoints[COCO_RS])
    hips = midpoint(keypoints[COCO_LH], keypoints[COCO_RH])
    dx = float(hips[0] - shoulders[0])
    dy = float(hips[1] - shoulders[1])
    if dx == 0:
        return 0.0
    ang = np.degrees(np.arctan2(dx, dy))
    return float(ang)


# Backwards-compatible alias (deprecated)
spine_tilt = lateral_spine_tilt


def knee_angle(keypoints: np.ndarray, side: str) -> float:
    """Knee flexion in degrees: 0 = straight, larger = more bent."""
    keypoints = np.asarray(keypoints, dtype=float)
    side = str(side).lower()
    if side == "left":
        hip = keypoints[COCO_LH]
        knee = keypoints[COCO_LK]
        ankle = keypoints[COCO_LA]
    elif side == "right":
        hip = keypoints[COCO_RH]
        knee = keypoints[COCO_RK]
        ankle = keypoints[COCO_RA]
    else:
        raise ValueError("side must be 'left' or 'right'")
    v1 = hip - knee
    v2 = ankle - knee
    return 180.0 - angle_between(v1, v2)


def head_displacement(keypoints_seq: np.ndarray) -> float:
    """Total pixel displacement of nose from first to last frame."""
    seq = np.asarray(keypoints_seq, dtype=float)
    start = seq[0, COCO_NOSE, :2]
    end = seq[-1, COCO_NOSE, :2]
    disp = float(np.linalg.norm(end - start))
    return disp


def wrist_velocity(keypoints_seq: np.ndarray, fps: float) -> np.ndarray:
    """Per-wrist speed in px/s, shape (T, 2) for left/right wrist."""
    seq = np.asarray(keypoints_seq, dtype=float)
    if seq.ndim != 3 or seq.shape[1] != 17:
        raise ValueError("keypoints_seq must have shape (T, 17, D)")
    lw = seq[:, COCO_LW, :2]
    rw = seq[:, COCO_RW, :2]
    dt = 1.0 / float(fps)
    vel_l = np.linalg.norm(np.diff(lw, axis=0, prepend=lw[0:1]), axis=1) / dt
    vel_r = np.linalg.norm(np.diff(rw, axis=0, prepend=rw[0:1]), axis=1) / dt
    return np.stack([vel_l, vel_r], axis=1)


def stride_foot_plant_frame(keypoints_seq: np.ndarray) -> int | None:
    """Find stride foot plant frame from lower-ankle y minima.

    Returns the index of the local minimum in y-position (highest on screen = lowest in image).
    None if no clear minimum is found.
    """
    seq = np.asarray(keypoints_seq, dtype=float)
    ankles = seq[:, [COCO_LA, COCO_RA], 1]
    lower_ankle_idx = np.argmin(ankles, axis=1)
    lower_y = np.array([ankles[t, lower_ankle_idx[t]] for t in range(len(ankles))])

    if len(lower_y) < 3:
        return None

    # Smooth longer sequences; use raw for short clips
    if len(lower_y) >= 15:
        window = max(3, len(lower_y) // 10)
        half = window // 2
        smoothed = np.array([
            lower_y[max(0, i - half):min(len(lower_y), i + half + 1)].mean()
            for i in range(len(lower_y))
        ])
    else:
        smoothed = lower_y

    # find local minima; pick the first significant one (not at edges)
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] <= smoothed[i - 1] and smoothed[i] < smoothed[i + 1]:
            if i > len(smoothed) * 0.1:
                return int(i)
    return None


def phase_durations(phase_labels: list[str]) -> dict[str, int]:
    """Count total frames per phase label (non-contiguous grouped)."""
    from collections import Counter
    return dict(Counter(phase_labels))
