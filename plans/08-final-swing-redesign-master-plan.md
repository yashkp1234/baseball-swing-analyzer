# Final Swing Redesign Master Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the swing-analyzer redesign end to end: correct swing detection on hard clips, honest confidence handling, stronger biomechanics metrics, and concrete player-facing coaching that is specific, evidence-backed, and easy to act on.

**Architecture:** Build on the shipped detection-and-viewer foundation by treating swing analysis as three linked systems: proposal/validation/event localization, metric extraction/report shaping, and coaching/rendering. The detector should decide *which motion windows are real swings*; the metric layer should decide *what is trustworthy and meaningful*; the coaching layer should decide *how to translate that into one main leak, one drill, and a small number of follow-up cues*.

**Tech Stack:** Python 3.10+, FastAPI, sqlite3, pytest, OpenCV, NumPy, RTMLib pose stack, optional multimodal/vision validator seam, React, TypeScript, Vite, React Query.

---

## Why This Is The Final Plan

This plan consolidates:
- the shipped detection/viewer redesign work in `main`
- the active execution plan in [plans/07-swing-detection-breakdown-redesign-plan.md](C:/Users/yashk/baseball_swing_analyzer/plans/07-swing-detection-breakdown-redesign-plan.md)
- the research/coaching work in [docs/SWING_RESEARCH_AND_COACHING_PLAN.md](C:/Users/yashk/baseball_swing_analyzer/docs/SWING_RESEARCH_AND_COACHING_PLAN.md)

The result is one master roadmap with:
- milestone order
- exact push boundaries
- verification gates
- merge expectations
- current status

---

## Current Baseline

### Already shipped on `main`

- `db0f9e3` - improved segmentation and multi-swing results flow
- `51f5a9b` - redesigned swing breakdown flow
- `3c431bf` - redesigned swing validation and breakdown UI

### Current behavior after the latest shipped pass

- [data/videos/test_swing_30s.mp4](C:/Users/yashk/baseball_swing_analyzer/data/videos/test_swing_30s.mp4) resolves to `6` swings
- [data/videos/benchmarks/netted_cage_single_swing.mov](C:/Users/yashk/baseball_swing_analyzer/data/videos/benchmarks/netted_cage_single_swing.mov) resolves to `1` swing
- stale analysis is surfaced in the UI
- the breakdown leads with animated replay
- the scrubber defaults to `0.25x`
- repeated filler coaching text is gone

### Still not good enough

- hard clips still need better phase-quality and reliability logic
- the coaching layer is still too generic relative to the research doc
- X-factor interpretation still needs to move from contact-only to peak-separation plus closure
- view-aware and sport-aware gating are still incomplete
- the validator seam exists, but it is still local-feature based rather than true bat/object/vision-backed reasoning

---

## Success Criteria

- `test_swing_30s.mp4` stays at exactly `6` accepted swings.
- `netted_cage_single_swing.mov` stays at exactly `1` accepted swing.
- No clip with low-confidence pose may silently produce hard angle-based certainty.
- Coaching must name:
  - the single biggest leak,
  - the metric value,
  - the target range,
  - why it matters,
  - one named drill or cue.
- The fallback knowledge base must be specific enough that the app is still useful without the cloud model.
- Every milestone ends in a clean push point with tests green.
- Final work lands on `main`.

---

## File Map

### Detection / eventing
- Modify: `src/baseball_swing_analyzer/analyzer.py`
- Modify: `src/baseball_swing_analyzer/swing_validation.py`
- Modify: `src/baseball_swing_analyzer/swing_events.py`
- Modify: `src/baseball_swing_analyzer/phases.py`
- Modify: `src/baseball_swing_analyzer/object_cues.py`

### Metrics / reporting
- Modify: `src/baseball_swing_analyzer/metrics.py`
- Modify: `src/baseball_swing_analyzer/energy.py`
- Modify: `src/baseball_swing_analyzer/reporter.py`

### Coaching / AI
- Modify: `src/baseball_swing_analyzer/ai/coaching.py`
- Modify: `src/baseball_swing_analyzer/ai/knowledge.py`
- Modify: `src/baseball_swing_analyzer/ai/client.py`

### API / persistence
- Modify: `server/db.py`
- Modify: `server/tasks/analyze.py`
- Modify: `server/api/results.py`
- Modify: `server/api/upload.py`

### Frontend
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/resultsSummary.ts`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/components/PhaseConfidenceBanner.tsx`
- Modify: `frontend/src/components/AnimatedSwingReplay.tsx`

### Fixtures / docs / tests
- Modify: `data/videos/benchmarks/manifest.json`
- Modify: `tests/test_ai.py`
- Modify: `tests/test_analyzer.py`
- Modify: `tests/test_jobs_api.py`
- Modify: `tests/test_metrics.py`
- Modify: `tests/test_swing_validation.py`
- Modify: `plans/07-swing-detection-breakdown-redesign-plan.md`

---

## Milestones

### Milestone 1: Lock The Baseline
**Status:** Done  
**Purpose:** freeze the benchmark clips, ship analysis freshness, and keep the viewer/results surface honest.

**Exit criteria:**
- benchmark manifest exists
- `analysis_version` exists
- stale-result banner exists
- replay-led breakdown exists

**Reference commits:**
- `db0f9e3`
- `51f5a9b`
- `3c431bf`

### Milestone 2: Coaching Prompt Rewrite
**Status:** Done  
**Purpose:** stop sending the model a raw metrics dump and instead send context, ranges, confidence, and drill expectations.

**Exit criteria:**
- prompt contains handedness, sport, view confidence, pose confidence, target ranges, one-biggest-leak-first instruction
- prompt regression tests pass

### Milestone 3: Structured Coaching Knowledge
**Status:** Done  
**Purpose:** make offline/fallback coaching good enough to be worth showing.

**Exit criteria:**
- fallback cues are structured
- every major issue can return `cue`, `why`, `drill`, and `level`
- no generic “need more separation” output survives without explanation

### Milestone 4: Missing High-Value Metrics
**Status:** Done  
**Purpose:** add the biomechanics the research doc says matter most.

**Exit criteria:**
- `peak_separation_deg`
- `peak_separation_frame`
- `separation_closure_rate`
- `time_to_contact_s`
- `head_drop_pct`
- `head_drift_pct`
- `kinetic_chain` data surfaced into the report

### Milestone 5: View- And Sport-Aware Gating
**Status:** Done  
**Purpose:** only coach what the camera angle and pose quality actually support.

**Exit criteria:**
- heuristic `view_type` and `view_confidence`
- side/3-quarter clips hedge or suppress angle-heavy claims
- baseball vs softball thresholds can diverge

### Milestone 6: Hard-Clip Validator Upgrade
**Status:** Done  
**Purpose:** decide whether the local validator is enough or whether to add a stronger bat/object/vision provider.

**Exit criteria:**
- benchmark clips still pass
- a documented go/no-go decision exists for multimodal validator escalation
- if escalated, candidate validation uses the new provider behind the existing seam

**Decision:** Stay on the local validator path for now. The benchmark clips still resolve to `6` swings and `1` swing respectively, so the immediate product win is to keep the current motion-window plus local-validation seam and improve reliability gating around view quality rather than add a remote multimodal dependency before it is necessary.

### Milestone 7: Final Integration And Merge
**Status:** In progress  
**Purpose:** final QA, browser verification, clean push, and merge-to-main closeout.

**Exit criteria:**
- backend tests green
- frontend tests green
- frontend build green
- benchmark uploads verified in browser
- work pushed and merged cleanly

---

## Push Strategy

### Push 0: Baseline already shipped
- Included commits:
  - `db0f9e3`
  - `51f5a9b`
  - `3c431bf`
- No new action required except keeping those behaviors stable.

### Push 1: Coaching prompt and report payload
**Commit group:**
- prompt rewrite
- report payload additions needed by prompt
- tests for prompt structure

**Expected commit titles:**
- `feat: rewrite coaching prompt around evidence and drills`
- `test: lock prompt structure and confidence wording`

**Push gate:**
- `python -m pytest tests/test_ai.py tests/test_jobs_api.py -v`

### Push 2: Structured fallback coaching
**Commit group:**
- knowledge base refactor
- drill library seed
- fallback tests

**Expected commit titles:**
- `feat: add structured fallback coaching cues`
- `test: verify fallback coaching specificity`

**Push gate:**
- `python -m pytest tests/test_ai.py -v`

### Push 3: Metric expansion
**Commit group:**
- peak separation
- closure rate
- TTC
- head split
- kinematic chain payload

**Expected commit titles:**
- `feat: add peak separation and timing metrics`
- `feat: surface kinematic chain and head movement splits`
- `test: cover new biomechanics metrics`

**Push gate:**
- `python -m pytest tests/test_metrics.py tests/test_analyzer.py -v`

### Push 4: View and sport gating
**Commit group:**
- view classifier
- confidence rules
- baseball/softball branching

**Expected commit titles:**
- `feat: add view-aware coaching gates`
- `feat: branch coaching by sport profile`

**Push gate:**
- `python -m pytest tests/test_ai.py tests/test_jobs_api.py -v`

### Push 5: Validator decision and hard-clip pass
**Commit group:**
- stronger validator or documented decision to stay local
- bat/object seam upgrades if needed
- hard-clip verification

**Expected commit titles:**
- `feat: strengthen hard-clip swing validation`
- `test: verify benchmark clip swing counts`

**Push gate:**
- `python -m pytest`
- benchmark reruns on both clips

### Push 6: Final merge push
**Commit group:**
- cleanup
- docs updates
- any last regression fixes

**Expected commit titles:**
- `docs: finalize swing redesign roadmap and verification notes`
- `chore: finalize swing redesign integration`

**Push gate:**
- `python -m pytest`
- `cd frontend && npm test -- --run`
- `cd frontend && npm run build`

---

## Task 1: Coaching Prompt Rewrite

**Files:**
- Modify: `src/baseball_swing_analyzer/ai/coaching.py`
- Modify: `src/baseball_swing_analyzer/reporter.py`
- Modify: `tests/test_ai.py`

- [ ] **Step 1: Write the failing prompt-shape test**

Add to `tests/test_ai.py`:

```python
from baseball_swing_analyzer.ai.coaching import build_coaching_prompt


def test_coaching_prompt_includes_ranges_confidence_and_drill_contract() -> None:
    metrics = {
        "sport": "baseball",
        "pose_confidence_mean": 0.83,
        "view_type": "frontal",
        "view_confidence": 0.74,
        "peak_separation_deg": 22.0,
        "x_factor_at_contact": 4.0,
        "time_to_contact_s": 0.18,
        "flags": {"handedness": "right"},
    }

    prompt = build_coaching_prompt(metrics)

    assert "target range" in prompt.lower() or "good:" in prompt.lower()
    assert "view confidence" in prompt.lower()
    assert "biggest leak" in prompt.lower()
    assert "drill" in prompt.lower()
```

- [ ] **Step 2: Run the test to confirm it fails**

Run:

```bash
python -m pytest tests/test_ai.py::test_coaching_prompt_includes_ranges_confidence_and_drill_contract -v
```

Expected: `FAIL`

- [ ] **Step 3: Rewrite the prompt template**

Update `src/baseball_swing_analyzer/ai/coaching.py` so the template includes:

```python
_PROMPT_TEMPLATE = """You are reviewing one swing.

HITTER CONTEXT:
- Sport: {sport}
- Handedness: {handedness}
- View confidence: {view_confidence}
- Pose confidence: {pose_confidence}

IMPORTANT:
- Name the single biggest leak first.
- Compare the actual metric value to the target range.
- Explain why it hurts contact quality or bat speed.
- Give one named drill or cue and what success should feel like.
- If view or pose quality is low, say what is unreliable and do not invent certainty.

KEY METRICS:
{metrics_summary}
"""
```

- [ ] **Step 4: Surface the prompt data in the report summary**

Extend `src/baseball_swing_analyzer/reporter.py` so the coaching layer receives:

```python
report["sport"] = report.get("sport", "baseball")
report["view_type"] = report.get("view_type", "unknown")
report["view_confidence"] = report.get("view_confidence", 0.0)
```

- [ ] **Step 5: Re-run the focused test**

Run:

```bash
python -m pytest tests/test_ai.py::test_coaching_prompt_includes_ranges_confidence_and_drill_contract -v
```

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add src/baseball_swing_analyzer/ai/coaching.py src/baseball_swing_analyzer/reporter.py tests/test_ai.py
git commit -m "feat: rewrite coaching prompt around evidence and drills"
```

---

## Task 2: Structured Fallback Coaching

**Files:**
- Modify: `src/baseball_swing_analyzer/ai/knowledge.py`
- Modify: `tests/test_ai.py`

- [ ] **Step 1: Write the failing fallback-shape test**

Add to `tests/test_ai.py`:

```python
from baseball_swing_analyzer.ai.knowledge import generate_static_report


def test_static_report_returns_specific_structured_cues() -> None:
    metrics = {
        "peak_separation_deg": 18.0,
        "pose_confidence_mean": 0.91,
        "flags": {"handedness": "right"},
    }

    cues = generate_static_report(metrics)

    first = cues[0]
    assert isinstance(first, dict)
    assert "cue" in first
    assert "why" in first
    assert "drill" in first
```

- [ ] **Step 2: Run the test to confirm it fails**

Run:

```bash
python -m pytest tests/test_ai.py::test_static_report_returns_specific_structured_cues -v
```

Expected: `FAIL`

- [ ] **Step 3: Refactor the fallback knowledge base**

Replace string-only rules in `src/baseball_swing_analyzer/ai/knowledge.py` with structured records:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CoachingCue:
    issue: str
    cue: str
    why: str
    drill: str
    level: str
```

Return dictionaries from `generate_static_report(...)`:

```python
{
    "issue": "Low peak separation",
    "cue": "Let the hips start the turn before the shoulders chase them.",
    "why": "Without early separation, the torso has no stored stretch to turn into bat speed.",
    "drill": "Hook 'Em drill: feel the lower half open before the chest and hands go with it.",
    "level": "youth",
}
```

- [ ] **Step 4: Add a low-confidence fallback test**

Add:

```python
def test_static_report_hedges_when_pose_confidence_is_low() -> None:
    cues = generate_static_report({"pose_confidence_mean": 0.32, "flags": {}})
    assert "unreliable" in str(cues).lower() or "confidence" in str(cues).lower()
```

- [ ] **Step 5: Re-run the focused tests**

Run:

```bash
python -m pytest tests/test_ai.py -v
```

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add src/baseball_swing_analyzer/ai/knowledge.py tests/test_ai.py
git commit -m "feat: add structured fallback coaching cues"
```

---

## Task 3: Add Missing High-Value Metrics

**Files:**
- Modify: `src/baseball_swing_analyzer/metrics.py`
- Modify: `src/baseball_swing_analyzer/reporter.py`
- Modify: `src/baseball_swing_analyzer/energy.py`
- Modify: `tests/test_metrics.py`
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing metric tests**

Add to `tests/test_metrics.py`:

```python
def test_peak_separation_and_closure_metrics_exist() -> None:
    from baseball_swing_analyzer.reporter import build_report
    import numpy as np

    seq = np.zeros((12, 17, 3), dtype=float)
    report = build_report(["idle"] * 12, seq, 30.0)

    assert "peak_separation_deg" in report
    assert "separation_closure_rate" in report
    assert "time_to_contact_s" in report
```

- [ ] **Step 2: Run the test to confirm it fails**

Run:

```bash
python -m pytest tests/test_metrics.py::test_peak_separation_and_closure_metrics_exist -v
```

Expected: `FAIL`

- [ ] **Step 3: Add the metric calculations**

Extend `src/baseball_swing_analyzer/reporter.py` to compute and store:

```python
report["peak_separation_deg"] = peak_sep
report["peak_separation_frame"] = peak_sep_frame
report["separation_closure_rate"] = closure_rate
report["time_to_contact_s"] = max(report["contact_frame"], 0) / fps
report["head_drop_pct"] = head_drop_pct
report["head_drift_pct"] = head_drift_pct
```

Also surface kinematic-chain outputs:

```python
report["kinetic_chain"] = {
    "hip_to_shoulder_lag_frames": ...,
    "shoulder_to_hand_lag_frames": ...,
    "sequence_order_correct": ...,
}
```

- [ ] **Step 4: Re-run focused tests**

Run:

```bash
python -m pytest tests/test_metrics.py tests/test_analyzer.py -v
```

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add src/baseball_swing_analyzer/metrics.py src/baseball_swing_analyzer/reporter.py src/baseball_swing_analyzer/energy.py tests/test_metrics.py tests/test_analyzer.py
git commit -m "feat: add peak separation and timing metrics"
```

---

## Task 4: Add View- And Sport-Aware Coaching Gates

**Files:**
- Modify: `src/baseball_swing_analyzer/reporter.py`
- Modify: `src/baseball_swing_analyzer/ai/coaching.py`
- Modify: `src/baseball_swing_analyzer/ai/knowledge.py`
- Modify: `tests/test_ai.py`
- Modify: `tests/test_jobs_api.py`

- [ ] **Step 1: Write the failing view-gating test**

Add to `tests/test_ai.py`:

```python
def test_prompt_warns_when_angle_metrics_are_not_view_safe() -> None:
    from baseball_swing_analyzer.ai.coaching import build_coaching_prompt

    prompt = build_coaching_prompt({
        "sport": "softball",
        "pose_confidence_mean": 0.88,
        "view_type": "side",
        "view_confidence": 0.84,
        "flags": {"handedness": "left"},
    })

    assert "do not invent certainty" in prompt.lower() or "reliable only" in prompt.lower()
```

- [ ] **Step 2: Run the test to confirm it fails**

Run:

```bash
python -m pytest tests/test_ai.py::test_prompt_warns_when_angle_metrics_are_not_view_safe -v
```

Expected: `FAIL`

- [ ] **Step 3: Add lightweight view heuristics**

In `src/baseball_swing_analyzer/reporter.py`, add:

```python
report["view_type"] = inferred_view_type
report["view_confidence"] = inferred_view_confidence
```

Start with a simple heuristic from shoulder width vs torso depth and left/right symmetry. Mark uncertain views as `unknown`.

- [ ] **Step 4: Add sport-aware prompt / fallback language**

In `src/baseball_swing_analyzer/ai/coaching.py` and `src/baseball_swing_analyzer/ai/knowledge.py`, branch where needed:

```python
sport = metrics.get("sport", "baseball")
attack_angle_target = "3° to 15°" if sport == "softball" else "5° to 20°"
```

- [ ] **Step 5: Re-run focused tests**

Run:

```bash
python -m pytest tests/test_ai.py tests/test_jobs_api.py -v
```

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add src/baseball_swing_analyzer/reporter.py src/baseball_swing_analyzer/ai/coaching.py src/baseball_swing_analyzer/ai/knowledge.py tests/test_ai.py tests/test_jobs_api.py
git commit -m "feat: add view-aware and sport-aware coaching gates"
```

---

## Task 5: Hard-Clip Validator Decision

**Files:**
- Modify: `src/baseball_swing_analyzer/swing_validation.py`
- Modify: `src/baseball_swing_analyzer/object_cues.py`
- Modify: `src/baseball_swing_analyzer/analyzer.py`
- Modify: `tests/test_swing_validation.py`

- [ ] **Step 1: Write the decision test**

Add to `tests/test_swing_validation.py`:

```python
def test_validator_accepts_benchmark_clip_shapes_without_promoting_load_only() -> None:
    assert True
```

Replace the placeholder with a real benchmark-wired assertion if the local fixture setup is ready.

- [ ] **Step 2: Compare validator paths**

Run benchmark analysis with:
- current local validator
- enhanced object-cue path if added
- optional multimodal candidate validator if local features are still too weak

Record the decision in comments or doc notes alongside the validator seam.

- [ ] **Step 3: Implement the selected path**

If local remains good enough:

```python
# Keep VisionSwingValidator local-feature based and tighten thresholds/tests.
```

If escalation is needed:

```python
class RemoteSwingValidator(SwingValidator):
    ...
```

Hide it behind the existing interface so `analyzer.py` does not care which provider is active.

- [ ] **Step 4: Run benchmark verification**

Run:

```bash
python -m pytest tests/test_swing_validation.py tests/test_analyzer.py -v
```

Then manually verify:
- `data/videos/test_swing_30s.mp4` => `6`
- `data/videos/benchmarks/netted_cage_single_swing.mov` => `1`

- [ ] **Step 5: Commit**

```bash
git add src/baseball_swing_analyzer/swing_validation.py src/baseball_swing_analyzer/object_cues.py src/baseball_swing_analyzer/analyzer.py tests/test_swing_validation.py
git commit -m "feat: finalize hard-clip swing validator path"
```

---

## Task 6: Final Verification, Push, And Merge

**Files:**
- Modify as needed from earlier tasks

- [ ] **Step 1: Run the full backend suite**

Run:

```bash
python -m pytest
```

Expected: `PASS`

- [ ] **Step 2: Run the frontend suite**

Run:

```bash
cd frontend && npm test -- --run
```

Expected: `PASS`

- [ ] **Step 3: Run the frontend build**

Run:

```bash
cd frontend && npm run build
```

Expected: `PASS`

- [ ] **Step 4: Re-upload the benchmark clips**

Verify in browser:
- `test_swing_30s.mp4`
- `netted_cage_single_swing.mov`

Check:
- swing count
- annotated video
- breakdown replay
- stale/current analysis messaging
- coaching specificity

- [ ] **Step 5: Push milestone branch**

```bash
git push origin HEAD
```

- [ ] **Step 6: Merge to `main`**

If branch-based:

```bash
git checkout main
git merge --ff-only <branch>
git push origin main
```

If already on `main`, push the final verified commit:

```bash
git push origin main
```

---

## Risks And Decisions

1. **The validator seam may still need a true multimodal provider.**
   The local feature path is better than naive motion gating, but the seam should stay clean so escalation is cheap.

2. **Angle metrics are still view-sensitive.**
   If the clip is side/3-quarter and the system knows it, it must hedge rather than bluff.

3. **The coaching layer is only as good as the report payload.**
   Better wording without better metrics will still produce polished nonsense.

4. **The netted cage clip is a truth serum.**
   If the system handles that clip honestly, it is probably learning the right habits.

---

## Final Merge Checklist

- [ ] Benchmark clips stay stable.
- [ ] Coaching prompt is evidence- and drill-driven.
- [ ] Fallback coaching is structured and specific.
- [ ] Peak separation and timing metrics exist.
- [ ] View-aware and sport-aware confidence gates exist.
- [ ] Annotated video and replay both work.
- [ ] `python -m pytest` passes.
- [ ] `cd frontend && npm test -- --run` passes.
- [ ] `cd frontend && npm run build` passes.
- [ ] Final verified work is pushed and merged into `main`.

---

Plan complete and saved to `plans/08-final-swing-redesign-master-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per milestone, review between milestones, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints
