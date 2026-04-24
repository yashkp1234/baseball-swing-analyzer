"""Qualitative biomechanical flags extracted purely from pose keypoints.

No external vision model required. Each function is a pure function of keypoint arrays.
"""

import numpy as np
from numpy.typing import NDArray


def front_shoulder_closed_in_load(keypoints_seq: NDArray[np.floating], phase_labels: list[str]) -> bool:
    """Return True if front shoulder (left for RHH, right for LHH) stays closed through load phase.

    Closed means the shoulder line is angled slightly *toward* camera / not opened early.
    For a right-handed hitter, front shoulder is left_shoulder (5).
    We check if front_shoulder_x < back_shoulder_x for most of load frames.
    """
    if "load" not in phase_labels:
        return False

    load_mask = np.array([p == "load" for p in phase_labels])
    if not load_mask.any():
        return False

    shoulders = keypoints_seq[load_mask]  # (N, 17, 2)
    left_shoulder_x = shoulders[:, 5, 0]
    right_shoulder_x = shoulders[:, 6, 0]
    # Right-handed hitter assumption: front = left (lower x at address)
    front_x = left_shoulder_x
    back_x = right_shoulder_x
    closed_ratio = (front_x < back_x).mean()
    return bool(closed_ratio >= 0.6)


def leg_kick_or_toe_tap(keypoints_seq: NDArray[np.floating], phase_labels: list[str]) -> str:
    """Classify front leg action: 'leg_kick', 'toe_tap', or 'neither'.

    Leg kick: front ankle peak y during stride is significantly lower (higher on screen) than stance.
    Toe tap: front ankle stays near stance level, minimal lift.
    """
    if "stance" not in phase_labels or "stride" not in phase_labels:
        return "neither"

    stance_mask = np.array([p == "stance" for p in phase_labels])
    stride_mask = np.array([p == "stride" for p in phase_labels])
    if not stance_mask.any() or not stride_mask.any():
        return "neither"

    # Right-handed = left foot is front foot (we assume convention)
    # Use lower ankle during stance as front foot
    stance_ankles = keypoints_seq[stance_mask][:, [15, 16], 1]  # y coords
    front_ankle_stance = stance_ankles[:, 0].mean()  # left ankle
    back_ankle_stance = stance_ankles[:, 1].mean()  # right ankle
    if back_ankle_stance < front_ankle_stance:
        # left ankle is higher on screen = front foot
        front_idx = 15
    else:
        front_idx = 16

    front_stance_y = keypoints_seq[stance_mask][:, front_idx, 1].mean()
    front_stride_y = keypoints_seq[stride_mask][:, front_idx, 1].min()

    lift = front_stance_y - front_stride_y  # positive = ankle lifted (higher on screen)
    if lift > 30:
        return "leg_kick"
    elif lift > 5:
        return "toe_tap"
    return "neither"


def high_or_low_finish(keypoints_seq: NDArray[np.floating], phase_labels: list[str]) -> str:
    """Classify finish height by wrist Y position in follow_through vs stance.

    High finish: wrists finish above shoulder height at contact.
    Low finish: wrists stay below shoulder height.
    """
    if "follow_through" not in phase_labels:
        return "unknown"

    ft_mask = np.array([p == "follow_through" for p in phase_labels])
    if not ft_mask.any():
        return "unknown"

    # Wrist y at end of follow-through
    wrist_y = keypoints_seq[ft_mask][:, 10, 1].mean()  # right wrist
    shoulder_y = keypoints_seq[ft_mask][:, 6, 1].mean()

    if wrist_y < shoulder_y:
        return "high"
    else:
        return "low"


def hip_casting_visible(keypoints_seq: NDArray[np.floating], phase_labels: list[str]) -> bool:
    """Return True if hips open early (rotate before hands start moving forward).

    Hip casting = hip angle increases sharply while hands are still loading backward.
    We check if hip rotation change during load/early-stride exceeds shoulder rotation change.
    """
    if "load" not in phase_labels or "stride" not in phase_labels:
        return False

    from baseball_swing_analyzer.metrics import hip_angle, shoulder_angle

    combined = [(i, hip_angle(kp), shoulder_angle(kp))
                for i, (kp, ph) in enumerate(zip(keypoints_seq, phase_labels))
                if ph in ("load", "stride")]
    if len(combined) < 3:
        return False

    hip_changes = np.diff([h for (_i, h, _s) in combined])
    sh_changes = np.diff([s for (_i, _h, s) in combined])
    # If hips are rotating forward much faster than shoulders during load-stride,
    # that's early opening / casting
    early_open = (hip_changes > 3.0) & (sh_changes < 1.0)
    return bool(early_open.mean() > 0.3)


def arm_slot_at_contact(
    kp_contact: NDArray[np.floating],
) -> str:
    """Classify arm slot (elbow height relative to shoulder) at contact.

    high: top of shoulder or above
    middle: between shoulder and chest
    low: below chest
    """
    shoulder_y = kp_contact[[5, 6], 1].mean()
    chest_y = shoulder_y + 20
    elbow_y = kp_contact[[7, 8], 1].mean()

    if elbow_y <= shoulder_y + 5:
        return "high"
    elif elbow_y <= chest_y:
        return "middle"
    else:
        return "low"


def generate_qualitative_flags(
    keypoints_seq: NDArray[np.floating],
    phase_labels: list[str],
) -> dict[str, str | bool]:
    """Return a dict of all qualitative flags for a swing."""
    contact_idx = phase_labels.index("contact") if "contact" in phase_labels else len(phase_labels) // 2
    kp_contact = keypoints_seq[contact_idx]

    return {
        "front_shoulder_closed_load": front_shoulder_closed_in_load(keypoints_seq, phase_labels),
        "leg_action": leg_kick_or_toe_tap(keypoints_seq, phase_labels),
        "finish_height": high_or_low_finish(keypoints_seq, phase_labels),
        "hip_casting": hip_casting_visible(keypoints_seq, phase_labels),
        "arm_slot_at_contact": arm_slot_at_contact(kp_contact),
    }
