# Cross-Sport Swing Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic baseball/softball sport profiling and remove baseball-specific advice when sport is not confidently detected.

**Architecture:** Keep one shared biomechanics pipeline and add a small sport-profile layer that runs after analysis. The backend will attach `sport_profile` to results and projection responses, while coaching and UI surfaces will switch between baseball-specific, softball-specific, and generic hitting language. Existing metric extraction stays untouched.

**Tech Stack:** Python 3.12, FastAPI, pytest, React, TypeScript, Vite

---

## File Map

- Create: `src/baseball_swing_analyzer/sport.py` - sport-profile types and conservative auto-detection helpers
- Modify: `server/tasks/analyze.py` - compute `sport_profile` and store it in `metrics_json`
- Modify: `server/api/results.py` - return `sport_profile` with results payload
- Modify: `server/api/projection.py` - include `sport_profile` in projection responses
- Modify: `src/baseball_swing_analyzer/projection.py` - attach sport-aware notes to estimate output
- Modify: `src/baseball_swing_analyzer/ai/knowledge.py` - generate generic or sport-aware coaching copy
- Modify: `src/baseball_swing_analyzer/ai/coaching.py` - remove baseball-only prompt wording
- Modify: `frontend/src/lib/api.ts` - type sport profile in results/projection contracts
- Modify: `frontend/src/pages/UploadPage.tsx` - remove baseball-only upload copy
- Modify: `frontend/src/pages/ResultsPage.tsx` - display detected sport / generic fallback messaging
- Modify: `frontend/src/pages/SwingViewerPage.tsx` - show sport profile in viewer and pass it to What If UI
- Modify: `frontend/src/components/WhatIfSimulator.tsx` - sport-aware estimate disclaimer copy
- Test: `tests/test_sport.py`
- Test: `tests/test_jobs_api.py`
- Test: `tests/test_ai.py`

### Task 1: Add Backend Sport Profile Detection

**Files:**
- Create: `src/baseball_swing_analyzer/sport.py`
- Modify: `server/tasks/analyze.py`
- Test: `tests/test_sport.py`
- Test: `tests/test_jobs_api.py`

- [ ] **Step 1: Write the failing sport-profile tests**

```python
from baseball_swing_analyzer.sport import detect_sport_profile


def test_detect_sport_profile_prefers_softball_keyword() -> None:
    profile = detect_sport_profile(
        original_filename="slowmo_softball_swing.mp4",
        metrics={"flags": {}, "pose_confidence_mean": 0.8},
    )

    assert profile["label"] == "softball"
    assert profile["context_confidence"] > 0.8


def test_detect_sport_profile_prefers_baseball_keyword() -> None:
    profile = detect_sport_profile(
        original_filename="batting_practice_baseball.mov",
        metrics={"flags": {}, "pose_confidence_mean": 0.8},
    )

    assert profile["label"] == "baseball"
    assert profile["context_confidence"] > 0.8


def test_detect_sport_profile_falls_back_to_unknown_without_strong_signal() -> None:
    profile = detect_sport_profile(
        original_filename="clip_001.mp4",
        metrics={"flags": {}, "pose_confidence_mean": 0.8},
    )

    assert profile["label"] == "unknown"
    assert profile["reasons"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sport.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing `detect_sport_profile`

- [ ] **Step 3: Implement minimal sport detection**

```python
SPORT_KEYWORDS = {
    "baseball": ("baseball", "bb", "batting-practice"),
    "softball": ("softball", "fastpitch", "slowpitch"),
}


def detect_sport_profile(original_filename: str, metrics: dict) -> dict[str, object]:
    lowered = original_filename.lower()
    for label, keywords in SPORT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return {
                "label": label,
                "confidence": 0.92,
                "context_confidence": 0.95,
                "mechanics_confidence": 0.5,
                "reasons": [f"Filename strongly suggests {label}"],
            }
    return {
        "label": "unknown",
        "confidence": 0.35,
        "context_confidence": 0.2,
        "mechanics_confidence": 0.45,
        "reasons": ["No strong baseball or softball signal detected"],
    }
```

- [ ] **Step 4: Attach `sport_profile` during analysis**

```python
from baseball_swing_analyzer.sport import detect_sport_profile

sport_profile = detect_sport_profile(job["original_filename"], result)
result["sport_profile"] = sport_profile
```

- [ ] **Step 5: Verify results endpoint exposes sport profile**

Add assertion in `tests/test_jobs_api.py`:

```python
assert body["sport_profile"]["label"] == "softball"
```

Run: `python -m pytest tests/test_sport.py tests/test_jobs_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/baseball_swing_analyzer/sport.py server/tasks/analyze.py tests/test_sport.py tests/test_jobs_api.py
git commit -m "feat: add automatic sport profile detection"
```

### Task 2: Make Coaching Cross-Sport Safe

**Files:**
- Modify: `src/baseball_swing_analyzer/ai/knowledge.py`
- Modify: `src/baseball_swing_analyzer/ai/coaching.py`
- Test: `tests/test_ai.py`

- [ ] **Step 1: Write the failing coaching tests**

```python
from baseball_swing_analyzer.ai.knowledge import generate_static_report


def test_static_report_uses_generic_copy_when_sport_unknown() -> None:
    cues = generate_static_report({
        "sport_profile": {"label": "unknown"},
        "flags": {"finish_height": "low"},
        "pose_confidence_mean": 0.8,
    })

    assert any("pitcher" not in cue.lower() for cue in cues)
    assert all("baseball" not in cue.lower() for cue in cues)


def test_build_coaching_prompt_is_not_baseball_specific() -> None:
    from baseball_swing_analyzer.ai.coaching import build_coaching_prompt

    prompt = build_coaching_prompt({"sport_profile": {"label": "unknown"}})
    assert "baseball swing" not in prompt.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai.py -v`
Expected: FAIL on baseball-specific wording

- [ ] **Step 3: Implement sport-aware coaching copy**

```python
sport_label = ((metrics.get("sport_profile") or {}).get("label") or "unknown")

if sport_label == "unknown":
    finish_cue = "Low finish detected — stay through contact longer and extend through the middle of the field."
else:
    finish_cue = "Low finish detected — stay through the ball longer and extend your arms toward the pitcher."
```

Update prompt template to:

```python
_PROMPT_TEMPLATE = \"\"\"You are an expert hitting coach reviewing biomechanical metrics from a swing video:

{metrics_summary}

Please provide a concise, actionable coaching report...\"\"\"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/baseball_swing_analyzer/ai/knowledge.py src/baseball_swing_analyzer/ai/coaching.py tests/test_ai.py
git commit -m "feat: make coaching cross-sport safe"
```

### Task 3: Surface Sport Profile in Results and Viewer

**Files:**
- Modify: `server/api/results.py`
- Modify: `server/api/projection.py`
- Modify: `src/baseball_swing_analyzer/projection.py`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/UploadPage.tsx`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/components/WhatIfSimulator.tsx`
- Test: `tests/test_jobs_api.py`

- [ ] **Step 1: Write the failing API/UI contract test**

Add to `tests/test_jobs_api.py`:

```python
assert body["sport_profile"]["label"] == "unknown"
```

- [ ] **Step 2: Run targeted backend test**

Run: `python -m pytest tests/test_jobs_api.py -v`
Expected: FAIL because `sport_profile` is absent

- [ ] **Step 3: Add sport profile to API responses**

```python
sport_profile = metrics.pop("sport_profile", None) if metrics else None

return {
    "job_id": job["id"],
    "status": job["status"],
    "metrics": metrics,
    "analysis": analysis,
    "sport_profile": sport_profile,
    "coaching": _coaching_lines(coaching),
    "frames_3d_url": f"/api/jobs/{job['id']}/artifacts/frames_3d.json",
}
```

For projection:

```python
projected = project_swing_viewer_data(viewer_data, request)
projected["sport_profile"] = (viewer_data.get("metrics", {}) or {}).get("sport_profile")
return projected
```

- [ ] **Step 4: Update frontend types and copy**

Add in `frontend/src/lib/api.ts`:

```ts
export interface SportProfile {
  label: "baseball" | "softball" | "unknown";
  confidence: number;
  context_confidence: number;
  mechanics_confidence: number;
  reasons: string[];
}
```

Update results/viewer copy to:

- upload page: `Upload a baseball or softball swing video`
- results page: show `Detected sport`
- viewer page: show sport badge and generic fallback note when `unknown`
- What If note: avoid baseball-specific wording and prefer `measured ball flight` language

- [ ] **Step 5: Run backend and frontend verification**

Run:
- `python -m pytest tests/test_jobs_api.py -v`
- `npm run build`

Expected:
- tests PASS
- build PASS

- [ ] **Step 6: Commit**

```bash
git add server/api/results.py server/api/projection.py src/baseball_swing_analyzer/projection.py frontend/src/lib/api.ts frontend/src/pages/UploadPage.tsx frontend/src/pages/ResultsPage.tsx frontend/src/pages/SwingViewerPage.tsx frontend/src/components/WhatIfSimulator.tsx tests/test_jobs_api.py
git commit -m "feat: surface cross-sport profile in UI"
```

### Task 4: End-to-End Verification and Cleanup

**Files:**
- Modify: `docs/superpowers/plans/2026-04-25-cross-sport-swing-analysis.md`

- [ ] **Step 1: Run focused regression suite**

Run: `python -m pytest tests/test_sport.py tests/test_ai.py tests/test_jobs_api.py tests/test_projection.py -v`
Expected: PASS

- [ ] **Step 2: Run frontend production build**

Run: `npm run build`
Expected: PASS with the existing bundle-size warning only

- [ ] **Step 3: Verify in browser**

Open:
- `http://127.0.0.1:5174/results/<job-id>`
- `http://127.0.0.1:5174/viewer/<job-id>`

Check:
- no baseball-only upload/results copy
- sport badge renders
- unknown profile shows generic explanation
- What If panel still renders estimate ranges

- [ ] **Step 4: Mark plan progress**

Update this plan file checkboxes as tasks complete.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-04-25-cross-sport-swing-analysis.md
git commit -m "docs: mark cross-sport plan complete"
```
