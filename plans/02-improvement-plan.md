# Baseball Swing Analyzer — Improvement Plan

This document is a self-contained, ordered task list for a low-context implementer. Each task has:
- **Problem** — what is wrong, with file paths and line numbers
- **Fix** — exact change, with before/after snippets where useful
- **Acceptance** — how to verify it worked
- **Depends on** — task IDs that must be done first

Work the tasks in numerical order unless `Depends on` says otherwise. Do NOT skip the acceptance step. Run the existing test suite (`pytest`) after every backend task; run `npm run build` (in `frontend/`) after every frontend task.

Repository root: `C:/Users/yashk/baseball_swing_analyzer/`

---

## Phase 0 — Inventory & guardrails (do first)

### Task 0.1 — Snapshot the current state
**Problem:** Future tasks will delete files. We need a baseline.
**Fix:**
1. From repo root, run `pytest -q` and record pass count. Should be ≥61 passing.
2. Run `cd frontend && npm run build`. Should succeed.
3. `git status` — confirm clean working tree, then `git checkout -b improvement-plan`.

**Acceptance:** New branch exists, baseline test/build pass counts noted in commit message of an empty commit `chore: baseline before improvement plan`.

---

## Phase 1 — Server consolidation (the biggest issue)

There are TWO server entry points. The frontend uses `server/main.py` (synchronous, holds a 30s HTTP request). The async router code in `server/api/*.py` + `server/db.py` + `server/tasks/analyze.py` is fully written but never registered. We will keep the async stack and delete the synchronous one.

### Task 1.1 — Wire the async routers into `server/main.py`
**Problem:** Routers in `server/api/upload.py`, `status.py`, `results.py`, `artifacts.py` are never imported by anything.
**Fix:** Replace the entire body of `server/main.py` with:

```python
"""FastAPI app — async job queue. Upload → poll status → fetch results."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server import db
from server.api import upload, status, results, artifacts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="SwingMetrics API", version="0.2.0", lifespan=lifespan)

_allowed_origins = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(upload.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(status.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(results.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(artifacts.router, prefix="/api/jobs", tags=["jobs"])
```

**Acceptance:**
- `uvicorn server.main:app --reload` starts without errors.
- `curl http://localhost:8000/docs` shows endpoints `POST /api/jobs/`, `GET /api/jobs/{job_id}`, `GET /api/jobs/{job_id}/results`, `GET /api/jobs/{job_id}/artifacts/{filename}`.
- The old `/api/analyze` endpoint NO LONGER exists.

**Depends on:** 0.1

### Task 1.2 — Consolidate the ThreadPoolExecutor
**Problem:** `server/db.py:31` and `server/api/upload.py:12` both create a `ThreadPoolExecutor(max_workers=2)`. Two pools, redundant.
**Fix:**
1. In `server/api/upload.py`, delete lines 4 (`from concurrent.futures import ThreadPoolExecutor`) and 12 (`_executor = ...`).
2. Replace line 41 (`_executor.submit(run_analysis, job_id)`) with `db.run_analysis_in_thread(job_id)`.
3. Confirm `server/db.py` already exports `run_analysis_in_thread` (it does, at line 90).

**Acceptance:** `grep -rn "ThreadPoolExecutor" server/` returns exactly one match (in `db.py`).

**Depends on:** 1.1

### Task 1.3 — Stop double-loading keypoints from disk
**Problem:** `analyze_swing` writes `keypoints.npy` to disk; `server/tasks/analyze.py:69-71` immediately reads it back. Wasteful round-trip.
**Fix:**
1. Modify `src/baseball_swing_analyzer/analyzer.py`'s `analyze_swing` to embed the keypoints in the returned dict under key `_keypoints_seq` (a numpy array, NOT serialized). Also embed the full `phase_labels` (already there).
   ```python
   # at the end of analyze_swing, after `report["flags"] = ...`
   report["_keypoints_seq"] = keypoints_seq
   ```
2. The `np.save(...)` call at line 116 STAYS (the CLI uses it). But it's now optional context, not the source of truth.
3. In `server/tasks/analyze.py`, replace lines 67-78 (`from baseball_swing_analyzer.export_3d ...` block) with:
   ```python
   from baseball_swing_analyzer.export_3d import generate_swing_3d_data_from_keypoints

   keypoints_seq = result.pop("_keypoints_seq")
   phase_labels = result.get("phase_labels", [])
   fps = result.get("fps", 30.0)
   frame_data = generate_swing_3d_data_from_keypoints(
       keypoints_seq, phase_labels, fps, report=result
   )
   ```
4. `result` is then JSON-serialized for the DB; since we popped `_keypoints_seq` it serializes cleanly.
5. Remove the now-dead `else: frame_data = generate_swing_3d_data(result)` branch (line 78).

**Acceptance:**
- `grep -rn "keypoints.npy" server/` returns no matches.
- E2E: upload a video, poll status, fetch results — `frames_3d` field is populated.

**Depends on:** 1.1

### Task 1.4 — Delete the synchronous `/api/analyze` legacy code
**Problem:** Already replaced by Task 1.1. The old code is gone if 1.1 was done correctly. This task is a verification.
**Fix:** Confirm `grep -n "/api/analyze" server/main.py` returns nothing.
**Acceptance:** No matches.
**Depends on:** 1.1

### Task 1.5 — Stream uploads, enforce max size
**Problem:** `server/api/upload.py:32` reads the entire upload into memory before writing. A 500MB phone video OOMs the worker.
**Fix:** Replace `server/api/upload.py` body with:

```python
"""Upload endpoint — stream video to disk, create job, queue analysis."""

import os
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from .. import db
from ..tasks.analyze import UPLOAD_DIR, OUTPUT_DIR

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 500 * 1024 * 1024))
ALLOWED_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

router = APIRouter()


@router.post("/")
async def create_job(video: UploadFile = File(...)):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = video.filename or "video.mp4"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Unsupported extension: {ext}")

    job_id = db.create_job(
        original_filename=filename, video_path="", output_dir=""
    )
    saved_path = UPLOAD_DIR / f"{job_id}{ext}"

    bytes_written = 0
    with open(saved_path, "wb") as f:
        while chunk := await video.read(1 << 20):  # 1 MiB
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                f.close()
                saved_path.unlink(missing_ok=True)
                db.update_job(job_id, status="failed",
                              error_message=f"File exceeds {MAX_UPLOAD_BYTES} bytes")
                raise HTTPException(413, "File too large")
            f.write(chunk)

    out_dir = OUTPUT_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    db.update_job(job_id, video_path=str(saved_path), output_dir=str(out_dir))
    db.run_analysis_in_thread(job_id)
    return {"job_id": job_id, "status": "queued"}
```

**Acceptance:**
- Uploading a 600MB file (use `dd if=/dev/urandom of=big.mp4 bs=1M count=600`) returns HTTP 413.
- Uploading a `.txt` file returns HTTP 400.
- Normal MP4 upload still works.

**Depends on:** 1.2

### Task 1.6 — Stop dumping `frames_3d` into the SQLite TEXT column
**Problem:** `server/tasks/analyze.py:91` stores `frames_3d_json` (often >500KB) in SQLite. Then `server/api/results.py:21` re-parses it on every request. The same data is also written to `frames_3d.json` on disk. Three copies.
**Fix:**
1. In `server/db.py`, drop `frames_3d_json` from the `_SCHEMA` (delete line `frames_3d_json TEXT,`).
2. In `server/tasks/analyze.py`:
   - Keep the `(out_dir / "frames_3d.json").write_text(...)` line.
   - Remove `frames_3d_json=frames_3d_json,` from the `db.update_job(...)` call.
3. In `server/api/results.py`, replace lines 19-27 with:
   ```python
   metrics = json.loads(job["metrics_json"]) if job["metrics_json"] else None
   return {
       "job_id": job["id"],
       "status": job["status"],
       "metrics": metrics,
       "coaching": metrics.pop("_coaching_lines", None) if metrics else None,
       "frames_3d_url": f"/api/jobs/{job['id']}/artifacts/frames_3d.json",
   }
   ```
4. Delete the existing `jobs.db` file so the new schema applies on next start: `rm server/jobs.db`.

**Acceptance:**
- `/api/jobs/{id}/results` response is small (<5KB).
- `/api/jobs/{id}/artifacts/frames_3d.json` returns the 3D frame data.
- DB file size grows much slower per job.

**Depends on:** 1.3, 1.5

### Task 1.7 — Use a per-thread SQLite connection
**Problem:** `server/db.py:_get_conn` opens a fresh connection per call. Wasteful.
**Fix:** Replace `_get_conn` and `init_db` in `server/db.py`:

```python
import threading

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _local.conn = conn
    return conn
```

Remove `conn.close()` from every helper (`create_job`, `get_job`, `update_job`, `list_jobs`). Keep `conn.commit()`.

**Acceptance:** Tests still pass. `lsof | grep jobs.db` (or equivalent on Windows) shows ≤ N_workers connections, not one per request.

**Depends on:** 1.6

---

## Phase 2 — Frontend rewiring for async flow

### Task 2.1 — Add TanStack Query
**Problem:** `sessionStorage` + `location.state` are used for inter-page state. Refresh on `/results/:jobId` loses everything.
**Fix:**
1. `cd frontend && npm install @tanstack/react-query`.
2. In `frontend/src/main.tsx`, wrap `<App/>`:
   ```tsx
   import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
   const qc = new QueryClient();
   // <QueryClientProvider client={qc}><App/></QueryClientProvider>
   ```

**Acceptance:** `npm run build` passes.

**Depends on:** 0.1

### Task 2.2 — Rewrite `frontend/src/lib/api.ts` for async flow
**Problem:** Current `uploadAndAnalyze` posts to the deleted `/api/analyze`. Need: upload → poll status → fetch results.
**Fix:** Replace the entire file:

```typescript
const API_BASE = "/api/jobs";

export interface CoachingLine {
  tone: "good" | "warn" | "info";
  text: string;
}

export interface SwingMetrics {
  phase_durations: Record<string, number>;
  stride_plant_frame: number | null;
  contact_frame: number;
  hip_angle_at_contact: number;
  shoulder_angle_at_contact: number;
  x_factor_at_contact: number;
  spine_tilt_at_contact: number;
  left_knee_at_contact: number;
  right_knee_at_contact: number;
  head_displacement_total: number;
  wrist_peak_velocity_px_s: number;
  wrist_peak_velocity_normalized: number;  // px/s / torso_px (added in Task 4.2)
  pose_confidence_mean: number;            // added in Task 4.4
  frames: number;
  fps: number;
  phase_labels: string[];
  flags: {
    handedness: string;
    front_shoulder_closed_load: boolean;
    leg_action: string;
    finish_height: string;
    hip_casting: boolean;
    arm_slot_at_contact: string;
  };
}

export interface Frame3D {
  keypoints: number[][];
  phase: string;
  efficiency: number;
  velocities: Record<string, number>;
  velocity_vectors?: Record<string, number[]>;
}

export interface EnergyLossEvent {
  frame: number;
  joint: string;
  joint_index: number;     // added in Task 3.4
  type: string;
  magnitude_pct: number;
  description: string;
}

export interface Swing3DData {
  fps: number;
  total_frames: number;
  contact_frame: number;
  stride_plant_frame: number | null;
  phase_labels: string[];
  frames: Frame3D[];
  kinetic_chain_scores: { hip_to_shoulder: number; shoulder_to_hand: number; overall: number };
  energy_loss_events: EnergyLossEvent[];
  metrics: Record<string, number | string>;
  skeleton: [number, number][];
  keypoint_names: string[];
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  current_step: string | null;
  error_message: string | null;
}

export interface JobResults {
  job_id: string;
  status: "completed" | "failed";
  metrics: SwingMetrics | null;
  coaching: CoachingLine[] | null;
  frames_3d_url: string;
}

export async function uploadVideo(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("video", file);
  const res = await fetch(`${API_BASE}/`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/${jobId}`);
  if (!res.ok) throw new Error(`Status failed: ${res.statusText}`);
  return res.json();
}

export async function getJobResults(jobId: string): Promise<JobResults> {
  const res = await fetch(`${API_BASE}/${jobId}/results`);
  if (!res.ok) throw new Error(`Results failed: ${res.statusText}`);
  return res.json();
}

export async function getFrames3D(jobId: string): Promise<Swing3DData> {
  const res = await fetch(`${API_BASE}/${jobId}/artifacts/frames_3d.json`);
  if (!res.ok) throw new Error(`3D data failed: ${res.statusText}`);
  return res.json();
}

export function artifactUrl(jobId: string, filename: string): string {
  return `${API_BASE}/${jobId}/artifacts/${filename}`;
}
```

**Acceptance:** `tsc -b` (via `npm run build`) passes.

**Depends on:** 2.1, 1.6

### Task 2.3 — Rewrite `UploadPage.tsx` for queued upload
**Fix:** Replace contents of `frontend/src/pages/UploadPage.tsx`:

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadZone } from "@/components/UploadZone";
import { uploadVideo } from "@/lib/api";

export function UploadPage() {
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setIsUploading(true);
    try {
      const { job_id } = await uploadVideo(file);
      navigate(`/results/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-xl">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold tracking-tight">
            Swing<span className="text-[var(--color-accent)]">Metrics</span>
          </h1>
          <p className="mt-2 text-[var(--color-text-dim)]">
            Upload a baseball swing video for biomechanical analysis
          </p>
        </div>
        <UploadZone onFileSelected={handleFile} isUploading={isUploading} />
        {error && (
          <div className="mt-4 rounded-lg border border-[var(--color-red)] bg-[var(--color-red)]/10 p-3 text-sm text-[var(--color-red)]">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
```

**Acceptance:** Build passes. Selecting a file uploads it and navigates to `/results/<uuid>`.

**Depends on:** 2.2

### Task 2.4 — Rewrite `ResultsPage.tsx` to poll
**Fix:** Replace `frontend/src/pages/ResultsPage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { getJobStatus, getJobResults, artifactUrl, type SwingMetrics } from "@/lib/api";
import { Card, CardTitle } from "@/components/Card";
import { MetricCard } from "@/components/MetricCard";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import { FlagsPanel } from "@/components/FlagsPanel";
import { CoachingReport } from "@/components/CoachingReport";
import { VideoPlayer } from "@/components/VideoPlayer";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { ArrowLeft, Box } from "lucide-react";

const DISPLAY_METRICS: { key: keyof SwingMetrics; label: string }[] = [
  { key: "x_factor_at_contact", label: "X-Factor" },
  { key: "hip_angle_at_contact", label: "Hip Angle" },
  { key: "shoulder_angle_at_contact", label: "Shoulder Angle" },
  { key: "spine_tilt_at_contact", label: "Spine Tilt" },
  { key: "left_knee_at_contact", label: "L Knee Flex" },
  { key: "right_knee_at_contact", label: "R Knee Flex" },
  { key: "head_displacement_total", label: "Head Displace" },
  { key: "wrist_peak_velocity_normalized", label: "Peak Wrist Vel (norm)" },
];

export function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();

  const statusQuery = useQuery({
    queryKey: ["status", jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "completed" || s === "failed" ? false : 1500;
    },
  });

  const isReady = statusQuery.data?.status === "completed" || statusQuery.data?.status === "failed";

  const resultsQuery = useQuery({
    queryKey: ["results", jobId],
    queryFn: () => getJobResults(jobId!),
    enabled: !!jobId && isReady,
  });

  if (!jobId) return null;

  if (!isReady) {
    return <ProcessingStatus status={statusQuery.data} />;
  }

  if (statusQuery.data?.status === "failed" || resultsQuery.data?.status === "failed") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <p className="text-[var(--color-red)] font-medium">
            {statusQuery.data?.error_message || "Analysis failed."}
          </p>
          <Link to="/" className="mt-4 inline-block text-[var(--color-accent)] text-sm hover:underline">
            Try another video
          </Link>
        </Card>
      </div>
    );
  }

  const m = resultsQuery.data?.metrics;
  if (!m) return <div className="min-h-screen flex items-center justify-center">Loading…</div>;

  const videoSrc = artifactUrl(jobId, "annotated.mp4");

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <header className="border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-[var(--color-text-dim)] hover:text-[var(--color-text)]">
          <ArrowLeft className="h-4 w-4" /><span className="text-sm">New Analysis</span>
        </Link>
        <h1 className="text-lg font-semibold">Swing<span className="text-[var(--color-accent)]">Metrics</span></h1>
        <div className="w-24" />
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        <Card>
          <CardTitle>Phase Timeline</CardTitle>
          <PhaseTimeline phaseLabels={m.phase_labels} />
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--color-text-dim)]">
            <span>Stride plant: frame {m.stride_plant_frame ?? "—"}</span>
            <span>Contact: frame {m.contact_frame}</span>
            <span>Total: {m.frames} frames @ {m.fps.toFixed(1)} fps</span>
            <span>Pose confidence: {(m.pose_confidence_mean * 100).toFixed(0)}%</span>
          </div>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardTitle>Annotated Video</CardTitle>
              <VideoPlayer src={videoSrc} />
            </Card>
            <Card>
              <CardTitle>Qualitative Flags</CardTitle>
              <FlagsPanel flags={m.flags} />
            </Card>
            <CoachingReport lines={resultsQuery.data?.coaching ?? []} />
          </div>

          <div className="space-y-3">
            <CardTitle className="px-1">Key Metrics</CardTitle>
            <div className="grid grid-cols-1 gap-3">
              {DISPLAY_METRICS.map(({ key, label }) => {
                const val = m[key];
                return <MetricCard key={key as string} label={label} value={typeof val === "number" ? val : String(val)} metricKey={key as string} />;
              })}
            </div>
            <Link
              to={`/viewer/${jobId}`}
              className="mt-4 flex items-center justify-center gap-2 rounded-xl border-2 border-[var(--color-accent)] bg-[var(--color-accent)]/10 px-6 py-4 text-[var(--color-accent)] font-semibold hover:bg-[var(--color-accent)]/20"
            >
              <Box className="h-5 w-5" />
              Launch 3D Swing Viewer
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
```

**Acceptance:**
- Hard-refresh on `/results/<id>` while job is running shows `ProcessingStatus`.
- Once complete, page renders metrics.
- Refreshing after completion still works.

**Depends on:** 2.2

### Task 2.5 — Rewrite `SwingViewerPage.tsx` to fetch on mount
**Problem:** Currently relies on `location.state.data.frames_3d` from `<Link state={...}>`. Direct URL access shows error.
**Fix:** Replace `frontend/src/pages/SwingViewerPage.tsx` to use `getFrames3D(jobId)` via `useQuery` instead of reading from `location.state`. Keep all the existing render logic; only swap the data source.

```tsx
// at top
import { useQuery } from "@tanstack/react-query";
import { getFrames3D } from "@/lib/api";

// replace the useLocation lines with:
const dataQuery = useQuery({
  queryKey: ["frames3d", jobId],
  queryFn: () => getFrames3D(jobId!),
  enabled: !!jobId,
});
const data = dataQuery.data;

// replace the !data branch:
if (!data) {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <Card className="max-w-md">
        <p>{dataQuery.isLoading ? "Loading 3D data…" : "Failed to load 3D data."}</p>
        <Link to={jobId ? `/results/${jobId}` : "/"} className="mt-4 inline-block text-[var(--color-accent)] hover:underline">Back to Results</Link>
      </Card>
    </div>
  );
}
```

Also change the `<Link to={`/viewer/${jobId}`} state={{ data }}>` in `ResultsPage.tsx` (already done in Task 2.4 — `state` prop removed).

**Acceptance:** Direct navigation to `/viewer/<id>` works without going through results first.

**Depends on:** 2.2, 2.4

### Task 2.6 — Wire `ProcessingStatus` to live data
**Problem:** Component exists but wasn't used.
**Fix:** Open `frontend/src/components/ProcessingStatus.tsx` and confirm it accepts a `status` prop matching `JobStatus`. If not, refactor it to:

```tsx
import { type JobStatus } from "@/lib/api";

interface Props { status: JobStatus | undefined }

export function ProcessingStatus({ status }: Props) {
  const pct = Math.round((status?.progress ?? 0) * 100);
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <h2 className="text-2xl font-semibold">Analyzing swing…</h2>
        <p className="mt-2 text-sm text-[var(--color-text-dim)]">{status?.current_step ?? "queued"}</p>
        <div className="mt-6 h-2 w-full rounded-full bg-[var(--color-surface-2)] overflow-hidden">
          <div className="h-full rounded-full bg-[var(--color-accent)] transition-all" style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-1 text-xs text-[var(--color-text-dim)]">{pct}%</p>
      </div>
    </div>
  );
}
```

**Acceptance:** While a job runs, the progress bar moves through queued → detecting_hitter → computing_metrics → generating_coaching → generating_3d_data.

**Depends on:** 2.2, 2.4

### Task 2.7 — Replace HTML coaching with structured array
**Problem:** Backend wraps lines in `<p>` and the frontend strips them with regex.
**Fix:**
1. In `src/baseball_swing_analyzer/ai/knowledge.py`, change `generate_static_report` return type from `list[str]` to `list[dict[str, str]]` where each item is `{"tone": "good" | "warn" | "info", "text": "..."}`. Most existing cues are corrections → `tone: "warn"`; the "Swing mechanics look solid" fallback → `tone: "good"`. Tag each existing rule with its tone in-place.
2. In `server/tasks/analyze.py`, replace lines 59-62 with:
   ```python
   coaching_lines = generate_static_report(result)
   result["_coaching_lines"] = coaching_lines  # carries through metrics_json
   (out_dir / "coaching.md").write_text(
       "\n".join(f"- [{c['tone']}] {c['text']}" for c in coaching_lines), encoding="utf-8"
   )
   ```
   Remove the `coaching_html=` parameter from the final `db.update_job` call.
3. In `server/db.py`, remove the `coaching_html TEXT,` column from `_SCHEMA`. Delete `server/jobs.db` again so the schema applies.
4. In `server/api/results.py`, the `coaching` field is already pulled from `metrics._coaching_lines` (Task 1.6).
5. In `frontend/src/components/CoachingReport.tsx`, replace contents:

```tsx
import { Card } from "@/components/Card";
import type { CoachingLine } from "@/lib/api";

const DOT_COLOR: Record<string, string> = {
  good: "bg-[var(--color-accent)]",
  warn: "bg-[var(--color-amber)]",
  info: "bg-[var(--color-text-dim)]",
};

export function CoachingReport({ lines }: { lines: CoachingLine[] }) {
  if (!lines || lines.length === 0) {
    return (
      <Card>
        <p className="text-[var(--color-text-dim)]">No coaching report available.</p>
      </Card>
    );
  }
  return (
    <Card>
      <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
        Coaching Report
      </h3>
      <ul className="space-y-2">
        {lines.map((line, i) => (
          <li key={i} className="flex items-start gap-2 animate-fade-in-up" style={{ animationDelay: `${i * 60}ms` }}>
            <span className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${DOT_COLOR[line.tone] ?? DOT_COLOR.info}`} />
            <span className="text-sm">{line.text}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
```

**Acceptance:** Coaching cards render with correct color dots; no HTML in network response.

**Depends on:** 1.6, 2.4

---

## Phase 3 — Pipeline correctness fixes

### Task 3.1 — Fix the fps drift in `analyzer.py`
**Problem:** `analyzer.py:103` passes downsampled fps to `classify_phases` but `analyzer.py:104` passes original fps to `build_report`. Wrist velocity is computed at the wrong rate.
**Fix:** In `src/baseball_swing_analyzer/analyzer.py`, compute the effective fps once and pass it everywhere:

```python
# in analyze_swing, after `indices = _subsample_indices(...)`:
stride = max(1, round(props.fps / _TARGET_ANALYSIS_FPS))
effective_fps = props.fps / stride  # the actual sampling rate of keypoints_seq

# replace the two calls:
phase_labels = classify_phases(keypoints_seq, fps=effective_fps)
report = build_report(phase_labels, keypoints_seq, effective_fps)
```

**Acceptance:**
- Add a unit test in `tests/test_analyzer.py` that builds a synthetic 60fps video with a known wrist trajectory and asserts `report["wrist_peak_velocity_px_s"]` matches the analytical value within 5%.
- Run on a real 60fps phone video; reported velocity should roughly halve compared to before (which was 2× too high).

**Depends on:** 1.3

### Task 3.2 — Normalize px-based metrics by torso length
**Problem:** `wrist_peak_velocity_px_s < 1500` and `lift > 30` are resolution-dependent. A 4K video and a 1080p video of the same swing get different verdicts.
**Fix:**
1. Add to `src/baseball_swing_analyzer/metrics.py`:
   ```python
   def torso_length_px(keypoints_seq: np.ndarray) -> float:
       """Median shoulder-mid → hip-mid distance across the sequence (pixels)."""
       seq = np.asarray(keypoints_seq, dtype=float)
       sh_mid = (seq[:, COCO_LS, :2] + seq[:, COCO_RS, :2]) / 2
       hp_mid = (seq[:, COCO_LH, :2] + seq[:, COCO_RH, :2]) / 2
       d = np.linalg.norm(sh_mid - hp_mid, axis=1)
       d = d[d > 1.0]
       return float(np.median(d)) if len(d) else 100.0
   ```
2. In `src/baseball_swing_analyzer/reporter.py`'s `build_report`, after computing `wrist_peak_velocity_px_s`, add:
   ```python
   from .metrics import torso_length_px
   torso_px = torso_length_px(keypoints_seq)
   report["torso_length_px"] = torso_px
   report["wrist_peak_velocity_normalized"] = report["wrist_peak_velocity_px_s"] / max(torso_px, 1.0)
   # units: torso-lengths per second
   ```
3. In `src/baseball_swing_analyzer/ai/flags.py`, in `leg_kick_or_toe_tap`, replace `lift > 30` / `lift > 5` with `lift > torso * 0.15` / `lift > torso * 0.025`. Compute `torso = torso_length_px(keypoints_seq)` at the top.
4. In `src/baseball_swing_analyzer/ai/knowledge.py`, change the `wrist_peak_velocity_px_s` rule to use `wrist_peak_velocity_normalized`. Calibrate threshold (`< 5.0` torso/s is a reasonable starting point — tune empirically).

**Acceptance:**
- Same video at 1080p and 540p downsample produces (within 10%) the same `wrist_peak_velocity_normalized`.
- Existing tests still pass; update assertions in `test_metrics.py` if they hardcoded torso-naive thresholds.

**Depends on:** 3.1

### Task 3.3 — Fix `phase_durations` to count contiguous runs only
**Problem:** `metrics.py:phase_durations` uses `Counter` — non-contiguous repeats get summed. Coaching wants the contiguous duration.
**Fix:** Replace the function:
```python
def phase_durations(phase_labels: list[str]) -> dict[str, int]:
    """Length of the longest contiguous run per phase label."""
    if not phase_labels:
        return {}
    out: dict[str, int] = {}
    i = 0
    while i < len(phase_labels):
        j = i
        while j < len(phase_labels) and phase_labels[j] == phase_labels[i]:
            j += 1
        run = j - i
        out[phase_labels[i]] = max(out.get(phase_labels[i], 0), run)
        i = j
    return out
```

**Acceptance:** Update `tests/test_metrics.py`'s `phase_durations` test to expect the longest-run semantic. Run `pytest tests/test_metrics.py`.

**Depends on:** none

### Task 3.4 — Fix the joint→keypoint-index mapping in `frames_3d`
**Problem:** `frontend/src/pages/SwingViewerPage.tsx:65` does `e.joint.replace("_", "")` which produces `"leftwrist"` etc., not in `keypoint_names`. Markers drop to origin.
**Fix:** Backend should send the index. In `src/baseball_swing_analyzer/energy.py`, in `detect_energy_loss_events`:

```python
JOINT_TO_KEYPOINT_IDX = {
    "right_wrist": 10,
    "left_wrist": 9,
    "right_elbow": 8,
    "left_elbow": 7,
    "hip_center": 12,  # use right_hip as proxy for the hip midpoint location
    "shoulder_center": 6,
}
# in the loop, when building the event dict:
events.append({
    "frame": t,
    "joint": name,
    "joint_index": JOINT_TO_KEYPOINT_IDX.get(name, -1),
    ...
})
```

In `frontend/src/pages/SwingViewerPage.tsx`, replace lines 60-68:
```tsx
const eventsInRange = data.energy_loss_events
  .filter((e) => Math.abs(e.frame - currentFrame) < 3)
  .map((e) => {
    const f = data.frames[e.frame] ?? frame;
    const kp = e.joint_index >= 0 ? f.keypoints[e.joint_index] : [0, 0, 0];
    return { ...e, position: kp as [number, number, number] };
  });
```

**Acceptance:** Click an energy-loss event in the side panel; the marker appears on the correct joint.

**Depends on:** 1.3

### Task 3.5 — Add pose-confidence gating
**Problem:** RTMPose returns per-keypoint scores in `keypoints_seq[:, :, 2]`. They're stored but never checked.
**Fix:**
1. In `src/baseball_swing_analyzer/reporter.py`, in `build_report`, add:
   ```python
   conf = keypoints_seq[:, :, 2]
   report["pose_confidence_mean"] = float(conf[conf > 0].mean()) if (conf > 0).any() else 0.0
   ```
2. In `src/baseball_swing_analyzer/ai/knowledge.py`, prepend to `generate_static_report`:
   ```python
   pcm = metrics.get("pose_confidence_mean", 1.0)
   if pcm < 0.4:
       return [{"tone": "warn", "text": (
           f"Pose detection confidence is low ({pcm*100:.0f}%). "
           "Results may be unreliable — try a video with better lighting, "
           "less occlusion, or the full body in frame."
       )}]
   ```

**Acceptance:** A heavily-occluded video produces a single warning instead of false metric verdicts.

**Depends on:** 2.7

### Task 3.6 — Decide YOLOv8n vs YOLOv8l and remove the unused weights
**Problem:** `detection.py:15` loads `yolov8n.pt` but `yolov8l.pt` (84MB) sits unused at the repo root. CLAUDE.md claims the latter is in use.
**Fix (pick one):**
- **Option A (default):** Keep YOLOv8n (faster). Delete `yolov8l.pt` from the repo root: `rm yolov8l.pt`. Update `CLAUDE.md` to say "YOLOv8n".
- **Option B:** Switch to YOLOv8l. Change `detection.py:15` to `_model = YOLO("yolov8l.pt")`. Move `yolov8l.pt` into `models/`. Delete `yolov8n.pt`.

Take Option A unless benchmarking shows YOLOv8n misses the hitter.

**Acceptance:** Repo root no longer has both `.pt` files. CLAUDE.md matches the loaded model.

**Depends on:** none

---

## Phase 4 — Frontend polish

### Task 4.1 — Drive 3D animation from `useFrame`, not React state
**Problem:** `SwingViewerPage.tsx:31-34` runs `setInterval(..., 1000/fps)`. At 60fps × 2x speed = 8ms intervals → React re-renders the whole `<Canvas>` subtree continuously.
**Fix:**
1. Move the playback clock inside the Canvas. Add a child component:

```tsx
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";

function FrameClock({ fps, speed, isPlaying, totalFrames, onTick }: {
  fps: number; speed: number; isPlaying: boolean; totalFrames: number;
  onTick: (frame: number) => void;
}) {
  const accum = useRef(0);
  const frame = useRef(0);
  useFrame((_, delta) => {
    if (!isPlaying) return;
    accum.current += delta * fps * speed;
    if (accum.current >= 1) {
      const advance = Math.floor(accum.current);
      accum.current -= advance;
      frame.current = (frame.current + advance) % totalFrames;
      onTick(frame.current);
    }
  });
  return null;
}
```

2. Replace the existing `useEffect`+`setInterval` block with `<FrameClock fps={data.fps} ...onTick={setCurrentFrame}/>` inside the `<Canvas>`.

**Acceptance:** Playback at 2x is smooth; React DevTools shows render counts on the page component dropping dramatically.

**Depends on:** 2.5

### Task 4.2 — Memoize `BatterFigure` joints with refs
**Problem:** `BatterFigure.tsx:32` rebuilds 17 `THREE.Vector3` instances per frame.
**Fix:** Use `useRef` to a flat array of meshes, then `mesh.position.set(x, y, z)` inside `useFrame`. Skeleton lines: use `<line>` with a ref to the geometry's position attribute and update it in place. This is a non-trivial refactor — if pressed for time, just memoize positions per `frame.phase` change instead of every render.

**Acceptance:** No new `Vector3` allocations during steady-state playback (verified via Performance profiler showing stable heap).

**Depends on:** 4.1

### Task 4.3 — Mobile-friendly upload & viewer
**Problem:** Phone is the primary capture device. Currently:
- File input has no `capture` attribute → on mobile it goes to the file picker, not the camera.
- 3D viewer's `lg:grid-cols-[1fr_320px]` stacks the side panel awkwardly on small screens.

**Fix:**
1. In `frontend/src/components/UploadZone.tsx`, change the input:
   ```tsx
   <input ref={inputRef} type="file" accept="video/*" capture="environment" onChange={handleChange} className="hidden" />
   ```
2. In `SwingViewerPage.tsx`, wrap the side panel in a collapsible drawer on mobile (`lg:hidden` toggle button + a fixed bottom sheet with `lg:static` for desktop). Minimum: ensure the Canvas gets `min-h-[60vh]` on small screens so it's actually visible.

**Acceptance:** On a phone, tapping the upload zone offers "Take video" as well as "Choose file". 3D viewer is usable in portrait.

**Depends on:** 2.3

### Task 4.4 — Tailwind v4 theme tokens
**Problem:** `bg-[var(--color-bg)]` everywhere — repetitive. Tailwind v4 supports `@theme` to bind CSS vars to utility classes.
**Fix:** In `frontend/src/index.css`, add (after the existing `:root` block):
```css
@theme {
  --color-bg: var(--color-bg);
  --color-surface: var(--color-surface);
  --color-surface-2: var(--color-surface-2);
  --color-text: var(--color-text);
  --color-text-dim: var(--color-text-dim);
  --color-accent: var(--color-accent);
  --color-amber: var(--color-amber);
  --color-red: var(--color-red);
  --color-border: var(--color-border);
}
```
Then bulk-replace `bg-[var(--color-X)]` → `bg-X`, `text-[var(--color-X)]` → `text-X`, etc. across `frontend/src/`.

**Acceptance:** No remaining `var(--color-` strings inside `className=""` attributes.

**Depends on:** 2.7

---

## Phase 5 — Honesty about "3D"

### Task 5.1 — Either wire a real 3D lifter or rebrand
**Problem:** `lifter.py:_lift_heuristic` invents Z values from hardcoded constants. The "kinetic chain efficiency" and "energy loss" numbers are computed on these fake depths and shown to the user as quantitative scores. The MotionBERT branch imports `mbert.models.MotionTransformer` which is not a real package.
**Fix (pick one):**
- **Option A — Use MediaPipe Pose for real 3D Z (recommended):**
  1. `pip install mediapipe`.
  2. Add a new `src/baseball_swing_analyzer/lifter_mp.py` that runs `mp.solutions.pose.Pose(static_image_mode=False)` per frame, extracts the 33-point pose with Z, remaps to the 17 COCO indices used elsewhere, and returns `(T, 17, 3)`.
  3. In `lifter.py`, make `lift_to_3d` try `lifter_mp.lift_to_3d` first, fall back to heuristic with a clear warning logged.
- **Option B — Rebrand:**
  1. Rename `SwingViewerPage` heading from "3D Swing Viewer" to "Stylized Pose Viewer".
  2. Add a banner: *"Depth is estimated from 2D heuristics — quantitative depth metrics are not available. View this as a stylized rendering of the 2D pose."*
  3. Remove `kinetic_chain_scores` and `energy_loss_events` from the UI, OR caveat them clearly as 2D-derived signals.

**Acceptance:** User is no longer shown fabricated 3D scores as if they were measured.

**Depends on:** 2.5

### Task 5.2 — Replace ad-hoc kinetic chain score with calibrated direction indicator
**Problem:** `energy.py:111-114` computes `0.5 + lag * 0.15` and presents it as a percentage. It's not calibrated against any reference data.
**Fix:**
1. Change the return type of `compute_kinetic_chain_scores` to:
   ```python
   {
       "hip_to_shoulder": {"lag_frames": int, "direction": "leads" | "trails" | "synced"},
       "shoulder_to_hand": {"lag_frames": int, "direction": "leads" | "trails" | "synced"},
   }
   ```
   `"leads"` if lag ≥ 1, `"trails"` if ≤ -1, `"synced"` otherwise.
2. Update the frontend's `EfficiencyBar` to render direction indicators instead of percent bars (✓ leads, ✗ trails, − synced).
3. Update `Swing3DData` interface in `frontend/src/lib/api.ts` accordingly.

**Acceptance:** No fake percentage scores in the UI. Direction is reported as discrete categories backed by clear mathematical definitions.

**Depends on:** 5.1

---

## Phase 6 — Documentation cleanup

### Task 6.1 — Update `CLAUDE.md` to match reality
**Fix:** In `CLAUDE.md`:
- Change "YOLOv8l" to whatever Task 3.6 settled on.
- Change "3D lifting: Deferred to Phase 2" to reflect the chosen Option A or B from Task 5.1.
- Remove the "Build Status" lies — write current truth.
- Add a "Server" section listing the async-job endpoints.

### Task 6.2 — Mark `ARCHITECTURE_AUDIT.md` as historical
**Fix:** Rename to `ARCHITECTURE_AUDIT_2026-04-24.md` and add a header:
```markdown
> Historical document — written before the async server, frontend, and 3D viewer
> were added. Retained for reference only. See README.md for current state.
```

### Task 6.3 — Update README with the new flow
**Fix:** README should describe:
1. How to start the backend: `uvicorn server.main:app --reload`.
2. How to start the frontend: `cd frontend && npm run dev`.
3. The async upload/poll/results flow at a high level.
4. Required env vars: `ALLOWED_ORIGINS`, `MAX_UPLOAD_BYTES`, `OLLAMA_API_KEY` (optional).

---

## Acceptance gate (run after every phase)

```bash
# from repo root
pytest -q                                    # Python tests
cd frontend && npm run build && cd ..        # Frontend type-check + build
ruff check src/ server/ || true              # Lint (advisory)
```

After Phase 2, run a manual E2E:
1. Start backend: `uvicorn server.main:app --reload`.
2. Start frontend: `cd frontend && npm run dev`.
3. Upload a real swing video.
4. Confirm progress bar advances; results page renders metrics; 3D viewer loads.
5. Hard-refresh on `/results/<id>` and `/viewer/<id>` — both still work.

If anything fails, fix before moving to the next phase.

---

## What is NOT in scope

These were considered and deliberately deferred:
- Replacing SQLite with a real job queue (Redis + RQ). SQLite + threads is fine until you have multiple uvicorn workers.
- Adding auth. Single-user local tool for now.
- ByteTrack, Kalman filter, BiLSTM phases — listed in `plan.md` Phase 2.
- Cloud LLM coaching wiring. Static rules are good enough for MVP.
- Multi-swing session DTW. `session.py` exists but the UI doesn't use it yet.

---

## Task summary table

| ID | Task | Phase | Effort |
|----|------|-------|--------|
| 0.1 | Snapshot baseline | 0 | 5 min |
| 1.1 | Wire async routers | 1 | 30 min |
| 1.2 | Consolidate ThreadPoolExecutor | 1 | 10 min |
| 1.3 | Stop disk round-trip for keypoints | 1 | 30 min |
| 1.4 | Verify legacy endpoint deleted | 1 | 2 min |
| 1.5 | Stream uploads + size limit | 1 | 30 min |
| 1.6 | Move frames_3d out of DB | 1 | 30 min |
| 1.7 | Per-thread SQLite connection | 1 | 20 min |
| 2.1 | Add TanStack Query | 2 | 5 min |
| 2.2 | Rewrite api.ts | 2 | 30 min |
| 2.3 | Rewrite UploadPage | 2 | 15 min |
| 2.4 | Rewrite ResultsPage with polling | 2 | 45 min |
| 2.5 | Rewrite SwingViewerPage to fetch | 2 | 30 min |
| 2.6 | Wire ProcessingStatus | 2 | 15 min |
| 2.7 | Structured coaching response | 2 | 45 min |
| 3.1 | Fix fps drift | 3 | 20 min |
| 3.2 | Normalize px metrics by torso | 3 | 45 min |
| 3.3 | Fix phase_durations | 3 | 15 min |
| 3.4 | Fix joint→index mapping | 3 | 20 min |
| 3.5 | Pose confidence gating | 3 | 20 min |
| 3.6 | YOLO model cleanup | 3 | 5 min |
| 4.1 | useFrame for 3D animation | 4 | 45 min |
| 4.2 | BatterFigure refs | 4 | 1 hr |
| 4.3 | Mobile UX | 4 | 1 hr |
| 4.4 | Tailwind theme tokens | 4 | 30 min |
| 5.1 | Real 3D lifter or rebrand | 5 | 2-4 hrs |
| 5.2 | Honest kinetic chain reporting | 5 | 30 min |
| 6.1 | Update CLAUDE.md | 6 | 15 min |
| 6.2 | Mark audit historical | 6 | 2 min |
| 6.3 | Update README | 6 | 30 min |

**Total estimated effort:** 12-15 hours of focused work.
