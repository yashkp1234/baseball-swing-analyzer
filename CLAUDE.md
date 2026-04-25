# Baseball Swing Analyzer — Agent Instructions

## Project Goal
Analyze a baseball swing from phone video and extract all key biomechanical metrics.
Input is variable: unknown camera angle, framing, lighting, distance. Output is a JSON metrics file + annotated video + plain-English coaching feedback.

## Architecture Overview

```
Video → Quality Gate → Person Detect (YOLOv8n) → RTMO-m → Phase Detection
     → Metric Extraction → Qualitative Flags → Static/Cloud Coaching → Output
```

## Key Technical Decisions (already settled, don't re-litigate)

- **Pose model**: RTMO-m via `rtmlib` (`Body(mode='balanced')`) — ONNX, no mmpose deps
- **Person detection**: YOLOv8n (Ultralytics)
- **3D lifting**: Heuristic depth from body proportions (lifter.py). MotionBERT optional. Depth is qualitative — not for quantitative 3D metrics.
- **Camera calibration**: Deferred to Phase 2. Fall back to view-specific metric confidence.
- **Bat tracking**: NOT direct tracking — infer from wrist/forearm keypoints
- **Phase detection**: Rule-based from keypoint kinematics (Phase 1); BiLSTM deferred to Phase 2
- **Handedness**: Auto-detected from stance-phase shoulder geometry; override with `--hand right|left`
- **AI coaching**: Static rule-based knowledge base (offline) + optional Ollama Cloud / any OpenAI-compatible API (Phase 3, no local LLM weights, no FAISS)
- **Temporal smoothing**: Simple moving-average window=3 (Kalman deferred to Phase 2)
- **Server**: FastAPI async job queue — upload → poll status → fetch results. Per-thread SQLite via threading.local(). Large 3D data served as file artifacts, not inline JSON.
- **Kinetic chain**: Direction-based (leads/trails/synced) with frame lag counts, not fake percentage scores.
- **Metrics normalization**: torso_length_px used for resolution-independent thresholds (leg kick, wrist velocity).
- **Phase durations**: Contiguous-run semantics (not Counter-based).

## What's Hard / Open Problems
- Rotational velocity from single camera is unsolved — report with low confidence or skip
- Batting cage videos have no field markings → 2D-only metrics, flag it
- Bat at 30fps moves 8 inches/frame — wrist inference is the only practical approach
- Handedness auto-detect assumes camera is roughly on the 1B/3B side; head-on view degrades it

## Build Status
- Phase 1: **Complete** — pipeline runs end-to-end, 72 tests pass
- Phase 3: **Partially complete** — static coaching + cloud LLM client done; vision API not yet wired
- Phase 2: Heuristic 3D lifting done (lifter.py + energy.py + export_3d.py). MotionBERT/CLIFF deferred.
- Phase 4: Deferred (fine-tune, DTW session mode, CLI polish) — `session.py` scaffolded
- **Server**: Async FastAPI job queue with streaming uploads, SQLite persistence, artifact endpoints.

## Real Module Layout
```
src/baseball_swing_analyzer/
  __init__.py
  __main__.py        — CLI: python -m baseball_swing_analyzer --video X --output Y [--hand auto]
  analyzer.py        — top-level pipeline orchestration
  ingestion.py       — video I/O, frame extraction, fps detection, blur flag
  detection.py       — YOLOv8n person detect
  pose.py            — RTMO-m on cropped frames, moving-average smoothing
  phases.py          — rule-based phase classifier (6 phases, fps-aware)
  metrics.py         — pure functions: angles, velocities, head disp, stride plant, torso_length_px
  lifter.py          — 2D→3D heuristic lifting (MotionBERT optional)
  visualizer.py      — keypoint overlay + phase label on video
  reporter.py        — build_report() → flat metrics dict; write_metrics_json()
  session.py         — multi-swing DTW + consistency stats (Phase 4 scaffold)
  ai/
    __init__.py
    client.py        — thin httpx wrapper for Ollama Cloud / any OpenAI-compatible API
    coaching.py      — build LLM prompt from metrics; encode_image_for_api
    flags.py         — pose-only qualitative flags; handedness auto-detect
    knowledge.py     — static rule-based coaching cues (offline fallback)
  energy.py          — velocity vectors, kinetic chain lag, energy loss event detection
  export_3d.py       — assembles 3D JSON blob for frontend visualization
server/
  main.py            — FastAPI app with lifespan, CORS, routers
  db.py              — per-thread SQLite, job CRUD
  api/
    upload.py        — streaming upload, size/extension validation
    status.py        — job status polling
    results.py       — metrics + coaching + 3D artifact URL
    artifacts.py     — serves frames_3d.json from disk
data/videos/         — test swing videos (add real .mp4 here; gitignored)
data/knowledge_base/ — RAG source docs (future use)
models/              — downloaded model weights (gitignored)
tests/
```

## Style Notes
- No comments unless the WHY is non-obvious
- No premature abstraction — three similar lines beats a helper
- Validate at system boundaries only (video input, model outputs)
- Each pipeline stage is a pure function: takes data in, returns data out

## GPU
RTX 4070, 12GB VRAM, CUDA v13.2. Phase 1 peak ~2.5GB. Models run sequentially.

## Server
Async FastAPI job queue. Upload video → get job ID → poll /status/{jobId} → fetch /results/{jobId}. 3D frames served as file artifact, not inline JSON. Per-thread SQLite connections via threading.local().
