# Swing Viewer Truthful 3D Design

**Date:** 2026-04-25  
**Scope:** Fix the current swing viewer so it shows an actual 3D rendering, uses truthful data, supports actionable What If projections, and fits inside the viewport without page scroll on desktop.

## Problem Statement

The current `/viewer/:jobId` experience breaks the user contract in four ways:

1. The "3D" viewer is not a 3D viewer. It replays `annotated.mp4` instead of rendering `frames_3d.json`.
2. The Hip vs Shoulder Rotation panel incorrectly treats 3D `z` coordinates as confidence values and frequently suppresses the diagram.
3. The swing breakdown page vertically scrolls, which makes the experience feel unfinished and prevents the viewer from acting like a focused analysis surface.
4. The What If simulator only changes a score card. It does not update the rendered swing and does not produce projected exit velocity or distance.

The result is that the viewer looks richer than it is, but does not actually earn the trust the rest of the analysis flow is trying to build.

## Goals

- Render a real animated 3D skeleton from `frames_3d.json` on the viewer page.
- Make the right-hand analysis surfaces accurate and resilient.
- Keep the desktop viewer on one screen with no document-level vertical scroll.
- Make What If produce:
  - a changed 3D swing preview
  - a projected exit velocity estimate
  - a projected carry distance estimate
- Keep uploads and core analysis latency unchanged. What If must not rerun the full analysis pipeline.

## Non-Goals

- No retraining or replacement of the pose model.
- No promise of Statcast-grade ball flight accuracy.
- No fully physics-based bat-ball collision engine.
- No redesign of unrelated results-page content outside what is needed to launch and explain the viewer.

## User-Facing Contract

When a user opens the swing viewer:

- The left side shows a real 3D skeleton animation driven by the exported 3D frames.
- The user can scrub/play/pause the swing and see phase-aware overlays.
- The Hip vs Shoulder panel reflects the current 3D frame instead of reporting false low-confidence failures.
- The page fits in the viewport on desktop with no page scroll.

When a user changes a What If control:

- The change is applied after slider release, not continuously while dragging.
- The app requests a fast projection result from the backend using the already-computed job artifacts.
- The 3D animation updates to the projected pose sequence.
- Exit velocity and carry distance update with the projection.
- The UI clearly labels the values as projected estimates.

## Architecture Decision

### Recommended Approach

Use a real Three.js viewer in the frontend and a lightweight backend projection endpoint for What If.

This keeps the live 3D rendering in the browser where it belongs, while moving the deterministic projection math to Python so it is testable, centralized, and easy to evolve. It also avoids rerunning the expensive analysis pipeline and keeps What If interactions fast.

### Alternatives Considered

#### 1. Frontend-only What If projection

Pros:
- Lowest request latency
- No new backend endpoint

Cons:
- Duplicates biomechanical projection logic in TypeScript
- Harder to test and evolve
- Easy for frontend and backend assumptions to drift apart

#### 2. Full backend recompute

Pros:
- Most "correct" in principle
- Could reuse existing analysis machinery

Cons:
- Far too slow for interactive What If
- Risks violating the user's responsiveness expectations
- Overkill for synthetic adjustments to an existing analyzed swing

#### 3. Backend projection over existing job artifacts

Pros:
- Fast and deterministic
- Testable in Python
- Honest separation between original analysis and projected simulation

Cons:
- Requires designing a projection model and API contract

This is the chosen approach.

## Data Model Changes

### Existing Inputs

- `frames_3d.json` already contains:
  - normalized 3D keypoints
  - phase labels
  - frame count / fps
  - contact frame
  - per-frame velocities
  - summary metrics

### New Projection Request

`POST /api/jobs/{job_id}/projection`

Request body:

```json
{
  "x_factor_delta_deg": 8,
  "head_stability_delta_norm": 0.08
}
```

### What If Control Contract

The What If sliders operate on **deltas from the current analyzed swing**, not absolute targets. The UI shows both the baseline metric and the applied delta so the user can understand what changed.

| Control | Request field | Unit | Default | Min | Max | Step | Clamp rule |
|---|---|---:|---:|---:|---:|---:|---|
| Hip/shoulder separation gain | `x_factor_delta_deg` | degrees | `0` | `-12` | `12` | `1` | clamp to range before transform |
| Head stability adjustment | `head_stability_delta_norm` | normalized viewer-space offset | `0` | `-0.12` | `0.12` | `0.01` | clamp to range before transform |

`head_stability_delta_norm` is defined in the same normalized coordinate space as `frames_3d.json`, not pixels. Positive values reduce head drift magnitude by pulling the upper-body chain back toward the head anchor across the active swing window; negative values exaggerate drift for simulation purposes.

### New Projection Response

```json
{
  "baseline": {
    "exit_velocity_mph": 84.1,
    "carry_distance_ft": 287.0,
    "score": 74
  },
  "projection": {
    "exit_velocity_mph": 88.4,
    "carry_distance_ft": 301.0,
    "score": 82,
    "notes": [
      "Projected from baseline swing metrics",
      "Estimate updates the rendered swing but does not rerun pose analysis"
    ]
  },
  "viewer": {
    "fps": 30,
    "total_frames": 120,
    "contact_frame": 63,
    "stride_plant_frame": 49,
    "phase_labels": ["..."],
    "frames": ["... projected 3D frame objects ..."],
    "skeleton": [[5, 6], [5, 7]],
    "keypoint_names": ["nose", "left_eye"]
  }
}
```

The response intentionally mirrors the `frames_3d.json` shape for all fields the viewer uses at render time so the frontend can swap baseline and projected sequences without partial special-casing.

### Baseline Ownership

Baseline EV, carry distance, and score are owned by the projection endpoint response. The frontend does not synthesize them locally. On viewer load, the frontend performs an initial zero-delta projection request to obtain the authoritative baseline and establish one response shape for both baseline and projected states.

## Backend Design

### 1. Projection Engine

Add a lightweight projection module that:

- loads the baseline 3D viewer data for a job
- applies deterministic pose transforms in the swing window
- recalculates derived projection outputs

The initial transform rules should be simple and explicit:

- `x_factor_delta_deg` rotates the shoulder chain relative to the hip chain around the viewer-space vertical axis (`y`), concentrated from `load` through `contact`
- `head_stability_delta_norm` applies a viewer-space translation to the shoulder/elbow/wrist chain opposite the baseline head-drift direction, anchored at the nose, concentrated from `load` through `contact`

### Projection Semantics

- Authoritative source artifact: `frames_3d.json`
- Coordinate space: normalized viewer-space coordinates emitted by `export_3d.py`
- Active window:
  - start at first `load` frame
  - end at first `contact` frame
  - if either label is missing, fall back to `max(0, contact_frame - 12)` through `contact_frame`
- Easing:
  - 0% effect before window
  - cosine ease-in from window start to contact
  - hold final transform from contact through follow-through
- Missing-data fallback:
  - if required joints for a transform are missing/non-finite in a frame, leave that frame unchanged and continue

The projection engine must never write back to stored artifacts or enqueue the main analysis pipeline.

This should change the rendered skeleton in a visible way without pretending to be a full biomechanical simulator.

### 2. Projected Outcome Estimator

Add a small deterministic estimator for:

- projected exit velocity
- projected carry distance

The estimator will derive its baseline from existing metrics such as:

- wrist peak velocity
- x-factor at contact
- head displacement
- phase timing / contact quality proxies

The model should be rule-based and transparent, with bounded output changes. It must never claim to be measured ball-tracking output.

### 3. API Surface

Add a new router endpoint returning projected viewer frames plus projected outcome values. The endpoint must:

- return `404` for unknown jobs
- return `409` or equivalent job-state error if analysis artifacts are unavailable
- validate deltas and clamp them to supported ranges
- avoid mutating stored baseline artifacts
- return baseline and projected summaries in one response
- never rerun or enqueue the main analysis job

### Performance Budget

- projection API p95 latency on a completed local job: `< 400 ms`
- viewer swap after slider release on desktop hardware: `< 150 ms` after response receipt
- uploads and analysis latency: unchanged, because What If never invokes the main job queue

## Frontend Design

### 1. Real 3D Viewer

Replace the `<video>` element in `SwingViewerPage.tsx` with a Three.js-based `SwingSkeletonViewer` component that:

- renders joints and bones from `frames_3d.json`
- animates at the exported fps
- supports play/pause, scrub, loop, speed control, and camera reset
- visually distinguishes the baseline and projected state when a What If projection is active

The viewer should also show a simple ground plane and axis orientation so the motion reads as spatial rather than flat.

### 2. Viewport-Stable Layout

Restructure the viewer page into a no-scroll desktop layout:

- top header strip
- left: fixed-height 3D canvas + transport controls
- right: tabbed analysis stack so only one major panel is visible at a time

Recommended right-side tabs:

- `Overview`
- `Kinematics`
- `What If`

This keeps the page inside the viewport without nesting multiple heavy cards in a long column.

### 3. Hip vs Shoulder Diagram Fix

Update the diagram to use the 3D data correctly:

- stop treating `keypoints[*][2]` as confidence
- compute top-down rotation as yaw in the `(x, z)` plane using `atan2(dz, dx)` between left/right hip and shoulder joints
- show unavailable only when required joints are actually missing or non-finite

### 4. What If Integration

The What If panel becomes stateful and real:

- slider changes update local draft values while dragging
- on release, the frontend calls the projection endpoint
- projected 3D frames replace the active viewer sequence
- projected EV and carry distance are shown beside the baseline values
- a reset action restores the original sequence and baseline estimates

### 5. Projection Request Lifecycle

- one projection request may be in flight at a time
- each request gets a monotonically increasing client request id
- the latest response wins; stale responses are discarded
- a new slider release supersedes the previous in-flight request in the UI
- while a projection request is pending:
  - keep showing the last successful viewer state
  - show compact loading feedback in the What If panel
  - disable reset only if no successful baseline/projection state exists yet

## Error Handling

- If projected data fails to load, preserve the baseline viewer and show a compact inline error in the What If panel.
- If the 3D viewer cannot initialize WebGL, show a non-crashing fallback explaining that the interactive 3D view is unavailable while keeping the analysis panels accessible.
- If job artifacts are incomplete, route-level messaging should explain what is missing instead of silently showing broken widgets.

## Testing Strategy

### Fixture Contract

- Backend unit/API tests use a checked-in synthetic fixture under `tests/fixtures/viewer_fixture.json`
- The fixture contains finite 3D keypoints, phase labels, contact frame, and metrics sufficient to compute deterministic projections
- Browser smoke testing may additionally use a live local job, but no acceptance criterion depends on a single ad hoc job id

### Backend

- unit tests for projection transforms
- unit tests for projected outcome estimator bounds and monotonic behavior
- API tests for success, missing job, and unavailable-artifact cases
- numeric assertions use deterministic tolerances:
  - EV tolerance: exact for synthetic fixture
  - carry tolerance: exact for synthetic fixture

### Frontend

- component tests for What If panel request lifecycle and reset behavior
- viewer-page tests for tab switching and baseline/projected state changes
- viewer verification must assert that projected frame data differs from baseline frame data before the canvas swaps state

### End-to-End

- verify `/viewer/:jobId` contains a rendered canvas and no primary `<video>` player
- verify the page has no document-level vertical scroll on a desktop viewport
- verify releasing a What If slider updates projected EV/distance and changes the rendered pose sequence
- verify play/pause/scrub/camera-reset controls function after baseline load

## Commit-Friendly Milestones

Autonomous execution proceeds **one milestone at a time**. Each milestone must be committed, tested, and reviewed before moving to the next.

### Milestone 1: Truthful Viewer Foundation

**Scope**
- Replace fake 3D video viewer with real 3D skeleton renderer
- Fix Hip vs Shoulder diagram data interpretation
- Restructure viewer page to remove desktop vertical scroll

**Success Criteria**
- `/viewer/:jobId` renders a 3D canvas from `frames_3d.json`
- the main viewer contains no `annotated.mp4` replay element
- Hip vs Shoulder panel renders for any fixture/job with finite left/right hip and shoulder joints
- desktop viewport `1366x900` has no document-level vertical scroll
- play/pause/scrub/camera-reset controls work
- frontend build passes

**Commit**
- `feat: replace fake viewer with real 3d swing scene`

### Milestone 2: Backend Projection API

**Scope**
- Add deterministic projection engine
- Add projected EV/carry estimator
- Add projection API endpoint and tests

**Success Criteria**
- projection endpoint returns modified frame data and projected EV/carry for a completed job
- endpoint responds without rerunning or enqueueing the core analysis job
- projection API meets the `< 400 ms` local latency budget on the fixture job
- backend tests pass, including new projection coverage

**Commit**
- `feat: add swing projection endpoint`

### Milestone 3: What If Becomes Real

**Scope**
- Wire What If slider release to projection API
- Swap viewer sequence to projected frames
- Show baseline vs projected EV/carry and reset path

**Success Criteria**
- releasing a What If control changes the rendered 3D motion
- projected EV and carry distance visibly update
- reset restores the baseline motion and values
- stale responses are discarded and do not overwrite newer slider releases
- no regression in results page launch flow

**Commit**
- `feat: connect what-if simulation to projected swing viewer`

### Milestone 4: Verification and Polish

**Scope**
- tighten empty/error states
- verify desktop viewer fit
- verify browser rendering with the real job fixture

**Success Criteria**
- end-to-end checks pass against the checked-in fixture path and an optional live job smoke test
- no crashing viewer panels on missing/partial data
- page remains usable when projection requests fail

**Commit**
- `fix: harden swing viewer states and verification`

## Acceptance Criteria

The work is done when all of the following are true:

- The swing viewer is visually and technically a real 3D viewer.
- The hip/shoulder panel reflects actual 3D geometry.
- The viewer fits in a desktop viewport without document scroll.
- What If updates the rendered swing and the projected EV/carry outputs.
- The implementation is covered by backend tests, frontend build verification, and browser-level checks.
