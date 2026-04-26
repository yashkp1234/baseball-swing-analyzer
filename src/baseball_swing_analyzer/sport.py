from __future__ import annotations

from typing import Any


_SPORT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "baseball": ("baseball", "batting_practice", "batting-practice"),
    "softball": ("softball", "fastpitch", "slowpitch"),
}


def detect_sport_profile(original_filename: str, metrics: dict[str, Any]) -> dict[str, Any]:
    lowered = original_filename.lower()

    for label, keywords in _SPORT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return {
                "label": label,
                "confidence": 0.92,
                "context_confidence": 0.95,
                "mechanics_confidence": 0.5,
                "reasons": [f"Filename strongly suggests {label}"],
            }

    pose_confidence = float(metrics.get("pose_confidence_mean", 0.0) or 0.0)
    return {
        "label": "unknown",
        "confidence": round(max(0.2, min(0.45, pose_confidence * 0.55)), 2),
        "context_confidence": 0.2,
        "mechanics_confidence": round(max(0.3, min(0.5, pose_confidence * 0.55)), 2),
        "reasons": ["No strong baseball or softball signal detected"],
    }
