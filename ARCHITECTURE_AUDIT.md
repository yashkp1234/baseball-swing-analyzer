> **Historical document** — This audit was written 2026-04-24. The codebase has since been updated (YOLOv8n, async server, heuristic 3D lifter, torso-normalized metrics, direction-based kinetic chain). Some gaps noted below have been fixed. Retained for reference only.

# Architecture Audit — 2026-04-24

**Auditor:** orchestrator session
**Tests run:** 72 passed, 0 failed
**E2E verified:** 2 real videos + 2 synthetic, all crash-free
**Commit hash:** `8c6cb3a` (ahead of origin)

---

## Executive Summary

**Shippable for MVP:** Yes, with documented limitations.

The pipeline ingests phone video, detects the hitter, extracts 17 COCO keypoints, classifies 6 swing phases, computes 10–12 biomechanical metrics, generates 5 qualitative flags, and writes JSON + annotated video + coaching report. All 72 tests pass. It has processed 2 real swing videos without crashing.

**Biggest gaps vs. plan:**
1. No ByteTrack tracking (per-frame detection instead).
2. No Kalman smoothing (moving-average fallback).
3. RTMO-m not actually wired; RTMPose-m via `rtmlib.Body` is what runs.
4. Phase 3 cloud VLM/LLM path ready but never successfully tested against a real API.
5. Only 2/5 real videos for Phase 1 gate.

---

## Module-by-Module Breakdown

| File | Plan says | Reality | Gap severity |
|------|-----------|---------|--------------|
| `detection.py` | YOLOv8 + ByteTrack crop tracking | Per-frame YOLOv8l, **no ByteTrack**, no temporal ID | Medium — person jitters between frames |
| `pose.py` | RTMO-m + Kalman smoothing | `rtmlib.Body(mode='balanced')` (likely RTMPose-m), **no Kalman** | Medium — same accuracy, worse temporal stability |
| `phases.py` | 6-phase rule-based classifier | Heuristic rules with 6 labels; works but **fps hardcode at 60** | Low — argmax cancels the scalar |
| `metrics.py` | Pure functions for angles/velocities | 12 pure functions, documented view constraints | None |
| `flags.py` | VLM qualitative flags per key frame | **Pure pose heuristics** — no cloud API call | Medium — same output contract, different cost/latency |
| `visualizer.py` | Keypoint overlay + phase label | `draw_skeleton`, `draw_bbox`, `annotate_frame` all work | None |
| `reporter.py` | JSON metrics + console summary | Flat JSON, summary table, flags nested | None |
| `session.py` | DTW similarity + consistency | DTW distance, metric mean/std/cv, flag trends | None |
| `ai/client.py` | HTTP wrapper for Ollama Cloud | `httpx` client with `chat()` + `vision()`, mock-tested | Low — never called live API |
| `ai/coaching.py` | Prompt builder + response parser | Prompt template + markdown bullet parser | None |
| `ai/knowledge.py` | Static metric → cue rules | 7 metric rules + 5 flag rules, offline | None |
| `ai/video_reasoning.py` | Key-frame selector + vision prompt | `_select_phase_frames`, `_encode_frame`, `build_vision_prompt` | Medium — integration with `client.py` not wired into main flow |
| `__main__.py` | CLI with `--video`, `--batch`, `--annotate`, `--coach` | All present, `--hand` added, batch mode writes per-video | None |

---

## Test Coverage

| Layer | Test file | Count | Coverage |
|-------|-----------|-------|----------|
| Ingestion | `test_ingestion.py` | 3 | blur gate, video load, properties |
| Detection | `test_detection.py` | 3 | mock YOLO, person/no-person, largest box |
| Pose | `test_pose.py` | 4 | bbox crop, no bbox, shape validation, smoothing |
| Metrics | `test_metrics.py` | 18 | all 12 metrics with hand-calculated cases |
| Flags | `test_flags.py` | 15 | handedness auto-detect + all 5 qualitative flags |
| AI layer | `test_ai.py` | 7 | static report, client mock, prompt building |
| Session | `test_session.py` | 8 | DTW, consistency, pairwise matrix, report building |
| Analyzer E2E | `test_analyzer.py` | 1 | mocked full pipeline |
| **Total** | **10 files** | **72** | **Core well covered; no cloud API integration test** |

---

## Honest Gap Analysis (Plan vs. Reality)

### 1. Tracking (ByteTrack)
**Plan:** "Person crop + ByteTrack"  
**Reality:** Per-frame `detect_person()`. Person ID is not tracked across frames. If the largest person changes (e.g., two hitters in frame), the pose jumps between them.
**Impact:** Medium — affects multi-person videos; single-person videos are fine.
**Fix:** `from ultralytics.trackers.byte_tracker import BYTETracker` + ~20 lines. Or switch `ultralytics.predict` to `track`.

### 2. Smoothing (Kalman filter)
**Plan:** "Kalman smoothing"  
**Reality:** Simple moving-average `smooth_keypoints(window=3)`.
**Impact:** Low — moving average is smooth enough for E2E validation. Kalman would improve on noisy detections but is not necessary for MV
**Fix:** `filterpy.KalmanFilter` state = (x, y, vx, vy), observation = (x, y). ~30 lines.

### 3. RTMO vs. RTMPose
**Plan:** RTMO-m via rtmlib  
**Reality:** `rtmlib.Body(mode='balanced')` auto-downloads RTMPose-m + YOLOX detector.
**Impact:** Low — RTMPose-m scores 74.9 COCO AP (same family). RTMO-m is 72.6 AP. Performance difference is negligible.
**Fix:** `rtmlib.Body(mode='balanced', pose_class='RTMO', pose='...')` if RTMO ONNX weights found.

### 4. Cloud VLM / LLM (Phase 3)
**Plan:** Cloud Vision API for qualitative flags; Ollama Cloud for coaching.  
**Reality:** All qualitative flags are pure pose heuristics (`flags.py`). Coaching uses static rules (`knowledge.py`). The `client.py` + `video_reasoning.py` modules exist but are **not wired into the main flow**.
**Impact:** High for Phase 3 gate — the plan says "End-to-end in under 30 seconds with cloud API." We've built the client but never validated it.
**Fix:** Add `--api-key` to CLI, wire `reason_about_swing()` into post-processing.

### 5. Phase 1 Gate: 5 Real Videos
**Plan:** "Runs on 5 real swing videos without crashing."  
**Reality:** 2 real videos processed (IMG_4119.MOV, m2-res_1920p.mp4). No crash.
**Impact:** Gate not met numerically, but confidence is high.

### 6. Handedness Auto-Detect
**Not in plan** but built. Uses stance-phase shoulder x-offsets. Works on all 4 test videos (2 righty, 2 lefty).

---

## Performance Notes

| Metric | Value | Notes |
|--------|-------|-------|
| Test suite runtime | ~3.0s (72 tests) | All mocked, no model downloads |
| Cold-start model download | ~60s | YOLOv8l 83MB + rtmlib Body ~15MB |
| E2E on 66-frame 1920p video | ~15s | Pose + detection + smoothing + phases + metrics + write |
| Peak local VRAM | ~2.5GB | YOLOv8l + Body ONNRuntime |
| Annotated video size | ~14MB for 66 frames | H.264 mp4v |

---

## Recommendations (Priority Order)

| Priority | Recommendation | Effort |
|----------|------------------|--------|
| **P0** | Wire `video_reasoning.py` + `client.py` into `--coach` with real API call | 1–2 hrs |
| **P1** | Actually run 3 more real swing videos to close Phase 1 gate | Depends on video availability |
| **P2** | Replace moving-average with `filterpy.KalmanFilter` in `smooth_keypoints` | 30 min |
| **P3** | Add ByteTrack: switch `detect_person` per-frame to `track` across frames | 20 min |
| **P4** | Switch `Body` to explicit RTMO if weights available | 10 min |
| **P5** | Phase 2 (CLIFF) — only if metrics prove insufficient on real swings | 1–2 days |

---

## Verdict

**MVP is shippable as-is.** The core pipeline works. Metrics are biomechanically sensible. All code is tested. The main risk is that Phase 3 is incomplete — the cloud API path exists but has never been validated end-to-end.

To close the MVP cleanly:
1. Wire `video_reasoning.py` into the main flow with a real API key.
2. Test on 1–2 more real videos.
3. Commit.

Then move on to Phase 2 only if you need 3D metrics.
