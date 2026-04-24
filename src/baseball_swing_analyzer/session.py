"""Multi-swing session analysis: compare swings, track consistency, and build session-level metrics."""

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray


def dtw_distance(seq_a: NDArray[np.floating], seq_b: NDArray[np.floating]) -> float:
    """Compute Euclidean DTW distance between two (T, K, D) sequences."""
    a = np.asarray(seq_a, dtype=float)
    b = np.asarray(seq_b, dtype=float)
    if a.ndim != b.ndim:
        raise ValueError(f"dimensionality mismatch: {a.ndim} vs {b.ndim}")
    # Flatten keypoint dimensions
    a = a.reshape(a.shape[0], -1)
    b = b.reshape(b.shape[0], -1)

    n, m = a.shape[0], b.shape[0]
    dtw = np.full((n + 1, m + 1), np.inf)
    dtw[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = float(np.linalg.norm(a[i - 1] - b[j - 1]))
            dtw[i, j] = cost + min(dtw[i - 1, j], dtw[i, j - 1], dtw[i - 1, j - 1])

    return float(dtw[n, m])


def session_consistency(
    swing_reports: list[dict[str, float]],
    metric_names: list[str] | None = None,
) -> dict[str, dict[str, float]]:
    """Compute mean and std dev per metric across multiple swings.

    Returns a nested dict {metric: {mean, std, cv}}.
    """
    if metric_names is None:
        metric_names = [
            "stride_plant_frame",
            "contact_frame",
            "hip_angle_at_contact",
            "shoulder_angle_at_contact",
            "x_factor_at_contact",
            "spine_tilt_at_contact",
            "left_knee_at_contact",
            "right_knee_at_contact",
            "head_displacement_total",
            "wrist_peak_velocity_px_s",
        ]

    summary: dict[str, dict[str, float]] = {}
    for name in metric_names:
        values = [r[name] for r in swing_reports if isinstance(r.get(name), (int, float))]
        if not values:
            continue
        arr = np.array(values, dtype=float)
        mean = float(arr.mean())
        std = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
        summary[name] = {
            "mean": mean,
            "std": std,
            "cv": std / abs(mean) if mean != 0 else 0.0,
        }
    return summary


def pairwise_dtw(swing_arrays: list[NDArray[np.floating]]) -> NDArray[np.floating]:
    """Pairwise DTW matrix for N swing keypoint sequences."""
    n = len(swing_arrays)
    if n == 0:
        return np.zeros((0, 0), dtype=float)

    matrix = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            d = dtw_distance(swing_arrays[i], swing_arrays[j])
            matrix[i, j] = d
            matrix[j, i] = d
    return matrix


def build_session_report(swing_reports: list[dict]) -> dict:
    """Build a session-level report from per-swing metrics arrays."""
    consistency = session_consistency(swing_reports)

    all_flags = [r.get("flags", {}) for r in swing_reports]
    flag_summary: dict[str, Any] = {}
    if all_flags and isinstance(all_flags[0], dict):
        for key in all_flags[0].keys():
            vals = [f[key] for f in all_flags if key in f]
            if isinstance(vals[0], bool):
                flag_summary[key] = {"true_pct": sum(vals) / len(vals) * 100}
            elif isinstance(vals[0], str):
                from collections import Counter
                flag_summary[key] = dict(Counter(vals))

    return {
        "swing_count": len(swing_reports),
        "metric_consistency": consistency,
        "flag_trends": flag_summary,
    }


def write_session_report(report: dict, output_path: Path) -> None:
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
