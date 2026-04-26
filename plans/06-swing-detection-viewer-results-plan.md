# Swing Detection, Viewer, and Results Plan

Date: 2026-04-26
Status: in progress

## Goal

Fix the long-clip swing detector so it stops treating generic movement as separate swings, improve the coaching language so it is understandable to players, add a better bat representation to the 3D view, improve 3D framing, and make the results surface use more of the screen.

## Research Notes

1. Pose-only action understanding is brittle for human-object interactions.
   - Pose-Based Two-Stream Relational Networks explicitly calls out that pose-only methods often miss action-related objects, and adds an object stream for better action recognition.
   - Source: https://arxiv.org/abs/1805.08484

2. Better temporal modeling matters when pose is noisy.
   - PoseC3D argues that stronger spatiotemporal representations are more robust to pose-estimation noise than simpler skeleton pipelines.
   - Source: https://arxiv.org/abs/2104.13586

3. We already have a plausible bat-detection path in the current stack.
   - Ultralytics COCO class lists include `baseball bat`, so the existing YOLO detector family can be extended beyond `person`.
   - Sources:
     - https://github.com/ultralytics/ultralytics/blob/main/docs/en/tasks/detect.md
     - https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml

4. The 3D framing problem should be solved with scene bounds, not fixed camera numbers.
   - Three.js `Box3.setFromObject(...)` and `getBoundingSphere(...)` provide the primitives needed to fit the rendered swing into view automatically.
   - Source: https://threejs.org/docs/pages/Box3.html

## What We Learned Locally

1. The current long-clip detector was combining sparse pose samples from the entire video into one pseudo-timeline.
2. On `data/videos/test_swing_30s.mp4`, the old path sampled 120 frames across 1012 source frames and collapsed the effective analysis rate to about `3.56 fps`.
3. That temporal collapse is a major reason the old detector produced `13` swing segments from a clip that should contain `6`.
4. A full-rate motion-window pass on the same clip produces `6` swing windows and keeps the per-window analysis rate near `24.7 fps`.

## Milestones

### Milestone 1: Make The Results Read Like Plain English
Status: complete

- Rewrite the summary layer to reduce repeated phrasing.
- Define terms like hip-shoulder separation (`X-factor`) in the UI.
- Clean up labels in the results diagnostics.
- Normalize coaching copy into player-facing language.

### Milestone 2: Replace Whole-Clip Swing Segmentation With Motion Windows
Status: in progress

- Detect repeated motion bursts on the full-rate motion signal.
- Expand and merge nearby bursts into swing candidate windows.
- Analyze each candidate window as its own dense clip instead of one sparse global clip.
- Keep the primary swing for the main report while preserving per-swing viewer artifacts.
- Validate against `data/videos/test_swing_30s.mp4` and the existing analyzer tests.

Current result:
- `test_swing_30s.mp4` now resolves to `6` swing windows instead of `13`.

### Milestone 3: Add Better Bat Capture To The 3D Model
Status: pending

- Start with a better bat estimate tied to the hands and forearms.
- Add an object-detection hook for `baseball bat` so we can upgrade from a hand-only proxy when a bat box is visible.
- Feed that representation into the 3D export so the viewer renders a clearer bat path.

### Milestone 4: Fix Viewer Framing And Results Layout
Status: pending

- Replace the fixed 3D camera start position with bounds-based fit logic.
- Reduce the overly tight framing in the 3D viewer.
- Widen the summary and analysis layout so the main review surface uses more of the viewport.

### Milestone 5: Final Verification And Merge
Status: pending

- Run Python and frontend test suites.
- Re-check the sample swing counts on the long test clip.
- Verify the results page and breakdown viewer in the browser.
- Merge the completed work into `main`.

## Execution Order

1. Finish the motion-window segmentation pass and stabilize tests.
2. Improve the bat representation and scene framing together so the viewer stays coherent.
3. Expand the results layout once the content and viewer behavior are stable.
4. Run full verification and merge.
