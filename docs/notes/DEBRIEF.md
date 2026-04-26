# Session Debrief — SLA / Hang Investigation

## Original problem
"Hangs after uploading a video."

## Root cause #1 (fixed, committed `6ed3419`, pushed)
`server/main.py` had `async def analyze(...)` calling the synchronous CPU-bound
`analyze_swing` directly on the asyncio event loop. While analysis ran the loop
was frozen — no other request, keepalive, or progress could be served, so the
browser appeared hung. Fix: drop `async`, read upload via `video.file.read()`.
FastAPI now offloads the route to its threadpool.

Verified live: 10 concurrent probes during an in-flight analyze returned in
1–50ms. Old behaviour would have queued them for the full duration.

## SLA goal
User wants total processing under 20s.

## Where the time was actually going (cold first request, 30-frame synthetic fixture)
- 5s — importing the analyzer module (cv2, ultralytics, rtmlib, scipy, ...)
- 15s — first-time loading YOLOX + RTMPose ONNX models
- 8s — actual per-frame inference (CPU)
- ~0s — metrics, coaching, 3D, JSON
- **Total ~29s on first request, ~8s on warm subsequent requests.**

## Misconception clarified
User asked to "use only cloud Ollama models, no local models." The local models
in this pipeline are not LLMs — they are YOLOX (person box) and RTMPose
(17-keypoint estimator). Cloud VLMs return prose, not numeric keypoint arrays
at sub-pixel precision, so they cannot replace these. Removing them breaks
every downstream metric. CLAUDE.md already codifies the split: pose stays
local; only the coaching/narrative LLM is cloud.

## Architectural change made by the user mid-session
`server/main.py` was rewritten from the synchronous endpoint to the async
job-queue version that mounts the existing `server/api/upload.py`,
`status.py`, `results.py`, `artifacts.py` routers under `/api/jobs`, with
analysis dispatched to a `ThreadPoolExecutor` and progress tracked in a
SQLite jobs table.

Frontend `frontend/src/lib/api.ts` still calls `/api/analyze` and
`/api/artifacts/{job_id}/{filename}` — **mismatched with the new backend**.
Will need updating to:
  - POST /api/jobs/ → returns {job_id}
  - GET  /api/jobs/{job_id} → status/progress
  - GET  /api/jobs/{job_id}/results → final metrics + coaching + 3D
  - GET  /api/jobs/{job_id}/artifacts/{filename} → annotated.mp4 etc.

## What I changed (in working tree, **not yet committed**)
1. `src/baseball_swing_analyzer/pose.py`
   - `_get_pose_model()` now requests `device="cuda"` when
     `CUDAExecutionProvider` is in `onnxruntime.get_available_providers()`,
     fallback to `cpu`.
2. `server/main.py`
   - Added `_warm_models()` + lifespan hook that imports the analyzer,
     instantiates YOLO + RTMPose Body, and runs one dummy frame through each
     to JIT-warm everything. Logs "Models warmed in Xs".
3. `src/baseball_swing_analyzer/reporter.py`
   - `write_metrics_json` now passes `default=str` to `json.dumps`. The new
     job-queue path called this function and crashed because `result` contains
     ndarray-typed values; the old synchronous endpoint had a `default=str`
     workaround inline.

## Environment quirks discovered
1. **pydantic / pydantic-core mismatch**: pydantic 2.12.5 needed
   pydantic-core 2.41.5 but 2.23.4 was installed. Fixed by
   `pip install --user pydantic-core==2.41.5`. (One-time, prerequisite for
   FastAPI to even import.)
2. **CUDA broken on this machine**:
   `onnxruntime.get_available_providers()` lists `CUDAExecutionProvider`, but
   creating a session with it fails:
   `Error loading "onnxruntime_providers_cuda.dll" which depends on
   "cublasLt64_12.dll" which is missing.` — onnxruntime 1.25.0 needs the
   CUDA 12 runtime; this machine has CUDA 13.2. So everything silently falls
   back to CPU. Warmup logs confirm CPU speeds (~13s first warmup, ~6s
   second warmup with OS-cached ONNX files).
3. **torch is CPU-only** (`2.11.0+cpu`). Even if we wanted ultralytics YOLO on
   GPU, it can't.

## Open issue blocking the SLA test (just hit)
After the warmup change, end-to-end via the new job-queue API failed
mid-run with `sqlite3.OperationalError: no such table: jobs`. The DB
**started** with the table (status polls returned 200 for ~12 calls, the job
row was clearly inserted), then the table disappeared. `jobs.db` ended up
4096 bytes (just SQLite header, no tables). I don't have a confirmed root
cause yet — candidates:
  - Windows + WAL + multiple connections from threadpool workers interacting
    badly. `db._get_conn()` opens a fresh connection per call and sets
    `PRAGMA journal_mode=WAL` each time.
  - Some import-time side effect (re-running `init_db` would NOT do it —
    schema uses `IF NOT EXISTS` and there is no DROP anywhere in the codebase).
  - File handle leak holding the WAL in a stale state.

After stopping the server, the .db files were "Device or resource busy" until
the uvicorn process fully terminated, suggesting the threadpool workers
held open handles.

## What might work for the DB issue
- Easiest: **drop WAL** — remove `PRAGMA journal_mode=WAL` in `db._get_conn`.
  Default rollback journal is fine for a single-process dev server and
  avoids the whole class of WAL-checkpoint-on-close issues on Windows.
- Defensive: have `_get_conn()` run `executescript(_SCHEMA)` every time
  (idempotent due to `IF NOT EXISTS`). Cheap insurance.
- Alternative: use a single long-lived connection guarded by a lock instead
  of open/close per call.

## What might work for the SLA (after the DB issue is fixed)
Best-case current capability (CPU-only, models pre-warmed):
  - Synthetic 30-frame fixture: ~8s end-to-end. **Under 20s.**
  - Real 30s phone video, 30fps → 506 frames after subsampling: ~8s × (506/30)
    ≈ 135s on CPU at ~0.27s/frame. **Way over 20s.**

Paths to hit 20s on a real video:
  1. **Get GPU working** (largest single win). Two sub-options:
     - Install onnxruntime-gpu wheel that targets CUDA 12, plus the CUDA 12
       runtime DLLs (`cublasLt64_12.dll`, `cudnn64_9.dll`) somewhere on PATH.
       Coexist with the system's CUDA 13.2 toolkit — DLL-search path issue,
       not a true install conflict.
     - Or wait for / find an onnxruntime build matching CUDA 13.x.
     Expected speedup: 3–5× per-frame on RTMPose (RTX 4070).
  2. **Smaller pose model**: switch `Body(mode='balanced')` to
     `mode='lightweight'` (uses RTMPose-s + YOLOX-tiny). Maybe 2–3× faster on
     CPU; some accuracy hit.
  3. **Subsample harder**: drop `_TARGET_ANALYSIS_FPS` from 15 to 5–8 fps.
     Linear speedup. Risk: contact frame timing precision degrades because
     contact events live on millisecond timescales.
  4. **Drop the redundant detector**: pose extraction in
     `pose.py:_get_pose_model` already includes YOLOX-m as `Body`'s internal
     detector, but `analyzer.py` *also* runs `ultralytics YOLOv8l` per frame
     before the crop. Two person-detectors per frame. Dropping the
     ultralytics pass would save ~30–40% of inference cost without any
     accuracy loss for the keypoints (RTMPose receives the same crop quality
     either way; the only thing lost is the persistent ByteTrack track id).
  5. **Cache the warmed model across processes** — already done via lifespan.

Cheapest combination likely sufficient: (4) + (3 → 8fps) gets a 30s real
video to ~20s on CPU. (1) makes everything trivially fast and is the right
long-term fix.

## Suggested next steps (in order)
1. Drop WAL in `db._get_conn` (one line) — unblocks SLA testing.
2. Update frontend `lib/api.ts` to talk to the new `/api/jobs/*` endpoints,
   plus a status-polling loop in `UploadPage.tsx`. Frontend is currently
   broken against the new backend.
3. Run a clean SLA measurement on the synthetic and on `test_swing_30s.mp4`
   via the job-queue API.
4. If the 30s video is still over SLA on CPU: drop the redundant
   ultralytics YOLO call in `analyzer.py` (bbox comes from rtmlib's
   internal YOLOX) and lower `_TARGET_ANALYSIS_FPS` to 8. Re-measure.
5. (Bigger fix) Get onnxruntime CUDA 12 runtime DLLs on PATH so the GPU
   actually engages. That's the real path to comfortable headroom under 20s
   for any video length.

## Files touched in this session
- `server/main.py` — async→sync route fix (committed `6ed3419`); warmup hook
  added (uncommitted, on top of the user's job-queue rewrite).
- `src/baseball_swing_analyzer/pose.py` — CUDA selection (uncommitted).
- `src/baseball_swing_analyzer/reporter.py` — JSON `default=str`
  (uncommitted).
- `docs/notes/DEBRIEF.md` — this file.

Pre-existing uncommitted changes (not mine, left untouched):
- `src/baseball_swing_analyzer/analyzer.py`
- `src/baseball_swing_analyzer/detection.py`
- `src/baseball_swing_analyzer/phases.py`
- `scripts/benchmark.py`
- `scripts/poll_job.py`
