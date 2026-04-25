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


def classify_phases(
    keypoints_seq: NDArray[np.floating],
    fps: float = 30.0,
) -> list[str]:
    """Assign a phase label to every frame using heuristic rules.

    Works on both short clips (entire video is the swing) and long
    phone recordings where the batter waits before swinging (extra
    ``"idle"`` frames).
    """
    seq = np.asarray(keypoints_seq, dtype=float)
    if seq.ndim != 3 or seq.shape[1] != 17:
        raise ValueError("keypoints_seq must have shape (T, 17, D)")

    T = seq.shape[0]
    if T < 4:
        return ["idle"] * T

    from .metrics import wrist_velocity

    vel = wrist_velocity(seq, fps)           # (T, 2)
    max_vel = vel.max(axis=1)
    contact = int(np.argmax(max_vel))
    peak_vel = float(max_vel.max())

    if peak_vel == 0:
        return ["idle"] * T

    # Simple swing-window heuristic: find the period where motion is active
    # before and after contact. Use a threshold based on contact velocity.
    threshold = peak_vel * 0.10
    above = max_vel > threshold

    # Search backwards from contact for first sustained run below threshold
    # (with at least 8 frames of low-velocity — ~0.25s)
    window_start = contact
    for t in range(max(0, contact - T + 1), contact + 1):
        if t >= 8 and np.all(max_vel[t - 8:t] < threshold):
            window_start = t
            break

    # Search forwards from contact for end of follow-through (~10 frames)
    window_end = min(T - 1, contact + 10)
    for t in range(contact + 1, T):
        if t + 8 < T and np.all(max_vel[t:t + 8] < threshold):
            window_end = t
            break

    window_start = max(0, window_start - 2)  # slight cushion
    window_end = min(T - 1, window_end)

    if window_end <= window_start:
        return ["idle"] * T

    # --- Inside the swing window, find sub-phases ---
    window_len = window_end - window_start + 1

    # Stride plant: ankle minima inside the swing window
    # (use the sub-sequence, offset back by window_start after finding)
    from .metrics import stride_foot_plant_frame
    window_seq = seq[window_start:window_end + 1]
    plant_rel = stride_foot_plant_frame(window_seq)
    if plant_rel is None:
        plant_rel = max(1, (window_len // 2) - 2)
    plant = window_start + plant_rel

    # Clamp plant
    plant = max(window_start + 1, min(plant, contact - 1))

    # Stance vs Load: use hand displacement inside window
    lw = seq[:, 9, :2]
    rw = seq[:, 10, :2]
    hands = (lw + rw) / 2.0
    hand_disp = np.linalg.norm(np.diff(hands, axis=0, prepend=hands[0:1]), axis=1)

    window_disp = hand_disp[window_start:contact + 1]
    if len(window_disp) > 10:
        cumdisp = np.cumsum(window_disp)
        load_rel = int(np.searchsorted(cumdisp, cumdisp[-1] * 0.3))
        load_end = window_start + load_rel
    else:
        load_end = max(window_start + 1, plant // 2)

    load_end = min(load_end, contact - 2)
    load_end = max(window_start + 1, load_end)

    # --- Assign labels ---
    labels: list[str] = ["idle"] * T
    for t in range(window_start, window_end + 1):
        if t <= load_end:
            is_stance = t == window_start
            labels[t] = "stance" if is_stance else "load"
        elif t < plant:
            labels[t] = "stride"
        elif t < contact:
            labels[t] = "swing"
        elif t == contact:
            labels[t] = "contact"
        else:
            labels[t] = "follow_through"

    # Protect "contact" and "follow_through" from merger; merge others
    labels = _merge_short_phases(labels, min_len=3, protected={"contact", "follow_through", "idle"})
    return labels


def _merge_short_phases(
    labels: list[str],
    min_len: int = 3,
    protected: set[str] | None = None,
) -> list[str]:
    """Collapse phase runs shorter than *min_len* into neighbors."""
    protected = protected or set()
    if not labels:
        return labels

    out = list(labels)
    i = 0
    while i < len(out):
        j = i
        while j < len(out) and out[j] == out[i]:
            j += 1
        run_len = j - i
        if run_len < min_len and out[i] not in protected:
            phase = out[i - 1] if i > 0 else out[j]
            for k in range(i, j):
                out[k] = phase
        i = j
    return out
