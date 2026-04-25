# Adaptive Sampling And Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase sampled-frame quality on GPU while keeping end-to-end uploads under 20 seconds and exposing honest progress plus analysis metadata to the frontend.

**Architecture:** Add richer progress fields to the job store and task runner first, then improve frontend wait-state rendering, then upgrade the analyzer from uniform sampling to bounded adaptive sampling with measurable runtime telemetry, and finally surface analysis metadata on completed results. Each milestone stays additive and independently releasable.

**Tech Stack:** Python 3.12, FastAPI, sqlite3, React, TypeScript, TanStack Query, pytest

---

### Task 1: Progress Telemetry Foundation

**Files:**
- Modify: `server/db.py`
- Modify: `server/tasks/analyze.py`
- Modify: `server/api/status.py`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/ProcessingStatus.tsx`
- Test: `tests/test_session.py`

- [ ] **Step 1: Write failing backend payload test**

```python
def test_status_payload_exposes_progress_details(client):
    ...
    assert body["progress_detail_current"] == 12
    assert body["progress_detail_total"] == 48
    assert body["progress_detail_label"] == "frames"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_session.py -k progress -v`
Expected: FAIL because detail fields are absent.

- [ ] **Step 3: Add DB fields and status serialization**

Implement additive columns/fields:
- `progress_detail_current`
- `progress_detail_total`
- `progress_detail_label`

Return them from `server/api/status.py`.

- [ ] **Step 4: Emit stage + detail progress from analysis task**

Update `server/tasks/analyze.py` so stage transitions are explicit and inference can update detail counts.

- [ ] **Step 5: Update frontend types and waiting UI**

Teach `frontend/src/lib/api.ts` and `frontend/src/components/ProcessingStatus.tsx` to render the new fields without breaking old payloads.

- [ ] **Step 6: Run targeted tests**

Run: `python -m pytest tests/test_session.py -v`
Expected: PASS

- [ ] **Step 7: Run app-level verification**

Run: `python -m pytest`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add server/db.py server/tasks/analyze.py server/api/status.py frontend/src/lib/api.ts frontend/src/components/ProcessingStatus.tsx tests/test_session.py
git commit -m "feat: add detailed analysis progress telemetry"
git push origin improvement-plan
```

### Task 2: Adaptive GPU Sampling

**Files:**
- Modify: `src/baseball_swing_analyzer/analyzer.py`
- Test: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing sampler tests**

Add tests for:
- short clip gets dense budget
- long clip prefers action window
- uncertain action window falls back to bounded uniform

- [ ] **Step 2: Run sampler tests to verify they fail**

Run: `python -m pytest tests/test_analyzer.py -v`
Expected: FAIL on new adaptive cases.

- [ ] **Step 3: Implement bounded adaptive sampling**

Introduce:
- preferred GPU density target
- coarse scan
- action-window weighting
- bounded fallback

- [ ] **Step 4: Return analysis metadata**

Add analysis summary fields needed by results and telemetry.

- [ ] **Step 5: Run targeted analyzer tests**

Run: `python -m pytest tests/test_analyzer.py -v`
Expected: PASS

- [ ] **Step 6: Run full suite**

Run: `python -m pytest`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/baseball_swing_analyzer/analyzer.py tests/test_analyzer.py
git commit -m "feat: add adaptive bounded swing sampling"
git push origin improvement-plan
```

### Task 3: Frontend Wait-State Improvements

**Files:**
- Modify: `frontend/src/components/ProcessingStatus.tsx`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Write component-level expectations**

Capture display expectations for:
- determinate bar
- human-readable stage
- `current / total frames` when present

- [ ] **Step 2: Implement staged waiting UI**

Render:
- progress percent
- stage label
- optional detail counts

- [ ] **Step 3: Verify frontend build**

Run: `npm run build`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ProcessingStatus.tsx frontend/src/pages/ResultsPage.tsx frontend/src/lib/api.ts
git commit -m "feat: improve job progress UI"
git push origin improvement-plan
```

### Task 4: Results Metadata Handoff

**Files:**
- Modify: `server/api/results.py`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Test: `tests/test_session.py`

- [ ] **Step 1: Write failing API payload test**

Assert `results.analysis` contains:
- `pose_device`
- `sampled_frames`
- `effective_analysis_fps`
- `analysis_duration_ms`

- [ ] **Step 2: Run targeted test to verify it fails**

Run: `python -m pytest tests/test_session.py -v`
Expected: FAIL on missing `analysis`.

- [ ] **Step 3: Extend results payload**

Expose an additive `analysis` object from `server/api/results.py`.

- [ ] **Step 4: Render analysis metadata**

Show a compact analysis summary on results and viewer pages.

- [ ] **Step 5: Verify backend + frontend**

Run:
- `python -m pytest`
- `npm run build`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add server/api/results.py frontend/src/lib/api.ts frontend/src/pages/ResultsPage.tsx frontend/src/pages/SwingViewerPage.tsx tests/test_session.py
git commit -m "feat: surface analysis quality metadata"
git push origin improvement-plan
```

### Task 5: Benchmark And Tuning

**Files:**
- Modify: `benchmark.py` or create `scripts/benchmark_analysis.py`
- Modify: `src/baseball_swing_analyzer/analyzer.py`

- [ ] **Step 1: Add a repeatable reference benchmark**

Measure:
- end-to-end runtime
- sampled frames
- effective fps
- pose device

- [ ] **Step 2: Run benchmark on reference clip**

Expected:
- under 20.0 seconds end-to-end
- sampled frames exceed 48 on GPU

- [ ] **Step 3: Tune GPU defaults conservatively**

Adjust preferred density and runtime budget until the target is met.

- [ ] **Step 4: Re-run validation**

Run:
- `python -m pytest`
- benchmark command
- `npm run build`

Expected: PASS + runtime target met

- [ ] **Step 5: Commit**

```bash
git add src/baseball_swing_analyzer/analyzer.py benchmark.py
git commit -m "perf: tune adaptive sampling for latency target"
git push origin improvement-plan
```
