# Results Interpretive Replay Design

**Date:** 2026-04-29  
**Scope:** Clean up the results page, fix demo routing, and replace the misleading 3D story with a simpler interpretive replay that matches three-quarter softball swings.

## Problem Statement

The current experience breaks trust in four ways:

1. The main `results/demo` route is not backed by a real demo payload, so the page can render a fake processing state instead of a real report.
2. The current 3D/breakdown story implies tracked bat and ball data even though the backend exports estimated bat geometry from wrists/forearms and estimated ball contact from the bat proxy.
3. The analyzed softball clip produces multiple artifact warnings and unstable timing/rotation/body-motion outputs, yet the UI still invites the user to read too much precision out of the scene.
4. The results page keeps stacking secondary surfaces below the main story, so the user has to fight through extra panels after the primary clip.

## Verified Root Cause

### Backend truth

- In [export_3d.py](C:/Users/yashk/baseball_swing_analyzer/.worktrees/results-interpretive-replay/src/baseball_swing_analyzer/export_3d.py), bat handle and barrel are estimated from wrist and forearm direction with fixed length and low confidence.
- Ball position is estimated from the contact-frame barrel proxy, not tracked from video.
- A real run on `Prettiest Softball Swing of All Time.mp4` produced artifact warnings for attack angle, pelvis angular velocity, clipped rotation metrics, clipped body motion metrics, and untrustworthy timing.

### Frontend truth

- [ResultsPage.tsx](C:/Users/yashk/baseball_swing_analyzer/.worktrees/results-interpretive-replay/frontend/src/pages/ResultsPage.tsx) does not special-case `demo`, so `results/demo` can only show a fake loading path unless a real job exists.
- The current page keeps the annotated video, summary, takeaways, improvement plan, and diagnostics all on one long surface.
- The current replay language does not make the truth boundary explicit enough for pose-only three-quarter clips.

## Goals

- Make `results/demo` render a first-class demo report.
- Redesign the results page into a cleaner watch-and-understand surface.
- Replace the misleading 3D framing with one clear interpretive replay that shows:
  - the hitter body
  - the estimated bat path
  - the current bat position
  - the contact point
  - an estimated exit path after contact
- Suppress or relabel unreliable claims for three-quarter pose-only clips.
- Keep diagnostics available, but clearly secondary.

## Non-Goals

- No claim of measured bat tracking.
- No claim of measured ball flight.
- No new bat-detection or ball-detection model in this pass.
- No rewrite of the entire backend analysis pipeline.
- No attempt to make clipped rotation metrics trustworthy for this clip type.

## Truthfulness Contract

Every major surface element must fall into one of four states:

- `measured`: directly observed from the pipeline with acceptable confidence
- `estimated`: inferred from pose heuristics
- `derived`: computed from measured and/or estimated inputs
- `unavailable`: hidden or replaced because the source signal is not trustworthy

For this redesign:

- Annotated video: `measured`
- Phase labels: `derived`
- Estimated bat path: `estimated`
- Contact point: `estimated`
- Exit trajectory: `estimated`
- Exact hip/shoulder rotation callouts on three-quarter clips: `unavailable`
- Attack angle on clips with attack-angle artifact warning: `unavailable`

## Recommended Experience

### Results page hierarchy

The results page should become:

1. Header
2. One primary split surface:
   - concise verdict + short takeaways
   - annotated clip
   - interpretive replay
3. One compact takeaway strip
4. One collapsed details section

The following should be removed from the primary story:

- improvement-plan block
- extra coaching scaffolding below the main clip
- any repeated “what to do next” cards that duplicate the hero verdict

### Interpretive replay

This should not present itself as measured 3D. It should be an **interpretive replay** tuned for a side/three-quarter softball swing.

Scene layers:

- hitter pose trail with restrained depth cue
- smoothed estimated bat path
- current bat segment
- contact point marker
- estimated exit trajectory beginning at contact
- subtle ground reference

Interaction:

- auto-play loop
- frame-following with the selected video frame
- no multi-variant 3D chooser
- no orbit-heavy controls in the primary results view

### Confidence gating

If the clip carries unreliable-metric warnings:

- hide exact attack-angle language
- hide exact rotation callouts
- hide head-movement claims when body-motion clipping is flagged
- replace them with one concise note explaining what this view is good for: timing, shape, path, and finish

## Architecture

### Recommended approach

Keep the current frontend replay model lightweight and honest:

- use a frontend demo-results fixture for `results/demo`
- enrich the replay component so it can show ball/contact/exit-path layers
- use existing artifact warnings and view type to gate which claims and labels render
- simplify the results page rather than adding another deep branch of viewer UI

This is preferred over building a more elaborate 3D scene first, because the current issue is not lack of rendering complexity. It is mismatch between scene language and source truth.

### Alternatives considered

#### 1. Keep the three-view breakdown and just polish visuals

Rejected because it still asks the user to infer too much from pose-only proxy data and keeps the “what are we even showing?” problem alive.

#### 2. Build a fully orbitable Three.js scene directly on the results page

Rejected for this pass because it would add complexity without fixing the trust problem first. A better-looking scene is not automatically a more truthful one.

#### 3. Remove all replay and keep only annotated video

Rejected because the user explicitly wants a cleaner motion story with ball and trajectory, and the annotated video alone does not provide that.

## Components And Data Flow

### Demo plumbing

- Add a demo results helper in the frontend that mirrors a completed job response.
- `ResultsPage` should special-case `jobId === "demo"` the same way `SwingViewerPage` already does.

### Results composition

- Reuse `ExecutiveSummaryHero` for the top verdict.
- Add a compact “swing read” rail instead of the larger improvement-plan surface.
- Keep `DetailsDiagnostics` collapsed and secondary.

### Replay composition

- Extend `AnimatedSwingReplay` with optional `ball`, `trajectory`, and `mode` props.
- Generate an estimated exit path from contact using existing bat direction and a simple fade-out arc.
- Use warning-aware copy so the replay says “estimated” in the right places.

## Testing Strategy

### Frontend unit tests

- `ResultsPage.test.tsx`
  - demo route renders a real report instead of processing UI
  - improvement-plan block is absent from the primary page
  - collapsed details remain available
- `AnimatedSwingReplay.test.tsx`
  - estimated contact/trajectory copy appears
  - unreliable metrics suppress exact-claim language

### Browser verification

- `results/demo` renders the cleaned page
- primary replay and annotated video both show
- replay contains visible bat path and exit path
- no fake processing UI for demo
- lower page clutter is reduced

## Milestones

### Milestone 1: Demo report plumbing and page cleanup

- add demo results fixture
- special-case `results/demo`
- remove improvement-plan section from the primary page
- keep only concise summary + video + replay + details

### Milestone 2: Interpretive replay redesign

- extend replay with contact marker, ball point, and estimated exit path
- revise copy to label estimated layers clearly
- gate unreliable exact claims

### Milestone 3: Verification and polish

- run frontend tests
- run build
- verify page and replay in browser screenshots

## PR Plan

- PR 1: `demo-results-plumbing-and-clean-results-layout`
- PR 2: `interpretive-replay-truthfulness-and-trajectory`
- PR 3: `verification-and-polish`
