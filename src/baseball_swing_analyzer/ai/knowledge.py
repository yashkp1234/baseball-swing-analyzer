"""Static coaching knowledge base.

Maps metric ranges to structured coaching cues. Used as fallback when the cloud
API is unavailable or when we want deterministic baseline guidance.
"""

from dataclasses import asdict, dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class CoachingCue:
    issue: str
    cue: str
    why: str
    drill: str
    level: str
    tone: str = "warn"
    metric: str | None = None


MetricRule = Callable[[float, dict[str, Any]], CoachingCue | None]
FlagPredicate = Callable[[Any], bool]
ANGLE_SENSITIVE_METRICS = {
    "peak_separation_deg",
    "x_factor_at_contact",
    "lateral_spine_tilt_at_contact",
    "peak_pelvis_angular_velocity_deg_s",
    "peak_torso_angular_velocity_deg_s",
}


def _sport_label(metrics: dict[str, Any]) -> str:
    return str(metrics.get("sport") or metrics.get("sport_profile", {}).get("label") or "unknown").lower()


def _front_side_label(metrics: dict[str, Any]) -> str:
    handedness = str(metrics.get("flags", {}).get("handedness", "unknown")).lower()
    if handedness == "left":
        return "right side"
    if handedness == "right":
        return "left side"
    return "front side"


def _cue(
    issue: str,
    cue: str,
    why: str,
    drill: str,
    *,
    level: str = "youth",
    tone: str = "warn",
    metric: str | None = None,
) -> CoachingCue:
    return CoachingCue(
        issue=issue,
        cue=cue,
        why=why,
        drill=drill,
        level=level,
        tone=tone,
        metric=metric,
    )


RULES: list[tuple[str, MetricRule]] = [
    (
        "peak_separation_deg",
        lambda v, metrics: None
        if 30 <= v <= 55
        else _cue(
            "Low peak separation",
            "Let the hips start the turn before the shoulders chase them.",
            "Without enough early separation, the torso never stores stretch that can turn into bat speed.",
            "Hook 'Em drill: land the stride, then feel the back hip pull the chest and hands through.",
            metric="peak_separation_deg",
        )
        if v < 30
        else _cue(
            "Excessive peak separation",
            "Keep the torso connected to the turn so the upper and lower body do not drift too far apart.",
            "Too much separation can leave the barrel late because the chest and hands are still catching up.",
            "Walk-through swings: move through contact without freezing the torso behind the hips.",
            metric="peak_separation_deg",
        ),
    ),
    (
        "x_factor_at_contact",
        lambda v, metrics: None
        if 0 <= v <= 10
        else _cue(
            "Low closure into contact",
            "Your hips and shoulders are arriving together too early. Let the hips lead and the shoulders follow later.",
            "If the gap is already gone before contact, the swing loses stored stretch before the barrel can use it.",
            "Separation pause drill: stop at heel plant, then fire the hips before the chest and hands go.",
            metric="x_factor_at_contact",
        )
        if v < 0
        else _cue(
            "Late torso closure",
            "Hip-shoulder separation (X-factor) is still high at contact. Turn the chest through sooner so the barrel can catch up.",
            "At contact the gap should be small. Staying too separated this late usually means the bat is dragging behind the turn.",
            "Connection-ball turns: keep a towel or ball under the lead arm and turn through contact without leaving it behind.",
            metric="x_factor_at_contact",
        ),
    ),
    (
        "stride_plant_frame",
        lambda v, metrics: None
        if 15 <= v <= 40
        else _cue(
            "Early foot plant",
            "Your front foot is landing early. Slow the stride down so you stay gathered before you turn.",
            "An early landing can rush the move and force the upper body to start before the lower half is ready.",
            "Toe-tap load: gather softly, tap, then turn only after the foot settles.",
            metric="stride_plant_frame",
        )
        if v < 15
        else _cue(
            "Late foot plant",
            "Your front foot is landing late. Get it down a little sooner so the lower half is braced before the swing.",
            "Late plant timing makes the body choose between planting and turning at the same time, which leaks power.",
            "Walk-in plant drill: arrive on time, post up, then swing from a stable front side.",
            metric="stride_plant_frame",
        ),
    ),
    (
        "wrist_peak_velocity_normalized",
        lambda v, metrics: None
        if v >= 5.0
        else _cue(
            "Low bat-speed proxy",
            "Bat speed looks low. Tighten the hand path and let the hips start the move earlier.",
            "A longer hand path or late lower-half turn makes the barrel work harder for less speed.",
            "Short-path tee drill: launch the knob to the ball and feel the barrel turn tight around the body.",
            metric="wrist_peak_velocity_normalized",
        ),
    ),
    (
        "left_knee_at_contact",
        lambda v, metrics: None
        if 10 <= v <= 45
        else _cue(
            "Front knee too straight",
            "Keep a little bend in the front knee so the front side can hold leverage through contact.",
            "A locked-out front knee too early can cut off rotation before the barrel is all the way through the zone.",
            "Lead-leg brace drill: plant softly, then firm up through contact without snapping the knee straight.",
            metric="left_knee_at_contact",
        )
        if v < 10
        else _cue(
            "Front knee too soft",
            "Your front knee stays very bent at contact. Push into the ground a little more so the front side can brace.",
            "If the lead leg never firms up, the pelvis has nothing stable to turn around.",
            "Wall-post drill: land and rotate without letting the front knee drift toward the wall.",
            metric="left_knee_at_contact",
        ),
    ),
    (
        "right_knee_at_contact",
        lambda v, metrics: None
        if 10 <= v <= 40
        else _cue(
            "Back knee too straight",
            "Keep a little bend in the back knee so the back side can keep driving the turn.",
            "A straight back knee too early can stall the rear hip and flatten out the turn.",
            "Rear-knee turn drill: keep pressure inside the back foot as the hip drives the swing.",
            metric="right_knee_at_contact",
        )
        if v < 10
        else _cue(
            "Back knee too bent",
            "Your back knee stays very bent. Turn through the ball instead of sinking under it.",
            "Too much bend can trap the rear hip and send the swing under the ball instead of through it.",
            "Pivot-and-post drill: feel the back hip work around the front side instead of dropping under it.",
            metric="right_knee_at_contact",
        ),
    ),
    (
        "head_displacement_total",
        lambda v, metrics: None
        if v <= 60
        else _cue(
            "Head movement",
            "Your head is moving too much from load to contact. Stay more centered through the move.",
            "Extra head drift makes the ball harder to track and can change where contact happens from swing to swing.",
            "Balance-hold swings: freeze at launch and contact to feel the head staying inside the torso window.",
            metric="head_displacement_total",
        ),
    ),
    (
        "lateral_spine_tilt_at_contact",
        lambda v, metrics: None
        if -15 <= v <= 15
        else _cue(
            "Excessive spine tilt",
            "You may be leaning away at contact. Stay more stacked through the middle of the swing.",
            "Too much lean can drop the back shoulder and send the barrel under the ball.",
            "Knob-through-center drill: turn around the middle of the body without collapsing the torso.",
            metric="lateral_spine_tilt_at_contact",
        ),
    ),
    (
        "time_to_contact_s",
        lambda v, metrics: None
        if 0.13 <= v <= 0.20
        else _cue(
            "Quick but rushed swing",
            "Time to contact is very short, which usually means the body is jumping at the ball before the lower half is loaded.",
            "Pros sit around 0.14 to 0.18 seconds. Going much shorter often comes from the hands starting before the stride lands.",
            "Soft-toss with stride pause: gather, plant, hold for a beat, then turn through.",
            metric="time_to_contact_s",
        )
        if v < 0.13
        else _cue(
            "Slow trigger to contact",
            "Time to contact is long, which shrinks the window to read the pitch.",
            "Pros sit around 0.14 to 0.18 seconds. A longer move often means a long hand path or a late lower-half turn.",
            "Short-path tee work: launch the knob to the ball and feel the barrel turn tight to the body.",
            metric="time_to_contact_s",
        ),
    ),
    (
        "head_drop_pct",
        lambda v, metrics: None
        if v <= 12.0
        else _cue(
            "Head dropping through the swing",
            "The head is sinking a lot from load to contact, which makes the ball harder to track.",
            "Skilled hitters drop the head a little but stay consistent. A big drop usually means the back side is collapsing.",
            "Posture drill: swing with a ball balanced on the head, or freeze at contact and check that the eyes are still over the zone.",
            metric="head_drop_pct",
        ),
    ),
    (
        "head_drift_pct",
        lambda v, metrics: None
        if v <= 8.0
        else _cue(
            "Head drifting toward the pitcher",
            "The head is sliding forward during the swing, which moves the eyes and changes contact depth.",
            "Forward head movement is the worst kind of head motion because it makes the ball appear to move differently every swing.",
            "No-stride tee swings: take the stride out, rotate around a stable head, then add the stride back gradually.",
            metric="head_drift_pct",
        ),
    ),
    (
        "stride_length_normalized",
        lambda v, metrics: None
        if 1.5 <= v <= 5.0
        else _cue(
            "Short stride",
            "Stride length looks short, which can leave the lower half disconnected from the swing.",
            "A small stride usually means weak forward momentum, so the swing has to come from the arms.",
            "Walk-up BP: take a slow step into each pitch to feel the lower half lead the move.",
            metric="stride_length_normalized",
        )
        if v < 1.5
        else _cue(
            "Long stride",
            "Stride length looks long, which can drop the head and delay the start of rotation.",
            "An overly long stride sinks the center of mass and forces the body to climb out of the move before turning.",
            "Stride-band drill: take a normal stride against light resistance to feel a controlled landing.",
            metric="stride_length_normalized",
        ),
    ),
    (
        "attack_angle_deg",
        lambda v, metrics: None
        if 5 <= v <= 20
        else _cue(
            "Flat or downward attack angle",
            "Bat-path angle at contact looks flat or downward, which produces ground balls and weak fly balls.",
            "Modern data shows ideal attack angle is +5° to +20° (a slight uppercut to match the pitch plane).",
            "High-tee work: hit the top half of a tee placed at chest height to feel the barrel staying through the ball, not chopping down.",
            metric="attack_angle_deg",
        )
        if v < 5
        else _cue(
            "Steep uppercut",
            "Bat path looks steep upward at contact, which can cause pop-ups and swings under fastballs.",
            "Above ~20° attack angle, the barrel only matches the pitch plane in a narrow window — easier to whiff.",
            "Low-tee work: hit a low pitch flush without scooping under it. Feel the hands stay on top of the ball longer.",
            metric="attack_angle_deg",
        ),
    ),
    (
        "peak_pelvis_angular_velocity_deg_s",
        lambda v, metrics: None
        if v >= 400
        else _cue(
            "Slow pelvis turn",
            "Peak pelvis rotation speed is below the high-school benchmark.",
            "HS pros average ~420 deg/s, college ~480, MLB ~540. A slow pelvis caps how fast every downstream segment can move.",
            "Med-ball rotational throws: side toss for explosive hip turn; cue the back hip pulling the chest through.",
            metric="peak_pelvis_angular_velocity_deg_s",
        ),
    ),
    (
        "peak_torso_angular_velocity_deg_s",
        lambda v, metrics: None
        if v >= 600
        else _cue(
            "Slow torso turn",
            "Peak torso rotation speed is below the high-school benchmark.",
            "HS averages ~510 deg/s, college ~620, MLB ~720. A slow torso means the chest never whips after the hips.",
            "Stretch-and-fire drill: pause at peak separation, then rip the chest through to feel the upper body accelerate after the hips.",
            metric="peak_torso_angular_velocity_deg_s",
        ),
    ),
]


FLAG_CUES: dict[str, list[tuple[FlagPredicate, Callable[[dict[str, Any]], CoachingCue]]]] = {
    "front_shoulder_closed_load": [
        (
            lambda value: value is False,
            lambda metrics: _cue(
                "Front side opening early",
                f"Your {_front_side_label(metrics)} shoulder is opening early. Keep it closed a beat longer so the torso stays loaded.",
                "Opening the front side too soon gives away stretch before the swing can launch forward.",
                "Opposite-field tee work: keep the front shoulder closed until the stride foot is down and the hips start the turn.",
            ),
        ),
    ],
    "hip_casting": [
        (
            lambda value: value is True,
            lambda metrics: _cue(
                "Early hip spin",
                "Your hips are spinning early. Let the stride foot get down before the hips really fire.",
                "When the hips go before the landing is stable, power leaks before the hands and barrel can use it.",
                "Pillar-turn drill: land, brace, then rotate around a stable front side.",
            ),
        ),
    ],
    "arm_slot_at_contact": [
        (
            lambda value: value == "high",
            lambda metrics: _cue(
                "High hand slot",
                "Your hands are working high at contact. Turn through the ball instead of pushing the barrel down to it.",
                "A high hand path can make the barrel cut across the zone instead of staying through it.",
                "High-tee turns: match the barrel to the pitch plane without chopping down.",
            ),
        ),
        (
            lambda value: value == "low",
            lambda metrics: _cue(
                "Low hand slot",
                "Your hands are working low at contact. Make sure the back shoulder is not dropping under the swing.",
                "When the hands work too low, the barrel often gets under the ball before it can square it up.",
                "Top-hand release drill: keep the shoulder working around the swing instead of dipping.",
            ),
        ),
    ],
}


def _dedupe(cues: list[CoachingCue]) -> list[CoachingCue]:
    seen: set[tuple[str, str]] = set()
    output: list[CoachingCue] = []
    for cue in cues:
        key = (cue.issue, cue.cue)
        if key in seen:
            continue
        seen.add(key)
        output.append(cue)
    return output


def generate_static_report(metrics: dict[str, Any]) -> list[dict[str, str]]:
    """Build structured coaching cues from the static rule set + qualitative flags."""
    pcm = float(metrics.get("pose_confidence_mean", 1.0) or 0.0)
    if pcm < 0.4:
        return [
            asdict(
                _cue(
                    "Low pose confidence",
                    f"Pose detection confidence is low ({pcm * 100:.0f}%), so these measurements may be unreliable.",
                    "Heavy occlusion, partial body visibility, or poor lighting can make angle-based feedback unstable.",
                    "Capture a brighter clip with the full body visible and as little obstruction as possible.",
                    level="all",
                    tone="info",
                )
            )
        ]

    cues: list[CoachingCue] = []
    view_type = str(metrics.get("view_type", "unknown")).lower()
    view_confidence = float(metrics.get("view_confidence", 0.0) or 0.0)
    angle_metrics_safe = view_type in {"frontal", "back"} and view_confidence >= 0.6

    chain = metrics.get("kinetic_chain")
    if isinstance(chain, dict):
        hs_dir = str(chain.get("hip_to_shoulder_direction", "synced"))
        sh_dir = str(chain.get("shoulder_to_hand_direction", "synced"))
        if hs_dir == "trails":
            cues.append(_cue(
                "Out-of-sequence: torso leads hips",
                "The torso is firing before the hips, so there is no stretch left to whip the bat through.",
                "Kinetic sequence should be hips, then torso, then arms, then hands. When the chest goes first, the lower half has nothing to whip around and bat speed leaks.",
                "Hook 'Em drill: take the back hand off at contact and pull the knob to the ball with the back hip, forcing the lower half to lead.",
                metric="kinetic_chain.hip_to_shoulder_direction",
            ))
        if sh_dir == "trails":
            cues.append(_cue(
                "Out-of-sequence: hands lead the torso",
                "The hands are starting before the chest finishes turning, which usually shows up as bat drag and a long swing.",
                "When the hands beat the torso, the barrel cannot ride the body's rotation and has to chase the ball with arm strength.",
                "Connection-ball turns: pin a towel under the lead arm and rotate the chest through contact without dropping it.",
                metric="kinetic_chain.shoulder_to_hand_direction",
            ))

    energy_events = metrics.get("energy_loss_events")
    if isinstance(energy_events, list):
        for event in energy_events[:2]:
            etype = str(event.get("type", ""))
            mag = float(event.get("magnitude_pct", 0.0) or 0.0)
            if etype == "early_opening" and mag >= 30.0:
                cues.append(_cue(
                    "Hips bleed energy before contact",
                    "Hip rotation slows down well before contact, which usually means the hips opened too early and have nothing left to give.",
                    "Once the pelvis decelerates, the only way to get the bat through is to push with the arms — slower and less consistent.",
                    "Pillar-turn drill: land the stride and feel the hips keep accelerating into the chest, not stalling at heel plant.",
                    metric="energy_loss_events.early_opening",
                ))
                break

    for name, rule in RULES:
        if name in ANGLE_SENSITIVE_METRICS and not angle_metrics_safe:
            continue
        value = metrics.get(name)
        if isinstance(value, (int, float)):
            cue = rule(float(value), metrics)
            if cue:
                cues.append(cue)

    flags = metrics.get("flags")
    if isinstance(flags, dict):
        for name, conditions in FLAG_CUES.items():
            value = flags.get(name)
            for check, builder in conditions:
                if check(value):
                    cues.append(builder(metrics))

        leg = flags.get("leg_action")
        if leg == "leg_kick":
            cues.append(
                _cue(
                    "Big leg kick",
                    "You are using a leg kick. Keep it under control so it does not pull the head forward.",
                    "A big move can help rhythm, but only if the head stays centered and the foot still gets down on time.",
                    "Controlled leg-kick drill: hold the gather for a beat, then land softly before turning.",
                )
            )
        elif leg == "neither":
            cues.append(
                _cue(
                    "Limited gather",
                    "There is very little leg lift. A small lift or toe-tap could help rhythm and the load.",
                    "A cleaner gather can organize timing and help the lower half start the move in sequence.",
                    "Toe-tap timing drill: small gather, quiet landing, then turn from the ground up.",
                    tone="info",
                )
            )

        finish = flags.get("finish_height")
        if finish == "low":
            cues.append(
                _cue(
                    "Low finish",
                    "Your finish stays low. Let the bat keep moving through contact instead of cutting off right after impact.",
                    "Cutting off the finish usually means the barrel leaves the zone early and loses extension.",
                    "Long-through-contact drill: hold the finish high and long after the barrel passes contact.",
                )
            )

    cues = _dedupe(cues)
    if not angle_metrics_safe:
        cues.insert(
            0,
            _cue(
                "Limited angle confidence",
                f"This clip looks like a {view_type.replace('_', ' ')} view, so angle-heavy measurements are less reliable.",
                "Hip rotation, shoulder rotation, and spine-tilt calls are strongest from frontal or back views where both sides are visible.",
                "Keep this clip for timing and rhythm, then capture one frontal or back-view clip for cleaner rotational feedback.",
                level="all",
                tone="info",
            ),
        )
    if not cues:
        cues.append(
            _cue(
                "Solid baseline",
                "Swing mechanics look solid. Keep working on consistency and timing.",
                "There are no obvious high-priority leaks in the fallback rules, so the next gain is repeating the same move under speed.",
                "Challenge-round tee work: repeat the same contact point and finish for five swings in a row.",
                tone="good",
                level="all",
            )
        )

    return [asdict(cue) for cue in cues]
