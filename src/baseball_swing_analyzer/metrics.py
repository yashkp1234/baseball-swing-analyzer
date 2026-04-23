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
    """Angle of LH->RH line vs horizontal, degrees."""
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
    """Angle of LS->RS line vs horizontal, degrees."""
    keypoints = np.asarray(keypoints, dtype=float)
    ls = keypoints[COCO_LS]
    rs = keypoints[COCO_RS]
    dx = float(rs[0] - ls[0])
    dy = float(rs[1] - ls[1])
    if dx == 0:
        return -90.0 if dy > 0 else 90.0
    ang = np.degrees(np.arctan2(dy, dx))
    return float(ang)


def x_factor(keypoints: np.ndarray) -> float:
    """Hip angle minus shoulder angle."""
    return float(hip_angle(keypoints) - shoulder_angle(keypoints))


def spine_tilt(keypoints: np.ndarray) -> float:
    """Angle of midpoint(shoulders)->midpoint(hips) vs vertical, degrees."""
    keypoints = np.asarray(keypoints, dtype=float)
    shoulders = midpoint(keypoints[COCO_LS], keypoints[COCO_RS])
    hips = midpoint(keypoints[COCO_LH], keypoints[COCO_RH])
    dx = float(hips[0] - shoulders[0])
    dy = float(hips[1] - shoulders[1])
    if dx == 0:
        return 0.0
    ang = np.degrees(np.arctan2(dx, dy))
    return float(ang)


def knee_angle(keypoints: np.ndarray, side: str) -> float:
    """Angle at knee (hip-knee-ankle) in degrees."""
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
    return angle_between(v1, v2)


def head_displacement(keypoints_seq: np.ndarray) -> float:
    """Total pixel displacement of nose from first to last frame."""
    seq = np.asarray(keypoints_seq, dtype=float)
    start = seq[0, COCO_NOSE, :2]
    end = seq[-1, COCO_NOSE, :2]
    disp = float(np.linalg.norm(end - start))
    return disp


def wrist_velocity(keypoints_seq: np.ndarray, fps: float) -> np.ndarray:
    """Per-wrist velocity in px/s, shape (T, 2) for left/right wrist."""
    seq = np.asarray(keypoints_seq, dtype=float)
    if seq.ndim != 3 or seq.shape[1:] != (17, 2):
        raise ValueError("keypoints_seq must have shape (T, 17, 2)")
    lw = seq[:, COCO_LW, :2]
    rw = seq[:, COCO_RW, :2]
    dt = 1.0 / float(fps)
    vel_l = np.linalg.norm(np.diff(lw, axis=0, prepend=lw[0:1]), axis=1) / dt
    vel_r = np.linalg.norm(np.diff(rw, axis=0, prepend=rw[0:1]), axis=1) / dt
    return np.stack([vel_l, vel_r], axis=1)


def phase_durations(phase_labels: list[str]) -> dict[str, int]:
    """Count total frames per phase label (non-contiguous grouped)."""
    from collections import Counter
    return dict(Counter(phase_labels))


def stride_foot_plant_frame(keypoints_seq: np.ndarray) -> int | None:
    """Find frame where lower ankle's y-velocity changes from negative to positive.

    Returns the first frame index after the sign change where y-velocity is >= 0
    after previously being < 0. None if no sign change.
    """
    seq = np.asarray(keypoints_seq, dtype=float)
    ankles = seq[:, [COCO_LA, COCO_RA], 1]
    lower_ankle_idx = np.argmin(ankles, axis=1)
    lower_y = np.array([ankles[t, lower_ankle_idx[t]] for t in range(len(ankles))])
    vy = np.diff(lower_y, prepend=lower_y[0])
    for i in range(1, len(vy)):
        if vy[i - 1] < 0 and vy[i] >= 0:
            return int(i - 1)
    return None
