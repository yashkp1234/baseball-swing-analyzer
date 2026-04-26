from __future__ import annotations

from typing import Any


_SPORT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "baseball": ("baseball", "batting_practice", "batting-practice"),
    "softball": ("softball", "fastpitch", "slowpitch"),
}
_MECHANICS_THRESHOLD = 0.68
_MECHANICS_MARGIN = 0.12


def detect_sport_profile(original_filename: str, metrics: dict[str, Any]) -> dict[str, Any]:
    lowered = original_filename.lower()
    filename_label: str | None = None

    for label, keywords in _SPORT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            filename_label = label
            break

    pose_confidence = float(metrics.get("pose_confidence_mean", 0.0) or 0.0)
    mechanics_label, mechanics_confidence, mechanics_reasons = _detect_from_mechanics(metrics, pose_confidence)

    if filename_label and mechanics_label and filename_label != mechanics_label:
        return {
            "label": "unknown",
            "confidence": round(max(0.45, mechanics_confidence), 2),
            "context_confidence": 0.95,
            "mechanics_confidence": mechanics_confidence,
            "reasons": [
                f"Filename suggests {filename_label}, but swing mechanics suggest {mechanics_label}",
                "Falling back to generic hitting guidance because sport signals conflict",
            ],
        }

    if filename_label:
        return {
            "label": filename_label,
            "confidence": 0.92 if filename_label == mechanics_label or mechanics_label is None else 0.88,
            "context_confidence": 0.95,
            "mechanics_confidence": mechanics_confidence,
            "reasons": [f"Filename strongly suggests {filename_label}", *mechanics_reasons[:2]],
        }

    if mechanics_label:
        return {
            "label": mechanics_label,
            "confidence": mechanics_confidence,
            "context_confidence": 0.2,
            "mechanics_confidence": mechanics_confidence,
            "reasons": mechanics_reasons,
        }

    return {
        "label": "unknown",
        "confidence": round(max(0.2, min(0.45, pose_confidence * 0.55)), 2),
        "context_confidence": 0.2,
        "mechanics_confidence": round(max(0.3, min(0.5, pose_confidence * 0.55)), 2),
        "reasons": ["No strong baseball or softball signal detected"],
    }


def _detect_from_mechanics(metrics: dict[str, Any], pose_confidence: float) -> tuple[str | None, float, list[str]]:
    flags = metrics.get("flags")
    if not isinstance(flags, dict):
        flags = {}

    baseball_score = 0.0
    softball_score = 0.0
    baseball_reasons: list[str] = []
    softball_reasons: list[str] = []

    x_factor = float(metrics.get("x_factor_at_contact", 0.0) or 0.0)
    wrist_velocity = float(metrics.get("wrist_peak_velocity_normalized", 0.0) or 0.0)
    head_displacement = float(metrics.get("head_displacement_total", 0.0) or 0.0)
    leg_action = str(flags.get("leg_action", "") or "")
    finish_height = str(flags.get("finish_height", "") or "")

    if x_factor >= 18.0:
        baseball_score += 0.34
        baseball_reasons.append("Large hip-shoulder separation is closer to baseball patterns")
    elif x_factor <= 12.0:
        softball_score += 0.34
        softball_reasons.append("Compact hip-shoulder separation is closer to softball patterns")

    if wrist_velocity >= 2.2:
        baseball_score += 0.28
        baseball_reasons.append("Higher hand-speed proxy favors baseball interpretation")
    elif wrist_velocity <= 1.5:
        softball_score += 0.28
        softball_reasons.append("More compact hand-speed proxy favors softball interpretation")

    if head_displacement <= 16.0:
        baseball_score += 0.18
        baseball_reasons.append("Lower head drift fits the baseball heuristic better")
    elif head_displacement >= 24.0:
        softball_score += 0.18
        softball_reasons.append("Larger forward move fits the softball heuristic better")

    if leg_action == "leg_kick":
        baseball_score += 0.16
        baseball_reasons.append("Leg kick cue points toward baseball timing")
    elif leg_action in {"toe_tap", "neither"}:
        softball_score += 0.16
        softball_reasons.append("Toe-tap or quieter gather points toward softball timing")

    if finish_height == "high":
        baseball_score += 0.1
        baseball_reasons.append("Higher finish favors baseball interpretation")
    elif finish_height == "low":
        softball_score += 0.1
        softball_reasons.append("Lower finish favors softball interpretation")

    confidence_scale = 0.65 + 0.35 * max(0.0, min(pose_confidence, 1.0))
    baseball_confidence = round(min(0.94, baseball_score * confidence_scale), 2)
    softball_confidence = round(min(0.94, softball_score * confidence_scale), 2)

    if baseball_confidence >= _MECHANICS_THRESHOLD and baseball_confidence - softball_confidence >= _MECHANICS_MARGIN:
        return "baseball", baseball_confidence, baseball_reasons
    if softball_confidence >= _MECHANICS_THRESHOLD and softball_confidence - baseball_confidence >= _MECHANICS_MARGIN:
        return "softball", softball_confidence, softball_reasons
    return None, round(max(baseball_confidence, softball_confidence), 2), []
