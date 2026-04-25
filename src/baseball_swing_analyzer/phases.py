"""Rule-based swing phase detection from keypoint kinematics."""

import numpy as np
from numpy.typing import NDArray


PHASE_LABELS = [
    "idle",
    "stance",
    "load",
    "stride",
    "swing",
    "contact",
    "follow_through",
]


def _find_swing_start(
    keypoints_seq: NDArray[np.floating],
    contact: int,
    fps: float,
) -> int:
    """Find the earliest frame that is part of the active swing sequence.

    Searches backwards from *contact* for a sustained low-wrist-velocity
    plateau. The frame after that plateau is treated as the start of the
    swing (stance/load).
    """
    from .metrics import wrist_velocity

    vel = wrist_velocity(keypoints_seq, fps)
    max_vel = vel.max(axis=1)
    if max_vel.max() == 0:
        return 0

    # threshold = 15% of peak  (tunable)
    threshold = float(max_vel.max()) * 0.15

    # Look for a sustained low-velocity run (>= 8 frames) before contact
    for t in range(contact - 8, -1, -1):
        if np.all(max_vel[t:t + 8] < threshold):
            return t + 8
    return 0


def classify_phases(
    keypoints_seq: NDArray[np.floating],
    fps: float = 30.0,
) -> list[str]:
    """Assign a phase label to every frame using heuristic rules.

    Works on both short clips (entire video is the swing) and long
    phone recordings where the batter waits before swinging (extra
    ``"idle"`` frames).

    Parameters
    ----------
    keypoints_seq :
        Shape ``(T, 17, 2|3)`` COCO keypoint array.
    fps :
        Frame rate of the source video.

    Returns
    -------
    labels :
        Length ``T`` list of phase strings.  Can include ``"idle"``
        for frames outside the detected swing window.
    """
    seq = np.asarray(keypoints_seq, dtype=float)
    if seq.ndim != 3 or seq.shape[1] != 17:
        raise ValueError("keypoints_seq must have shape (T, 17, D)")

    T = seq.shape[0]
    if T < 4:
        return ["idle"] * T

    from .metrics import (
        stride_foot_plant_frame,
        wrist_velocity,
    )

    vel = wrist_velocity(seq, fps)           # (T, 2)
    max_vel = vel.max(axis=1)
    contact = int(np.argmax(max_vel))

    # Detect the swing window within the longer video
    window_start = _find_swing_start(seq, contact, fps)
    window_len = T - window_start

    plant = stride_foot_plant_frame(seq)
    if plant is None:
        plant = max(window_start + 1, contact - max(1, int(fps // 5)))

    # Clamp plant so it sits inside the swing window
    plant = max(window_start + 1, min(plant, contact - 1))

    # Split stance vs load using hand movement inside the swing window
    lw = seq[:, 9, :2]
    rw = seq[:, 10, :2]
    hands = (lw + rw) / 2.0
    hand_disp = np.linalg.norm(np.diff(hands, axis=0, prepend=hands[0:1]), axis=1)

    # Only consider cumulative displacement inside the swing window
    window_disp = hand_disp[window_start : contact + 1]
    if len(window_disp) > 10:
        cumdisp = np.cumsum(window_disp)
        # End of load = ~first third of cumulative hand motion before contact
        load_rel = int(np.searchsorted(cumdisp, cumdisp[-1] * 0.3))
        load_end = window_start + load_rel
    else:
        load_end = max(window_start + 1, plant // 3)

    # Clamp load_end
    load_end = min(load_end, contact - 2)
    load_end = max(window_start, load_end)

    labels: list[str] = ["idle"] * T
    for t in range(window_start, T):
        if t <= load_end:
            # First frame of window is always stance (standing at address).
            is_stance = (t == window_start) or hand_disp[t] < hand_disp[load_end] * 0.15
            labels[t] = "stance" if is_stance else "load"
        elif t < plant:
            labels[t] = "stride"
        elif t < contact:
            labels[t] = "swing"
        elif t == contact:
            labels[t] = "contact"
        else:
            labels[t] = "follow_through"

    # Refine: merge tiny stance/load clusters
    labels = _merge_short_phases(labels, min_len=3)
    return labels


def _merge_short_phases(labels: list[str], min_len: int = 3) -> list[str]:
    """Collapse phase runs shorter than *min_len* into neighbors.

    ``"idle"`` and ``"follow_through"`` are protected from merger
    because they are often valid long stretches.
    """
    if not labels:
        return labels

    out = list(labels)
    i = 0
    while i < len(out):
        j = i
        while j < len(out) and out[j] == out[i]:
            j += 1
        run_len = j - i
        if run_len < min_len and out[i] not in ("idle", "follow_through"):
            # merge into previous or next non-idle phase
            phase = out[i - 1] if i > 0 else out[j]
            # Prefer nearest non-idle
            for k in range(i, j):
                out[k] = phase
        i = j
    return out
