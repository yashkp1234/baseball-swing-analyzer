# Swing Viewer Redesign Plan

## Problem Statement

The current "3D Swing Viewer" fails the primary user — a player trying to understand and improve their swing:

- Floating stick figure in a black void requires 3D spatial reasoning from a non-technical user
- "Kinetic chain efficiency: 50%" — every value is 0.50 because the heuristic 3D lifter returns uniform scores
- "Frame 2: hip center velocity drop — 39%" — raw biomechanics log, not coaching
- The "3D" label is misleading: depth is heuristically estimated from 2D keypoints, not real
- Player leaves the viewer not knowing what to do

**Rename: "3D Swing Viewer" → "Swing Breakdown"**

---

## What We're Building

Three panels answering three questions a player would actually ask.

### Panel 1 — What did my body do?
**Component:** `HipShoulderDiagram.tsx`

Top-down SVG arc diagram:
- Red arc = hip rotation sweep from load to contact
- Blue arc = shoulder rotation sweep from load to contact
- Gap label = "Your hips led your shoulders by X°" (plain-English X-factor)
- Animated: scrubbing grows the arcs in real time

Data: `keypoints[11/12]` (hips) + `keypoints[5/6]` (shoulders) → compute axis angle per frame client-side.

### Panel 2 — Where did my power build and leak?
**Component:** `PhaseEnergyChart.tsx`

Bar chart — one bar per swing phase:
- Height = average right-wrist velocity in that phase
- Color = existing phase color from `metrics.ts`
- Labels: Load · Stride · Launch · Contact · Follow-Through
- Red marker on frames where velocity dropped >30%
- One plain-English sentence below each bar: "Power built well here." / "You lost speed here."

Filter: only show energy loss events with `magnitude_pct > 30`. Typical swing shows 1–3 meaningful events.

Data: `frames[i].velocities.right_wrist` grouped by `phase_labels[i]`.

### Panel 3 — What happens if I fix this?
**Component:** `WhatIfSimulator.tsx`

Two sliders. 100% client-side. No backend re-run.

| Slider | Target range | Human label |
|--------|-------------|-------------|
| X-Factor | 20–45° | Hip-Shoulder Separation |
| Head Movement | 0–30px | Head Stability |

Live score projection: "If you reach both targets, your score goes from 74 → [live number]"

Scoring: good zone = 100pts, moderate = 60pts, poor = 20pts. Weighted average = overall score. Sliders override their metric's value and score recalculates synchronously.

### Frame Scrubber
Reuses `PhaseTimeline` + existing `Slider` component.

**Frame count by video type:**

| Video | Source FPS | Processed Frames |
|-------|-----------|-----------------|
| 2s phone swing @ 30fps | 30 | **30 frames** |
| 4s phone swing @ 30fps | 30 | **60 frames** |
| 2s slow-mo @ 60fps | 60 | **60 frames** |
| 10s long video @ 60fps | 60 | **~150 frames** |
| Display cap | — | **200 frames** |

Shows: phase color bands · gold dot at `contact_frame` · white dot at `stride_plant_frame` · label "Frame 12 of 30 · Contact"

---

## Backend Changes

**None required.** All data already in `frames_3d` JSON:
- `frames[i].keypoints` → rotation diagram
- `frames[i].velocities.right_wrist` → energy chart
- `phase_labels` → phase grouping
- `contact_frame`, `stride_plant_frame` → markers
- `energy_loss_events` → filter >30%
- `metrics` → What-If baseline values

---

## Milestones

---

### M0 — Demolition
**Goal:** Remove Three.js entirely. App still builds and loads. Existing results page unaffected.

**Tasks:**
- `npm uninstall @react-three/fiber @react-three/drei three` in `frontend/`
- Delete `components/three/` directory (all 5 files)
- Gut `SwingViewerPage.tsx` — replace Three.js canvas with a placeholder div: "Swing Breakdown coming soon"
- Fix any TypeScript errors from removed imports

**Success criteria:**
- [ ] `npm run build` exits 0 with no errors
- [ ] Navigate to `/viewer/:jobId` — page loads, no crash, no blank screen
- [ ] Results page still works — "Launch 3D Swing Viewer" button navigates without error
- [ ] Bundle size reduced (check with `npm run build` output — should drop ~2MB)

**Commit:** `feat: remove Three.js viewer, scaffold Swing Breakdown shell`
**Push:** yes — this is a clean, safe breaking change on the viewer only

---

### M1 — Scoring Engine
**Goal:** Client-side score function that powers the What-If simulator. Tested and correct before any UI is built on top of it.

**Tasks:**
- Create `frontend/src/lib/scoring.ts`
- `computeScore(metrics: Partial<SwingMetrics>, overrides?: Record<string, number>): number`
  - Loops over all metric keys with defined ranges
  - Zones each value: good=100, moderate=60, poor=20
  - Weighted average (all weights equal for MVP)
  - `overrides` map replaces specific metric values (for What-If)
- Write inline test cases as `scoring.test.ts` or validate manually with known values

**Success criteria:**
- [ ] `computeScore({ x_factor_at_contact: 30, hip_angle_at_contact: 170, ... })` returns a number in 0–100
- [ ] X-factor of -14.3° scores lower than X-factor of 30° (poor < good)
- [ ] `overrides` parameter changes the score as expected
- [ ] All existing metric keys in `METRIC_RANGES` are covered

**Commit:** `feat: add client-side swing scoring engine`
**Push:** yes

---

### M2 — Phase Energy Chart
**Goal:** First visible panel. Player can see where power built and leaked across phases.

**Tasks:**
- Create `frontend/src/components/PhaseEnergyChart.tsx`
- Accept props: `frames: Frame3D[]`, `phaseLabels: string[]`, `energyLossEvents: EnergyLossEvent[]`
- Group frames by phase, compute average `velocities.right_wrist` per phase
- Render bars with phase colors and human phase names
- Add plain-English sentence per bar (derive from velocity trend: rising/falling/flat)
- Show red dot markers only for events with `magnitude_pct > 30`
- Integrate into `SwingViewerPage.tsx` replacing placeholder
- Handle edge case: `velocities.right_wrist` missing → show "Speed data unavailable" gracefully

**Success criteria:**
- [ ] Screenshot of `/viewer/:jobId` shows a bar chart with labeled phases
- [ ] Phase colors match the timeline on results page
- [ ] At least one plain-English sentence visible below each bar
- [ ] No crash when `energy_loss_events` is empty
- [ ] No crash when a phase has 0 frames (e.g., short synthetic video missing some phases)
- [ ] Looks correct on 1440px wide screen (desktop)

**Commit:** `feat: add PhaseEnergyChart to Swing Breakdown`
**Push:** yes

---

### M3 — Hip-Shoulder Rotation Diagram
**Goal:** Player can see their hip vs shoulder rotation as a top-down arc — the X-factor story told visually.

**Tasks:**
- Create `frontend/src/components/HipShoulderDiagram.tsx`
- Accept props: `frames: Frame3D[]`, `currentFrame: number`, `contactFrame: number`
- Compute hip axis angle and shoulder axis angle from keypoints each frame:
  - Hip angle: `atan2(left_hip.y - right_hip.y, left_hip.x - right_hip.x)`
  - Shoulder angle: same for shoulders
- Draw SVG: circle for body center, two arcs sweeping from frame-0 angle to current-frame angle
- Label the gap: "Hips led shoulders by X°" or "Shoulders ahead of hips — work on this"
- At `contactFrame`, freeze arcs and show final separation label
- Wire into `SwingViewerPage.tsx` with frame scrubber controlling `currentFrame`

**Success criteria:**
- [ ] Screenshot shows two visible colored arcs on a circular diagram
- [ ] Scrubbing the frame slider animates the arcs growing
- [ ] Gap label updates as frames change
- [ ] At contact frame, arcs show final position with separation value
- [ ] Diagram renders correctly when hip/shoulder keypoints have low confidence (score < 0.3) — show "Low confidence" warning instead of incorrect arc
- [ ] No crash on synthetic video (30 frames, limited phase variety)

**Commit:** `feat: add HipShoulderDiagram to Swing Breakdown`
**Push:** yes

---

### M4 — What-If Simulator
**Goal:** Player can drag sliders and see live score projection. Most actionable feature.

**Tasks:**
- Create `frontend/src/components/WhatIfSimulator.tsx`
- Accept props: `metrics: SwingMetrics`
- Show current overall score (from `computeScore(metrics)`)
- Two sliders: X-Factor (range -20 to 60°) and Head Movement (range 0 to 100px)
- Each slider initialised to the actual value from `metrics`
- Projected score = `computeScore(metrics, { x_factor_at_contact: sliderVal, head_displacement_total: sliderVal2 })`
- Score diff display: "+15 points if you hit both targets" in green / "–" if slider is at current value
- Target zone indicator on each slider: green highlight over the good range
- Integrate into `SwingViewerPage.tsx`

**Success criteria:**
- [ ] Screenshot shows two sliders with current values pre-filled
- [ ] Moving X-Factor slider from -14° toward 30° increases the projected score visibly
- [ ] Score diff label shows correct arithmetic (verify manually)
- [ ] Sliders are keyboard-accessible (Tab + arrow keys)
- [ ] Sliders have ARIA labels
- [ ] Score never goes below 0 or above 100 regardless of slider position

**Commit:** `feat: add WhatIfSimulator to Swing Breakdown`
**Push:** yes

---

### M5 — Layout, Polish & Full Integration
**Goal:** All three panels assembled into a page that looks finished. Player can navigate the full flow: upload → results → swing breakdown.

**Tasks:**
- Finalize `SwingViewerPage.tsx` layout:
  - Header: "← Back to Results" + "Swing Breakdown" title + date/video name
  - Frame scrubber pinned to bottom (phase bands, contact dot, frame label)
  - Play/Pause button with 0.25× / 0.5× / 1× speed options (reuse existing)
  - Desktop: 2-column grid — diagram left, energy chart right, simulator full-width below
  - Mobile: single column, all panels stacked
- Add loading skeleton (shimmer bars while `frames_3d` loads)
- Add error state ("Breakdown data unavailable — return to results")
- Update results page: rename "Launch 3D Swing Viewer" button → "See Swing Breakdown"
- Ensure page title in `<header>` says "Swing Breakdown" not "3D Swing Viewer"
- Run `web-design-guidelines` skill audit, fix any flagged issues

**Success criteria:**
- [ ] Screenshot shows all three panels visible without scrolling on 1440px desktop
- [ ] Mobile screenshot (375px) shows panels stacked, no horizontal overflow
- [ ] Loading state shows shimmer, not blank page
- [ ] Error state shows graceful message, not crash
- [ ] Full flow works: upload video → see results → click "See Swing Breakdown" → viewer loads with real data
- [ ] No console errors or React warnings in browser dev tools
- [ ] `npm run build` exits 0

**Commit:** `feat: Swing Breakdown — full layout, polish, mobile, error states`
**Push:** yes

---

### M6 — Results Page Redesign
**Goal:** Fix all the broken/ugly items on the main results page identified in the screenshot.

**Specific fixes:**
- `NaN%` pose confidence → guard: `isNaN(val) ? "—" : val + "%"`
- `undefined` peak wrist vel → add `wrist_peak_velocity_normalized` to `METRIC_RANGES`
- Empty coaching bullets → fix field name: `coaching_html` not `coaching`
- Render `coaching_html` as HTML (`dangerouslySetInnerHTML`) or parse into lines
- Black video → add `crossOrigin="anonymous"` to `<video>` + verify `Accept-Ranges` header on artifact endpoint
- Metric cards: add a one-line plain-English tooltip or sub-label explaining what each metric means (e.g. "X-Factor: how far your hips lead your shoulders")
- MetricCard color: `poor` = red border, but add text label "NEEDS WORK" / "GOOD" / "ON TRACK" so color isn't the only indicator
- Overall swing score card at top (using `computeScore` from M1)
- Phase timeline: replace raw phase names with human names ("load" → "Load Up", "contact" → "Contact", "follow_through" → "Follow Through")

**Success criteria:**
- [ ] No `NaN` or `undefined` visible anywhere on results page
- [ ] Coaching text renders with actual content (not empty bullets)
- [ ] Annotated video plays (or shows explicit "Video processing…" fallback if not ready)
- [ ] Every metric card has a plain-English sub-label
- [ ] Overall score card visible at top of results page
- [ ] Phase timeline shows human-readable phase names
- [ ] `npm run build` exits 0

**Commit:** `fix: results page — NaN, coaching, video, metric labels, score card`
**Push:** yes

---

### M7 — Landing Page Redesign
**Goal:** Upload page is visually compelling and immediately clear. Player knows what to do in under 3 seconds.

**Specific improvements:**
- Larger, bolder headline with a clear value proposition (not just "SwingMetrics")
- Sub-headline: "Upload your swing video. Get a personalized breakdown in under 30 seconds."
- Upload zone: larger hit area, animated dashed border on hover, accepts drag-and-drop
- Example of what you get: small preview strip showing the 3 panels (static image or illustrated)
- Processing screen: replace generic spinner with step-by-step progress that explains what's happening: "Detecting your stance…" / "Measuring hip rotation…" / "Building your report…"
- Better typography: load a web font (Geist or Inter from Google Fonts)
- Consistent use of accent green for CTAs only (not structural elements)

**Success criteria:**
- [ ] Screenshot of landing page at 1440px shows headline, sub-headline, and upload zone clearly
- [ ] Drag a video file onto the page → upload zone highlights visually
- [ ] Processing screen shows human step labels matching `current_step` values from the API
- [ ] Web font loads (verify in Network tab: font file fetched)
- [ ] No layout shift on load (no CLS)
- [ ] Mobile screenshot (375px) — headline readable, upload zone tappable

**Commit:** `feat: redesign landing page and processing screen`
**Push:** yes

---

## Dependency on Each Other

```
M0 (demolition)
  └── M1 (scoring engine)
        ├── M2 (energy chart)       ← independent of M3
        ├── M3 (rotation diagram)   ← independent of M2
        └── M4 (what-if simulator)  ← depends on M1
              └── M5 (full layout + polish)  ← depends on M2, M3, M4
                    ├── M6 (results page)    ← independent of M5
                    └── M7 (landing page)    ← independent of M5
```

M2, M3 can be built in parallel after M1. M6 and M7 can be built in parallel after M5.

---

## Skills to Invoke

| Milestone | Skill |
|-----------|-------|
| All UI components | `/frontend-design` |
| After each milestone | `webapp-testing` — screenshot to verify |
| Before M5 push | `web-design-guidelines` — accessibility audit |
| Before M5 push | `vercel-react-best-practices` — React perf review |

---

## Definition of Done

The full redesign is complete when:
1. All 7 milestones committed and pushed
2. `npm run build` exits 0
3. Full flow tested: upload → processing → results → swing breakdown
4. No `NaN`, `undefined`, or empty content visible on any screen
5. Mobile layout verified at 375px on all three pages
6. No console errors in browser dev tools on any page
