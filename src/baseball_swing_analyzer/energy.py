"""Kinetic chain analysis: velocity vectors, deceleration events, chain efficiency.

Computes where energy flows through the body during a swing and where it
leaks. This powers the 3D visualization's velocity arrows and efficiency markers.

The kinetic chain in baseball hitting flows:
    Hips → Shoulders → Arms/Hands → Bat

Good swings have a sequential cascade where each segment peaks AFTER
the previous one. Energy leaks show up as:
- Early hip opening (hips fire but shoulders don't follow quickly)
- Bat drag (hands lag behind shoulder rotation)
- Deceleration before contact (wrist velocity drops before the ball)
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


COCO_LHIP = 11
COCO_RHIP = 12
COCO_LSHOULDER = 5
COCO_RSHOULDER = 6
COCO_LWRIST = 9
COCO_RWRIST = 10
COCO_LELBOW = 7
COCO_RELBOW = 8


def compute_velocities(
    keypoints_3d: NDArray[np.floating],
    fps: float,
) -> dict[str, NDArray[np.float32]]:
    """Compute 3D velocity vectors for key joints.

    Returns dict of joint name → (T, 3) velocity arrays in world units/s.
    """
    dt = 1.0 / max(fps, 1.0)

    def vel(arr: NDArray) -> NDArray:
        d = np.diff(arr, axis=0, prepend=arr[0:1])
        return d / dt

    hip_mid = (keypoints_3d[:, COCO_LHIP] + keypoints_3d[:, COCO_RHIP]) / 2
    shoulder_mid = (keypoints_3d[:, COCO_LSHOULDER] + keypoints_3d[:, COCO_RSHOULDER]) / 2
    wrist_mid = (keypoints_3d[:, COCO_LWRIST] + keypoints_3d[:, COCO_RWRIST]) / 2

    return {
        "hip_center": vel(hip_mid).astype(np.float32),
        "shoulder_center": vel(shoulder_mid).astype(np.float32),
        "left_wrist": vel(keypoints_3d[:, COCO_LWRIST]).astype(np.float32),
        "right_wrist": vel(keypoints_3d[:, COCO_RWRIST]).astype(np.float32),
        "left_elbow": vel(keypoints_3d[:, COCO_LELBOW]).astype(np.float32),
        "right_elbow": vel(keypoints_3d[:, COCO_RELBOW]).astype(np.float32),
    }


def compute_speeds(
    velocities: dict[str, NDArray[np.floating]],
) -> dict[str, NDArray[np.float32]]:
    """Compute per-frame speed (magnitude of velocity) for each joint."""
    return {name: np.linalg.norm(vel, axis=1).astype(np.float32) for name, vel in velocities.items()}


def _cross_correlation_lag(a: NDArray, b: NDArray, max_lag: int = 10) -> int:
    """Find the lag that maximizes cross-correlation between two 1D signals.

    Positive lag means a leads b (a happens first).
    """
    best_corr = -np.inf
    best_lag = 0
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            corr = np.corrcoef(a[lag:], b[:len(a) - lag if lag else len(a)])[0, 1]
        else:
            corr = np.corrcoef(a[:len(a) + lag], b[-lag:])[0, 1]
        if not np.isnan(corr) and corr > best_corr:
            best_corr = corr
            best_lag = lag
    return best_lag


def compute_kinetic_chain_scores(
    keypoints_3d: NDArray[np.floating],
    fps: float,
) -> dict[str, float]:
    """Compute kinetic chain efficiency scores.

    Returns scores between 0 and 1 for each transfer segment:
    - hip_to_shoulder: how well hip rotation leads shoulder rotation
    - shoulder_to_hand: how well shoulder rotation leads hand speed
    - overall: weighted combination
    """
    velocities = compute_velocities(keypoints_3d, fps)
    speeds = compute_speeds(velocities)

    hip_speed = speeds["hip_center"]
    shoulder_speed = speeds["shoulder_center"]
    wrist_speed = speeds["right_wrist"]

    max_lag = min(10, len(hip_speed) // 3)

    if len(hip_speed) < 5:
        return {"hip_to_shoulder": 0.5, "shoulder_to_hand": 0.5, "overall": 0.5}

    lag_hs = _cross_correlation_lag(hip_speed, shoulder_speed, max_lag=max_lag)
    lag_sh = _cross_correlation_lag(shoulder_speed, wrist_speed, max_lag=max_lag)

    hip_to_shoulder = min(1.0, max(0.0, 0.5 + lag_hs * 0.15))
    shoulder_to_hand = min(1.0, max(0.0, 0.5 + lag_sh * 0.15))

    overall = hip_to_shoulder * 0.4 + shoulder_to_hand * 0.6

    return {
        "hip_to_shoulder": float(hip_to_shoulder),
        "shoulder_to_hand": float(shoulder_to_hand),
        "overall": float(overall),
    }


def detect_energy_loss_events(
    keypoints_3d: NDArray[np.floating],
    fps: float,
    phase_labels: list[str],
) -> list[dict]:
    """Detect moments where kinetic energy is lost in the swing.

    Returns a list of events, each with:
    - frame: frame index
    - joint: which joint lost energy
    - type: 'deceleration' or 'early_opening' or 'push_off_loss'
    - magnitude_pct: percentage drop in velocity
    - description: human-readable description
    """
    velocities = compute_velocities(keypoints_3d, fps)
    speeds = compute_speeds(velocities)
    events: list[dict] = []

    T = keypoints_3d.shape[0]
    if T < 5:
        return events

    contact_idx = None
    try:
        contact_idx = phase_labels.index("contact")
    except ValueError:
        pass

    for name in ["right_wrist", "left_wrist", "hip_center", "right_elbow"]:
        if name not in speeds:
            continue
        speed = speeds[name]
        mean_speed = speed[speed > 0].mean() if (speed > 0).any() else 1.0

        if mean_speed < 1e-6:
            continue

        for t in range(2, T - 2):
            before = speed[t - 2:t].mean()
            after = speed[t:t + 2].mean()
            if before < mean_speed * 0.1:
                continue

            drop_pct = max(0, (1 - after / before) * 100)
            if drop_pct > 20 and before > mean_speed * 0.3:
                joint_label = name.replace("_", " ")

                if name in ("right_wrist", "left_wrist") and contact_idx and t < contact_idx:
                    desc = f"Bat deceleration before contact — {drop_pct:.0f}% velocity loss"
                    etype = "deceleration"
                elif name == "hip_center" and contact_idx and t < contact_idx - 3:
                    desc = f"Early hip energy dissipation — {drop_pct:.0f}% loss"
                    etype = "early_opening"
                else:
                    desc = f"{joint_label} velocity drop — {drop_pct:.0f}%"
                    etype = "deceleration"

                events.append({
                    "frame": t,
                    "joint": name,
                    "type": etype,
                    "magnitude_pct": round(float(drop_pct), 1),
                    "description": desc,
                })

    events.sort(key=lambda e: e["frame"])

    seen = set()
    deduped = []
    for e in events:
        key = (e["frame"], e["joint"])
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    return deduped


def generate_full_energy_report(
    keypoints_3d: NDArray[np.floating],
    fps: float,
    phase_labels: list[str],
) -> dict:
    """Generate a complete energy analysis report.

    Returns dict with:
    - velocities: per-joint velocity vectors
    - speeds: per-joint speed arrays
    - kinetic_chain_scores: efficiency of energy transfer
    - energy_loss_events: detected moments of velocity loss
    """
    velocities = compute_velocities(keypoints_3d, fps)
    speeds = compute_speeds(velocities)
    chain_scores = compute_kinetic_chain_scores(keypoints_3d, fps)
    events = detect_energy_loss_events(keypoints_3d, fps, phase_labels)

    return {
        "velocities": {k: v.tolist() for k, v in velocities.items()},
        "speeds": {k: v.tolist() for k, v in speeds.items()},
        "kinetic_chain_scores": chain_scores,
        "energy_loss_events": events,
    }