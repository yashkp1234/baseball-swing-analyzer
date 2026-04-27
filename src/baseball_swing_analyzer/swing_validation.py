from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .metrics import torso_length_px, wrist_velocity, x_factor


@dataclass(frozen=True)
class SwingCandidate:
    start_frame: int
    end_frame: int
    source: str


@dataclass(frozen=True)
class SwingDecision:
    accepted: bool
    label: str
    confidence: float
    reason: str


VALID_SWING_LABELS = {
    "swing",
    "load_only",
    "pickup",
    "reset",
    "other_motion",
}


def extract_clip_features(
    keypoints_seq: NDArray[np.floating],
    fps: float,
) -> dict[str, float | bool]:
    seq = np.asarray(keypoints_seq, dtype=float)
    if seq.ndim != 3 or seq.shape[0] < 2:
        return {
            "bat_visible": False,
            "has_forward_commit": False,
            "has_follow_through": False,
            "hand_path_arc_ratio": 0.0,
            "net_hand_displacement_ratio": 0.0,
            "peak_velocity_frame_ratio": 1.0,
            "post_peak_motion_ratio": 0.0,
            "rotation_range_deg": 0.0,
        }

    hand_path = (seq[:, 9, :2] + seq[:, 10, :2]) / 2.0
    deltas = np.diff(hand_path, axis=0)
    step_lengths = np.linalg.norm(deltas, axis=1)
    arc_length = float(step_lengths.sum())
    net_displacement = float(np.linalg.norm(hand_path[-1] - hand_path[0]))
    torso_px = max(1.0, torso_length_px(seq))

    velocity = wrist_velocity(seq, fps).max(axis=1)
    peak_idx = int(np.argmax(velocity))
    peak_ratio = peak_idx / max(len(velocity) - 1, 1)
    peak_speed = float(max(float(velocity.max()), 1e-6))

    if peak_idx + 1 < len(velocity):
        post_peak_ratio = float(np.mean(velocity[peak_idx + 1 :]) / peak_speed)
    else:
        post_peak_ratio = 0.0

    rotations = np.asarray([x_factor(frame) for frame in seq], dtype=float)
    finite_rotations = rotations[np.isfinite(rotations)]
    rotation_range = float(finite_rotations.max() - finite_rotations.min()) if finite_rotations.size else 0.0

    return {
        "bat_visible": False,
        "has_forward_commit": (arc_length / torso_px) >= 0.9 and (net_displacement / torso_px) >= 0.35 and 0.2 <= peak_ratio <= 0.85,
        "has_follow_through": post_peak_ratio >= 0.18 and peak_ratio <= 0.8,
        "hand_path_arc_ratio": arc_length / torso_px,
        "net_hand_displacement_ratio": net_displacement / torso_px,
        "peak_velocity_frame_ratio": peak_ratio,
        "post_peak_motion_ratio": post_peak_ratio,
        "rotation_range_deg": rotation_range,
    }


class SwingValidator:
    def classify_candidate(self, candidate: SwingCandidate, **kwargs) -> SwingDecision:
        raise NotImplementedError


class HeuristicSwingValidator(SwingValidator):
    def classify_candidate(self, candidate: SwingCandidate, **kwargs) -> SwingDecision:
        duration = candidate.end_frame - candidate.start_frame + 1
        if duration < 8:
            return SwingDecision(False, "other_motion", 0.2, "window too short")
        return SwingDecision(True, "swing", 0.5, "baseline validator")


class VisionSwingValidator(SwingValidator):
    def classify_candidate(self, candidate: SwingCandidate, **kwargs) -> SwingDecision:
        clip_features = kwargs.get("clip_features", {})
        has_bat = clip_features.get("bat_visible", False)
        has_direction_change = clip_features.get("has_forward_commit", False)
        has_follow_through = clip_features.get("has_follow_through", False)
        hand_path_arc_ratio = float(clip_features.get("hand_path_arc_ratio", 0.0))
        net_hand_displacement_ratio = float(clip_features.get("net_hand_displacement_ratio", 0.0))
        peak_ratio = float(clip_features.get("peak_velocity_frame_ratio", 1.0))
        rotation_range_deg = float(clip_features.get("rotation_range_deg", 0.0))

        if peak_ratio > 0.82 and not has_follow_through:
            return SwingDecision(False, "load_only", 0.78, "motion peaks late without follow-through")
        if hand_path_arc_ratio < 0.75 or net_hand_displacement_ratio < 0.25:
            return SwingDecision(False, "other_motion", 0.7, "hand path too small for a committed swing")
        if has_direction_change and has_follow_through and (has_bat or rotation_range_deg >= 12.0):
            confidence = 0.85 if has_bat else 0.72
            return SwingDecision(True, "swing", confidence, "committed move with usable follow-through")
        if has_direction_change and not has_follow_through:
            return SwingDecision(False, "load_only", 0.74, "forward move never carries through contact")
        if has_bat and not has_direction_change:
            return SwingDecision(False, "load_only", 0.75, "bat visible but no committed forward move")
        return SwingDecision(False, "other_motion", 0.6, "window lacks enough swing evidence")
