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


def torso_length_px(keypoints_seq: np.ndarray) -> float:
    """Median shoulder-mid → hip-mid distance across the sequence (pixels)."""
    seq = np.asarray(keypoints_seq, dtype=float)
    sh_mid = (seq[:, COCO_LS, :2] + seq[:, COCO_RS, :2]) / 2
    hp_mid = (seq[:, COCO_LH, :2] + seq[:, COCO_RH, :2]) / 2
    d = np.linalg.norm(sh_mid - hp_mid, axis=1)
    d = d[d > 1.0]
    return float(np.median(d)) if len(d) else 100.0


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
    """Length of the longest contiguous run per phase label."""
    if not phase_labels:
        return {}
    out: dict[str, int] = {}
    i = 0
    while i < len(phase_labels):
        j = i
        while j < len(phase_labels) and phase_labels[j] == phase_labels[i]:
            j += 1
        run = j - i
        out[phase_labels[i]] = max(out.get(phase_labels[i], 0), run)
        i = j
    return out


def clip_metric(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))


def attack_angle_deg(keypoints_seq: np.ndarray, contact_idx: int, window: int = 3) -> float:
    """Approximate attack angle from wrist-midpoint trajectory near contact.

    We don't track the bat directly. The wrist midpoint over the last few
    frames before contact is the best pose-only proxy for bat-path angle.

    Returns degrees above horizontal (positive = upward swing). Sign flipped
    because image y increases downward.
    """
    seq = np.asarray(keypoints_seq, dtype=float)
    T = seq.shape[0]
    if T < 2 or window < 2:
        return float("nan")
    end = max(1, min(contact_idx, T - 1))
    start = max(0, end - window + 1)
    if end - start < 1:
        return float("nan")
    wrist_mid = (seq[start:end + 1, COCO_LW, :2] + seq[start:end + 1, COCO_RW, :2]) / 2
    if len(wrist_mid) < 2:
        return float("nan")
    dx = float(wrist_mid[-1, 0] - wrist_mid[0, 0])
    dy = float(wrist_mid[-1, 1] - wrist_mid[0, 1])
    if abs(dx) < 1e-3 and abs(dy) < 1e-3:
        return 0.0
    angle = np.degrees(np.arctan2(-dy, abs(dx) if dx != 0 else 1e-3))
    return float(angle)


def stride_length_normalized(
    keypoints_seq: np.ndarray,
    plant_frame: int | None,
    handedness: str,
) -> float:
    """Front-ankle horizontal displacement from frame 0 to plant, in hip-widths.

    Returns NaN if plant_frame missing or hip width too small to trust.
    """
    if plant_frame is None:
        return float("nan")
    seq = np.asarray(keypoints_seq, dtype=float)
    T = seq.shape[0]
    if T < 2 or plant_frame <= 0 or plant_frame >= T:
        return float("nan")
    front_idx = COCO_LA if str(handedness).lower() == "right" else COCO_RA
    start_x = float(seq[0, front_idx, 0])
    plant_x = float(seq[plant_frame, front_idx, 0])
    hip_width = float(np.linalg.norm(seq[0, COCO_LH, :2] - seq[0, COCO_RH, :2]))
    if hip_width < 5.0:
        return float("nan")
    return float(abs(plant_x - start_x) / hip_width)


def stride_direction_deg(
    keypoints_seq: np.ndarray,
    plant_frame: int | None,
    handedness: str,
) -> float:
    """Angle of front-foot stride vector in image plane, degrees from horizontal.

    Image plane only, so interpretation requires a frontal/back view. Positive
    = stride goes upward in the image (toward camera-far side).
    """
    if plant_frame is None:
        return float("nan")
    seq = np.asarray(keypoints_seq, dtype=float)
    T = seq.shape[0]
    if T < 2 or plant_frame <= 0 or plant_frame >= T:
        return float("nan")
    front_idx = COCO_LA if str(handedness).lower() == "right" else COCO_RA
    dx = float(seq[plant_frame, front_idx, 0] - seq[0, front_idx, 0])
    dy = float(seq[plant_frame, front_idx, 1] - seq[0, front_idx, 1])
    if abs(dx) < 1e-3 and abs(dy) < 1e-3:
        return 0.0
    return float(np.degrees(np.arctan2(-dy, dx if dx != 0 else 1e-3)))


def _peak_angular_velocity(angles: np.ndarray, fps: float) -> float:
    angles = np.asarray(angles, dtype=float)
    valid = angles[~np.isnan(angles)]
    if len(valid) < 3:
        return float("nan")
    unwrapped = np.degrees(np.unwrap(np.radians(angles)))
    diffs = np.diff(unwrapped) * float(fps)
    if len(diffs) == 0:
        return float("nan")
    return float(np.nanmax(np.abs(diffs)))


def peak_pelvis_angular_velocity_deg_s(keypoints_seq: np.ndarray, fps: float) -> float:
    """Peak |d(hip_angle)/dt| in deg/s. Angle-sensitive — frontal/back view only."""
    seq = np.asarray(keypoints_seq, dtype=float)
    angles = np.array([hip_angle(frame) for frame in seq])
    return _peak_angular_velocity(angles, fps)


def peak_torso_angular_velocity_deg_s(keypoints_seq: np.ndarray, fps: float) -> float:
    """Peak |d(shoulder_angle)/dt| in deg/s. Angle-sensitive — frontal/back view only."""
    seq = np.asarray(keypoints_seq, dtype=float)
    angles = np.array([shoulder_angle(frame) for frame in seq])
    return _peak_angular_velocity(angles, fps)
