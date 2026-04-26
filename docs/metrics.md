# Metrics Reference

## Phase 1 (2D) Metrics

All derived from COCO-17 pose keypoints. Units are degrees for angles, pixels for distances, pixels/second for velocities.

### Angles

| Metric | Formula | View constraint | Coaching relevance |
|--------|---------|-----------------|-------------------|
| hip_angle | angle(LH→RH vs horizontal) | Frontal/back view only | Pelvic rotation in transverse plane |
| shoulder_angle | angle(LS→RS vs horizontal) | Frontal/back view only | Shoulder rotation in transverse plane |
| x_factor | hip_angle − shoulder_angle (normalized ±180°) | Frontal/back view only | Hip-shoulder separation = stretch |
| lateral_spine_tilt | angle(shoulder_mid→hip_mid vs vertical) | Any view | Side-bend / posture |
| knee_angle(side) | 180° − interior(hip−knee−ankle) | Any view | Flexion: 0° = straight, ↑ = more bent |

### Timing / Kinematics

| Metric | Formula | Coaching relevance |
|--------|---------|-------------------|
| stride_foot_plant_frame | local minimum of lower ankle y-position | Timing anchor for kinetic chain |
| wrist_velocity | ‖Δwrist‖ / Δt per frame, max over both wrists | Bat speed proxy |
| head_displacement | total Euclidean movement of nose (load→contact) | Stability / "quiet head" |
| phase_durations | frame counts per phase label | Rhythm and consistency |

### Output report fields

- `phase_durations` — dict of frame counts
- `stride_plant_frame`
- `contact_frame` — frame of peak wrist velocity
- `hip_angle_at_contact`
- `shoulder_angle_at_contact`
- `x_factor_at_contact`
- `spine_tilt_at_contact` (alias for `lateral_spine_tilt_at_contact`)
- `left_knee_at_contact`
- `right_knee_at_contact`
- `head_displacement_total`
- `wrist_peak_velocity_px_s`
- `frames`, `fps`

## Swing Segments

Long videos are reduced to active swing windows using wrist and hand velocity. The segment detector keeps a pre-swing buffer so the load, hand start, and stride context remain visible instead of clipping directly at the fastest hand movement. If multiple swings are present, the analyzer returns multiple segment windows and chooses the highest-confidence segment as the primary report.

Segment fields:

- `start_frame`
- `end_frame`
- `contact_frame`
- `duration_s`
- `confidence`

## Estimated Bat And Ball Position

The viewer estimates bat handle and barrel position from wrist and forearm keypoints. The ball/contact point is estimated from the barrel position at the contact frame. These are visual coaching aids, not measured bat or ball tracking.

## Projected EV And Carry

Projected exit velocity and carry are pose-proxy estimates. They help compare the current swing against a projected mechanical change, but they are not measured launch metrics or measured ball flight.
