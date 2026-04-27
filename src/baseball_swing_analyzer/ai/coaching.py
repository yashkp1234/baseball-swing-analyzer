"""AI coaching layer - cloud LLM integration and knowledge base."""

import cv2
import numpy as np

from baseball_swing_analyzer.reporter import summarize_metrics


_PROMPT_TEMPLATE = """You are an expert hitting coach reviewing a motion analysis report from a hitter video.

HITTER CONTEXT
- Sport: {sport}
- Handedness: {handedness}
- View type: {view_type}
- View confidence: {view_confidence}
- Pose confidence: {pose_confidence}

VALIDITY NOTE
- Hip, shoulder, X-factor, and spine-tilt angles are reliable only on frontal/back views with decent visibility.
- This clip should be treated as: {view_validity}

IMPORTANT
- Start with the biggest leak first, not a generic compliment sandwich.
- Compare the hitter's actual metric to a target range when you mention a mechanical issue.
- Define technical terms in plain language the first time you use them.
- Give one named drill or one short on-field cue for each correction.
- If confidence is limited, say so and avoid pretending the measurement is exact.

REFERENCE RANGES
- Peak hip-shoulder separation target range: 25 to 45 degrees
- Hip-shoulder separation at contact (X-factor) target range: 10 to 30 degrees
- Time to contact target range: 0.14 to 0.20 seconds
- Attack angle target range: {attack_angle_target}

KEY METRICS

{metrics_summary}

OUTPUT
Write 3 to 4 bullet points.
- Bullet 1: one thing that is working and why it helps.
- Bullet 2: the biggest leak, the hitter's actual value, the target range, and why it costs performance.
- Bullet 3: a drill or cue tied directly to that leak.
- Bullet 4: only if needed, add a secondary issue or confidence caveat.

Keep each bullet to 1 to 2 sentences. Use plain language a youth player can understand."""


def build_coaching_prompt(metrics: dict) -> str:
    """Build an LLM prompt from a metrics dict."""
    summary = summarize_metrics(metrics)
    flags = metrics.get("flags", {})
    sport = metrics.get("sport") or metrics.get("sport_profile", {}).get("label") or "unknown"
    handedness = flags.get("handedness", "unknown")
    view_type = metrics.get("view_type", "unknown")
    view_confidence = metrics.get("view_confidence")
    pose_confidence = metrics.get("pose_confidence_mean")

    attack_angle_target = (
        "3 to 15 degrees for softball"
        if str(sport).lower() == "softball"
        else "5 to 20 degrees for baseball"
    )
    view_validity = _view_validity_note(view_type, view_confidence)

    return _PROMPT_TEMPLATE.format(
        sport=sport,
        handedness=handedness,
        view_type=view_type,
        view_confidence=_format_confidence(view_confidence),
        pose_confidence=_format_confidence(pose_confidence),
        view_validity=view_validity,
        attack_angle_target=attack_angle_target,
        metrics_summary=summary,
    )


def parse_coaching_text(response: str) -> list[str]:
    """Split raw LLM response into bullet points."""
    lines = [line.strip(" -•*") for line in response.splitlines() if line.strip()]
    return [line for line in lines if line]


def encode_image_for_api(frame: np.ndarray, fmt: str = ".jpg") -> str:
    """Encode a frame to base64 for vision API, returning a data URI."""
    import base64

    buf = cv2.imencode(fmt, frame)[1]
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def _format_confidence(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    return "unknown"


def _view_validity_note(view_type: object, view_confidence: object) -> str:
    label = str(view_type or "unknown").lower()
    confidence = float(view_confidence) if isinstance(view_confidence, (int, float)) else 0.0
    if label in {"frontal", "back"} and confidence >= 0.6:
        return "angle metrics are usable, but still hedge if pose quality is poor"
    if label == "side":
        return "timing and path are more trustworthy than rotational angle claims, so do not invent certainty"
    return "mixed view confidence; use angle-heavy claims carefully and hedge when needed"
