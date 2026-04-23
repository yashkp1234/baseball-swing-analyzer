"""Static coaching knowledge base — no LLM required.

Maps metric ranges to coaching cues. Used as fallback when cloud API is unavailable.
"""

from typing import Callable

MetricRule = Callable[[float], str | None]


RULES: list[tuple[str, MetricRule]] = [
    (
        "x_factor_at_contact",
        lambda v: None if 5 <= v <= 35 else (
            "X-factor is too small — focus on turning your hips more before your shoulders fire. Think 'hips lead, hands follow.'"
            if v < 5 else
            "X-factor is very large — ensure you're not over-rotating hips and getting stuck behind the ball."
        ),
    ),
    (
        "stride_plant_frame",
        lambda v: None if 15 <= v <= 40 else (
            "Foot plant is early — your stride may be rushed. Try a softer, controlled toe-tap load."
            if v < 15 else
            "Foot plant is late — you may be losing power because your lower half hasn't anchored before swing."
        ),
    ),
    (
        "wrist_peak_velocity_px_s",
        lambda v: None if v >= 1500 else (
            "Bat speed looks low — focus on a tighter hand path and earlier hip rotation to increase whip."
        ),
    ),
    (
        "left_knee_at_contact",
        lambda v: None if 10 <= v <= 45 else (
            "Front knee is too straight at contact — you're losing leverage. Maintain slight flexion through the ball."
            if v < 10 else
            "Front knee is very bent — you may be collapsing into the plate. Push into the ground for a firm front side."
        ),
    ),
    (
        "right_knee_at_contact",
        lambda v: None if 10 <= v <= 40 else (
            "Back knee is too straight — you may be losing power from your backside. Keep a slight sit as you rotate."
            if v < 10 else
            "Back knee is very bent — you may be sinking instead of rotating up through the ball."
        ),
    ),
    (
        "head_displacement_total",
        lambda v: None if v <= 60 else (
            "Head is moving a lot during the swing — stay centered over the plate from load to contact."
        ),
    ),
    (
        "lateral_spine_tilt_at_contact",
        lambda v: None if -15 <= v <= 15 else (
            "You may be leaning away from the plate at contact — stay stacked and drive through the middle of the ball."
        ),
    ),
]


def generate_static_report(metrics: dict) -> list[str]:
    """Build a coaching report from the static rule set."""
    cues: list[str] = []
    for name, rule in RULES:
        value = metrics.get(name)
        if isinstance(value, (int, float)):
            cue = rule(value)
            if cue:
                cues.append(cue)
    if not cues:
        cues.append("Swing mechanics look solid. Keep working on consistency and timing.")
    return cues
