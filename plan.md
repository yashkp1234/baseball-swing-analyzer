# Baseball Swing Analyzer — Implementation Plan

## Goal
Analyze a baseball swing from phone video and extract all key biomechanical metrics.
Input is any camera angle. Ball trajectory not always visible and not required.

---

## Hardware Context
- GPU: NVIDIA RTX 4070 (12GB VRAM)
- Input: Phone video (ideally 60–240fps, but 30fps supported)
- Processing: Offline (not real-time constraint)

---

## Research Findings (settled decisions — don't re-litigate)

### What's Solved
- Person detection from any framing/distance: **YOLOv8**
- 2D pose on sports video: **RTMPose-m** (400+ FPS on 4070, 75.8 AP COCO)
- Swing phase detection: **BiLSTM** (99.7% accuracy in literature, GolfDB pattern)
- Coaching text from structured metrics: **RAG + Mistral 7B**
- VLM qualitative frame analysis: **Phi-3.5-vision** (70ms/frame, ~4GB VRAM INT4)

### What's Hard / Open
- **Bat tracking at 30fps**: Physics problem — bat moves 8 inches/frame. Infer from wrist + forearm keypoints instead.
- **Rotational velocity from arbitrary angle**: Requires 3D reconstruction. High confidence from back view (rotation in-plane), medium from side, unreliable from other angles without CLIFF.
- **BiLSTM training data**: No public baseball swing dataset. Rule-based phase detection for Phase 1; BiLSTM deferred to Phase 2.

### Camera Angle Strategy
**Primary (any angle):** CLIFF estimates camera rotation alongside pose → world-coordinate 3D metrics → per-metric confidence score.

**Fallback (when CLIFF confidence low):** Classify into side or back view from pose keypoint geometry → view-specific 2D metric extraction → flag unreliable metrics.

- Side view best for: X-factor, stride length, spine tilt, knee angles, contact depth, bat path
- Back view best for: hip/shoulder rotation angle + speed, stride direction, head movement

### Commercial Benchmark
**WIN Reality SwingAI** — 12 biomechanical dimensions from phone video. That's our target.

---

## Full Pipeline (all phases combined)

```
Phone Video
    ├─[P1] Quality gate (YOLOv8 person detect, blur check, fps flag)
    ├─[P1] Person crop + ByteTrack
    ├─[P1] RTMPose-m → 17 keypoints + Kalman smoothing
    ├─[P1] Rule-based phase detection (6 phases)
    ├─[P1] 2D metric extraction → JSON + video overlay
    │
    ├─[P2] CLIFF → camera angle estimation + 3D lifting
    ├─[P2] MotionBERT → temporal 3D consistency
    ├─[P2] BiLSTM phase classifier (replaces rules)
    ├─[P2] MediaPipe Hands on wrist ROI → bat estimation
    ├─[P2] Full metric suite with confidence scores
    │
    ├─[P3] Phi-3.5-vision → qualitative flags per key frame
    ├─[P3] FAISS RAG → retrieve coaching cues
    ├─[P3] Mistral 7B → plain-English coaching report
    │
    └─[P4] RTMPose fine-tune on AthletePose3D
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
| YOLOv8x | 130MB | ~2.5GB | `pip install ultralytics` (auto-download) |
| RTMPose-m (ONNX) | 15MB | ~500MB | `pip install rtmlib` (auto-download) |
| filterpy (Kalman) | — | None | `pip install filterpy` |

### What Gets Built
1. `src/pipeline/ingestion.py` — load video, extract frames, detect fps, flag blur
2. `src/pipeline/detection.py` — YOLOv8 person detect, ByteTrack crop tracking
3. `src/pipeline/pose.py` — RTMPose-m on cropped frames, Kalman smoothing
4. `src/pipeline/phases.py` — rule-based phase classifier from keypoint positions
5. `src/pipeline/metrics.py` — compute Phase 1 metric set (see below)
6. `src/output/visualizer.py` — keypoint overlay + phase label on video
7. `src/output/reporter.py` — JSON metrics file

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

## Phase 2 — Robustness + 3D

**Goal:** Handle any camera angle properly. Add bat estimation. Replace rule-based phases with learned classifier.
**VRAM:** ~6GB peak (CLIFF + RTMPose, unloaded between). **New disk:** ~600MB. **Setup pain:** SMPL registration required.

### New Models
| Model | Disk | VRAM | Install / Pain |
|-------|------|------|---------------|
| CLIFF | ~350MB | ~3GB | GitHub clone + **manual SMPL account at smpl.is.tue.mpg.de** |
| MotionBERT | ~200MB | ~3GB | Google Drive download (rate-limited sometimes) |
| MediaPipe Hands | 8MB | CPU | `pip install mediapipe` |
| BiLSTM (custom) | ~5MB | ~200MB | Must label swing data + train |

**Model unloading required:** CLIFF must be unloaded before MotionBERT. Both must be unloaded before Phase 3 AI models. Use `del model; torch.cuda.empty_cache()` between stages.

### What Gets Built
8. `src/pipeline/calibration.py` — CLIFF camera angle estimation, confidence scoring
9. `src/pipeline/lifting.py` — CLIFF 3D lift → MotionBERT temporal pass → world coords
10. `src/pipeline/phases.py` — BiLSTM replaces rule-based classifier (train on labeled data)
11. `src/pipeline/bat.py` — forearm vector → barrel position estimate, swing plane
12. Update `src/pipeline/metrics.py` — add 3D-dependent metrics + per-metric confidence

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

## Phase 3 — AI Layer

**Goal:** Qualitative coaching observations + plain-English feedback report.
**VRAM:** ~5GB peak (Phi-3.5 or Mistral, never simultaneously). **New disk:** ~8GB.

### New Models
| Model | Disk | VRAM | Install / Pain |
|-------|------|------|---------------|
| Phi-3.5-vision (INT4) | ~4GB | ~4GB | HuggingFace auto |
| Mistral 7B Q4_K_M (GGUF) | ~4GB | ~4.5GB | Manual GGUF download + `CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python` (Windows CUDA build — 30–60min) |
| BGE-small-en embeddings | 130MB | CPU | `pip install sentence-transformers` |

### What Gets Built
13. `src/ai/vlm.py` — extract 6 key frames (one per phase) → Phi-3.5-vision → structured observation JSON
14. `src/ai/rag.py` — FAISS index over coaching knowledge base, BGE embeddings, retrieval
15. `data/knowledge_base/` — curate coaching docs (biomechanics papers, drill libraries, cue databases)
16. `src/ai/coaching.py` — build augmented prompt from metrics + RAG results → Mistral 7B → coaching text
17. Update `src/output/reporter.py` — full report: metrics JSON + VLM flags + coaching paragraphs

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
18. Fine-tune RTMPose-m on **AthletePose3D** (1.3M frames) + **SportsPose** (includes baseball pitch) — expected 30–50% keypoint error reduction
19. Multi-swing session mode: DTW similarity scoring across swings, consistency metrics
20. CLI: `python analyze.py --video swing.mp4 --output results/`
21. Confidence threshold tuning based on real-world test set

---

## Model Memory Reference

| Model | Phase | Disk | VRAM | Notes |
|-------|-------|------|------|-------|
| YOLOv8x | 1 | 130MB | 2.5GB | Auto-download |
| RTMPose-m | 1 | 15MB | 500MB | Auto-download |
| CLIFF | 2 | 350MB | 3GB | SMPL registration required |
| MotionBERT | 2 | 200MB | 3GB | Google Drive |
| MediaPipe Hands | 2 | 8MB | CPU | Auto |
| BiLSTM | 2 | 5MB | 200MB | Must train |
| Phi-3.5-vision | 3 | 4GB | 4GB | HuggingFace auto |
| Mistral 7B Q4_K_M | 3 | 4GB | 4.5GB | CUDA build painful |
| BGE-small | 3 | 130MB | CPU | Auto |
| **Phase 1 total** | | **~150MB** | **~3GB** | |
| **Phase 2 total** | | **~750MB** | **~6GB peak** | Unload between models |
| **Phase 3 total** | | **~9GB** | **~5GB peak** | Never load VLM + LLM together |

---

## Tech Stack

```
Python 3.11+
opencv-python       — video I/O, annotation
ultralytics         — YOLOv8
rtmlib              — RTMPose-m (no mmpose dependency)
mediapipe           — hand keypoints (Phase 2)
filterpy            — Kalman filter
torch + torchvision — CLIFF, MotionBERT, BiLSTM (Phase 2+)
numpy / scipy       — metric math
faiss-cpu           — RAG vector search (Phase 3)
sentence-transformers — BGE embeddings (Phase 3)
transformers        — Phi-3.5-vision (Phase 3)
llama-cpp-python    — Mistral 7B INT4 (Phase 3)
```

---

## Open Questions (decide before building that phase)

1. **CLIFF confidence threshold** — what MPJPE proxy or rotation uncertainty score defines "too low to trust"? Needs empirical testing in Phase 2.
2. **Frame rate minimum** — enforce 60fps or accept 30fps with a warning? At 30fps bat estimation from wrist is the only option.
3. **BiLSTM training data** — label our own swings or find a proxy dataset? GolfDB structure is the template.
4. **RAG knowledge base sources** — what coaching documents to curate for Phase 3?

---

## Key References

- [rtmlib (RTMPose)](https://github.com/Tau-J/rtmlib)
- [CLIFF](https://github.com/haofanwang/CLIFF)
- [MotionBERT](https://github.com/Walter0807/MotionBERT)
- [GolfDB/SwingNet](https://github.com/wmcnally/golfdb)
- [AthletePose3D](https://arxiv.org/html/2503.07499v3)
- [SportsPose](https://openaccess.thecvf.com/content/CVPR2023W/CVSports/papers/Ingwersen_SportsPose_-_A_Dynamic_3D_Sports_Pose_Dataset_CVPRW_2023_paper.pdf)
- [SportsGPT/SportsRAG](https://arxiv.org/html/2512.14121v1)
- [Motion blur in baseball pose](https://dl.acm.org/doi/10.1145/3606038.3616163)
- [WIN Reality SwingAI](https://winreality.com/swing-ai/)
