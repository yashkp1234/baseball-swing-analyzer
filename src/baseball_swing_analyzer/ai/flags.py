"""Qualitative biomechanical flags extracted purely from pose keypoints.

No external vision model required. Each function is a pure function of keypoint arrays.
"""

import numpy as np
from numpy.typing import NDArray


def detect_handedness(keypoints_seq: NDArray[np.floating], labels: list[str]) -> str:
    """Auto-detect batter handedness from stance-phase shoulder positions.

    RHH: left shoulder (idx 5) is camera-left of right shoulder (idx 6) at address.
    LHH: right shoulder is camera-left of left shoulder.
    Falls back to 'right' if no stance frames exist.

    Returns
    -------
    'right' or 'left'
    """
    stance_mask = np.array([p == "stance" for p in labels])
    if not stance_mask.any():
        return "right"

    kp = keypoints_seq[stance_mask]
    ls_x = kp[:, 5, 0].mean()
    rs_x = kp[:, 6, 0].mean()
    return "right" if ls_x <= rs_x else "left"


def front_shoulder_closed_in_load(
    keypoints_seq: NDArray[np.floating],
    labels: list[str],
    handedness: str = "auto",
) -> bool:
    """Return True if front shoulder stays closed through load phase.

    For RHH the front shoulder is left (idx 5). For LHH it is right (idx 6).
    Closed = front shoulder x is less than back shoulder x (camera-left).
    """
    if "load" not in labels:
        return False

    hand = detect_handedness(keypoints_seq, labels) if handedness == "auto" else handedness

    load_mask = np.array([p == "load" for p in labels])
    if not load_mask.any():
        return False

    shoulders = keypoints_seq[load_mask]  # (N, 17, D)
    if hand == "right":
        front_x = shoulders[:, 5, 0]
        back_x = shoulders[:, 6, 0]
    else:
        front_x = shoulders[:, 6, 0]
        back_x = shoulders[:, 5, 0]

    closed_ratio = (front_x < back_x).mean()
    return bool(closed_ratio >= 0.6)


def leg_kick_or_toe_tap(
    keypoints_seq: NDArray[np.floating],
    labels: list[str],
    handedness: str = "auto",
) -> str:
    """Classify front leg action: 'leg_kick', 'toe_tap', or 'neither'.

    Leg kick: front ankle peak y during stride is significantly higher on screen than stance.
    Toe tap: front ankle stays near stance level, minimal lift.
    """
    if "stance" not in labels or "stride" not in labels:
        return "neither"

    hand = detect_handedness(keypoints_seq, labels) if handedness == "auto" else handedness

    stance_mask = np.array([p == "stance" for p in labels])
    stride_mask = np.array([p == "stride" for p in labels])
    if not stance_mask.any() or not stride_mask.any():
        return "neither"

    # RHH: front foot = left (idx 15). LHH: front foot = right (idx 16).
    front_idx = 15 if hand == "right" else 16

    front_stance_y = keypoints_seq[stance_mask][:, front_idx, 1].mean()
    front_stride_y = keypoints_seq[stride_mask][:, front_idx, 1].min()

    lift = front_stance_y - front_stride_y  # positive = ankle lifted higher on screen
    if lift > 30:
        return "leg_kick"
    elif lift > 5:
        return "toe_tap"
    return "neither"


def high_or_low_finish(
    keypoints_seq: NDArray[np.floating],
    labels: list[str],
    handedness: str = "auto",
) -> str:
    """Classify finish height by wrist Y position in follow_through.

    High finish: top-hand wrist finishes above shoulder height.
    Low finish: wrist stays below shoulder height.
    """
    if "follow_through" not in labels:
        return "unknown"

    hand = detect_handedness(keypoints_seq, labels) if handedness == "auto" else handedness

    ft_mask = np.array([p == "follow_through" for p in labels])
    if not ft_mask.any():
        return "unknown"

    # Top-hand wrist: RHH = right (10), LHH = left (9)
    wrist_idx = 10 if hand == "right" else 9
    shoulder_idx = 6 if hand == "right" else 5

    wrist_y = keypoints_seq[ft_mask][:, wrist_idx, 1].mean()
    shoulder_y = keypoints_seq[ft_mask][:, shoulder_idx, 1].mean()

    return "high" if wrist_y < shoulder_y else "low"


def hip_casting_visible(
    keypoints_seq: NDArray[np.floating],
    labels: list[str],
) -> bool:
    """Return True if hips open early (rotate before hands start moving forward).

    Hip casting = hip angle increases sharply while hands are still loading backward.
    """
    if "load" not in labels or "stride" not in labels:
        return False

    from baseball_swing_analyzer.metrics import hip_angle, shoulder_angle

    combined = [(i, hip_angle(kp), shoulder_angle(kp))
                for i, (kp, ph) in enumerate(zip(keypoints_seq, labels))
                if ph in ("load", "stride")]
    if len(combined) < 3:
        return False

    hip_changes = np.diff([h for (_i, h, _s) in combined])
    sh_changes = np.diff([s for (_i, _h, s) in combined])
    early_open = (hip_changes > 3.0) & (sh_changes < 1.0)
    return bool(early_open.mean() > 0.3)


def arm_slot_at_contact(
    kp_contact: NDArray[np.floating],
    handedness: str = "right",
) -> str:
    """Classify arm slot (elbow height relative to shoulder) at contact.

    high: elbow at or above shoulder
    middle: between shoulder and chest
    low: below chest
    """
    shoulder_y = kp_contact[[5, 6], 1].mean()
    elbow_y = kp_contact[[7, 8], 1].mean()
    chest_y = shoulder_y + 20

    if elbow_y <= shoulder_y + 5:
        return "high"
    elif elbow_y <= chest_y:
        return "middle"
    else:
        return "low"


def generate_qualitative_flags(
    keypoints_seq: NDArray[np.floating],
    labels: list[str],
    handedness: str = "auto",
) -> dict[str, str | bool]:
    """Return a dict of all qualitative flags for a swing."""
    hand = detect_handedness(keypoints_seq, labels) if handedness == "auto" else handedness

    contact_idx = labels.index("contact") if "contact" in labels else len(labels) // 2
    kp_contact = keypoints_seq[contact_idx]

    return {
        "handedness": hand,
        "front_shoulder_closed_load": front_shoulder_closed_in_load(keypoints_seq, labels, hand),
        "leg_action": leg_kick_or_toe_tap(keypoints_seq, labels, hand),
        "finish_height": high_or_low_finish(keypoints_seq, labels, hand),
        "hip_casting": hip_casting_visible(keypoints_seq, labels),
        "arm_slot_at_contact": arm_slot_at_contact(kp_contact, hand),
    }
