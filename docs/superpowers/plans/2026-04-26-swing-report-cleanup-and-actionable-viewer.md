# Swing Report Cleanup And Actionable Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove internal/debug language from the report, clip analysis down to actual swings, and turn the viewer into a single useful coaching surface with a one-mistake fix toggle that changes the projected swing and outcome estimates.

**Architecture:** Keep the results page user-facing and simple. Move sport-confidence and analysis-processing details out of primary UI, add backend swing-segment detection so long clips produce one or more swing clips, enrich the viewer JSON with bat/ball estimates and segment metadata, then replace the three-tab viewer with one repeatable comparison panel driven by a single recommended fix.

**Tech Stack:** Python 3.10+, pytest, OpenCV, NumPy, FastAPI, React 19, TypeScript, Vite, Vitest, Three.js.

---

## Current Findings

- `frontend/src/components/ExecutiveSummaryHero.tsx` renders user-hostile labels and explanations: `Score Signal`, `Evidence Layer`, and `Immediate Read`.
- `frontend/src/pages/SwingViewerPage.tsx` exposes `Detected Sport`, confidence-adjacent interpretation, and analysis details that should stay internal unless they change coaching copy.
- `frontend/src/components/PhaseTimeline.tsx` uses raw phase strings, tiny uppercase labels, hover-only explanations, and cramped markers.
- `src/baseball_swing_analyzer/analyzer.py` samples motion adaptively but still processes/report-displays idle frames around the swing. It does not produce multiple swing segments.
- `src/baseball_swing_analyzer/phases.py` classifies a single swing window inside the sampled sequence and labels everything else `idle`.
- `src/baseball_swing_analyzer/export_3d.py` exports pose-only skeleton frames. There is no bat path, bat barrel, contact-ball estimate, or per-swing segment metadata.
- `frontend/src/components/SwingSkeletonViewer.tsx` renders only body joints and bones.
- `frontend/src/components/WhatIfSimulator.tsx` offers sliders for x-factor and head stability. The requested interaction is a toggle for one recommended fix, not manual tuning.
- `src/baseball_swing_analyzer/projection.py` already supports pose projection and EV/carry estimates from proxy metrics, which can be reused behind the fix toggle.

## Scope Boundaries

Included:

- User-facing copy cleanup on executive summary and viewer.
- Hide sport-confidence diagnostics from normal user UI.
- Better phase timeline typography, labels, markers, and mobile behavior.
- Swing segmentation for long clips, including multiple-swing outputs.
- Annotated clip output trimmed to the swing segment instead of random extra movement.
- Viewer data enriched with swing segments, bat estimates, and ball/contact estimate.
- Single-panel viewer replacing tabs and the three-panel layout.
- One recommended-fix toggle that loops baseline/projected swing and updates projected score, EV, and carry estimates.
- Tests for backend segmentation/export/projection and frontend rendering/state.

Deferred:

- Real bat or ball detection model dependency. Use heuristic estimates from hands/wrists/contact frame for this pass.
- Real measured exit velocity or ball flight. Keep EV/carry as clearly-labeled estimates.
- Multi-camera calibration.
- MotionBERT or heavy 3D model changes.

## Branch And Commit Strategy

- Branch: `codex/actionable-swing-report`
- Commit after each task passes its task-level tests.
- Push once after all commits pass full backend and frontend verification.
- Final PR should describe that bat/ball and EV/carry are estimates, not measured outputs.

Commands:

```bash
git checkout main
git fetch origin
git pull --ff-only origin main
git checkout -b codex/actionable-swing-report
```

Final push:

```bash
git push -u origin codex/actionable-swing-report
```

---

## File Structure

Backend files:

- Create `src/baseball_swing_analyzer/swing_segments.py`: detect active swing windows from wrist/hand velocity and phase labels.
- Modify `src/baseball_swing_analyzer/analyzer.py`: use segment windows for sampled frames, report metadata, and annotated clip writing.
- Modify `src/baseball_swing_analyzer/phases.py`: expose reusable active-window helpers or keep classification compatible with segmented clips.
- Modify `src/baseball_swing_analyzer/export_3d.py`: include swing segment metadata plus bat and ball estimates in viewer JSON.
- Modify `src/baseball_swing_analyzer/projection.py`: support one named fix preset and return clearer before/after estimate labels.
- Modify `server/api/projection.py`: accept `fix_id` in addition to existing numeric fields for backward compatibility.
- Modify `server/api/results.py` if needed to expose new segment artifact URLs.
- Add tests in `tests/test_swing_segments.py`, `tests/test_analyzer.py`, `tests/test_projection.py`, and `tests/test_export_3d.py`.

Frontend files:

- Modify `frontend/src/lib/api.ts`: add swing segment, bat, ball, and fix-toggle response types.
- Modify `frontend/src/lib/resultsSummary.ts`: keep advice but simplify summary text generation.
- Modify `frontend/src/components/ExecutiveSummaryHero.tsx`: remove internal explanatory cards and replace with user-readable coaching.
- Modify `frontend/src/components/AnalysisSummary.tsx`: remove from primary viewer or gate behind a diagnostics expander if still needed.
- Modify `frontend/src/components/PhaseTimeline.tsx`: redesign phase display with human labels and readable markers.
- Modify `frontend/src/components/SwingSkeletonViewer.tsx`: draw body, estimated bat, estimated ball/contact point, and baseline/projected states.
- Replace `frontend/src/components/WhatIfSimulator.tsx` with `frontend/src/components/FixTogglePanel.tsx`.
- Modify `frontend/src/pages/SwingViewerPage.tsx`: replace tabs/three panels with one viewer panel and one compact coaching/control rail.
- Add or update Vitest tests in `frontend/src/components/*.test.tsx`, `frontend/src/lib/resultsSummary.test.ts`, and `frontend/src/pages/ResultsPage.test.tsx`.

Docs:

- Modify `docs/metrics.md`: document swing segmentation, bat/ball estimate limits, and projection estimate limits.

---

## Task 1: User-Facing Executive Summary Cleanup

**Owner:** systems-plumber or frontend worker

**Files:**

- Modify: `frontend/src/components/ExecutiveSummaryHero.tsx`
- Modify: `frontend/src/lib/resultsSummary.ts`
- Test: `frontend/src/lib/resultsSummary.test.ts`
- Create: `frontend/src/components/ExecutiveSummaryHero.test.tsx`

### Acceptance Criteria

- No visible text contains `Score Signal`, `Evidence Layer`, `Immediate Read`, `proof surface`, `tied to the actual move`, or `diagnostics`.
- The score remains visible.
- The user sees one plain-language verdict and 1-3 plain-language next actions.
- Existing coaching advice is preserved when available.

### Steps

- [ ] **Step 1: Write failing summary text tests**

Add these assertions to `frontend/src/lib/resultsSummary.test.ts`:

```ts
test("builds plain-language summary without internal report labels", () => {
  const summary = buildExecutiveSummary(makeMetrics(), [
    { tone: "warn", text: "Foot plant is early. Try a softer, controlled toe-tap load." },
  ]);

  expect(summary.summary).toContain("Foot plant is early");
  expect(summary.summary).not.toMatch(/signal|evidence|diagnostic|proof surface/i);
  expect(summary.nextSteps[0].text).toContain("Foot plant is early");
});
```

- [ ] **Step 2: Create failing component test**

Create `frontend/src/components/ExecutiveSummaryHero.test.tsx`:

```ts
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { ExecutiveSummaryHero } from "@/components/ExecutiveSummaryHero";

describe("ExecutiveSummaryHero", () => {
  test("renders only user-facing coaching language", () => {
    const html = renderToStaticMarkup(
      <ExecutiveSummaryHero
        summary={{
          score: 64,
          label: "Needs cleanup",
          summary: "This swing needs cleaner movement before the power can play consistently.",
          strengths: ["Rotation stays connected instead of leaking early from the pelvis."],
          issues: ["Foot plant is early."],
          nextSteps: [{ tone: "warn", text: "Try a softer, controlled toe-tap load." }],
        }}
      />,
    );

    expect(html).toContain("64");
    expect(html).toContain("Needs cleanup");
    expect(html).toContain("Try a softer, controlled toe-tap load.");
    expect(html).not.toMatch(/Score Signal|Evidence Layer|Immediate Read|proof surface|diagnostics/i);
  });
});
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
cd frontend
npm test -- ExecutiveSummaryHero resultsSummary
```

Expected: fail because current component renders the rejected internal labels.

- [ ] **Step 4: Simplify `ExecutiveSummaryHero`**

Implement this structure:

```tsx
export function ExecutiveSummaryHero({ summary, embedded = false }: ExecutiveSummaryHeroProps) {
  const primaryStep = summary.nextSteps[0]?.text;

  return (
    <section className={embedded ? "h-full" : "rounded-2xl border border-white/10 bg-[var(--color-surface)] p-6 shadow-[0_18px_60px_rgba(0,0,0,0.24)]"}>
      <div className="grid gap-5 lg:grid-cols-[180px_minmax(0,1fr)] lg:items-center">
        <div>
          <p className={`text-6xl font-semibold leading-none lg:text-7xl ${scoreAccent(summary.score)}`}>
            {summary.score}
          </p>
          <p className="mt-2 text-xl font-semibold text-[var(--color-text)]">{summary.label}</p>
        </div>
        <div className="space-y-4">
          <p className="max-w-3xl text-base leading-7 text-[var(--color-text)]">{summary.summary}</p>
          {primaryStep ? (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-dim)]">Work on this first</p>
              <p className="mt-2 text-sm leading-6 text-[var(--color-text)]">{primaryStep}</p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Run task tests**

Run:

```bash
cd frontend
npm test -- ExecutiveSummaryHero resultsSummary
npm run build
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ExecutiveSummaryHero.tsx frontend/src/components/ExecutiveSummaryHero.test.tsx frontend/src/lib/resultsSummary.ts frontend/src/lib/resultsSummary.test.ts
git commit -m "fix: make executive summary player-readable"
```

---

## Task 2: Hide Internal Sport And Analysis Diagnostics

**Owner:** frontend worker

**Files:**

- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/components/AnalysisSummary.tsx`
- Test: `frontend/src/pages/ResultsPage.test.tsx`
- Create: `frontend/src/pages/SwingViewerPage.test.tsx`

### Acceptance Criteria

- Viewer does not show `Detected Sport`, `Confidence`, `Context`, `Mechanics`, or "not confidently detected".
- Sport profile can still influence copy internally.
- Analysis details do not appear in the normal viewer panel.
- Diagnostics remain available only behind a clearly secondary developer/debug affordance if kept at all.

### Steps

- [ ] **Step 1: Write failing viewer test**

Create `frontend/src/pages/SwingViewerPage.test.tsx` with mocked API calls:

```ts
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { SwingViewerPage } from "@/pages/SwingViewerPage";

vi.mock("@/lib/api", () => ({
  getFrames3D: vi.fn(),
  getJobResults: vi.fn(),
  projectSwing: vi.fn(),
}));

describe("SwingViewerPage copy", () => {
  test("does not expose sport confidence diagnostics in user view", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={["/viewer/job-1"]}>
        <Routes>
          <Route path="/viewer/:jobId" element={<SwingViewerPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(html).not.toMatch(/Detected Sport|Confidence|Context|Mechanics|not confidently detected/i);
  });
});
```

- [ ] **Step 2: Remove sport card from `SwingViewerPage`**

Delete the `Detected Sport` card from the overview UI. Keep `sportProfile` state because projection copy can still use it.

- [ ] **Step 3: Remove `AnalysisSummary` from the primary viewer**

Delete the `AnalysisSummary analysis={analysis}` usage from the viewer. If diagnostics are still needed later, add them to a collapsed section outside the primary coaching path in a separate task.

- [ ] **Step 4: Run tests**

```bash
cd frontend
npm test -- SwingViewerPage ResultsPage
npm run build
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SwingViewerPage.tsx frontend/src/pages/SwingViewerPage.test.tsx frontend/src/components/AnalysisSummary.tsx frontend/src/pages/ResultsPage.test.tsx
git commit -m "fix: hide internal sport diagnostics from viewer"
```

---

## Task 3: Phase Timeline Redesign

**Owner:** frontend-design worker

**Files:**

- Modify: `frontend/src/components/PhaseTimeline.tsx`
- Modify: `frontend/src/lib/metrics.ts`
- Create: `frontend/src/components/PhaseTimeline.test.tsx`

### Acceptance Criteria

- Timeline uses human-readable phase labels: `Set Up`, `Load`, `Stride`, `Turn`, `Contact`, `Finish`.
- Font sizes are readable on 375px mobile and desktop.
- Marker labels do not overlap each other or the phase labels.
- Current frame has a clear playhead.
- No hover-only essential information.

### Steps

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/PhaseTimeline.test.tsx`:

```ts
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { PhaseTimeline } from "@/components/PhaseTimeline";

describe("PhaseTimeline", () => {
  test("renders human labels instead of raw phase keys", () => {
    const html = renderToStaticMarkup(
      <PhaseTimeline
        phaseLabels={["stance", "load", "stride", "swing", "contact", "follow_through"]}
        totalFrames={6}
        currentFrame={3}
        contactFrame={4}
        stridePlantFrame={2}
      />,
    );

    expect(html).toContain("Set Up");
    expect(html).toContain("Turn");
    expect(html).toContain("Finish");
    expect(html).not.toContain(">follow_through<");
  });
});
```

- [ ] **Step 2: Add shared human phase map**

In `frontend/src/lib/metrics.ts`, export:

```ts
export const PHASE_LABELS: Record<string, string> = {
  idle: "Before Swing",
  stance: "Set Up",
  load: "Load",
  stride: "Stride",
  swing: "Turn",
  contact: "Contact",
  follow_through: "Finish",
};
```

- [ ] **Step 3: Update timeline rendering**

Update `PhaseTimeline.tsx` to import `PHASE_LABELS`, use readable labels, and move explanatory copy below the bar:

```tsx
const phaseLabel = PHASE_LABELS[segment.phase] ?? segment.phase.replaceAll("_", " ");
```

Use `text-[11px] sm:text-xs`, remove ultra-wide letter spacing on labels, and keep marker pills above the timeline with `max-w-[90px] whitespace-normal text-center`.

- [ ] **Step 4: Run tests and build**

```bash
cd frontend
npm test -- PhaseTimeline
npm run build
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/PhaseTimeline.tsx frontend/src/components/PhaseTimeline.test.tsx frontend/src/lib/metrics.ts
git commit -m "style: improve phase timeline readability"
```

---

## Task 4: Backend Swing Segmentation

**Owner:** metric-engineer

**Files:**

- Create: `src/baseball_swing_analyzer/swing_segments.py`
- Modify: `src/baseball_swing_analyzer/analyzer.py`
- Test: `tests/test_swing_segments.py`
- Modify: `tests/test_analyzer.py`

### Acceptance Criteria

- Long clips with idle motion return swing segment windows.
- Multiple swings return multiple windows.
- Each window includes `start_frame`, `end_frame`, `contact_frame`, `duration_s`, and `confidence`.
- Default report focuses primary metrics on the best swing segment.
- Existing short synthetic tests still pass.

### Steps

- [ ] **Step 1: Write failing segmentation tests**

Create `tests/test_swing_segments.py`:

```py
import numpy as np

from baseball_swing_analyzer.swing_segments import detect_swing_segments


def _pose_sequence(speed_peaks: list[tuple[int, int]], frames: int = 120) -> np.ndarray:
    seq = np.zeros((frames, 17, 3), dtype=float)
    seq[:, :, 2] = 1.0
    for start, end in speed_peaks:
        for t in range(start, end):
            seq[t, 9, 0] = (t - start) * 0.08
            seq[t, 10, 0] = (t - start) * 0.1
    return seq


def test_detects_single_swing_inside_long_clip() -> None:
    seq = _pose_sequence([(40, 62)])
    segments = detect_swing_segments(seq, fps=30.0)

    assert len(segments) == 1
    assert 35 <= segments[0].start_frame <= 42
    assert 60 <= segments[0].end_frame <= 72
    assert segments[0].contact_frame >= segments[0].start_frame
    assert segments[0].confidence > 0.5


def test_detects_multiple_swings() -> None:
    seq = _pose_sequence([(20, 38), (78, 96)])
    segments = detect_swing_segments(seq, fps=30.0)

    assert len(segments) == 2
    assert segments[0].end_frame < segments[1].start_frame
```

- [ ] **Step 2: Implement `SwingSegment` and detector**

Create `src/baseball_swing_analyzer/swing_segments.py`:

```py
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

from .metrics import wrist_velocity


@dataclass(frozen=True)
class SwingSegment:
    start_frame: int
    end_frame: int
    contact_frame: int
    duration_s: float
    confidence: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def detect_swing_segments(
    keypoints_seq: NDArray[np.floating],
    fps: float,
    min_duration_s: float = 0.25,
    merge_gap_s: float = 0.18,
    context_s: float = 0.18,
) -> list[SwingSegment]:
    seq = np.asarray(keypoints_seq, dtype=float)
    if seq.ndim != 3 or seq.shape[0] < 4:
        return []

    speeds = wrist_velocity(seq, fps).max(axis=1)
    peak = float(speeds.max(initial=0.0))
    if peak <= 0:
        return []

    threshold = max(float(np.percentile(speeds, 75)), peak * 0.18)
    active = speeds >= threshold
    runs = _active_runs(active)
    runs = _merge_runs(runs, max_gap=max(1, round(merge_gap_s * fps)))

    context = max(1, round(context_s * fps))
    min_len = max(3, round(min_duration_s * fps))
    segments: list[SwingSegment] = []
    for start, end in runs:
        if end - start + 1 < min_len:
            continue
        window_start = max(0, start - context)
        window_end = min(len(speeds) - 1, end + context)
        contact = int(window_start + np.argmax(speeds[window_start:window_end + 1]))
        confidence = min(1.0, peak / (float(np.mean(speeds)) + float(np.std(speeds)) + 1e-6) / 4.0)
        segments.append(
            SwingSegment(
                start_frame=window_start,
                end_frame=window_end,
                contact_frame=contact,
                duration_s=round((window_end - window_start + 1) / fps, 3),
                confidence=round(confidence, 3),
            )
        )

    return segments


def best_swing_segment(segments: list[SwingSegment]) -> SwingSegment | None:
    if not segments:
        return None
    return max(segments, key=lambda segment: (segment.confidence, segment.duration_s))


def _active_runs(active: NDArray[np.bool_]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    i = 0
    while i < len(active):
        if not bool(active[i]):
            i += 1
            continue
        start = i
        while i + 1 < len(active) and bool(active[i + 1]):
            i += 1
        runs.append((start, i))
        i += 1
    return runs


def _merge_runs(runs: list[tuple[int, int]], max_gap: int) -> list[tuple[int, int]]:
    if not runs:
        return []
    merged = [runs[0]]
    for start, end in runs[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= max_gap:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged
```

- [ ] **Step 3: Integrate segment metadata into `analyzer.py`**

After smoothing keypoints, call:

```py
from .swing_segments import best_swing_segment, detect_swing_segments

segments = detect_swing_segments(keypoints_seq, analysis_fps)
primary_segment = best_swing_segment(segments)
if primary_segment is not None:
    keypoints_for_metrics = keypoints_seq[primary_segment.start_frame:primary_segment.end_frame + 1]
else:
    keypoints_for_metrics = keypoints_seq

phase_labels = classify_phases(keypoints_for_metrics, fps=analysis_fps)
report = build_report(phase_labels, keypoints_for_metrics, analysis_fps)
report["swing_segments"] = [segment.to_dict() for segment in segments]
report["primary_swing_segment"] = primary_segment.to_dict() if primary_segment else None
```

When writing annotated frames, pass only the primary segment frames if present.

- [ ] **Step 4: Update analyzer tests**

Add an assertion in `tests/test_analyzer.py` that `analyze_swing(...)` returns `swing_segments` and `primary_swing_segment` keys.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_swing_segments.py tests/test_analyzer.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/baseball_swing_analyzer/swing_segments.py src/baseball_swing_analyzer/analyzer.py tests/test_swing_segments.py tests/test_analyzer.py
git commit -m "feat: detect and focus actual swing segments"
```

---

## Task 5: Multi-Swing Artifacts And Trimmed Annotated Clips

**Owner:** systems-plumber

**Files:**

- Modify: `src/baseball_swing_analyzer/analyzer.py`
- Modify: `server/tasks/analyze.py`
- Modify: `server/api/results.py`
- Test: `tests/test_analyzer.py`
- Test: `tests/test_jobs_api.py`

### Acceptance Criteria

- Primary `annotated.mp4` contains only the primary swing segment.
- Multiple swings produce metadata for each swing.
- API results include enough segment metadata for frontend to choose swing 1, swing 2, etc.
- Existing clients that read `annotated.mp4` still work.

### Steps

- [ ] **Step 1: Write failing API artifact test**

In `tests/test_jobs_api.py`, assert completed job results can include:

```py
assert "swing_segments" in payload["metrics"]
assert payload["metrics"]["primary_swing_segment"] is None or "start_frame" in payload["metrics"]["primary_swing_segment"]
```

- [ ] **Step 2: Keep primary output stable**

In `_write_annotated_frames`, use the trimmed frame/keypoint/phase arrays passed from `analyze_swing`. Do not change the artifact name.

- [ ] **Step 3: Add optional per-swing artifact names**

If multiple segments are present, write:

```text
annotated_swing_1.mp4
annotated_swing_2.mp4
```

Each file uses that segment's frame slice.

- [ ] **Step 4: Expose segment metadata through results API**

Ensure `metrics_json` includes `swing_segments` and `primary_swing_segment`. If `server/api/results.py` filters fields, add these fields to the response.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_analyzer.py tests/test_jobs_api.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/baseball_swing_analyzer/analyzer.py server/tasks/analyze.py server/api/results.py tests/test_analyzer.py tests/test_jobs_api.py
git commit -m "feat: output trimmed swing clips"
```

---

## Task 6: Bat And Ball Estimate Export

**Owner:** cv-engineer plus swing-theorist review

**Files:**

- Modify: `src/baseball_swing_analyzer/export_3d.py`
- Modify: `frontend/src/lib/api.ts`
- Test: `tests/test_export_3d.py`
- Modify: `tests/fixtures/viewer_fixture.json`

### Acceptance Criteria

- Each viewer frame has an estimated `bat` object with `handle`, `barrel`, and `confidence`.
- Viewer data has a `ball` object with `contact_position`, `contact_frame`, and `confidence`.
- Estimation is derived from wrist/forearm geometry, not presented as measured tracking.
- Tests verify finite coordinates and stable schema.

### Steps

- [ ] **Step 1: Write failing export test**

Create or update `tests/test_export_3d.py`:

```py
import numpy as np

from baseball_swing_analyzer.export_3d import generate_swing_3d_data_from_keypoints


def test_export_includes_bat_and_ball_estimates() -> None:
    seq = np.zeros((8, 17, 3), dtype=float)
    seq[:, :, 2] = 1.0
    seq[:, 9, :3] = [0.2, 0.2, 1.0]
    seq[:, 10, :3] = [0.4, 0.2, 1.0]
    seq[:, 7, :3] = [0.1, 0.3, 1.0]
    seq[:, 8, :3] = [0.5, 0.3, 1.0]
    phases = ["load", "load", "stride", "swing", "contact", "follow_through", "follow_through", "follow_through"]

    data = generate_swing_3d_data_from_keypoints(seq, phases, 30.0, {"contact_frame": 4})

    assert "bat" in data["frames"][4]
    assert len(data["frames"][4]["bat"]["handle"]) == 3
    assert len(data["frames"][4]["bat"]["barrel"]) == 3
    assert data["frames"][4]["bat"]["confidence"] > 0
    assert data["ball"]["contact_frame"] == 4
    assert len(data["ball"]["contact_position"]) == 3
```

- [ ] **Step 2: Add bat estimator**

In `export_3d.py`, add helper:

```py
def _estimate_bat(frame_points: NDArray[np.float32]) -> dict:
    left_wrist = frame_points[9]
    right_wrist = frame_points[10]
    left_elbow = frame_points[7]
    right_elbow = frame_points[8]
    handle = (left_wrist + right_wrist) / 2.0
    hand_axis = right_wrist - left_wrist
    forearm_axis = ((left_wrist - left_elbow) + (right_wrist - right_elbow)) / 2.0
    direction = hand_axis + forearm_axis
    length = float(np.linalg.norm(direction))
    if not np.isfinite(length) or length < 1e-6:
        direction = np.array([0.45, 0.0, 0.0], dtype=np.float32)
        length = float(np.linalg.norm(direction))
    unit = direction / length
    barrel = handle + unit * 0.55
    return {
        "handle": [round(float(v), 4) for v in handle],
        "barrel": [round(float(v), 4) for v in barrel],
        "confidence": 0.45,
        "estimate_basis": "wrist_forearm_proxy",
    }
```

- [ ] **Step 3: Add ball contact estimate**

Use the contact frame bat barrel as the ball contact estimate:

```py
def _estimate_ball(frames_list: list[dict], contact_idx: int) -> dict:
    bat = frames_list[contact_idx].get("bat") if frames_list else None
    position = bat["barrel"] if bat else [0.0, 0.0, 0.0]
    return {
        "contact_frame": contact_idx,
        "contact_position": position,
        "confidence": 0.35,
        "estimate_basis": "contact_frame_barrel_proxy",
    }
```

- [ ] **Step 4: Update frontend API types**

Add to `Frame3D`:

```ts
bat?: {
  handle: number[];
  barrel: number[];
  confidence: number;
  estimate_basis: "wrist_forearm_proxy";
};
```

Add to `Swing3DData`:

```ts
ball?: {
  contact_frame: number;
  contact_position: number[];
  confidence: number;
  estimate_basis: "contact_frame_barrel_proxy";
};
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_export_3d.py -q
cd frontend
npm run build
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/baseball_swing_analyzer/export_3d.py frontend/src/lib/api.ts tests/test_export_3d.py tests/fixtures/viewer_fixture.json
git commit -m "feat: export estimated bat and ball positions"
```

---

## Task 7: Named Fix Projection Preset

**Owner:** metric-engineer

**Files:**

- Modify: `src/baseball_swing_analyzer/projection.py`
- Modify: `server/api/projection.py`
- Modify: `frontend/src/lib/api.ts`
- Test: `tests/test_projection.py`

### Acceptance Criteria

- API accepts `{ "fix_id": "lower_half_timing" }`.
- Fix maps to concrete projection inputs for the current first pass: better x-factor and lower head drift.
- Response includes `fix` metadata: name, short coach text, baseline estimate, projected estimate.
- Existing numeric projection requests still work.

### Steps

- [ ] **Step 1: Write failing projection test**

Add to `tests/test_projection.py`:

```py
from baseball_swing_analyzer.projection import ProjectionRequest, project_swing_viewer_data


def test_named_lower_half_fix_returns_metadata() -> None:
    viewer = _viewer_fixture()
    request = ProjectionRequest(fix_id="lower_half_timing")

    result = project_swing_viewer_data(viewer, request)

    assert result["fix"]["id"] == "lower_half_timing"
    assert "lower half" in result["fix"]["label"].lower()
    assert result["projection"]["score"] >= result["baseline"]["score"]
```

- [ ] **Step 2: Extend dataclass**

Update:

```py
@dataclass(frozen=True)
class ProjectionRequest:
    x_factor_delta_deg: float = 0.0
    head_stability_delta_norm: float = 0.0
    fix_id: str | None = None
```

- [ ] **Step 3: Add preset resolver**

Add:

```py
_FIX_PRESETS = {
    "lower_half_timing": {
        "label": "Fix lower-half timing",
        "coach_text": "Keep the stride controlled so the front side braces before the swing turns.",
        "x_factor_delta_deg": 7.0,
        "head_stability_delta_norm": 0.05,
    }
}


def _resolve_request(request: ProjectionRequest) -> tuple[float, float, dict | None]:
    if request.fix_id and request.fix_id in _FIX_PRESETS:
        preset = _FIX_PRESETS[request.fix_id]
        return float(preset["x_factor_delta_deg"]), float(preset["head_stability_delta_norm"]), {
            "id": request.fix_id,
            "label": str(preset["label"]),
            "coach_text": str(preset["coach_text"]),
        }
    return request.x_factor_delta_deg, request.head_stability_delta_norm, None
```

Use the resolved values in `project_swing_viewer_data`.

- [ ] **Step 4: Update server payload**

In `server/api/projection.py`:

```py
class ProjectionPayload(BaseModel):
    x_factor_delta_deg: float = 0.0
    head_stability_delta_norm: float = 0.0
    fix_id: str | None = None
```

Pass `fix_id=payload.fix_id`.

- [ ] **Step 5: Update frontend API**

Change `projectSwing` payload type:

```ts
payload: { x_factor_delta_deg?: number; head_stability_delta_norm?: number; fix_id?: string | null }
```

Add `fix?: { id: string; label: string; coach_text: string }` to `ProjectionResponse`.

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_projection.py -q
cd frontend
npm run build
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/baseball_swing_analyzer/projection.py server/api/projection.py frontend/src/lib/api.ts tests/test_projection.py
git commit -m "feat: add lower-half fix projection preset"
```

---

## Task 8: Single-Panel Actionable Viewer

**Owner:** frontend-design worker

**Files:**

- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/components/SwingSkeletonViewer.tsx`
- Create: `frontend/src/components/FixTogglePanel.tsx`
- Delete or stop using: `frontend/src/components/WhatIfSimulator.tsx`
- Test: `frontend/src/components/FixTogglePanel.test.tsx`
- Test: `frontend/src/pages/SwingViewerPage.test.tsx`

### Acceptance Criteria

- Viewer is one coherent panel, not three tabs or three disconnected panels.
- Swing loops automatically.
- User can toggle `Show fix` on/off.
- Toggle calls projection with `fix_id: "lower_half_timing"`.
- Baseline/projected EV, carry, and score update visibly.
- No sliders are visible.
- Bat and ball estimates render in the 3D view.

### Steps

- [ ] **Step 1: Write failing FixTogglePanel test**

Create `frontend/src/components/FixTogglePanel.test.tsx`:

```ts
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { FixTogglePanel } from "@/components/FixTogglePanel";

describe("FixTogglePanel", () => {
  test("renders a toggle and estimate changes without sliders", () => {
    const html = renderToStaticMarkup(
      <FixTogglePanel
        enabled={false}
        pending={false}
        baseline={{ estimate_basis: "pose_proxy", exit_velocity_mph: 70, exit_velocity_mph_low: 65, exit_velocity_mph_high: 75, carry_distance_ft: 210, carry_distance_ft_low: 190, carry_distance_ft_high: 230, score: 64 }}
        projection={{ estimate_basis: "pose_proxy", exit_velocity_mph: 76, exit_velocity_mph_low: 71, exit_velocity_mph_high: 81, carry_distance_ft: 238, carry_distance_ft_low: 218, carry_distance_ft_high: 258, score: 72 }}
        fix={{ id: "lower_half_timing", label: "Fix lower-half timing", coach_text: "Keep the stride controlled." }}
        onToggle={() => undefined}
      />,
    );

    expect(html).toContain("Fix lower-half timing");
    expect(html).toContain("64");
    expect(html).toContain("72");
    expect(html).not.toMatch(/slider|range/i);
  });
});
```

- [ ] **Step 2: Implement `FixTogglePanel`**

Create `frontend/src/components/FixTogglePanel.tsx`:

```tsx
import { LoaderCircle } from "lucide-react";
import type { ProjectionResponse, ProjectionSummary } from "@/lib/api";

interface Props {
  enabled: boolean;
  pending: boolean;
  baseline: ProjectionSummary | null;
  projection: ProjectionSummary | null;
  fix: ProjectionResponse["fix"] | null | undefined;
  onToggle: (enabled: boolean) => void;
}

function estimate(summary: ProjectionSummary | null, key: "score" | "exit_velocity_mph" | "carry_distance_ft"): string {
  if (!summary) return "-";
  return String(Math.round(Number(summary[key])));
}

export function FixTogglePanel({ enabled, pending, baseline, projection, fix, onToggle }: Props) {
  const active = enabled && projection ? projection : baseline;

  return (
    <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-text)]">{fix?.label ?? "Fix lower-half timing"}</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">
            {fix?.coach_text ?? "Keep the stride controlled so the front side braces before the swing turns."}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          onClick={() => onToggle(!enabled)}
          className="inline-flex min-w-24 items-center justify-center rounded-md border border-[var(--color-border)] px-3 py-2 text-sm font-semibold"
        >
          {pending ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : null}
          {enabled ? "Fix on" : "Fix off"}
        </button>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-[var(--color-surface-2)] p-3">
          <p className="text-xs text-[var(--color-text-dim)]">Score</p>
          <p className="mt-1 text-2xl font-semibold text-[var(--color-text)]">{estimate(active, "score")}</p>
        </div>
        <div className="rounded-lg bg-[var(--color-surface-2)] p-3">
          <p className="text-xs text-[var(--color-text-dim)]">Est. EV</p>
          <p className="mt-1 text-2xl font-semibold text-[var(--color-text)]">{estimate(active, "exit_velocity_mph")} mph</p>
        </div>
        <div className="rounded-lg bg-[var(--color-surface-2)] p-3">
          <p className="text-xs text-[var(--color-text-dim)]">Est. Carry</p>
          <p className="mt-1 text-2xl font-semibold text-[var(--color-text)]">{estimate(active, "carry_distance_ft")} ft</p>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Draw bat and ball in `SwingSkeletonViewer`**

Add refs for bat line and ball mesh. In scene setup, create:

```tsx
const batGeometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
const batMaterial = new THREE.LineBasicMaterial({ color: "#f5d36b", linewidth: 3 });
const batLine = new THREE.Line(batGeometry, batMaterial);
scene.add(batLine);
batRef.current = batLine;

const ball = new THREE.Mesh(
  new THREE.SphereGeometry(0.035, 16, 16),
  new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 0.35 }),
);
scene.add(ball);
ballRef.current = ball;
```

On frame update:

```tsx
const bat = frame.bat;
if (bat && bat.handle.length >= 3 && bat.barrel.length >= 3) {
  batRef.current.visible = true;
  batRef.current.geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array([...bat.handle, ...bat.barrel]), 3));
} else {
  batRef.current.visible = false;
}

const ballPosition = data.ball?.contact_position;
if (ballPosition && ballPosition.length >= 3) {
  ballRef.current.visible = Math.abs(currentFrame - (data.ball?.contact_frame ?? currentFrame)) <= 4;
  ballRef.current.position.set(ballPosition[0], ballPosition[1], ballPosition[2]);
}
```

- [ ] **Step 4: Replace tab layout in `SwingViewerPage`**

Remove `TABS`, `activeTab`, `Panel`, `PhaseEnergyChart`, `HipShoulderDiagram`, and `WhatIfSimulator` usage from primary layout.

Use one layout:

```tsx
<main className="grid h-[calc(100vh-56px)] grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px]">
  <section className="min-h-0 bg-black">
    <SwingSkeletonViewer ... />
  </section>
  <aside className="space-y-4 overflow-auto bg-[var(--color-bg)] p-4">
    <FixTogglePanel ... />
    <PhaseTimeline ... />
  </aside>
</main>
```

The `onToggle` handler calls:

```ts
if (enabled) {
  const result = await projectSwing(jobId, { fix_id: "lower_half_timing" });
  setProjection(result.projection);
  setActiveData(result.viewer);
} else {
  setProjection(null);
  setActiveData(baseData);
}
```

- [ ] **Step 5: Run frontend tests and build**

```bash
cd frontend
npm test -- FixTogglePanel SwingViewerPage
npm run build
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/SwingViewerPage.tsx frontend/src/components/SwingSkeletonViewer.tsx frontend/src/components/FixTogglePanel.tsx frontend/src/components/FixTogglePanel.test.tsx frontend/src/pages/SwingViewerPage.test.tsx
git commit -m "feat: replace viewer tabs with fix toggle panel"
```

---

## Task 9: Results Page Integration For Multiple Swings

**Owner:** frontend worker

**Files:**

- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/lib/api.ts`
- Test: `frontend/src/pages/ResultsPage.test.tsx`

### Acceptance Criteria

- If one swing is found, the results page uses the trimmed annotated swing and normal viewer link.
- If multiple swings are found, the user sees `Swing 1`, `Swing 2`, etc. as selectable chips or a compact list.
- Selection changes annotated video source and viewer link segment query.
- No raw start/end frame metadata is shown in primary UI.

### Steps

- [ ] **Step 1: Add API types**

In `SwingMetrics`, add:

```ts
swing_segments?: Array<{
  start_frame: number;
  end_frame: number;
  contact_frame: number;
  duration_s: number;
  confidence: number;
}>;
primary_swing_segment?: {
  start_frame: number;
  end_frame: number;
  contact_frame: number;
  duration_s: number;
  confidence: number;
} | null;
```

- [ ] **Step 2: Write failing ResultsPage test**

Update `ResultsPage.test.tsx` to expect `Swing 1` and `Swing 2` when mocked metrics include two segments.

- [ ] **Step 3: Add segment selector**

In `ResultsPage.tsx`, render selector only when `metrics.swing_segments?.length > 1`.

Use labels:

```ts
const label = `Swing ${index + 1}`;
```

Do not expose confidence values in the primary UI.

- [ ] **Step 4: Run tests and build**

```bash
cd frontend
npm test -- ResultsPage
npm run build
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ResultsPage.tsx frontend/src/lib/api.ts frontend/src/pages/ResultsPage.test.tsx
git commit -m "feat: support multiple swing selections"
```

---

## Task 10: Documentation And Truthfulness

**Owner:** swing-theorist plus systems-plumber

**Files:**

- Modify: `docs/metrics.md`
- Modify: `README.md`

### Acceptance Criteria

- Docs say bat and ball are estimated from pose, not tracked.
- Docs say EV/carry are directional estimates, not measured ball flight.
- Docs explain swing segmentation and multi-swing behavior.

### Steps

- [ ] **Step 1: Update `docs/metrics.md`**

Add:

```md
## Swing Segments

Long videos are reduced to active swing windows using wrist and hand velocity. If multiple swings are present, the analyzer returns multiple segment windows and chooses the highest-confidence segment as the primary report.

## Estimated Bat And Ball Position

The viewer estimates bat handle and barrel position from wrist and forearm keypoints. The ball/contact point is estimated from the barrel position at the contact frame. These are visual coaching aids, not measured bat or ball tracking.

## Projected EV And Carry

Projected exit velocity and carry are pose-proxy estimates. They help compare the current swing against a projected mechanical change, but they are not measured launch metrics.
```

- [ ] **Step 2: Update README feature language**

Replace any wording that implies measured 3D/bat/ball outputs with estimated language.

- [ ] **Step 3: Commit**

```bash
git add docs/metrics.md README.md
git commit -m "docs: clarify swing segmentation and estimate limits"
```

---

## Task 11: Full Verification

**Owner:** qa-harness

**Files:**

- No code changes unless fixing failures.

### Acceptance Criteria

- Backend tests pass.
- Frontend tests pass.
- Frontend build passes.
- Manual browser check verifies report copy, timeline, trimmed swing playback, viewer toggle, bat/ball rendering, and no sport diagnostics.

### Steps

- [ ] **Step 1: Run backend tests**

```bash
pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests**

```bash
cd frontend
npm test
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend build**

```bash
cd frontend
npm run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 4: Start local app**

Use existing project server instructions. If not already running:

```bash
uvicorn server.main:app --reload
cd frontend
npm run dev
```

- [ ] **Step 5: Browser verification checklist**

Open the app and verify:

- Upload a long clip with extra motion before/after swing.
- Results page shows trimmed annotated swing.
- Executive summary contains only readable player-facing copy.
- Sport confidence/debug details are not visible.
- Phase timeline labels are readable on desktop.
- Phase timeline labels are readable at 375px width.
- Viewer is one panel.
- Bat and ball estimate appear near contact.
- `Fix lower-half timing` toggle turns projected swing on/off.
- Score, estimated EV, and estimated carry change when fix is on.
- Swing loops without user scrubbing.

- [ ] **Step 6: Commit any verification fixes**

Only if fixes were needed:

```bash
git add <changed-files>
git commit -m "fix: address verification issues"
```

---

## Task 12: Push And PR

**Owner:** orchestrator

**Files:**

- No code changes.

### Acceptance Criteria

- Branch is pushed.
- PR summary lists user-visible changes and estimate caveats.
- PR test plan includes exact commands and browser checks.

### Steps

- [ ] **Step 1: Check final status**

```bash
git status --short --branch
git log --oneline origin/main..HEAD
```

Expected: clean worktree and task commits listed.

- [ ] **Step 2: Push**

```bash
git push -u origin codex/actionable-swing-report
```

- [ ] **Step 3: Create PR**

PR title:

```text
Make swing report player-readable and viewer actionable
```

PR summary:

```md
## Summary
- cleans up executive summary and removes internal sport-confidence diagnostics from user UI
- clips analysis/viewer outputs to actual swing segments, including multiple-swing metadata
- adds estimated bat/ball visualization and a single lower-half fix toggle with projected score, EV, and carry

## Caveats
- bat, ball, EV, and carry outputs are pose-based estimates, not measured tracking
- first fix preset focuses lower-half timing using x-factor and head-stability projection proxies

## Test Plan
- `pytest`
- `cd frontend && npm test`
- `cd frontend && npm run build`
- manual upload flow: long clip -> trimmed results video -> viewer -> fix toggle on/off
```

---

## Self-Review Checklist

- Requirement coverage:
  - Executive summary copy cleanup: Task 1.
  - Hide sport detection/confidence: Task 2.
  - Phase timeline design: Task 3.
  - Cut clip down to swings: Tasks 4 and 5.
  - Multiple swing breakdown: Tasks 4, 5, and 9.
  - One viewer panel: Task 8.
  - Bat and ball estimate: Tasks 6 and 8.
  - Toggle a single mistake fix: Tasks 7 and 8.
  - EV/score changes with fix: Tasks 7 and 8.
  - Commits and push: every task plus Task 12.
- Placeholder scan: no unfinished marker text or undefined implementation placeholders are intentionally left.
- Type consistency:
  - `fix_id` appears in backend `ProjectionRequest`, server payload, and frontend `projectSwing`.
  - `bat` and `ball` schema appears in backend export and frontend API types.
  - `swing_segments` appears in backend report and frontend `SwingMetrics`.
- Risk flags:
  - Segmentation based on wrist velocity may need tuning against real videos.
  - Bat/ball estimates must stay visually helpful without being oversold.
  - Projection is directionally useful but not measured physics.
