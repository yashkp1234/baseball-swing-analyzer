# Baseball Swing Analyzer — Implementation Plan

## Goal
Analyze a baseball swing from phone video and extract key biomechanical metrics.
Input is any camera angle. Ball trajectory not always visible and not required.

---

## Hardware Context
- GPU: NVIDIA RTX 4070 (12GB VRAM)
- Input: Phone video (ideally 60–240fps, but 30fps supported)
- Processing: Offline (not real-time constraint)

---

## Architecture Constraint
All source modules live under `src/baseball_swing_analyzer/`. No sibling directories (`src/pipeline/`, `src/ai/`, etc.) — hatchling will omit them from the wheel.

---

## Research Findings (settled decisions)

### What's Solved
- Person detection from any framing/distance: **YOLOv8**
- 2D pose on sports video: **RTMO-m via rtmlib** (supersedes RTMPose-m; ONNX, no mmpose deps)
- Swing phase detection (MVP): **Rule-based** from keypoint kinematics; no training data needed
- Coaching text generation: **Ollama Cloud + Cloud Vision API** via HTTP; no local LLM/VLM weights or builds
- Tracking: **ByteTrack** via ultralytics (person crop continuity)

### What's Hard / Deferred
- **Bat tracking at 30fps**: Physics problem — bat moves ~8 inches/frame. Infer from wrist + forearm keypoints for MVP; true bat detection deferred.
- **3D lifting from arbitrary angle**: Requires CLIFF/SMPL. Moved to Phase 2.5 (optional stretch). MVP targets user-selected side-view or back-view with 2D inference.
- **Learned phase classifier (BiLSTM)**: No public baseball swing dataset. Deferred until 50+ self-labeled swings exist.

---

## Revised Phase Strategy

| Phase | Scope | Local VRAM | Local Disk | Setup Pain |
|-------|-------|------------|------------|------------|
| 1 | 2D skeleton pipeline, rule-based phases, metrics JSON + annotated video | ~3GB | ~150MB | Low |
| 2 | 3D lifting + learned phases + bat estimation | ~6GB peak | ~750MB | High (SMPL) |
| 3 | Cloud AI layer — VLM qualitative flags + coaching text via API | Near 0 | Near 0 | None |
| 4 | Fine-tune, session-level DTW, CLI polish | TBD | TBD | Medium |

**Phase 2 is now optional.** Phase 3 can be built immediately after Phase 1 because it consumes Phase 1 metrics and calls cloud APIs — it does not depend on Phase 2.

---

## Full Pipeline (all phases combined)

```
Phone Video
    ├─[P1] Quality gate (YOLOv8 person detect, blur check, fps flag)
    ├─[P1] Person crop + ByteTrack
    ├─[P1] RTMO-m → 17 keypoints + Kalman smoothing
    ├─[P1] Rule-based phase detection (6 phases)
    ├─[P1] 2D metric extraction → JSON + video overlay
    │
    ├─[P2 — optional] CLIFF → camera angle estimation + 3D lifting
    ├─[P2 — optional] MotionBERT → temporal 3D consistency
    ├─[P2 — optional] BiLSTM phase classifier (replaces rules)
    ├─[P2 — optional] Forearm vector → bat plane estimate
    ├─[P2 — optional] Full metric suite with confidence scores
    │
    ├─[P3] Cloud Vision API → qualitative flags per key frame
    ├─[P3] Ollama Cloud (Mistral) → plain-English coaching report
    │
    └─[P4] RTMO fine-tune on AthletePose3D
           Multi-swing consistency (DTW)
           CLI polish
```

---

## Phase 1 — Skeleton Pipeline

**Goal:** Prove the pipeline works on real swing video end-to-end.
**VRAM:** ~3GB peak. **Disk:** ~150MB. **Setup time:** ~15 minutes.

### Models
| Model | Disk | VRAM | Install |
|-------|------|------|---------|
| YOLOv8l (or YOLOv8x) | ~90MB | ~2GB | `pip install ultralytics` (auto-download) |
| RTMO-m (ONNX via rtmlib) | ~20MB | ~500MB | `pip install rtmlib` (auto-download) |
| filterpy (Kalman) | — | None | `pip install filterpy` |

### Module Layout
```
src/baseball_swing_analyzer/
  __init__.py
  analyzer.py
  ingestion.py      — video I/O, frame extraction, fps detection, blur flag
  detection.py      — YOLOv8 person detect, ByteTrack crop tracking
  pose.py           — RTMO on cropped frames, Kalman smoothing
  phases.py         — rule-based phase classifier from keypoint positions
  metrics.py        — pure functions: compute metrics from pose + phase arrays
  visualizer.py     — keypoint overlay + phase label on video
  reporter.py       — JSON metrics file + console summary
```

All metric math is in small pure functions in `metrics.py`. I/O (`ingestion.py`, `detection.py`) is separate so tests can inject arrays.

### Phase 1 Metrics (2D only, no 3D)
| Metric | Method |
|--------|--------|
| Hip initiation frame | Hip angle inflection point |
| Shoulder initiation frame | Shoulder angle inflection point |
| Hip–shoulder timing delta | Derived |
| Stride foot plant frame | Ankle y-velocity zero crossing |
| X-factor at stride plant | Angle between hip line and shoulder line |
| Spine lateral tilt | Shoulder midpoint vs hip midpoint angle |
| Back knee collapse | Knee angle over time |
| Front knee bracing | Knee angle at contact frame |
| Head displacement | Head keypoint total movement load→contact |
| Wrist peak velocity | Wrist displacement/frame (bat speed proxy) |
| Phase durations | Frames per phase |

### Phase 1 Output
- `output/metrics.json` — all metrics above
- `output/annotated.mp4` — keypoint skeleton + phase label per frame
- Console summary table

### Done When
Runs on 5 real swing videos without crashing. Metrics look biomechanically sensible.

---

## Phase 2 — Robustness + 3D (Optional Stretch)

**Goal:** Handle any camera angle properly. Add bat estimation. Replace rule-based phases with learned classifier.
**Status:** Only build if Phase 1 metrics prove insufficient for hip rotation, stride length, or true bat plane.
**VRAM:** ~6GB peak (CLIFF + RTMO, unloaded between). **New disk:** ~600MB. **Setup pain:** SMPL registration required.

### New Models
| Model | Disk | VRAM | Install / Pain |
|-------|------|------|---------------|
| CLIFF | ~350MB | ~3GB | GitHub clone + **manual SMPL account at smpl.is.tue.mpg.de** |
| MotionBERT | ~200MB | ~3GB | Google Drive download (rate-limited sometimes) |
| MediaPipe Hands | 8MB | CPU | `pip install mediapipe` |
| BiLSTM (custom) | ~5MB | ~200MB | Must label swing data + train |

**Model unloading required:** CLIFF must be unloaded before MotionBERT. Use `del model; torch.cuda.empty_cache()` between stages.

### What Gets Built (if Phase 2 proceeds)
8. `src/baseball_swing_analyzer/calibration.py` — CLIFF camera angle estimation, confidence scoring
9. `src/baseball_swing_analyzer/lifting.py` — CLIFF 3D lift → MotionBERT temporal pass → world coords
10. `src/baseball_swing_analyzer/phases.py` — BiLSTM replaces rule-based classifier (train on labeled data)
11. `src/baseball_swing_analyzer/bat.py` — forearm vector → barrel position estimate, swing plane
12. Update `src/baseball_swing_analyzer/metrics.py` — add 3D-dependent metrics + per-metric confidence

### Phase 2 Additional Metrics
| Metric | Method | Confidence |
|--------|--------|------------|
| Hip rotation angle (absolute) | 3D hip line change | High if CLIFF succeeds |
| Hip angular velocity (peak) | 3D derivative | High (back view), Medium (other) |
| Shoulder angular velocity (peak) | 3D derivative | High (back view), Medium (other) |
| Stride length | 3D ankle displacement | High |
| Stride direction | 3D foot vector | High |
| CoM path | Estimated 3D center of mass | Medium |
| Bat attack angle | Forearm vector × bat length | Low–Medium |
| Bat swing plane | Forearm trajectory arc | Low–Medium |
| Kinematic chain efficiency | Segment deceleration sequencing | Medium |
| Back elbow slot | 3D elbow position at contact | High |

### Confidence Fallback
If CLIFF angle confidence < threshold → classify as side or back from pose heuristic → apply view-specific 2D metrics → flag in JSON.

### Done When
3D metrics appear in JSON. Annotated video shows phase labels from BiLSTM. Bat plane visible in overlay.

---

## Phase 3 — Cloud AI Layer

**Goal:** Qualitative coaching observations + plain-English feedback report.
**Local VRAM:** Near 0. **Local Disk:** Near 0. **Setup pain:** None (API keys only).

### Dependencies
| Service | Role | How |
|---------|------|-----|
| Cloud Vision API (e.g., GPT-4o-vision, Gemini Flash) | Extract qualitative flags per key frame | HTTP POST with base64 image |
| Ollama Cloud (Mistral 7B or equivalent) | Generate plain-English coaching report | HTTP POST with prompt + metrics JSON |

No local `transformers`, `llama-cpp-python`, `faiss-cpu`, `sentence-transformers`, or GGUF downloads.

### Module Layout
```
src/baseball_swing_analyzer/
  ai/
    __init__.py
    client.py      — thin HTTP wrapper for Ollama Cloud + Vision API
    coaching.py    — build prompt from metrics → call client → parse response
```

### What Gets Built
13. `src/baseball_swing_analyzer/ai/client.py` — generic `chat(messages)` and `vision(image, prompt)` functions via httpx
14. `src/baseball_swing_analyzer/ai/coaching.py` — map Phase 1 metrics to observation strings → prompt Mistral → return coaching report
15. Update `src/baseball_swing_analyzer/reporter.py` — full report: metrics JSON + VLM flags + coaching paragraphs

### VLM Qualitative Flags (per key frame)
- Front shoulder closed through load? (Y/N)
- Leg kick vs toe tap? (classified)
- High vs low finish? (classified)
- Hip-casting visible? (Y/N)
- Arm slot at contact? (high/middle/low)

### Done When
Full pipeline produces: metrics JSON + annotated video + coaching text report. End-to-end on one swing in under 30 seconds.

---

## Phase 4 — Fine-Tuning & Polish

**Goal:** Push accuracy, add session-level analysis, clean up CLI.

### What Gets Built
18. Fine-tune RTMO on **AthletePose3D** (1.3M frames) + **SportsPose** — expected 30–50% keypoint error reduction
19. Multi-swing session mode: DTW similarity scoring across swings, consistency metrics
20. CLI: `python -m baseball_swing_analyzer --video swing.mp4 --output results/`
21. Confidence threshold tuning based on real-world test set

---

## Model Memory Reference

| Model | Phase | Local Disk | Local VRAM | Notes |
|-------|-------|------------|------------|-------|
| YOLOv8l | 1 | ~90MB | ~2GB | Auto-download |
| RTMO-m | 1 | ~20MB | ~500MB | Auto-download via rtmlib |
| CLIFF | 2 | ~350MB | ~3GB | SMPL registration required |
| MotionBERT | 2 | ~200MB | ~3GB | Google Drive |
| MediaPipe Hands | 2 | 8MB | CPU | Auto |
| BiLSTM | 2 | ~5MB | ~200MB | Must train |
| **Phase 1 total** | | **~110MB** | **~2.5GB** | |
| **Phase 2 total** | | **~750MB** | **~6GB peak** | Unload between models |
| **Phase 3 total** | | **Near 0** | **Near 0** | Cloud APIs only |

---

## Tech Stack

```
Python 3.11+
opencv-python      — video I/O, annotation
ultralytics        — YOLOv8
rtmlib             — RTMO (no mmpose dependency)
filterpy           — Kalman filter
torch + torchvision — Phase 2 only: CLIFF, MotionBERT, BiLSTM
numpy / scipy      — metric math
httpx              — Phase 3: Ollama Cloud + Vision API client
```

**Removed from original plan:** `mediapipe` (deferred), `faiss-cpu`, `sentence-transformers`, `transformers`, `llama-cpp-python`.

---

## Open Questions (decide before building that phase)

1. **Frame rate minimum** — enforce 60fps or accept 30fps with a warning? At 30fps bat estimation from wrist is the only option.
2. **BiLSTM training data** — label our own swings or find a proxy dataset? GolfDB structure is the template.
3. **Cloud vision API choice** — OpenAI GPT-4o-vision vs. Google Gemini Flash vs. Groq vision? Decide based on cost/latency after Phase 1 ships.
4. **RAG knowledge base sources** — what coaching documents to curate for Phase 3? Can start with static JSON/MD files; FAISS is overkill for <100 docs.

---

## Key References

- [rtmlib (RTMO / RTMPose)](https://github.com/Tau-J/rtmlib)
- [RTMO paper](https://arxiv.org/abs/2312.07526)
- [CLIFF](https://github.com/haofanwang/CLIFF)
- [MotionBERT](https://github.com/Walter0807/MotionBERT)
- [GolfDB/SwingNet](https://github.com/wmcnally/golfdb)
- [AthletePose3D](https://arxiv.org/html/2503.07499v3)
- [SportsPose](https://openaccess.thecvf.com/content/CVPR2023W/CVSports/papers/Ingwersen_SportsPose_-_A_Dynamic_3D_Sports_Pose_Dataset_CVPRW_2023_paper.pdf)
- [WIN Reality SwingAI](https://winreality.com/swing-ai/)
