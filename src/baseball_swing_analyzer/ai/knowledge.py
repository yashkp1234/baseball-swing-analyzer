"""Static coaching knowledge base - no LLM required.

Maps metric ranges to coaching cues. Used as fallback when cloud API is unavailable.
"""

from typing import Any, Callable

MetricRule = Callable[[float], str | None]


RULES: list[tuple[str, MetricRule]] = [
    (
        "x_factor_at_contact",
        lambda v: None
        if 5 <= v <= 35
        else (
            "Hip-shoulder separation (X-factor) is low. Let the hips start the turn before the shoulders and hands follow."
            if v < 5
            else "Hip-shoulder separation (X-factor) is high. Your upper and lower body may be getting too far apart, which can leave the bat late to contact."
        ),
    ),
    (
        "stride_plant_frame",
        lambda v: None
        if 15 <= v <= 40
        else (
            "Your front foot is landing early. Slow the stride down so you can stay gathered before you turn."
            if v < 15
            else "Your front foot is landing late. Get it down a little sooner so the lower half is braced before the swing."
        ),
    ),
    (
        "wrist_peak_velocity_normalized",
        lambda v: None
        if v >= 5.0
        else "Bat speed looks low. Focus on a tighter hand path and let the hips start the move earlier.",
    ),
    (
        "left_knee_at_contact",
        lambda v: None
        if 10 <= v <= 45
        else (
            "Your front knee is too straight at contact. Keep a little bend so you can hold leverage through contact."
            if v < 10
            else "Your front knee is very bent at contact. Push into the ground a little more so the front side can brace."
        ),
    ),
    (
        "right_knee_at_contact",
        lambda v: None
        if 10 <= v <= 40
        else (
            "Your back knee is too straight. Keep a little bend so the back side can keep driving the turn."
            if v < 10
            else "Your back knee is very bent. Make sure you are turning through the ball instead of sinking under it."
        ),
    ),
    (
        "head_displacement_total",
        lambda v: None
        if v <= 60
        else "Your head is moving too much from load to contact. Staying more centered should make timing easier.",
    ),
    (
        "lateral_spine_tilt_at_contact",
        lambda v: None
        if -15 <= v <= 15
        else "You may be leaning away at contact. Try to stay more stacked through the middle of the swing.",
    ),
]


FLAG_CUES: dict[str, list[tuple[Callable[[Any], bool], str]]] = {
    "front_shoulder_closed_load": [
        (
            lambda v: not v,
            "Your front shoulder is opening early. Keep it closed a beat longer so the torso stays loaded.",
        ),
    ],
    "hip_casting": [
        (
            lambda v: v is True,
            "Your hips are spinning early. Let the stride foot get down before the hips really fire.",
        ),
    ],
    "arm_slot_at_contact": [
        (
            lambda v: v == "high",
            "Your hands are working high at contact. Make sure you are turning through the ball instead of pushing the barrel down to it.",
        ),
        (
            lambda v: v == "low",
            "Your hands are working low at contact. Make sure the back shoulder is not dropping under the swing.",
        ),
    ],
}


def generate_static_report(metrics: dict) -> list[str]:
    """Build a coaching report from the static rule set + qualitative flags."""
    pcm = metrics.get("pose_confidence_mean", 1.0)
    if pcm < 0.4:
        return [
            (
                f"Pose detection confidence is low ({pcm*100:.0f}%). "
                "Results may be unreliable - try a video with better lighting, "
                "less occlusion, or the full body in frame."
            )
        ]

    cues: list[str] = []

    for name, rule in RULES:
        value = metrics.get(name)
        if isinstance(value, (int, float)):
            cue = rule(value)
            if cue:
                cues.append(cue)

    flags = metrics.get("flags")
    if isinstance(flags, dict):
        for name, conditions in FLAG_CUES.items():
            val = flags.get(name)
            for check, cue in conditions:
                if check(val):
                    cues.append(cue)

        leg = flags.get("leg_action")
        if leg == "leg_kick":
            cues.append("You are using a leg kick. Keep it under control so it does not pull the head forward.")
        elif leg == "neither":
            cues.append("There is very little leg lift. A small lift or toe-tap could help with rhythm and the load.")

        finish = flags.get("finish_height")
        if finish == "low":
            cues.append("Your finish stays low. Let the bat keep moving through contact instead of cutting off right after impact.")

    if not cues:
        cues.append("Swing mechanics look solid. Keep working on consistency and timing.")
    return cues
