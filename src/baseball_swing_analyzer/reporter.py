"""Reporter: metrics JSON and console summary."""

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


def write_metrics_json(
    metrics: dict,
    output_path: Path,
) -> None:
    """Write *metrics* dict to *output_path* as JSON."""
    output_path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")


def summarize_metrics(metrics: dict) -> str:
    """Return a human-readable summary table string."""
    lines: list[str] = ["=" * 40, "SWING METRICS", "=" * 40]
    for name, value in metrics.items():
        if name == "flags" and isinstance(value, dict):
            lines.append(f"  {name:30s} {str(value):10s}")
        elif name == "phase_labels":
            continue
        elif isinstance(value, float):
            lines.append(f"  {name:30s} {value:10.2f}")
        else:
            lines.append(f"  {name:30s} {str(value):10s}")
    lines.append("=" * 40)
    return "\n".join(lines)


def build_report(
    phase_labels: list[str],
    keypoints_seq: NDArray[np.floating],
    fps: float,
) -> dict:
    """Compute all Phase 1 metrics from labels + pose and return a flat dict."""
    from .energy import compute_kinetic_chain_scores
    from .metrics import (
        head_displacement,
        hip_angle,
        knee_angle,
        lateral_spine_tilt,
        phase_durations,
        shoulder_angle,
        clip_metric,
        stride_foot_plant_frame,
        torso_length_px,
        wrist_velocity,
        x_factor,
    )

    T = keypoints_seq.shape[0]
    durations = phase_durations(phase_labels)

    contact_idx = phase_labels.index("contact") if "contact" in phase_labels else T // 2

    kp_contact = keypoints_seq[contact_idx]
    torso = torso_length_px(keypoints_seq)
    separations = np.array([x_factor(frame) for frame in keypoints_seq], dtype=float)
    peak_separation_idx = int(np.nanargmax(np.abs(separations))) if len(separations) else 0
    peak_separation = float(np.abs(separations[peak_separation_idx])) if len(separations) else 0.0
    contact_separation = float(np.abs(separations[contact_idx])) if len(separations) else 0.0
    frames_from_peak_to_contact = max(contact_idx - peak_separation_idx, 1)
    closure_rate = (peak_separation - contact_separation) / frames_from_peak_to_contact
    active_start_idx = _time_to_contact_start_frame(phase_labels, contact_idx, fps)
    head_drop_pct, head_drift_pct = _split_head_movement(keypoints_seq, torso)
    chain_scores = compute_kinetic_chain_scores(keypoints_seq[:, :, :3], fps)
    view_type, view_confidence = _infer_view(keypoints_seq, torso)
    hip_to_shoulder = chain_scores.get("hip_to_shoulder", {})
    shoulder_to_hand = chain_scores.get("shoulder_to_hand", {})

    report: dict = {
        "phase_durations": durations,
        "stride_plant_frame": stride_foot_plant_frame(keypoints_seq),
        "contact_frame": contact_idx,
        "hip_angle_at_contact": float(hip_angle(kp_contact)),
        "shoulder_angle_at_contact": float(shoulder_angle(kp_contact)),
        "x_factor_at_contact": float(x_factor(kp_contact)),
        "spine_tilt_at_contact": float(lateral_spine_tilt(kp_contact)),
        "left_knee_at_contact": float(knee_angle(kp_contact, "left")),
        "right_knee_at_contact": float(knee_angle(kp_contact, "right")),
        "head_displacement_total": float(head_displacement(keypoints_seq)),
        "peak_separation_deg": float(clip_metric(peak_separation, 0.0, 90.0)),
        "peak_separation_frame": peak_separation_idx,
        "separation_closure_rate": float(clip_metric(closure_rate, -90.0, 90.0)),
        "time_to_contact_s": float(max(contact_idx - active_start_idx, 0) / max(fps, 1.0)),
        "head_drop_pct": float(clip_metric(head_drop_pct, 0.0, 100.0)),
        "head_drift_pct": float(clip_metric(head_drift_pct, 0.0, 100.0)),
        "kinetic_chain": {
            "hip_to_shoulder_lag_frames": int(hip_to_shoulder.get("lag_frames", 0)),
            "hip_to_shoulder_direction": str(hip_to_shoulder.get("direction", "synced")),
            "shoulder_to_hand_lag_frames": int(shoulder_to_hand.get("lag_frames", 0)),
            "shoulder_to_hand_direction": str(shoulder_to_hand.get("direction", "synced")),
            "sequence_order_correct": (
                hip_to_shoulder.get("direction") == "leads"
                and shoulder_to_hand.get("direction") == "leads"
            ),
        },
        "view_type": view_type,
        "view_confidence": view_confidence,
    }

    vel = wrist_velocity(keypoints_seq, fps)
    report["wrist_peak_velocity_px_s"] = float(vel.max())
    report["torso_length_px"] = torso
    report["wrist_peak_velocity_normalized"] = clip_metric(float(vel.max() / max(torso, 1.0)), 0.0, 12.0)
    report["pose_confidence_mean"] = float(np.mean(keypoints_seq[:, :, 2]))
    report["head_displacement_total"] = clip_metric(report["head_displacement_total"], 0.0, 200.0)
    angle_view_safe = view_type in {"frontal", "back"} and view_confidence >= 0.6
    report["measurement_reliability"] = (
        "low" if report["pose_confidence_mean"] < 0.55 or not angle_view_safe else "normal"
    )
    report["frames"] = T
    report["fps"] = fps
    report["phase_labels"] = phase_labels
    return report


def _time_to_contact_start_frame(phase_labels: list[str], contact_idx: int, fps: float) -> int:
    for target in ("swing", "stride", "load"):
        for index, label in enumerate(phase_labels):
            if label == target:
                return index
    fallback_frames = max(3, int(round(max(fps, 1.0) * 0.12)))
    return max(0, contact_idx - fallback_frames)


def _split_head_movement(keypoints_seq: NDArray[np.floating], torso_length: float) -> tuple[float, float]:
    seq = np.asarray(keypoints_seq, dtype=float)
    nose = seq[:, 0, :2]
    if len(nose) == 0:
        return 0.0, 0.0

    x0 = float(nose[0, 0])
    y_positions = nose[:, 1]
    x_positions = nose[:, 0]
    scale = max(float(torso_length), 1.0)

    head_drop_pct = (float(np.max(y_positions)) - float(np.min(y_positions))) / scale * 100.0
    head_drift_pct = float(np.max(np.abs(x_positions - x0))) / scale * 100.0
    return head_drop_pct, head_drift_pct


def _infer_view(keypoints_seq: NDArray[np.floating], torso_length: float) -> tuple[str, float]:
    seq = np.asarray(keypoints_seq, dtype=float)
    shoulder_widths = np.linalg.norm(seq[:, 5, :2] - seq[:, 6, :2], axis=1)
    valid_widths = shoulder_widths[shoulder_widths > 1.0]
    if len(valid_widths) == 0:
        return "unknown", 0.2

    width_ratio = float(np.median(valid_widths) / max(torso_length, 1.0))
    stability = 1.0 - min(1.0, float(np.std(valid_widths) / max(np.mean(valid_widths), 1.0)))

    if width_ratio >= 0.72:
        return "frontal", round(0.55 + 0.4 * stability, 2)
    if width_ratio <= 0.42:
        return "side", round(0.55 + 0.35 * stability, 2)
    return "three_quarter", round(0.5 + 0.3 * stability, 2)
