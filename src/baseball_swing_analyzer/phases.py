"""Rule-based swing phase detection from keypoint kinematics."""

import numpy as np
from numpy.typing import NDArray


PHASE_LABELS = [
    "stance",
    "load",
    "stride",
    "swing",
    "contact",
    "follow_through",
]


def classify_phases(keypoints_seq: NDArray[np.floating]) -> list[str]:
    """Assign a phase label to every frame using heuristic rules.

    Rules (order matters):
    1. **stance** — before hands begin moving backward.
    2. **load** — hands move backward (loading / cocking phase).
    3. **stride** — back foot/ankle moving toward plate until plant.
    4. **swing** — bat (wrist proxy) accelerating forward after stride plant.
    5. **contact** — nearest frame to peak wrist velocity.
    6. **follow_through** — everything after contact.

    Parameters
    ----------
    keypoints_seq :
        Shape ``(T, 17, 2|3)`` COCO keypoint array.

    Returns
    -------
    labels :
        Length ``T`` list of phase strings.
    """
    seq = np.asarray(keypoints_seq, dtype=float)
    if seq.ndim != 3 or seq.shape[1] != 17:
        raise ValueError("keypoints_seq must have shape (T, 17, D)")

    T = seq.shape[0]
    if T < 4:
        return ["stance"] * T

    from .metrics import (
        stride_foot_plant_frame,
        wrist_velocity,
    )

    fps = 60.0  # default; caller can rescale if needed
    vel = wrist_velocity(seq, fps)  # (T, 2)
    max_vel = vel.max(axis=1)
    contact = int(np.argmax(max_vel))

    plant = stride_foot_plant_frame(seq)
    if plant is None:
        plant = max(1, contact - 5)

    # Split load vs stance using hand movement
    lw = seq[:, 9, :2]
    rw = seq[:, 10, :2]
    hands = (lw + rw) / 2.0
    hand_disp = np.linalg.norm(np.diff(hands, axis=0, prepend=hands[0:1]), axis=1)
    # Frame where cumulative backward hand displacement is greatest = end of load
    cumdisp = np.cumsum(hand_disp)
    load_end = int(np.searchsorted(cumdisp, cumdisp[-1] * 0.3)) if T > 10 else max(1, plant // 3)

    labels: list[str] = []
    for t in range(T):
        if t <= load_end:
            labels.append("stance" if hand_disp[t] < hand_disp[load_end] * 0.2 else "load")
        elif t < plant:
            labels.append("stride")
        elif t < contact:
            labels.append("swing")
        elif t == contact:
            labels.append("contact")
        else:
            labels.append("follow_through")

    # Refine: merge tiny stance/load clusters
    labels = _merge_short_phases(labels, min_len=3)
    return labels


def _merge_short_phases(labels: list[str], min_len: int = 3) -> list[str]:
    """Collapse phase runs shorter than *min_len* into neighbors."""
    if not labels:
        return labels

    out = list(labels)
    i = 0
    while i < len(out):
        j = i
        while j < len(out) and out[j] == out[i]:
            j += 1
        run_len = j - i
        if run_len < min_len:
            # merge into previous or next phase
            if i > 0:
                phase = out[i - 1]
            elif j < len(out):
                phase = out[j]
            else:
                break
            for k in range(i, j):
                out[k] = phase
        i = j
    return out
