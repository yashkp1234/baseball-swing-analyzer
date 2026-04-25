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
    from .metrics import (
        head_displacement,
        hip_angle,
        knee_angle,
        lateral_spine_tilt,
        phase_durations,
        shoulder_angle,
        stride_foot_plant_frame,
        torso_length_px,
        wrist_velocity,
        x_factor,
    )

    T = keypoints_seq.shape[0]
    durations = phase_durations(phase_labels)

    contact_idx = phase_labels.index("contact") if "contact" in phase_labels else T // 2

    kp_contact = keypoints_seq[contact_idx]

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
    }

    vel = wrist_velocity(keypoints_seq, fps)
    report["wrist_peak_velocity_px_s"] = float(vel.max())
    torso = torso_length_px(keypoints_seq)
    report["torso_length_px"] = torso
    report["wrist_peak_velocity_normalized"] = float(vel.max() / max(torso, 1.0))
    report["pose_confidence_mean"] = float(np.mean(keypoints_seq[:, :, 2]))
    report["frames"] = T
    report["fps"] = fps
    report["phase_labels"] = phase_labels
    return report
