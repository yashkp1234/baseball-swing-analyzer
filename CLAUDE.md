# Baseball Swing Analyzer — Agent Instructions

## Project Goal
Analyze a baseball swing from phone video and extract all key biomechanical metrics.
Input is variable: unknown camera angle, framing, lighting, distance. Output is a JSON metrics file + annotated video + plain-English coaching feedback.

## Architecture Overview (read plan.md for full detail)

```
Video → Quality Gate → Camera Calibration → Person Detect → 2D Pose → Phase Detection
     → 3D Lift (if calibrated) → Metric Extraction → VLM Analysis → RAG+LLM → Output
```

## Key Technical Decisions (already researched, don't re-litigate)

- **Pose model**: RTMPose-m via `rtmlib` (not MediaPipe — bad with sports equipment)
- **Person detection**: YOLOv8 (Ultralytics)
- **3D lifting**: CLIFF (camera-aware) — only when field calibration succeeds
- **Camera calibration**: Pose2Sim / PartialSportsFieldReg from visible field markings
- **Bat tracking**: NOT direct tracking — infer from wrist/forearm keypoints
- **Phase detection**: BiLSTM (Phase 2); rule-based for Phase 1
- **VLM**: Phi-3.5-vision (not Qwen2-VL 7B — too slow at 5.4s/frame)
- **LLM coaching**: Mistral 7B INT4 via llama-cpp-python + FAISS RAG
- **Temporal smoothing**: Kalman filter (filterpy)

## What's Hard / Open Problems
- Rotational velocity from single camera is unsolved — report it with low confidence or skip
- Batting cage videos have no field markings → 2D-only metrics, flag it
- Bat at 30fps moves 8 inches/frame — wrist inference is the only practical approach

## Build Order
See plan.md Phase 1 → Phase 4. Always build Phase 1 first and test on real videos before adding complexity.

## Project Structure
```
src/pipeline/   — video processing stages (one file per stage)
src/ai/         — VLM, RAG, LLM coaching
src/output/     — video overlay, JSON reporter
data/videos/    — input test videos
data/knowledge_base/ — RAG source documents
models/         — downloaded model weights
tests/
```

## Style Notes
- No comments unless the WHY is non-obvious
- No premature abstraction — three similar lines beats a helper
- Validate at system boundaries only (video input, model outputs)
- Each pipeline stage is a pure function: takes data in, returns data out

## GPU
RTX 4070, 12GB VRAM, CUDA. Models run sequentially. Peak usage ~5-6GB.
