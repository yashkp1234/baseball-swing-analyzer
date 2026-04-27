# Swing Analysis Research & Coaching Improvement Plan

**Date:** 2026-04-26
**Owner:** yashkp123@gmail.com
**Status:** Research + audit + actionable plan. Implementation pending.

## Why this exists

The current AI coaching output is generic — it says things like *"need more separation"* without telling the hitter how, where, by how much, or what drill fixes it. This document does three things:

1. **Research** — synthesizes modern hitting biomechanics (Driveline, K-Vest/K-Motion, MLB Statcast bat tracking, Welch/Fleisig studies, Blast Motion data) plus classical frameworks (Williams, Epstein, Lau) so the analyzer's coaching is grounded in evidence, not folk wisdom.
2. **Audit** — documents exactly what we currently extract and exactly what we send the LLM, so we can see the gap between "data we have" and "data the model uses."
3. **Plan** — concrete additions to metrics, knowledge base, prompts, and the report schema, ordered by impact.

---

## Part 1 — Research: What Makes a Powerful, Repeatable Swing

### 1.1 The kinematic sequence is the single most important concept

**Order:** Pelvis → Torso → Lead Arm → Hands/Bat. Each segment reaches its peak rotational velocity *after* the previous one and *before* the next. This is the same pattern as a golf swing, a tennis serve, and a pitching delivery. It is how the body acts as a whip and transfers ground-up energy into the bat.

**Pro-level peak rotational velocities** (Driveline + K-Vest data):

| Segment      | Pro range (°/s) | College (°/s) | High School (°/s) |
| ------------ | --------------: | ------------: | ----------------: |
| Pelvis       |       490 – 760 |          ~480 |              ~420 |
| Torso        |      760 – 1150 |          ~620 |              ~510 |
| Lead arm     |     970 – 1360  |          ~870 |              ~680 |
| Hand / bat   |     1530 – 2230 |         ~1400 |             ~1050 |

**Speed gain ratio** (segment N+1 peak ÷ segment N peak): pro range is **1.3 – 1.6** at every transition. A flat or declining ratio means energy leaks at that transition.

**Sequence percentage** (Driveline metric): the % of swings where the hitter actually hits 1-2-3-4 in order. Pros are highly consistent. Amateurs often get pelvis → torso right but invert torso ↔ arm or arm ↔ hand.

**Why this matters more than X-factor alone:** the *order* and *timing* of peaks is what produces bat speed. A hitter can have plenty of static separation but lose all of it because the torso peaks *before* the pelvis.

### 1.2 Hip-shoulder separation (X-factor) — peak vs. at-contact are different metrics

The classical "X-factor" is the angular gap between pelvis and torso about the longitudinal (spine) axis.

- **Peak separation:** 30°–55° in elite hitters (some sources push 35°–60°). This is achieved at or just before front foot plant.
- **At contact:** **the gap closes to 0–5°.** Hips and shoulders should be nearly aligned at impact — the torso has caught up. A *static* late separation is not the goal.
- **At contact, hips should be 80°–90° open** to the pitcher. **>90°** indicates over-rotation / late deceleration / front side flying out.

**Implication:** measuring X-factor at contact alone (which is what we currently do) is the *worst* single moment to measure it, because by then it should be near zero. We need:
- **Peak separation** (highest gap during stride/load)
- **Frame index of peak separation** (relative to contact)
- **Closure rate** (how fast it closes — too slow = bat is late)
- **Gap at contact** (current metric — but interpret as "should be small")

**Source studies report:** pelvis peak rotational velocity ~714°/s, shoulder ~937°/s, with shoulder peak occurring after pelvis peak — confirming sequence order.

### 1.3 Attack angle and bat path — the modern revolution

Statcast added bat-tracking metrics in 2024 and **Swing Path / Attack Angle / Ideal Attack Angle / Attack Direction in 2025**. The data overturned a generation of "swing down" coaching.

- **Attack angle** = angle of bat path at impact relative to horizontal (positive = swinging up).
- **Ideal range:** **5°–20° upward** for line drives and barrels. MLB's "ideal" classification sits there.
- **For distance / power:** ~18° if hitter has 105+ mph EV potential; 5°–15° if EV < 105.
- **For line drives:** 6°–14°.
- **Softball:** pros sit at 3°–15° (slightly flatter than baseball because pitches arrive flatter / rising).

**Vertical Bat Angle (VBA)** — orientation of barrel relative to knob at contact. Steeper VBA for low pitches, shallower for high pitches. Should *change with pitch location*; a hitter with one fixed VBA can't cover the zone.

**On-Plane Efficiency** (Blast metric): % of swing where bat is on the plane of the pitch. Recommended **65%–85%, average 70%+**. Below that, the hitter has a "sword" through the zone — short window where contact is even possible.

**Ted Williams was right.** *The Science of Hitting* (1970) prescribed a slight uppercut to match the downward plane of the pitch. Statcast data validated him 50 years later. Lau-style "swing down on the ball" is now considered mechanically incorrect.

### 1.4 Stride mechanics — timing matters more than length

- **Length:** ~3.75× hip-width (hip-center to hip-center). Variable by hitter; rhythm matters more than length.
- **Direction:** ~10° closed (pointing slightly toward pull-side foul line; 0° = straight at pitcher).
- **Timing of front foot plant:** between pitcher's release and the halfway point of the pitch's flight. Younger / slower-bat hitters need to plant earlier.
- **Critical rule:** **the hands and bat should not move forward until the front foot is flat.** Hands moving with the stride = bat is committed too early = no adjustability.

**Common stride flaws** (each has measurable signatures):
- *Stride too long* → drops center of mass, delays rotation, lowers all downstream peak velocities.
- *Stride too short* → no forward momentum, hitter hangs back, low GRF.
- *Stride opens (foot points at pitcher / away)* → leaks rotational energy through the front side.
- *Late foot plant* → hands fire before plant → "early hip cast" / "spinning."

### 1.5 Ground reaction forces — the engine

Bat speed is built from the ground. Welch/Fleisig and a 2023 lower-extremity study confirmed:

- **Back leg:** generates large vertical and medial-lateral GRF early in the swing — this is the rotational engine.
- **Front leg:** *blocks*. After plant, the front leg goes to near-extension and acts as a stiff post. The pelvis whips around it. **Front knee extension velocity** is one of the strongest predictors of bat speed.
- **Pro vs. amateur:** adult pro hitters had **greater lead knee extension, more open pelvis at contact, higher peak upper torso angular velocity, higher peak left elbow extension velocity, higher peak left knee extension velocity, and higher bat speed at contact** vs. youth.

**Coaching implication:** "stay back / squish the bug" (linear / Lau era) is wrong. Modern model is **"push, plant, post, pivot"** — back leg pushes, front leg plants and posts up, pelvis pivots around the front leg.

### 1.6 Head stability and ball-tracking

SABR and frontiersin.org research:

- Skilled hitters drop the head **~9 cm** (roughly 3.5 in) on average through the swing — but **less variable** than amateurs.
- **Head moves more than eyes** during ball tracking. Head rotation does most of the work; eyes can only resolve ~50 ms before contact regardless.
- Some forward head movement toward the pitcher is normal — *lateral / rotational* head displacement is the killer because it disrupts the visual fix on the ball.
- **Total head displacement** (what we measure) is OK, but better is the **2D path** — vertical drop + lateral drift separately, with thresholds calibrated by torso length.

### 1.7 Time to contact and bat speed (Blast Motion benchmarks)

| Metric                     | Pro range          | Notes                                              |
| -------------------------- | -----------------: | -------------------------------------------------- |
| Time to Contact            | 0.13 – 0.17 sec    | From start of downswing to impact                  |
| Bat Speed (sweet spot)     | 65 – 80+ mph       | Measured 6 in from bat tip                         |
| Rotational Acceleration    | ~17 g (MLB avg)    | How fast bat reaches peak speed                    |
| Blast Factor (composite)   | 83 – 97            | Quality of swing 0–100                             |
| MLB Statcast Swing Length  | 7.3 ft avg         | <6.6 short, >8.0 long                              |
| MLB Squared Up % / Blast % | varies             | Ball/bat sweet-spot match × bat speed achievement  |

**Why TTC matters:** lower TTC = later swing decision = better pitch recognition. Pros buy themselves milliseconds by being mechanically efficient.

### 1.8 Swing path leaks — the named flaws and what they look like

| Flaw                  | What it is                                                                | Pose-detectable signature                                                           | Drill                                              |
| --------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------- |
| **Bat drag**          | Back elbow leads barrel; barrel trails into zone                          | Back elbow ahead of back wrist (in swing-direction frame) at 50% of swing window    | George Brett drill, fence drill                    |
| **Casting**           | Hands push out away from body; long swing path                            | Distance from hand to back-shoulder grows in stride/swing phase                     | Paint-the-wall, fence drill                        |
| **Hitch**             | Hands drop/move during load with no path to launch                        | Wrist y-position dips then re-rises during load                                     | Sequence drill, wall-tap drill                     |
| **Pull-off / fly open** | Front shoulder rotates open before stride foot plant                    | `front_shoulder_closed_load = false` AND hip rotation > shoulder rotation in load   | Opposite-field BP, lead-arm-only swings            |
| **Dipping / scoop**   | Back shoulder drops; barrel goes under the ball                           | Spine tilt > 25° away from pitcher at contact                                       | Knob-to-ball drill, level-bat plane drill          |
| **Early hip cast**    | Hips fire before front foot plants                                        | Already detected — `hip_casting` flag (good)                                        | Hook 'Em, no-stride hip rotation, Pillar Turn      |
| **Bat dip / loop**    | Barrel drops below hands well before contact, then loops up               | Bat-path angle > 25° at first half of swing                                         | Top-hand release drill, A-to-B drill               |
| **Lunging**           | Center of mass rushes forward, head dives                                 | Head displacement > 12% of torso length forward                                     | No-stride, walk-up to tee with stop                |
| **Pushing the bat**   | Top hand dominates; arms over-extend before rotation                      | Lead elbow extends > 160° before contact                                            | One-hand bottom-hand swings                        |
| **Spinning** (no stride into the ball) | Rotates in place; no forward energy                          | Stride length < 5% of body height                                                   | Step-back drill, walking BP                        |

### 1.9 Softball-specific notes

The mechanics are **~85% identical** to baseball at the contact-and-power level. The differences:

- **Pitch plane is flatter or rising** (riseball, screw, drop). Hitters need a **slightly flatter attack angle** (3°–15° vs. baseball 5°–20°) and the ability to adjust *up*, not just *down*.
- **Reaction time is shorter** at high pitch speeds (43-foot mound, 65+ mph = ~0.4 sec). TTC and swing decision matter more.
- **Slap hitting** is a separate skill set: forward lean, contact-over-power, hand path emphasis. Slappers are particularly vulnerable to riseballs because their forward weight shift makes them swing under high pitches. Slap mechanics are *not* a "broken" power swing — they are a different swing entirely and should be detected and coached differently.
- **Optimal launch angle for HR is ~26°** for softball (vs. ~25–30° for baseball; very close).
- The "rise ball" doesn't require a special swing — the best response to a true riseball is *don't swing*. Coaching should reflect this rather than promising mechanical fixes.

### 1.10 Old-school vs. new-school — what to keep, what to discard

| Classical principle              | Modern verdict                                                                |
| -------------------------------- | ----------------------------------------------------------------------------- |
| Williams' slight uppercut        | **Confirmed** — Statcast attack angle data validates                          |
| Williams' "get a good pitch"     | **Confirmed** — Plate discipline + zone control                               |
| Lau's weight shift forward       | **Wrong** — center-of-mass shift is not how energy is generated               |
| Lau's "swing down on the ball"   | **Wrong** — produces ground balls, low EV                                     |
| Lau's "extension through ball"   | **Partial** — early extension is bat drag; extension *after* contact is fine  |
| Epstein's rotational hitting     | **Mostly correct** — though pure rotation w/o stride underplays GRF           |
| Epstein's "axis of rotation"     | **Correct** — front-leg-post model                                            |
| "Squish the bug" (back foot)     | **Wrong** — back foot rolls naturally; teaching it as a cue creates spinning  |
| "Keep your eye on the ball"      | **Wrong literally** — eyes can't track final 50 ms; head rotation does it     |
| "Hands inside the ball"          | **Correct** — synonymous with "no casting"                                    |
| "Stay back"                      | **Misleading** — should be "stay loaded until plant," then go                 |

---

## Part 2 — Audit: What We Currently Do

(Full audit is in the codebase — this is a summary keyed to the gap analysis below.)

### 2.1 Metrics we extract (13 total)

From `reporter.py:34-82` and `metrics.py`:

| Metric                          | What we capture                                                | Limit                                                       |
| ------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------- |
| `phase_durations`               | Frames per phase                                               | Frame-count — not time-of-event                             |
| `stride_plant_frame`            | Frame of front foot plant                                      | Good                                                        |
| `contact_frame`                 | Frame of max wrist velocity                                    | Good (proxy for contact)                                    |
| `hip_angle_at_contact`          | Pelvis line angle, only valid frontal/back view                | **Zero validation that view is correct**                    |
| `shoulder_angle_at_contact`     | Shoulder line angle, only valid frontal/back view              | Same                                                        |
| `x_factor_at_contact`           | Hip − shoulder at contact                                      | **At contact this should be ~0; we have no peak metric**    |
| `spine_tilt_at_contact`         | Lateral spine bend                                             | Good — direction matters (toward / away from pitcher)       |
| `left_knee_at_contact`          | Front knee flexion                                             | Good — but velocity matters more than static angle          |
| `right_knee_at_contact`         | Back knee flexion                                              | Good — but again, dynamic > static                          |
| `head_displacement_total`       | Total head motion in pixels                                    | Lumps vertical & lateral; not normalized                    |
| `wrist_peak_velocity_px_s`      | Max wrist speed                                                | Pixel-based; not scaled                                     |
| `wrist_peak_velocity_normalized`| Wrist speed ÷ torso length                                     | Best metric we have for "bat speed"                         |
| `pose_confidence_mean`          | Pose model confidence                                          | Good — but we don't act on low values                       |

**6 qualitative flags** from `flags.py`: `handedness`, `front_shoulder_closed_load`, `leg_action`, `finish_height`, `hip_casting`, `arm_slot_at_contact`. Reasonable coverage of categorical issues.

**`energy.py` computes but never sends to the LLM:**
- Pelvis / shoulder / wrist / elbow per-frame velocity vectors
- Hip → shoulder lag and shoulder → hand lag (kinematic sequencing!)
- Energy loss events ("deceleration", "early_opening", "push_off_loss")

This is the single biggest immediate opportunity — **the kinematic sequence data is computed but not coached on.**

### 2.2 The prompt we send the LLM (verbatim)

System prompt (`__main__.py:100`):

> "You are an MLB-level hitting coach. Be concise and actionable."

User prompt template (`coaching.py:13-22`):

```
You are an expert hitting coach. A swing analysis pipeline has extracted
the following biomechanical metrics from a phone video of a swing:

{metrics_summary}

Please provide a concise, actionable coaching report (3-5 bullet points) covering:
1. What looked good mechanically
2. The most important area for improvement
3. One specific drill or cue to address it

Keep each bullet to 1-2 sentences. Use plain language a youth player can understand.
```

`{metrics_summary}` is just a stringified dump of the metrics dict. The LLM sees raw numbers like `x_factor_at_contact: -6.83` with **no reference range, no interpretation, no biomechanics framework, no drill library, no handedness context, no view-validity warning, and no kinematic sequence data**.

### 2.3 Static knowledge base (`knowledge.py`) thresholds

| Metric                           | "Good" range  | Below cue                                     | Above cue                                                                 |
| -------------------------------- | ------------- | --------------------------------------------- | ------------------------------------------------------------------------- |
| `x_factor_at_contact`            | 5° – 35°      | "Hip-shoulder separation is low..."           | "Hip-shoulder separation is high..."                                      |
| `stride_plant_frame`             | 15 – 40 frames| "Front foot landing early..."                 | "Front foot landing late..."                                              |
| `wrist_peak_velocity_normalized` | ≥ 5.0         | "Bat speed looks low..."                      | (no upper)                                                                |
| `left_knee_at_contact`           | 10° – 45°     | "Front knee too straight..."                  | "Front knee very bent..."                                                 |
| `right_knee_at_contact`          | 10° – 40°     | "Back knee too straight..."                   | "Back knee very bent..."                                                  |
| `head_displacement_total`        | ≤ 60 px       | (none)                                        | "Head is moving too much..."                                              |
| `spine_tilt_at_contact`          | -15° – +15°   | (none)                                        | "May be leaning away at contact..."                                       |

**Problems:**
- `x_factor 5°–35° at contact` contradicts the literature, which says the gap should be near zero at contact and the *peak* should be 30°–55°.
- Pixel-based thresholds (`head_displacement_total ≤ 60`) won't generalize — should be normalized to torso length or body height.
- No drill text — just cues.
- No handedness, no view-quality, no progression.

---

## Part 3 — Gap Analysis: Literature ↔ Code

| Literature concept                          | Currently in codebase?                       | Gap                                                                  |
| ------------------------------------------- | -------------------------------------------- | -------------------------------------------------------------------- |
| Kinematic sequence (1-2-3-4 order)          | Computed in `energy.py`, **not in report**   | Surface to LLM. Add `sequence_order_correct: bool`.                  |
| Hip / torso / arm / hand peak ang. velocity | Wrist velocity only                          | Add per-segment angular velocities (degrees/sec, not px/s)           |
| Speed gain ratios between segments          | Not computed                                 | Add: torso/pelvis, lead-arm/torso, hand/lead-arm ratios              |
| **Peak X-factor** (separation)              | Only `x_factor_at_contact` (wrong moment)    | Add `peak_separation_deg`, `peak_separation_frame`, `closure_rate`   |
| Hips % open at contact (target 80–90°)      | Have `hip_angle_at_contact` but no target    | Add interpretation: pro 80–90°, >90° over-rotation                   |
| Attack angle (5–20° ideal)                  | Not computed at all                          | **Major gap** — derive from bat-line trajectory at contact            |
| Vertical Bat Angle (VBA)                    | Not computed                                 | Derive from forearm orientation at contact                           |
| On-Plane Efficiency %                       | Not computed                                 | Compute % of swing where bat path is within ±5° of attack angle      |
| Time to Contact (sec, target 0.13–0.17)     | We have phase durations in frames            | Convert: `swing_phase_duration / fps`. Add `time_to_contact_s`.      |
| Swing length                                | Not computed                                 | Sum of bat-tip displacement during swing window                      |
| Stride length (× hip-width)                 | Not computed                                 | Add `stride_length_normalized = ankle Δ / hip_width`                 |
| Stride direction (closed/open degrees)      | Not computed                                 | Angle of stride vector vs. line to pitcher                           |
| Front knee extension velocity               | Static angle only                            | Add `front_knee_extension_velocity_deg_s` peak                       |
| Back knee push / GRF proxy                  | Not computed                                 | Vertical hip drop magnitude during load (proxy)                      |
| Head displacement: vertical vs. lateral     | Total only                                   | Split into vertical drop and horizontal drift; scale by torso        |
| Head stability (variance)                   | Not computed                                 | Frame-to-frame head variance during swing window                     |
| Bat path / swing path geometry              | None — we don't track the bat                | Infer bat line from wrists+forearms; trace tip path                  |
| Camera view detection                       | **None — assumed frontal/back**              | **Critical** — flag side views; downgrade angle metrics' confidence  |
| Energy loss events                          | Computed in `energy.py`, **not surfaced**    | Send to LLM with frame and type                                      |
| Sport (baseball vs. softball)               | Not in report flow                           | Pass through; adjust thresholds + use sport-specific cues            |
| Slap hitter detection                       | Not computed                                 | Forward lean + slap-step from stance — softball only                  |
| Drill library                               | **One generic cue per flag**                 | Build drill database keyed by flaw + level                           |
| Reference ranges in prompt                  | **None — just raw numbers**                  | Inject "good range" alongside each metric in prompt                  |
| Handedness in coaching prompt               | Detected but not given to LLM                | Include "RHH: front shoulder = left" so feedback is left/right-aware |

**Bottom line:** roughly half the literature's "important" metrics aren't computed at all, and the other half are computed but either not surfaced to the LLM or surfaced without context.

---

## Part 4 — Concrete Plan

Ordered by impact-per-effort. Each block is independently shippable.

### Phase A — Prompt overhaul (no new code, biggest immediate win)

**A1. Replace the system prompt** with a richer one that includes the biomechanics framework. Draft:

```
You are a high-level hitting coach trained on modern biomechanics
(Driveline, K-Vest/K-Motion data, MLB Statcast bat tracking) and
classical principles (Williams, Epstein). You give feedback to
hitters from youth through pro level.

Core principles you operate on:
- The swing is a kinematic chain: pelvis → torso → lead arm → hands.
  Each segment must peak in order. Out-of-order = energy leak.
- Hip-shoulder separation peaks at 30°–55° at front-foot plant and
  closes to ~0–5° by contact. Hips reach 80°–90° open at contact.
- Ideal attack angle is 5°–20° upward. Lower for line drives, higher
  for power. Softball runs 3°–15°.
- The front leg is a post: it plants, extends, and the body whips
  around it. The back leg is the engine that pushes into the ground.
- Bat speed comes from sequencing and ground force, not arm strength.
- Head moves a little (≈9 cm down) but stays consistent. Lateral
  head drift is the worst form of motion.

Coaching rules:
- ALWAYS lead with the single biggest leak (the issue costing the
  most bat speed or contact quality), then 1–2 secondary items.
- ALWAYS give the WHY (which kinetic-chain link is failing) and a
  specific, named drill with a one-sentence "how."
- NEVER say "you need more X" without saying how to feel it, what
  to do, and what success looks like.
- If a metric is unreliable (low pose confidence, side view, etc.)
  say so explicitly — don't fabricate certainty.
- Use the hitter's actual handedness: for a RHH, "front" = left.
- Match language to the hitter: high school and up can handle
  terms like "kinematic sequence" and "attack angle" with a brief
  gloss; younger kids get the cue without the jargon.
```

**A2. Replace the user prompt template** with a structured payload that includes reference ranges, handedness, view confidence, and the kinematic-chain data we already compute but don't send. Draft:

```
You are reviewing one swing. Here is everything we know.

HITTER CONTEXT:
- Sport: {sport}                          (baseball | softball)
- Handedness: {handedness}                (front side = {front_side})
- Camera view: {view_type}                ({view_confidence}% confident)
- Pose detection quality: {pose_quality}  (mean conf {pose_conf:.2f})

NOTE on validity: angle-based metrics (hip_angle, shoulder_angle,
x_factor, spine_tilt) are reliable only on frontal/back views.
This swing's view confidence is {view_confidence}%.
{warning_if_low_confidence}

CORE METRICS (with reference ranges):

Bat path / power:
  Bat speed (normalized):      {bat_speed_norm:.2f}    (good: ≥ 5.0)
  Time to contact:             {ttc_s:.2f} s           (pro: 0.13–0.17 s)
  Attack angle (est.):         {attack_angle:+.1f}°    (ideal: +5° to +20°)
  Swing length (norm.):        {swing_length:.2f}      (target: short)

Kinematic sequence (in order pelvis → torso → arm → hand):
  Sequence order correct:      {seq_order_ok}          (target: yes)
  Hip → shoulder lag:          {hip_to_shoulder_lag} frames  (good: 1–3, lead)
  Shoulder → hand lag:         {shoulder_to_hand_lag} frames (good: 0–2, lead)
  Energy loss events:          {energy_events}         (target: none)

Separation:
  Peak hip-shoulder separation: {peak_x:.1f}°           (good: 30°–55°)
  Frame of peak separation:     {peak_x_frame}          (should be near plant)
  X-factor at contact:          {x_at_contact:.1f}°     (good: 0°–10° — should be small)

Lower body:
  Stride length (× hip-width):  {stride_norm:.2f}      (good: ~3.75)
  Stride direction:             {stride_dir:+.0f}°     (good: ~10° closed)
  Front foot plant timing:      {plant_pct:.0%} of swing window (good: ≤ 40%)
  Front knee at contact:        {front_knee:.0f}°      (good: 10°–30°, extending)
  Back knee at contact:         {back_knee:.0f}°       (good: 10°–40°)
  Hips open at contact:         {hip_at_contact:.0f}°  (good: 80°–90°; >90° = over-rotated)

Posture / head:
  Spine tilt at contact:        {spine_tilt:+.1f}°     (good: -10° to +15°, slight tilt away from pitcher)
  Head vertical drop:           {head_drop_pct:.1f}%  of torso (good: ≤ 8%)
  Head lateral drift:           {head_drift_pct:.1f}% of torso (good: ≤ 5%)

QUALITATIVE FLAGS:
{flags_with_explanations}

OUTPUT FORMAT (markdown):

## What's Working
One bullet, max 2 sentences. Specific.

## Biggest Leak
Name the single biggest issue. State the metric value and the target.
Explain WHY it costs bat speed / contact quality (point to which link
in the kinetic chain is failing). Give one named drill and how it feels.

## Secondary Fixes
Up to 2 more bullets, same format but shorter.

## Confidence Note
One line. If view or pose confidence is low, say what you're not sure
about and why.

Keep total under 250 words. No fluff. The reader has the metrics — your
job is to translate them into "do this, feel this, look like this."
```

**Why this prompt works:**
- Reference ranges are *in the prompt*, so the LLM compares each value to a target instead of guessing.
- Sequencing data is *in the prompt* — we already compute it.
- Handedness, view, and pose confidence are explicit — the model can hedge.
- Output structure forces *one big leak first*, which matches how good hitting coaches actually teach.
- Drill requirement forces specificity.

### Phase B — Surface what we already compute (small code change, big payoff)

Add to `reporter.py:build_report()`:

```python
# After the existing metrics block:
from .energy import joint_velocities, kinetic_chain_scores, energy_loss_events

velocities = joint_velocities(keypoints_seq, fps)
chain = kinetic_chain_scores(velocities)
events = energy_loss_events(velocities, contact_frame)

report["kinetic_chain"] = {
    "hip_to_shoulder_lag_frames": chain.hip_to_shoulder.lag_frames,
    "hip_to_shoulder_direction":  chain.hip_to_shoulder.direction,   # leads/trails/synced
    "shoulder_to_hand_lag_frames": chain.shoulder_to_hand.lag_frames,
    "shoulder_to_hand_direction":  chain.shoulder_to_hand.direction,
    "sequence_order_correct":      chain.is_proper_order,
}
report["energy_loss_events"] = [
    {"frame": e.frame, "type": e.type, "magnitude_pct": e.magnitude_pct}
    for e in events
]
```

That alone unlocks proper kinematic-sequence coaching with zero new computation.

### Phase C — Add the missing high-value metrics

**Priority order — biggest coaching value first:**

1. **`peak_separation_deg` + `peak_separation_frame` + `separation_closure_rate`**
   Walk the swing window, compute `hip_angle - shoulder_angle` at every frame, find max. Closure rate = `(peak - at_contact) / (contact_frame - peak_frame)`.

2. **`time_to_contact_s`**
   Trivially derived: `(contact_frame - swing_phase_start_frame) / fps`. No new pose math.

3. **`attack_angle_deg`**
   Estimate bat line from `mid_wrist + forearm_extension`. At contact frame and the 2 frames before, fit a line through that bat-tip estimate; angle vs. horizontal = attack angle. Caveat: requires reasonable side view OR 3D depth — flag confidence.

4. **`stride_length_normalized` + `stride_direction_deg`**
   `stride_length_normalized = (front_ankle_x_at_plant - front_ankle_x_at_stance) / hip_width`. Direction = atan2 of stride vector vs. line to pitcher (which we have to infer — assume horizontal in pixel space and warn).

5. **`head_drop_pct` + `head_drift_pct`** (split the existing combined metric)
   `head_drop_pct = (max_nose_y - min_nose_y) / torso_length_px * 100`
   `head_drift_pct = max horizontal nose displacement from stance position / torso_length_px * 100`

6. **`peak_pelvis_angular_velocity_deg_s` + `peak_torso_angular_velocity_deg_s`**
   Take the hip-line and shoulder-line angles per frame, differentiate, smooth with the existing window=3, find peak in swing window. Compare to literature ranges; flag amateur-level numbers.

7. **`front_knee_extension_velocity_deg_s`**
   Differentiate `left_knee_angle` (or right for LHH) per frame; find peak after plant.

8. **`bat_speed_estimate_mph`** (calibrated estimate)
   Multiply `wrist_peak_velocity_px_s` by `bat_length_estimate / wrist_to_grip_length` (assumed 32 in / 6 in ratio = 5.3) and convert to mph using a video-scale factor. Will be rough but at least returns a familiar unit. Mark as estimate.

### Phase D — Fix the static knowledge base

`knowledge.py` should:

1. **Use literature-correct ranges.** In particular: `x_factor_at_contact 0°–10°` (was 5°–35°), and add a separate `peak_separation_deg 30°–55°` rule.
2. **Normalize all pixel-based thresholds** by `torso_length_px`.
3. **Replace single-cue strings with `{cue, why, drill, level}` tuples.** Example:

```python
@dataclass
class CoachingCue:
    issue: str             # "Early hip cast"
    cue: str               # "Stay closed until the front foot is flat."
    why: str               # "When the hips fire before the front foot plants, the
                           # torso has nothing to whip around. Bat is late."
    drill: str             # "Hook 'Em drill: tee work, take the back hand off the
                           # bat at contact. Forces the body to lead the hands."
    level: str             # "youth" | "hs" | "advanced"
```

4. **Build a drill library** keyed by flaw, with 2–3 drills per flaw covering progressions.

### Phase E — Camera view detection

Add a lightweight view classifier — even a heuristic is better than nothing:

- Compare `shoulder_width_px / torso_length_px` ratio over the swing window.
  - High and steady → frontal/back view (hips and shoulders visible)
  - Low → side view (shoulders compressed)
  - Mid + asymmetric → 3/4 view
- Output `view_type` and `view_confidence` and pass to the prompt.
- Downgrade or omit angle metrics on side views and tell the LLM why.

### Phase F — Sport branching

`build_report` already gets a sport hint from earlier work. Wire it through:

- Pass `sport` into `knowledge.py` and load sport-specific thresholds (attack angle 3°–15° for softball, 5°–20° for baseball, etc.).
- Add a slap-hitter detector for softball (forward lean at stance + shortened back swing + step into pitch).
- Sport-specific cues in the prompt: e.g., for softball, mention riseball pitch-selection rather than promising mechanical fixes.

### Phase G — Confidence-aware coaching

If `pose_confidence_mean < 0.5` OR `view_confidence < 0.6` OR `frames < 12`:

- Skip angle-based assessments
- Tell the LLM: *"Pose / view quality is low. Limit feedback to obvious flags (handedness, leg action, finish height). Do not assess separation, knee angles, or attack angle."*

This stops the LLM from confidently coaching off garbage data.

---

## Part 5 — Suggested implementation order

| Step | Effort | Impact |
| ---- | ------ | ------ |
| Phase A1+A2: prompt rewrite                                  | 30 min  | **Massive** — instantly more specific output |
| Phase B: surface kinetic_chain + energy_loss in report       | 1 hr    | **Massive** — feeds A2 with real data        |
| Phase C1: peak separation + closure                          | 1 hr    | High                                          |
| Phase C2: time_to_contact_s                                  | 15 min  | Medium                                        |
| Phase C5: split head_drop / head_drift                       | 30 min  | Medium                                        |
| Phase D: knowledge.py rewrite with `{cue, why, drill, level}`| 2 hr    | High (offline path quality)                  |
| Phase E: view detection heuristic                            | 1 hr    | High (correctness)                           |
| Phase C3: attack angle estimate                              | 2 hr    | High but harder — depends on 2D vs. 3D       |
| Phase C4: stride length + direction                          | 1 hr    | Medium                                        |
| Phase C6: pelvis/torso angular velocities + sequence vis     | 1 hr    | High (fills in the missing rotational data)   |
| Phase F: sport branching                                     | 1 hr    | Medium                                        |
| Phase G: confidence gating                                   | 30 min  | Medium (prevents wrong answers)              |

A 1-day push would land Phases A, B, C1, C2, C5, E, G — the highest-leverage changes — and make the coaching dramatically more concrete.

---

## Part 6 — Sample output, before vs. after

**Today's coaching (typical):**

> - Your hip-shoulder separation is low. Try to let the hips start the turn before the shoulders.
> - Front knee looks bent at contact. Push into the ground.
> - Bat speed could improve. Start the move earlier.

**With Phase A + B + C1 in place:**

> ## What's Working
> - Front shoulder stays closed through the load (good coil), and your finish is high — the bat is getting through the zone.
>
> ## Biggest Leak
> Your **peak hip-shoulder separation only hits 18°** (target 30°–55°), and it's reached at the same frame your foot plants — too late. The cause is sequencing: your **shoulder peaks before your pelvis** (`hip_to_shoulder_lag = -2`, meaning the upper body leads the lower body). You're spinning the chest to start the swing instead of letting the hips fire first, so there's no stretch left to whip the bat through. **Drill: Hook 'Em.** Take a tee, hold the bat with only your bottom hand, and try to drag the knob to the ball with your hips. Feel the back hip *pull* the chest open instead of the chest opening on its own. Success = peak separation in the high 30s with the gap closing right at contact.
>
> ## Secondary Fixes
> - **Front knee** flexes 38° at contact and isn't extending — you're sitting on it instead of posting up. Add a wall drill: stand with the outside of your front foot 2 inches from a wall and rotate without letting the front knee touch the wall.
> - **Estimated attack angle is +1°** (target +5° to +20°). Combined with the leak above, the swing is flat *and* late. The Hook 'Em drill should help; if not, layer in a high tee to bias the swing slightly upward.
>
> ## Confidence Note
> Pose confidence 0.81, frontal view detected at 0.74 confidence — separation and angle measurements are reliable. Bat speed is a normalized proxy (no calibrated bat tracker), so treat it as relative.

That's the difference: the same hitter, the same data, but the second version *tells them where the leak is, why it costs them speed, what specific drill targets it, and what success looks like.*

---

## Sources

- [Rotational Acceleration, Sequencing, and the Swing — Driveline](https://www.drivelinebaseball.com/2020/06/rotational-acceleration-sequencing-and-the-swing/)
- [Hitting Biomechanics — Driveline](https://www.drivelinebaseball.com/2022/09/hitting-biomechanics/)
- [Introduction to K-Vest — Driveline](https://www.drivelinebaseball.com/2018/11/introduction-k-vest/)
- [Evaluating a Swing Using K-Vest Performance Graphs — Driveline](https://www.drivelinebaseball.com/2019/06/evaluating-a-swing-using-k-vest-performance-graphs/)
- [Using Swing Plane to Coach Hitters — Driveline](https://www.drivelinebaseball.com/2018/05/using-swing-plane-coach-hitters-deeper-look/)
- [Using MLB Bat Tracking Data to Better Understand Swings — Driveline](https://www.drivelinebaseball.com/2024/07/using-mlb-bat-tracking-data-to-better-understand-swings/)
- [Hip Hinge, Hip Shoulder Separation, and Maintaining Spine Angle — Driveline](https://www.drivelinebaseball.com/2019/10/hitting-concepts-visualizing-the-why-behind-hip-hinge-hip-torso-separation-and-maintaining-spine-angle/)
- [Understanding the Kinematic Sequence — RPP Baseball](https://rocklandpeakperformance.com/understanding-the-kinematic-sequence/)
- [3 Most Common Kinematic Sequence Flaws in Baseball Swings — RPP](https://rocklandpeakperformance.com/3-most-common-kinematic-sequence-flaws-in-baseball-swings/)
- [3 Questions When Analyzing Kinematic Sequence with K-Vest — RPP](https://rocklandpeakperformance.com/3-questions-when-analyzing-kinematic-sequence-k-vest-baseball/)
- [The Truth About Hip-to-Shoulder Separation — Florida Baseball ARMory](https://floridabaseballarmory.com/the-truth-about-hip-to-shoulder-separation/)
- [Hitting a baseball: a biomechanical description — Welch et al. (PubMed)](https://pubmed.ncbi.nlm.nih.gov/8580946/)
- [Lower extremity kinematic and kinetic factors associated with bat speed at ball contact during the baseball swing — PubMed](https://pubmed.ncbi.nlm.nih.gov/37853750/)
- [Longitudinal changes in youth baseball batting based on body rotation and separation — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10683358/)
- [Energy Flow and Ground Reaction Force Predictors of Bat Swing Speed (NMU)](https://commons.nmu.edu/isbs/vol41/iss1/45/)
- [Statcast Bat Tracking — MLB.com](https://baseballsavant.mlb.com/leaderboard/bat-tracking)
- [New Statcast metrics measure swing path, attack angle, attack direction (2025) — MLB](https://www.mlb.com/news/new-statcast-swing-metrics-2025)
- [Test Driving Statcast's Newest Bat Tracking Metrics — FanGraphs](https://blogs.fangraphs.com/test-driving-statcasts-newest-bat-tracking-metrics/)
- [Blast Motion Baseball metrics review — RPP](https://rocklandpeakperformance.com/a-review-of-blast-motion-baseball-and-its-swing-quality-metrics/)
- [Blast Connect — Attack Angle (baseball)](https://blastconnect.com/training_center/baseball/metrics/baseball-swing/49)
- [Blast Connect — Attack Angle (softball)](https://blastconnect.com/training_center/softball/metrics/softball-swing/55)
- [Blast — Time to Contact](https://blastmotion.com/blog/building-efficient-swings-time-contact/)
- [Vertical Bat Angle — Eric Cressey](https://ericcressey.com/vertical-bat-angle-a-new-way-to-look-at-batter-vs-pitcher-matchups/)
- [Baseball Swing Stride and Head Movement Relationships — SABR](https://sabr.org/journal/article/baseball-swing-stride-and-head-movement-relationships/)
- [Eye and Head Movements of Elite Baseball Players in Real Batting — Frontiers / PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7739578/)
- [Temporally Coupled Coordination of Eye and Body Movements in Baseball Batting — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7739824/)
- [Do Baseball Batters Keep Their Eye on the Ball? — SABR](https://sabr.org/journal/article/do-baseball-batters-keep-their-eye-on-the-ball/)
- [The Science and Artistry Behind a Perfect Swing (Williams) — Ted Williams Foundation](https://tedwilliamsfoundation.com/the-science-and-artistry-behind-a-perfect-swing-ted-williams-approach-to-hitting/)
- [Hitting Mechanics: The Twisting Model and Williams's "The Science of Hitting" — SABR](https://sabr.org/journal/article/hitting-mechanics-the-twisting-model-and-ted-williamss-the-science-of-hitting/)
- [The History of Swing Mechanics in Baseball — Jaime Cevallos](https://www.jaimecevallos.com/blogs/baseball-swing/the-history-of-swing-mechanics-in-baseball-old-school-new-school-and-me)
- [Linear vs Rotational Hitting — Pro Baseball Insider](https://probaseballinsider.com/linear-vs-rotational-hitting-pros-cons-baseball-swing/)
- [Rotational Hitting History — Mike Epstein](http://www.mikeepsteinhitting.com/TipsAndInfo/RotationalHittingHistory.html)
- [The Biomechanics of the Softball Swing in Seven Stages — Lawrence University](https://lux.lawrence.edu/cgi/viewcontent.cgi?article=1162&context=luhp)
- [Softball swing mechanics — MVP Batting Cages](https://mvpbattingcages.com/softball-swing-mechanics/)
- [Slap Hitting Softball: The Complete Guide — GoRout](https://gorout.com/slap-hitting-softball/)
- [Launch Angle in Baseball and Softball — The Hitting Vault](https://thehittingvault.com/launch-angles-baseball-softball/)
- [Baseball Hitting Drills — Driveline](https://www.drivelinebaseball.com/2022/06/baseball-hitting-drills/)
- [Pillar Turn Drill — The Hitting Vault](https://thehittingvault.com/pillar-turn-drill/)
- [Fixing Bat Drag — Chris O'Leary](https://clients.chrisoleary.com/Hitting/Fixing-Bat-Drag)
- [The 5 Most Common Baseball Swing Mechanics Flaws — Momentum Sports NY](https://momentumsportsny.com/the-5-most-common-baseball-swing-mechanics-flaws-we-see-and-how-to-fix-them/)
