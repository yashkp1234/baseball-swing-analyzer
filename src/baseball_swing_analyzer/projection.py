from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math
from typing import Iterable


_UPPER_CHAIN = (5, 6, 7, 8, 9, 10)
_MAX_X_FACTOR_DELTA = 12.0
_MAX_HEAD_STABILITY_DELTA = 0.12


@dataclass(frozen=True)
class ProjectionRequest:
    x_factor_delta_deg: float = 0.0
    head_stability_delta_norm: float = 0.0


def project_swing_viewer_data(viewer_data: dict, request: ProjectionRequest) -> dict:
    projected = deepcopy(viewer_data)
    frames = projected.get("frames", [])
    if not frames:
        baseline = _estimate_projection_summary(projected.get("metrics", {}), 0.0, 0.0)
        return {
            "baseline": baseline,
            "projection": baseline,
            "viewer": projected,
        }

    x_factor_delta = _clamp(request.x_factor_delta_deg, -_MAX_X_FACTOR_DELTA, _MAX_X_FACTOR_DELTA)
    head_delta = _clamp(request.head_stability_delta_norm, -_MAX_HEAD_STABILITY_DELTA, _MAX_HEAD_STABILITY_DELTA)
    start_idx, contact_idx = _projection_window(projected)
    initial_nose = _point(frames[start_idx]["keypoints"], 0)

    for index, frame in enumerate(frames):
        amount = _window_amount(index, start_idx, contact_idx)
        if amount <= 0.0:
            continue
        _apply_x_factor(frame["keypoints"], x_factor_delta * amount)
        _apply_head_stability(frame["keypoints"], initial_nose, head_delta * amount)

    baseline = _estimate_projection_summary(projected.get("metrics", {}), 0.0, 0.0)
    projection = _estimate_projection_summary(projected.get("metrics", {}), x_factor_delta, head_delta)
    notes: list[str] = [
        "Pose-only estimate derived from swing mechanics proxies, not measured ball flight",
        "Projected from baseline swing metrics and viewer-space pose adjustments",
    ]
    sport_label = _sport_label(projected.get("metrics", {}))
    if sport_label == "unknown":
        notes.append("Using generic hitting calibration because sport was not confidently detected")
    elif sport_label in {"baseball", "softball"}:
        notes.append(f"Using {sport_label} interpretation where sport-specific wording applies")
    if x_factor_delta:
        notes.append(f"Applied {x_factor_delta:+.0f} deg x-factor delta")
    if head_delta:
        notes.append(f"Applied {head_delta:+.2f} normalized head-stability delta")

    projection["notes"] = notes
    return {
        "baseline": baseline,
        "projection": projection,
        "viewer": projected,
    }


def _estimate_projection_summary(metrics: dict, x_factor_delta: float, head_delta: float) -> dict[str, float | int | str]:
    base_x_factor = float(metrics.get("x_factor_at_contact", 0.0) or 0.0)
    head_displacement = float(metrics.get("head_displacement_total", 0.0) or 0.0)
    wrist_velocity = float(metrics.get("wrist_peak_velocity_normalized", 0.0) or 0.0)
    pose_confidence = float(metrics.get("pose_confidence_mean", 0.0) or 0.0)

    adjusted_x_factor = base_x_factor + x_factor_delta
    adjusted_head_displacement = max(0.0, head_displacement - (head_delta / _MAX_HEAD_STABILITY_DELTA) * 12.0)

    wrist_proxy = _clamp(wrist_velocity, 0.0, 6.0)
    head_penalty = min(adjusted_head_displacement / 30.0, 2.5)
    exit_velocity = 60.0 + wrist_proxy * 7.0 + adjusted_x_factor * 0.35 - head_penalty * 3.5
    carry_distance = 155.0 + max(exit_velocity - 65.0, 0.0) * 4.5 + adjusted_x_factor * 0.75 - head_penalty * 8.0
    score = 42.0 + wrist_proxy * 8.0 + adjusted_x_factor * 0.6 - head_penalty * 9.0
    exit_velocity = _clamp(exit_velocity, 55.0, 110.0)
    carry_distance = _clamp(carry_distance, 140.0, 395.0)
    score = _clamp(score, 20.0, 99.0)

    confidence = _clamp(pose_confidence, 0.0, 1.0)
    ev_spread = _clamp(10.0 - confidence * 5.0, 4.0, 10.0)
    carry_spread = _clamp(ev_spread * 4.5, 18.0, 45.0)

    return {
        "estimate_basis": "pose_proxy",
        "exit_velocity_mph": round(exit_velocity, 1),
        "exit_velocity_mph_low": round(_clamp(exit_velocity - ev_spread, 50.0, 110.0), 1),
        "exit_velocity_mph_high": round(_clamp(exit_velocity + ev_spread, 50.0, 118.0), 1),
        "carry_distance_ft": round(carry_distance, 1),
        "carry_distance_ft_low": round(_clamp(carry_distance - carry_spread, 120.0, 395.0), 1),
        "carry_distance_ft_high": round(_clamp(carry_distance + carry_spread, 120.0, 410.0), 1),
        "score": int(round(score)),
    }


def _projection_window(viewer_data: dict) -> tuple[int, int]:
    phase_labels = viewer_data.get("phase_labels") or []
    contact_idx = int(viewer_data.get("contact_frame", max(0, len(phase_labels) - 1)) or 0)
    start_idx = _first_phase_index(phase_labels, "load")
    if start_idx is None:
        start_idx = max(0, contact_idx - 12)
    return start_idx, contact_idx


def _first_phase_index(phases: Iterable[str], target: str) -> int | None:
    for index, phase in enumerate(phases):
        if phase == target:
            return index
    return None


def _window_amount(index: int, start_idx: int, contact_idx: int) -> float:
    if index < start_idx:
        return 0.0
    if contact_idx <= start_idx:
        return 1.0
    if index >= contact_idx:
        return 1.0
    progress = (index - start_idx) / float(contact_idx - start_idx)
    return 0.5 - 0.5 * math.cos(progress * math.pi)


def _apply_x_factor(keypoints: list[list[float]], delta_deg: float) -> None:
    hip_left = _point(keypoints, 11)
    hip_right = _point(keypoints, 12)
    if hip_left is None or hip_right is None:
        return
    hip_center = [
        (hip_left[0] + hip_right[0]) / 2.0,
        (hip_left[1] + hip_right[1]) / 2.0,
        (hip_left[2] + hip_right[2]) / 2.0,
    ]
    for joint_index in _UPPER_CHAIN:
        point = _point(keypoints, joint_index)
        if point is None:
            continue
        keypoints[joint_index] = _rotate_xz(point, hip_center, delta_deg)


def _apply_head_stability(keypoints: list[list[float]], initial_nose: list[float] | None, head_delta: float) -> None:
    current_nose = _point(keypoints, 0)
    if initial_nose is None or current_nose is None or head_delta == 0.0:
        return
    factor = head_delta / _MAX_HEAD_STABILITY_DELTA
    translation = [
        -(current_nose[0] - initial_nose[0]) * factor,
        -(current_nose[1] - initial_nose[1]) * factor,
        -(current_nose[2] - initial_nose[2]) * factor,
    ]
    for joint_index in _UPPER_CHAIN:
        point = _point(keypoints, joint_index)
        if point is None:
            continue
        keypoints[joint_index] = [
            round(point[0] + translation[0], 6),
            round(point[1] + translation[1], 6),
            round(point[2] + translation[2], 6),
        ]


def _rotate_xz(point: list[float], origin: list[float], delta_deg: float) -> list[float]:
    radians = math.radians(delta_deg)
    rel_x = point[0] - origin[0]
    rel_z = point[2] - origin[2]
    cos_v = math.cos(radians)
    sin_v = math.sin(radians)
    rot_x = rel_x * cos_v - rel_z * sin_v
    rot_z = rel_x * sin_v + rel_z * cos_v
    return [
        round(origin[0] + rot_x, 6),
        round(point[1], 6),
        round(origin[2] + rot_z, 6),
    ]


def _point(keypoints: list[list[float]], index: int) -> list[float] | None:
    if index >= len(keypoints):
        return None
    point = keypoints[index]
    if len(point) < 3 or any(not math.isfinite(value) for value in point[:3]):
        return None
    return [float(point[0]), float(point[1]), float(point[2])]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _sport_label(metrics: dict) -> str:
    sport_profile = metrics.get("sport_profile")
    if isinstance(sport_profile, dict):
        label = sport_profile.get("label")
        if isinstance(label, str):
            return label
    return "unknown"
