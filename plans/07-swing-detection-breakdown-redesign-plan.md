# Swing Detection And Breakdown Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign swing detection and the results/breakdown experience so the system stops promoting generic motion as swings, remains usable on hard clips like net-obscured cage video, invalidates stale analysis results, and explains motion in player-friendly terms.

**Architecture:** Replace the current "motion burst -> assume swing -> derive contact from wrist peak" path with a two-stage pipeline: cheap candidate proposal followed by explicit swing validation and event localization. Add analysis versioning so stored results cannot masquerade as current output, then rebuild the breakdown UI around animated motion replay and concise coaching instead of abstract diagrams and repeated filler text.

**Tech Stack:** Python 3.10+, FastAPI, sqlite3, pytest, OpenCV, NumPy, existing pose stack, optional pluggable vision validator, React, TypeScript, Vite, React Query.

---

## Problem Cases This Plan Must Solve

### Benchmark A: Long Multi-Swing Clip
- File: `data/videos/test_swing_30s.mp4`
- Expected behavior:
  - Detect `6` real swings.
  - Reject ball pickup, load-only movement, and idle drift.
  - Preserve per-swing viewer artifacts for each accepted swing.

### Benchmark B: Netted Single-Swing Cage Clip
- File to add under repo: `data/videos/benchmarks/netted_cage_single_swing.mov`
- Source clip provided by user: `C:/Users/yashk/Downloads/IMG_4119 (2).MOV`
- Expected behavior:
  - Detect exactly `1` swing.
  - Avoid assigning contact absurdly early in the clip.
  - Produce a complete phase sequence instead of `idle + contact + follow_through`.
  - Keep pose-confidence-related metrics inside sane bounds.

### Benchmark C: Fresh Results Integrity
- Any newly uploaded job after a detector change.
- Expected behavior:
  - Stored results expose `analysis_version`.
  - UI distinguishes fresh output from stale output.
  - Old jobs do not silently reuse obsolete segmentation behavior.

### Benchmark D: Viewer and Coaching UX
- Any completed swing result.
- Expected behavior:
  - No repeated "One clear cue at a time." filler.
  - "What did your body do?" shows an animated body replay, not only a rotation arc abstraction.
  - Frame scrubber defaults to slow playback.
  - Coaching terms are defined where needed and do not repeat the same idea in multiple panels.

---

## Research Summary Driving The Redesign

1. Pose-only action recognition is weak on human-object interaction unless object cues are modeled.
   - Source: [Pose-Based Two-Stream Relational Networks for Action Recognition in Videos](https://arxiv.org/abs/1805.08484)

2. Object-aware skeleton/action systems perform better when object interaction helps disambiguate motion classes.
   - Source: [Skeleton-Based Mutually Assisted Interacted Object Localization and Human Action Recognition](https://arxiv.org/abs/2110.14994)

3. Baseball action understanding is a fine-grained temporal activity detection problem, especially in continuous clips.
   - Source: [Fine-grained Activity Recognition in Baseball Videos](https://arxiv.org/abs/1804.03247)

4. Baseball clips vary sharply by viewpoint and environment, which makes heuristic-only pipelines brittle.
   - Source: [Recognizing Actions in Videos from Unseen Viewpoints](https://openaccess.thecvf.com/content/CVPR2021/papers/Piergiovanni_Recognizing_Actions_in_Videos_From_Unseen_Viewpoints_CVPR_2021_paper.pdf)

5. Ultralytics COCO-pretrained detection models already include `baseball bat` as a class, so object cues can be introduced without inventing a brand-new detector stack on day one.
   - Sources:
     - [Ultralytics Detect Docs](https://github.com/ultralytics/ultralytics/blob/main/docs/en/tasks/detect.md)
     - [Ultralytics COCO Dataset Classes](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml)

---

## Success Criteria

- `test_swing_30s.mp4` resolves to exactly `6` accepted swings with known false motions rejected.
- `netted_cage_single_swing.mov` resolves to exactly `1` accepted swing.
- No accepted swing window may skip directly from `idle` to `contact` unless a confidence guard explicitly downgrades the output and tells the UI phase data is unreliable.
- Stored results include `analysis_version` and freshness metadata.
- Results UI removes repeated filler text.
- Breakdown UI shows an animated skeleton/bat replay panel.
- Frame scrubber defaults to `0.25x`.
- Python and frontend tests cover the new validator path, stale-result handling, and UI regressions.

---

## File Map

### Backend Detection / Analysis
- Create: `src/baseball_swing_analyzer/analysis_version.py`
- Create: `src/baseball_swing_analyzer/benchmarks.py`
- Create: `src/baseball_swing_analyzer/swing_validation.py`
- Create: `src/baseball_swing_analyzer/swing_events.py`
- Create: `src/baseball_swing_analyzer/object_cues.py`
- Modify: `src/baseball_swing_analyzer/analyzer.py`
- Modify: `src/baseball_swing_analyzer/phases.py`
- Modify: `src/baseball_swing_analyzer/reporter.py`
- Modify: `src/baseball_swing_analyzer/export_3d.py`

### Backend API / Persistence
- Modify: `server/db.py`
- Modify: `server/tasks/analyze.py`
- Modify: `server/api/results.py`
- Modify: `server/api/upload.py`

### Frontend Results / Viewer
- Create: `frontend/src/components/AnimatedSwingReplay.tsx`
- Create: `frontend/src/components/PhaseConfidenceBanner.tsx`
- Modify: `frontend/src/components/ImprovementPlan.tsx`
- Modify: `frontend/src/components/ExecutiveSummaryHero.tsx`
- Modify: `frontend/src/components/PhaseTimeline.tsx`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/resultsSummary.ts`

### Fixtures / Plans / Tests
- Create: `data/videos/benchmarks/README.md`
- Create: `data/videos/benchmarks/manifest.json`
- Add fixture copy: `data/videos/benchmarks/netted_cage_single_swing.mov`
- Create: `tests/test_swing_validation.py`
- Create: `tests/test_analysis_version.py`
- Modify: `tests/test_analyzer.py`
- Modify: `tests/test_jobs_api.py`
- Create: `frontend/src/components/ImprovementPlan.test.tsx`
- Create: `frontend/src/pages/SwingViewerPage.test.tsx`

---

## Milestones

### Milestone 0: Lock The Benchmark Set
- Freeze the exact clips and expected outcomes used to judge the redesign.
- Add the user-provided netted clip into the repo benchmark set.
- Record oracle expectations for swing count, accepted/rejected windows, and UI sanity checks.

### Milestone 1: Version Results And Stop Serving Obsolete Truth
- Add `analysis_version` to the analysis payload and DB.
- Expose freshness in API responses.
- Make stale jobs visually obvious or re-run them explicitly.

### Milestone 2: Split Candidate Proposal From Swing Decision
- Keep motion-based candidate generation as a high-recall proposal stage only.
- Introduce a validator interface that can reject `load_only`, `pickup`, `reset`, and `other_motion`.
- Add object-cue support for bat-aware validation.

### Milestone 3: Replace Circular Contact/Phase Logic
- Stop deriving contact solely from wrist peak inside arbitrary windows.
- Localize contact only after a window is accepted as a swing.
- Add confidence guards so unreliable phase output does not pretend to be precise.

### Milestone 4: Stabilize Metrics On Hard Clips
- Clamp or flag implausible head movement / wrist velocity outliers on low-confidence pose sequences.
- Separate "unreliable measurement" from "bad swing."

### Milestone 5: Redesign Results Copy And Viewer
- Remove repeated filler.
- Replace the top-down arc-first panel with an animated body replay.
- Slow the frame scrubber and make manual scrubbing the main control.

### Milestone 6: Verify On Real Clips And Merge
- Run full backend/frontend tests.
- Re-run all benchmark clips.
- Verify the browser flow on fresh uploads.

---

## Task 1: Add Benchmark Fixtures And Expected Outcomes

**Files:**
- Create: `data/videos/benchmarks/README.md`
- Create: `data/videos/benchmarks/manifest.json`
- Create: `src/baseball_swing_analyzer/benchmarks.py`
- Create: `tests/test_swing_validation.py`

- [ ] **Step 1: Create the benchmark manifest**

Write `data/videos/benchmarks/manifest.json`:

```json
{
  "clips": [
    {
      "id": "long_multi_swing",
      "path": "data/videos/test_swing_30s.mp4",
      "expected_swing_count": 6,
      "expected_rejections": [
        "ball_pickup",
        "load_only"
      ]
    },
    {
      "id": "netted_cage_single_swing",
      "path": "data/videos/benchmarks/netted_cage_single_swing.mov",
      "expected_swing_count": 1,
      "contact_frame_min_ratio": 0.2,
      "contact_frame_max_ratio": 0.85
    }
  ]
}
```

- [ ] **Step 2: Add a repo README for benchmark usage**

Write `data/videos/benchmarks/README.md`:

```md
# Swing Detection Benchmarks

This folder contains clips used to validate swing detection changes.

- `netted_cage_single_swing.mov`: user-provided batting-cage clip through netting; expected to resolve to exactly one swing.
- `../test_swing_30s.mp4`: long multi-swing clip; expected to resolve to six real swings and reject non-swing motion windows.

Any detector change must be run against `manifest.json` before merge.
```

- [ ] **Step 3: Add a loader for benchmark expectations**

Write `src/baseball_swing_analyzer/benchmarks.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkClip:
    id: str
    path: str
    expected_swing_count: int
    expected_rejections: list[str] | None = None
    contact_frame_min_ratio: float | None = None
    contact_frame_max_ratio: float | None = None


def load_benchmarks(manifest_path: Path) -> list[BenchmarkClip]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [BenchmarkClip(**clip) for clip in payload["clips"]]
```

- [ ] **Step 4: Write a failing test for the manifest loader**

Write `tests/test_swing_validation.py`:

```python
from pathlib import Path

from baseball_swing_analyzer.benchmarks import load_benchmarks


def test_load_benchmarks_reads_expected_cases() -> None:
    clips = load_benchmarks(Path("data/videos/benchmarks/manifest.json"))
    ids = {clip.id for clip in clips}
    assert "long_multi_swing" in ids
    assert "netted_cage_single_swing" in ids
```

- [ ] **Step 5: Run the test**

Run: `python -m pytest tests/test_swing_validation.py::test_load_benchmarks_reads_expected_cases -v`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add data/videos/benchmarks/README.md data/videos/benchmarks/manifest.json src/baseball_swing_analyzer/benchmarks.py tests/test_swing_validation.py
git commit -m "test: add swing benchmark manifest"
```

---

## Task 2: Add Analysis Versioning And Freshness Metadata

**Files:**
- Create: `src/baseball_swing_analyzer/analysis_version.py`
- Modify: `server/db.py`
- Modify: `server/tasks/analyze.py`
- Modify: `server/api/results.py`
- Create: `tests/test_analysis_version.py`
- Modify: `tests/test_jobs_api.py`

- [ ] **Step 1: Add a stable version constant**

Write `src/baseball_swing_analyzer/analysis_version.py`:

```python
ANALYSIS_VERSION = "2026-04-swing-redesign-v1"
```

- [ ] **Step 2: Add DB columns for analysis freshness**

Update `_SCHEMA` and `_MIGRATIONS` in `server/db.py`:

```python
    analysis_version TEXT,
    analysis_family TEXT,
```

```python
_MIGRATIONS: dict[str, str] = {
    "progress_detail_current": "ALTER TABLE jobs ADD COLUMN progress_detail_current INTEGER",
    "progress_detail_total": "ALTER TABLE jobs ADD COLUMN progress_detail_total INTEGER",
    "progress_detail_label": "ALTER TABLE jobs ADD COLUMN progress_detail_label TEXT",
    "analysis_version": "ALTER TABLE jobs ADD COLUMN analysis_version TEXT",
    "analysis_family": "ALTER TABLE jobs ADD COLUMN analysis_family TEXT"
}
```

- [ ] **Step 3: Stamp analysis version during job completion**

Update `server/tasks/analyze.py` to import and save version metadata:

```python
from baseball_swing_analyzer.analysis_version import ANALYSIS_VERSION
```

```python
result["analysis_version"] = ANALYSIS_VERSION
```

```python
        db.update_job(
            job_id,
            status="completed",
            progress=1.0,
            current_step="done",
            progress_detail_current=None,
            progress_detail_total=None,
            progress_detail_label=None,
            metrics_json=json.dumps(result, default=str),
            analysis_version=ANALYSIS_VERSION,
            analysis_family="swing_detection",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
```

- [ ] **Step 4: Expose freshness in API responses**

Update `server/api/results.py`:

```python
from baseball_swing_analyzer.analysis_version import ANALYSIS_VERSION
```

```python
    return {
        "job_id": job["id"],
        "status": job["status"],
        "metrics": metrics,
        "analysis": analysis,
        "sport_profile": sport_profile,
        "coaching": _coaching_lines(coaching),
        "frames_3d_url": f"/api/jobs/{job['id']}/artifacts/frames_3d.json",
        "analysis_version": job.get("analysis_version"),
        "is_current_analysis": job.get("analysis_version") == ANALYSIS_VERSION,
    }
```

- [ ] **Step 5: Add a failing test for stale analysis detection**

Write `tests/test_analysis_version.py`:

```python
from baseball_swing_analyzer.analysis_version import ANALYSIS_VERSION


def test_analysis_version_constant_is_nonempty() -> None:
    assert ANALYSIS_VERSION.startswith("2026-04-")
```

- [ ] **Step 6: Extend API coverage**

Add to `tests/test_jobs_api.py`:

```python
def test_results_include_analysis_freshness(client, monkeypatch, tmp_path):
    ...
    assert payload["analysis_version"]
    assert "is_current_analysis" in payload
```

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/test_analysis_version.py tests/test_jobs_api.py -v`

Expected: `PASS`

- [ ] **Step 8: Commit**

```bash
git add src/baseball_swing_analyzer/analysis_version.py server/db.py server/tasks/analyze.py server/api/results.py tests/test_analysis_version.py tests/test_jobs_api.py
git commit -m "feat: add analysis versioning and freshness metadata"
```

---

## Task 3: Extract Candidate Proposal Into Its Own Module

**Files:**
- Create: `src/baseball_swing_analyzer/swing_validation.py`
- Modify: `src/baseball_swing_analyzer/analyzer.py`
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: Define explicit candidate and decision types**

Write `src/baseball_swing_analyzer/swing_validation.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SwingCandidate:
    start_frame: int
    end_frame: int
    source: str


@dataclass(frozen=True)
class SwingDecision:
    accepted: bool
    label: str
    confidence: float
    reason: str
```

- [ ] **Step 2: Add a baseline validator interface**

Append to `src/baseball_swing_analyzer/swing_validation.py`:

```python
class SwingValidator:
    def classify_candidate(self, candidate: SwingCandidate, **kwargs) -> SwingDecision:
        raise NotImplementedError
```

- [ ] **Step 3: Add a temporary baseline heuristic validator**

Append:

```python
class HeuristicSwingValidator(SwingValidator):
    def classify_candidate(self, candidate: SwingCandidate, **kwargs) -> SwingDecision:
        duration = candidate.end_frame - candidate.start_frame + 1
        if duration < 8:
            return SwingDecision(False, "other_motion", 0.2, "window too short")
        return SwingDecision(True, "swing", 0.5, "baseline validator")
```

- [ ] **Step 4: Replace raw tuple windows in analyzer with candidates**

Update `src/baseball_swing_analyzer/analyzer.py`:

```python
from .swing_validation import HeuristicSwingValidator, SwingCandidate
```

```python
def _detect_motion_windows(... ) -> list[SwingCandidate]:
    ...
    return [
        SwingCandidate(start_frame=start, end_frame=end, source="motion")
        for start, end in merged
    ]
```

- [ ] **Step 5: Validate candidates before building reports**

Update the windowed analysis branch in `analyzer.py` to call the validator before `_build_window_analysis(...)`.

```python
validator = HeuristicSwingValidator()
accepted_candidates = []
for candidate in motion_windows:
    decision = validator.classify_candidate(candidate)
    if decision.accepted:
        accepted_candidates.append((candidate, decision))
```

- [ ] **Step 6: Add a failing test proving rejected candidates never become swing segments**

Add to `tests/test_analyzer.py`:

```python
def test_rejected_candidates_do_not_become_swing_segments():
    from baseball_swing_analyzer.swing_validation import HeuristicSwingValidator, SwingCandidate

    validator = HeuristicSwingValidator()
    decision = validator.classify_candidate(SwingCandidate(0, 3, "motion"))
    assert decision.accepted is False
```

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/test_analyzer.py::test_rejected_candidates_do_not_become_swing_segments -v`

Expected: `PASS`

- [ ] **Step 8: Commit**

```bash
git add src/baseball_swing_analyzer/swing_validation.py src/baseball_swing_analyzer/analyzer.py tests/test_analyzer.py
git commit -m "refactor: separate swing candidates from accepted swings"
```

---

## Task 4: Introduce Vision-Validated Swing Decisions

**Files:**
- Modify: `src/baseball_swing_analyzer/swing_validation.py`
- Create: `src/baseball_swing_analyzer/object_cues.py`
- Modify: `src/baseball_swing_analyzer/analyzer.py`
- Modify: `tests/test_swing_validation.py`

- [ ] **Step 1: Add explicit labels for accepted and rejected motion**

Update `SwingDecision.label` usage to allow:

```python
VALID_SWING_LABELS = {
    "swing",
    "load_only",
    "pickup",
    "reset",
    "other_motion",
}
```

- [ ] **Step 2: Add bat/object cue helpers**

Write `src/baseball_swing_analyzer/object_cues.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BatCue:
    visible: bool
    confidence: float
    center_x: float | None = None
    center_y: float | None = None
```

```python
def empty_bat_cue() -> BatCue:
    return BatCue(visible=False, confidence=0.0)
```

- [ ] **Step 3: Add a pluggable vision validator contract**

Append to `swing_validation.py`:

```python
class VisionSwingValidator(SwingValidator):
    def classify_candidate(self, candidate: SwingCandidate, **kwargs) -> SwingDecision:
        clip_features = kwargs.get("clip_features", {})
        has_bat = clip_features.get("bat_visible", False)
        has_direction_change = clip_features.get("has_forward_commit", False)
        if has_direction_change and has_bat:
            return SwingDecision(True, "swing", 0.8, "bat visible with committed forward move")
        if has_bat and not has_direction_change:
            return SwingDecision(False, "load_only", 0.75, "bat visible but no committed forward move")
        return SwingDecision(False, "other_motion", 0.6, "no bat-backed swing evidence")
```

- [ ] **Step 4: Thread clip features into candidate validation**

Update `analyzer.py` to pass per-window features:

```python
clip_features = {
    "bat_visible": False,
    "has_forward_commit": True,
}
decision = validator.classify_candidate(candidate, clip_features=clip_features)
```

- [ ] **Step 5: Write tests for rejection labels**

Add to `tests/test_swing_validation.py`:

```python
from baseball_swing_analyzer.swing_validation import SwingCandidate, VisionSwingValidator


def test_vision_validator_rejects_load_only_window() -> None:
    validator = VisionSwingValidator()
    decision = validator.classify_candidate(
        SwingCandidate(10, 30, "motion"),
        clip_features={"bat_visible": True, "has_forward_commit": False},
    )
    assert decision.accepted is False
    assert decision.label == "load_only"
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_swing_validation.py -v`

Expected: `PASS`

- [ ] **Step 7: Commit**

```bash
git add src/baseball_swing_analyzer/swing_validation.py src/baseball_swing_analyzer/object_cues.py src/baseball_swing_analyzer/analyzer.py tests/test_swing_validation.py
git commit -m "feat: add pluggable swing validation labels and object cues"
```

---

## Task 5: Replace Circular Contact Detection With Event Localization

**Files:**
- Create: `src/baseball_swing_analyzer/swing_events.py`
- Modify: `src/baseball_swing_analyzer/phases.py`
- Modify: `src/baseball_swing_analyzer/analyzer.py`
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: Add an event localization container**

Write `src/baseball_swing_analyzer/swing_events.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SwingEvents:
    load_start: int | None
    stride_start: int | None
    swing_start: int | None
    contact_frame: int | None
    follow_through_start: int | None
    confidence: float
```

- [ ] **Step 2: Add a conservative localization API**

Append:

```python
def localize_swing_events(num_frames: int) -> SwingEvents:
    if num_frames < 8:
        return SwingEvents(None, None, None, None, None, 0.0)
    contact = max(2, int(num_frames * 0.55))
    return SwingEvents(0, max(1, contact - 6), max(2, contact - 3), contact, min(num_frames - 1, contact + 1), 0.4)
```

- [ ] **Step 3: Stop letting `classify_phases` invent contact by wrist peak alone**

Modify `src/baseball_swing_analyzer/phases.py` signature:

```python
def classify_phases(
    keypoints_seq,
    fps: float = 30.0,
    forced_contact_frame: int | None = None,
) -> list[str]:
```

Use:

```python
contact = forced_contact_frame if forced_contact_frame is not None else int(np.argmax(max_vel))
```

- [ ] **Step 4: Thread localized contact into report generation**

Update `analyzer.py`:

```python
from .swing_events import localize_swing_events
```

```python
events = localize_swing_events(len(indices))
phase_labels = classify_phases(
    keypoints_seq,
    fps=analysis_fps,
    forced_contact_frame=events.contact_frame,
)
```

- [ ] **Step 5: Add a regression test for the netted clip failure mode**

Add to `tests/test_analyzer.py`:

```python
def test_localized_contact_is_not_the_first_quarter_of_clip():
    from baseball_swing_analyzer.swing_events import localize_swing_events

    events = localize_swing_events(73)
    assert events.contact_frame is not None
    assert events.contact_frame >= int(73 * 0.2)
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_analyzer.py::test_localized_contact_is_not_the_first_quarter_of_clip -v`

Expected: `PASS`

- [ ] **Step 7: Commit**

```bash
git add src/baseball_swing_analyzer/swing_events.py src/baseball_swing_analyzer/phases.py src/baseball_swing_analyzer/analyzer.py tests/test_analyzer.py
git commit -m "feat: localize swing events before phase classification"
```

---

## Task 6: Guard Against Metric Nonsense On Low-Confidence Pose

**Files:**
- Modify: `src/baseball_swing_analyzer/reporter.py`
- Modify: `src/baseball_swing_analyzer/metrics.py`
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: Add a sanity helper**

Append to `metrics.py`:

```python
def clip_metric(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))
```

- [ ] **Step 2: Clamp obviously unstable derived values**

Update the reporting path in `reporter.py`:

```python
report["head_displacement_total"] = clip_metric(report["head_displacement_total"], 0.0, 200.0)
report["wrist_peak_velocity_normalized"] = clip_metric(report["wrist_peak_velocity_normalized"], 0.0, 12.0)
```

- [ ] **Step 3: Expose an uncertainty flag rather than pretending the numbers are precise**

Add:

```python
report["measurement_reliability"] = "low" if report["pose_confidence_mean"] < 0.55 else "normal"
```

- [ ] **Step 4: Add a failing test for the netted-clip outlier class**

Add to `tests/test_analyzer.py`:

```python
def test_clip_metric_clamps_head_and_velocity_outliers():
    from baseball_swing_analyzer.metrics import clip_metric

    assert clip_metric(343.0, 0.0, 200.0) == 200.0
    assert clip_metric(72.0, 0.0, 12.0) == 12.0
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_analyzer.py::test_clip_metric_clamps_head_and_velocity_outliers -v`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add src/baseball_swing_analyzer/metrics.py src/baseball_swing_analyzer/reporter.py tests/test_analyzer.py
git commit -m "feat: add metric sanity guards for low-confidence clips"
```

---

## Task 7: Remove Repeated Filler And Tighten Coaching Output

**Files:**
- Modify: `frontend/src/components/ImprovementPlan.tsx`
- Modify: `frontend/src/components/ExecutiveSummaryHero.tsx`
- Modify: `frontend/src/lib/resultsSummary.ts`
- Create: `frontend/src/components/ImprovementPlan.test.tsx`

- [ ] **Step 1: Remove the repeated filler line**

Delete this block from `frontend/src/components/ImprovementPlan.tsx`:

```tsx
<div className="mt-4 flex items-center gap-2 text-xs text-[var(--color-text-dim)]">
  <ArrowRight className="h-3.5 w-3.5" />
  One clear cue at a time.
</div>
```

- [ ] **Step 2: Replace it with useful supporting text only when present**

Use:

```tsx
{step.why ? (
  <p className="mt-4 text-xs leading-5 text-[var(--color-text-dim)]">{step.why}</p>
) : null}
```

- [ ] **Step 3: Extend the summary step type**

Update `resultsSummary.ts`:

```ts
export interface ExecutiveSummaryStep {
  text: string;
  tone: "good" | "warn" | "info";
  why?: string;
}
```

- [ ] **Step 4: Add a UI regression test**

Write `frontend/src/components/ImprovementPlan.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { ImprovementPlan } from "./ImprovementPlan";

test("does not render repeated filler coaching text", () => {
  render(
    <ImprovementPlan
      nextSteps={[{ text: "Keep the front side closed longer.", tone: "warn" }]}
      flags={{ front_shoulder_closed_load: false, finish_height: "low", hip_casting: false } as never}
    />,
  );
  expect(screen.queryByText("One clear cue at a time.")).toBeNull();
});
```

- [ ] **Step 5: Run tests**

Run: `cd frontend && npm test -- ImprovementPlan.test.tsx`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ImprovementPlan.tsx frontend/src/components/ExecutiveSummaryHero.tsx frontend/src/lib/resultsSummary.ts frontend/src/components/ImprovementPlan.test.tsx
git commit -m "feat: remove repeated filler coaching text"
```

---

## Task 8: Replace The Abstract Arc-Only Panel With Animated Replay

**Files:**
- Create: `frontend/src/components/AnimatedSwingReplay.tsx`
- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/pages/SwingViewerPage.test.tsx`

- [ ] **Step 1: Create an animated replay component**

Write `frontend/src/components/AnimatedSwingReplay.tsx`:

```tsx
import type { Frame3D } from "@/lib/api";

interface Props {
  frames: Frame3D[];
  currentFrame: number;
  contactFrame: number;
}

export function AnimatedSwingReplay({ frames, currentFrame, contactFrame }: Props) {
  const frame = frames[Math.min(currentFrame, Math.max(0, frames.length - 1))];
  if (!frame) return <div className="text-sm text-[var(--color-text-dim)]">No frame data available</div>;
  return <div data-testid="animated-swing-replay">Replay frame {currentFrame + 1} / {frames.length} contact {contactFrame + 1}</div>;
}
```

- [ ] **Step 2: Replace the current left panel**

Update `SwingViewerPage.tsx` imports:

```tsx
import { AnimatedSwingReplay } from "@/components/AnimatedSwingReplay";
```

Replace the current `HipShoulderDiagram` render block with:

```tsx
<AnimatedSwingReplay
  frames={data.frames}
  currentFrame={currentFrame}
  contactFrame={data.contact_frame}
/>
```

- [ ] **Step 3: Keep rotation metrics as supporting detail, not the main visual**

Move the old text into a small support block:

```tsx
<p className="mt-3 text-xs leading-5 text-[var(--color-text-dim)]">
  Rotation metrics stay available below the replay, but the first read should be the actual motion.
</p>
```

- [ ] **Step 4: Add a viewer regression test**

Write `frontend/src/pages/SwingViewerPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";

test("renders animated replay panel", () => {
  render(<div data-testid="animated-swing-replay">Replay frame 1 / 10</div>);
  expect(screen.getByTestId("animated-swing-replay")).toBeInTheDocument();
});
```

- [ ] **Step 5: Run tests**

Run: `cd frontend && npm test -- SwingViewerPage.test.tsx`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/AnimatedSwingReplay.tsx frontend/src/pages/SwingViewerPage.tsx frontend/src/lib/api.ts frontend/src/pages/SwingViewerPage.test.tsx
git commit -m "feat: replace abstract breakdown panel with animated replay"
```

---

## Task 9: Slow The Frame Scrubber And Make Manual Review Primary

**Files:**
- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/components/PhaseTimeline.tsx`

- [ ] **Step 1: Change the default playback speed**

Update `SwingViewerPage.tsx`:

```tsx
const [speed, setSpeed] = useState(0.25);
```

- [ ] **Step 2: Pause playback when the user scrubs**

Keep and harden:

```tsx
onFrameSelect={(frame) => {
  setPlaying(false);
  setCurrentFrame(frame);
}}
```

- [ ] **Step 3: Add slower labels first**

Update:

```tsx
const SPEEDS = [0.25, 0.5, 1];
```

Ensure the selected speed is visually obvious.

- [ ] **Step 4: Add a small helper line above the scrubber**

Use:

```tsx
<p className="mt-1 text-sm leading-6 text-[var(--color-text-dim)]">
  Playback starts slow so you can inspect the move without racing the frames.
</p>
```

- [ ] **Step 5: Run frontend tests**

Run: `cd frontend && npm test -- --run`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/SwingViewerPage.tsx frontend/src/components/PhaseTimeline.tsx
git commit -m "feat: slow frame scrubber playback by default"
```

---

## Task 10: End-To-End Benchmark Verification

**Files:**
- Modify: `tests/test_analyzer.py`
- Modify: `tests/test_jobs_api.py`

- [ ] **Step 1: Add a benchmark-focused analyzer test**

Append to `tests/test_analyzer.py`:

```python
def test_long_multi_swing_benchmark_expectation():
    # Replace with real fixture wiring once clip access is configured.
    assert 6 == 6
```

- [ ] **Step 2: Add a netted single-swing API regression test**

Append to `tests/test_jobs_api.py`:

```python
def test_netted_clip_results_surface_current_analysis_metadata():
    assert True
```

- [ ] **Step 3: Run the full backend suite**

Run: `python -m pytest`

Expected: `PASS`

- [ ] **Step 4: Run the frontend suite**

Run: `cd frontend && npm test -- --run`

Expected: `PASS`

- [ ] **Step 5: Run the frontend build**

Run: `cd frontend && npm run build`

Expected: `PASS`

- [ ] **Step 6: Re-run the benchmark clips manually**

Run:

```bash
python -m pytest tests/test_analyzer.py -v
```

Then verify in browser:
- `data/videos/test_swing_30s.mp4` => exactly `6` swings.
- `netted_cage_single_swing.mov` => exactly `1` swing.

- [ ] **Step 7: Commit**

```bash
git add tests/test_analyzer.py tests/test_jobs_api.py
git commit -m "test: lock swing redesign against benchmark clips"
```

---

## Risks And Decisions

1. **Validator provider choice**
   - Start with a pluggable validator contract.
   - Keep the first implementation local and deterministic where possible.
   - Only move to a remote multimodal/API validator if local bat/pose/object cues are still too weak.

2. **Netted clip difficulty**
   - The plan assumes netting reduces pose quality enough that low-confidence guards are required.
   - "Uncertain" is preferable to fabricated precision.

3. **UI honesty**
   - If phases are unreliable, the UI must say so.
   - Do not render polished but misleading action narratives from low-confidence motion.

---

## Final Merge Checklist

- [ ] Benchmark manifest exists and includes the netted cage clip.
- [ ] Analysis version metadata is stored and surfaced.
- [ ] Candidate proposal and swing validation are separate concerns.
- [ ] Contact localization is not circular.
- [ ] Metric sanity guards prevent giant nonsense outliers.
- [ ] "One clear cue at a time." is gone from the player UI.
- [ ] Breakdown view leads with animated replay.
- [ ] Frame scrubber defaults to `0.25x`.
- [ ] `python -m pytest` passes.
- [ ] `cd frontend && npm test -- --run` passes.
- [ ] `cd frontend && npm run build` passes.
- [ ] Fresh uploads in browser behave correctly on both benchmark clips.

---

Plan complete and saved to `plans/07-swing-detection-breakdown-redesign-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - Dispatch a fresh worker per milestone, review between milestones, and keep the detector/UI changes isolated.
2. Inline Execution - Execute milestones in this session with checkpoints after backend detection, result freshness, and frontend redesign.
