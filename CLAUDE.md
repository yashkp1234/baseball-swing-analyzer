# Baseball Swing Analyzer — Agent Instructions

## Project Goal
Analyze a baseball swing from phone video and extract all key biomechanical metrics.
Input is variable: unknown camera angle, framing, lighting, distance. Output is a JSON metrics file + annotated video + plain-English coaching feedback.

## Architecture Overview

```
Video → Quality Gate → Person Detect (YOLOv8l) → RTMO-m → Phase Detection
     → Metric Extraction → Qualitative Flags → Static/Cloud Coaching → Output
```

## Key Technical Decisions (already settled, don't re-litigate)

- **Pose model**: RTMO-m via `rtmlib` (`Body(mode='balanced')`) — ONNX, no mmpose deps
- **Person detection**: YOLOv8l (Ultralytics)
- **3D lifting**: Deferred to Phase 2 (optional). MVP is 2D-only.
- **Camera calibration**: Deferred to Phase 2. Fall back to view-specific metric confidence.
- **Bat tracking**: NOT direct tracking — infer from wrist/forearm keypoints
- **Phase detection**: Rule-based from keypoint kinematics (Phase 1); BiLSTM deferred to Phase 2
- **Handedness**: Auto-detected from stance-phase shoulder geometry; override with `--hand right|left`
- **AI coaching**: Static rule-based knowledge base (offline) + optional Ollama Cloud / any OpenAI-compatible API (Phase 3, no local LLM weights, no FAISS)
- **Temporal smoothing**: Simple moving-average window=3 (Kalman deferred to Phase 2)

## What's Hard / Open Problems
- Rotational velocity from single camera is unsolved — report with low confidence or skip
- Batting cage videos have no field markings → 2D-only metrics, flag it
- Bat at 30fps moves 8 inches/frame — wrist inference is the only practical approach
- Handedness auto-detect assumes camera is roughly on the 1B/3B side; head-on view degrades it

## Build Status
- Phase 1: **Complete** — pipeline runs end-to-end, 61 tests pass
- Phase 3: **Partially complete** — static coaching + cloud LLM client done; vision API not yet wired
- Phase 2: Deferred (CLIFF 3D, BiLSTM phases, forearm bat estimate)
- Phase 4: Deferred (fine-tune, DTW session mode, CLI polish) — `session.py` scaffolded

## Real Module Layout
```
src/baseball_swing_analyzer/
  __init__.py
  __main__.py        — CLI: python -m baseball_swing_analyzer --video X --output Y [--hand auto]
  analyzer.py        — top-level pipeline orchestration
  ingestion.py       — video I/O, frame extraction, fps detection, blur flag
  detection.py       — YOLOv8l person detect
  pose.py            — RTMO-m on cropped frames, moving-average smoothing
  phases.py          — rule-based phase classifier (6 phases, fps-aware)
  metrics.py         — pure functions: angles, velocities, head disp, stride plant
  visualizer.py      — keypoint overlay + phase label on video
  reporter.py        — build_report() → flat metrics dict; write_metrics_json()
  session.py         — multi-swing DTW + consistency stats (Phase 4 scaffold)
  ai/
    __init__.py
    client.py        — thin httpx wrapper for Ollama Cloud / any OpenAI-compatible API
    coaching.py      — build LLM prompt from metrics; encode_image_for_api
    flags.py         — pose-only qualitative flags; handedness auto-detect
    knowledge.py     — static rule-based coaching cues (offline fallback)
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
RTX 4070, 12GB VRAM, CUDA. Phase 1 peak ~2.5GB. Models run sequentially.
