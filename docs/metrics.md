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
