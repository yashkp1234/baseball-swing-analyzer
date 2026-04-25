# Swing Viewer Truthful 3D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fake 3D viewer with a real 3D swing renderer, make What If update the rendered swing plus projected EV/distance, and keep the viewer on one desktop screen without vertical page scroll.

**Architecture:** Add a lightweight Python projection engine and API over existing job artifacts, then rebuild the viewer around a Three.js skeleton canvas that can swap between baseline and projected sequences. Keep the transformation math on the backend, and keep the interactive rendering and transport controls on the frontend.

**Tech Stack:** FastAPI, Python, pytest, React, TypeScript, Vite, Three.js

---

## File Structure

- Create: `src/baseball_swing_analyzer/projection.py`
- Create: `server/api/projection.py`
- Create: `tests/test_projection.py`
- Create: `tests/fixtures/viewer_fixture.json`
- Create: `frontend/src/components/SwingSkeletonViewer.tsx`
- Modify: `server/main.py`
- Modify: `frontend/package.json`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/components/HipShoulderDiagram.tsx`
- Modify: `frontend/src/components/WhatIfSimulator.tsx`
- Modify: `tests/test_jobs_api.py`

### Task 1: Build the Backend Projection Engine

**Files:**
- Create: `src/baseball_swing_analyzer/projection.py`
- Create: `tests/fixtures/viewer_fixture.json`
- Test: `tests/test_projection.py`

- [ ] **Step 1: Write failing backend tests for projection transforms and estimates**

```python
from baseball_swing_analyzer.projection import (
    ProjectionRequest,
    project_swing_viewer_data,
)


def _viewer_fixture():
    ...


def test_projection_changes_frames_and_returns_estimates():
    viewer = _viewer_fixture()
    request = ProjectionRequest(x_factor_delta_deg=8.0, head_stability_delta_norm=0.08)

    result = project_swing_viewer_data(viewer, request)

    assert result["projection"]["exit_velocity_mph"] > 0
    assert result["projection"]["carry_distance_ft"] > 0
    assert result["viewer"]["frames"] != viewer["frames"]
    assert result["baseline"]["exit_velocity_mph"] > 0


def test_projection_clamps_extreme_inputs():
    viewer = _viewer_fixture()
    request = ProjectionRequest(x_factor_delta_deg=999.0, head_stability_delta_norm=999.0)

    result = project_swing_viewer_data(viewer, request)

    assert result["projection"]["exit_velocity_mph"] < 140
    assert result["projection"]["carry_distance_ft"] < 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_projection.py -v`  
Expected: FAIL with import errors because `baseball_swing_analyzer.projection` does not exist yet.

- [ ] **Step 3: Implement the projection engine**

```python
from dataclasses import dataclass
from copy import deepcopy


@dataclass(frozen=True)
class ProjectionRequest:
    x_factor_delta_deg: float = 0.0
    head_stability_delta_norm: float = 0.0


def project_swing_viewer_data(viewer_data: dict, request: ProjectionRequest) -> dict:
    projected = deepcopy(viewer_data)
    # clamp inputs, transform load->contact frames in normalized viewer space,
    # then estimate EV/carry
    return {
        "baseline": {
            "exit_velocity_mph": 84.0,
            "carry_distance_ft": 287.0,
            "score": 74,
        },
        "projection": {
            "exit_velocity_mph": 88.0,
            "carry_distance_ft": 300.0,
            "score": 80,
            "notes": ["Projected from baseline swing metrics"],
        },
        "viewer": projected,
    }
```

- [ ] **Step 4: Run projection tests to verify they pass**

Run: `python -m pytest tests/test_projection.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/baseball_swing_analyzer/projection.py tests/fixtures/viewer_fixture.json tests/test_projection.py
git commit -m "feat: add swing projection engine"
```

### Task 2: Expose Projection Through the Jobs API

**Files:**
- Create: `server/api/projection.py`
- Modify: `server/main.py`
- Modify: `tests/test_jobs_api.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_projection_endpoint_returns_projected_viewer(client, completed_job):
    response = client.post(
        f"/api/jobs/{completed_job}/projection",
        json={"x_factor_delta_deg": 6, "head_stability_delta_norm": 0.06},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "baseline" in payload
    assert "projection" in payload
    assert "viewer" in payload


def test_projection_endpoint_404_for_missing_job(client):
    response = client.post(
        "/api/jobs/not-a-real-job/projection",
        json={"x_factor_delta_deg": 6, "head_stability_delta_norm": 0.06},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_jobs_api.py::test_projection_endpoint_returns_projected_viewer tests/test_jobs_api.py::test_projection_endpoint_404_for_missing_job -v`  
Expected: FAIL because the route does not exist.

- [ ] **Step 3: Implement the projection route and wire it into FastAPI**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class ProjectionPayload(BaseModel):
    x_factor_delta_deg: float = 0.0
    head_stability_delta_norm: float = 0.0


@router.post("/{job_id}/projection")
async def project_job(job_id: str, payload: ProjectionPayload):
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    ...
```

- [ ] **Step 4: Run focused API tests**

Run: `python -m pytest tests/test_jobs_api.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/api/projection.py server/main.py tests/test_jobs_api.py
git commit -m "feat: add swing projection endpoint"
```

### Task 3: Replace the Fake Viewer With a Real 3D Scene

**Files:**
- Create: `frontend/src/components/SwingSkeletonViewer.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/components/HipShoulderDiagram.tsx`

- [ ] **Step 1: Add a failing viewer acceptance test or explicit verification target**

Use this concrete verification target for the task:

```text
Viewer page must render a <canvas> for the swing scene, must not use the main annotated <video> player, must fit inside a 1366x900 desktop viewport without document scroll, and must support play/pause/scrub/camera reset.
```

- [ ] **Step 2: Install Three.js**

Run: `npm install three`  
Expected: `three` is added to `frontend/package.json`.

- [ ] **Step 3: Implement a minimal skeleton renderer**

```tsx
export function SwingSkeletonViewer({ data, currentFrame, playing, speed }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    ...
    return () => renderer.dispose();
  }, []);

  return <div ref={mountRef} className="h-full w-full" />;
}
```

- [ ] **Step 4: Replace the left-column video with the new 3D viewer and make the layout no-scroll**

```tsx
<div className="h-[calc(100vh-64px)] overflow-hidden grid grid-cols-1 lg:grid-cols-[minmax(0,1.4fr)_420px]">
  <SwingSkeletonViewer ... />
  <aside className="h-full overflow-hidden">...</aside>
</div>
```

- [ ] **Step 5: Fix HipShoulderDiagram to use 3D geometry instead of fake confidence**

```tsx
function axisAngle3D(kp: number[][], a: number, b: number): number | null {
  const pa = kp[a];
  const pb = kp[b];
  if (!pa || !pb || !Number.isFinite(pa[0]) || !Number.isFinite(pb[0])) return null;
  return Math.atan2(pb[2] - pa[2], pb[0] - pa[0]) * (180 / Math.PI);
}
```

- [ ] **Step 6: Build the frontend**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/src/components/SwingSkeletonViewer.tsx frontend/src/pages/SwingViewerPage.tsx frontend/src/components/HipShoulderDiagram.tsx
git commit -m "feat: replace fake viewer with real 3d swing scene"
```

### Task 4: Make What If Update the Rendered Swing and Projected Outcomes

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/WhatIfSimulator.tsx`
- Modify: `frontend/src/pages/SwingViewerPage.tsx`

- [ ] **Step 1: Add the frontend projection API types**

```ts
export interface ProjectionResponse {
  baseline: {
    exit_velocity_mph: number;
    carry_distance_ft: number;
    score: number;
  };
  projection: {
    exit_velocity_mph: number;
    carry_distance_ft: number;
    score: number;
    notes: string[];
  };
  viewer: Swing3DData;
}

export async function projectSwing(jobId: string, payload: {
  x_factor_delta_deg: number;
  head_stability_delta_norm: number;
}): Promise<ProjectionResponse> {
  ...
}
```

- [ ] **Step 2: Rework WhatIfSimulator into a release-driven control surface**

```tsx
<input
  type="range"
  onChange={(e) => setDraft(Number(e.target.value))}
  onMouseUp={commitProjection}
  onTouchEnd={commitProjection}
/>
```

- [ ] **Step 3: Wire projection results back into the viewer page**

```tsx
const [activeViewerData, setActiveViewerData] = useState<Swing3DData | null>(null);
const [projection, setProjection] = useState<ProjectionResponse["projection"] | null>(null);

const handleProjection = async (input: ProjectionInput) => {
  const requestId = ++latestRequestId.current;
  const result = await projectSwing(jobId, input);
  if (requestId !== latestRequestId.current) return;
  setActiveViewerData(result.viewer);
  setProjection(result.projection);
};
```

- [ ] **Step 4: Add reset behavior and baseline/projected summaries**

```tsx
<button onClick={resetProjection}>Reset projection</button>
<dl>
  <div><dt>Baseline EV</dt><dd>{baseline.exit_velocity_mph}</dd></div>
  <div><dt>Projected EV</dt><dd>{projection?.exit_velocity_mph ?? baseline.exit_velocity_mph}</dd></div>
</dl>
```

- [ ] **Step 5: Build the frontend again**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/components/WhatIfSimulator.tsx frontend/src/pages/SwingViewerPage.tsx
git commit -m "feat: connect what-if simulation to projected swing viewer"
```

### Task 5: Verify End-to-End and Harden Error States

**Files:**
- Modify: `frontend/src/pages/SwingViewerPage.tsx`
- Modify: `frontend/src/components/WhatIfSimulator.tsx`
- Modify: `tests/test_projection.py`
- Modify: `tests/test_jobs_api.py`

- [ ] **Step 1: Add targeted failure-state tests**

```python
def test_projection_endpoint_rejects_missing_artifacts(...):
    ...


def test_projection_estimator_handles_zero_velocity_baseline():
    ...
```

- [ ] **Step 2: Add compact UI fallbacks for projection and WebGL failures**

```tsx
{projectionError ? <p className="text-xs text-[var(--color-red)]">{projectionError}</p> : null}
{viewerError ? <div>Interactive 3D view unavailable</div> : <SwingSkeletonViewer ... />}
```

- [ ] **Step 3: Run the full backend suite**

Run: `python -m pytest`  
Expected: PASS

- [ ] **Step 4: Run the frontend build**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 5: Verify in the browser with the real job fixture**

Use the checked-in fixture-backed local job and optionally smoke-test a live completed job. Verify:

```text
1. Viewer renders a 3D skeleton scene.
2. No document-level vertical scroll at 1366x900.
3. Hip vs Shoulder diagram renders.
4. Releasing a What If slider updates projected EV/carry and the visible swing pose.
5. Reset returns to baseline.
6. A rapid second slider release wins over the first response.
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/SwingViewerPage.tsx frontend/src/components/WhatIfSimulator.tsx tests/test_projection.py tests/test_jobs_api.py
git commit -m "fix: harden swing viewer states and verification"
```

## Self-Review

- Spec coverage: the plan covers truthful viewer replacement, hip/shoulder fix, backend projection, What If wiring, and verification.
- Placeholder scan: no TODO/TBD markers remain.
- Type consistency: the projection API uses `ProjectionResponse`, `ProjectionRequest`, `head_stability_delta_norm`, and `Swing3DData` consistently across backend/frontend tasks.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-25-swing-viewer-truthful-3d.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

User preference already established in this session: proceed autonomously. Use Subagent-Driven execution with review gates.
