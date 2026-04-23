# Baseball Swing Analyzer

Analyze baseball swings from phone video and extract key biomechanical metrics with AI coaching feedback.

## Features

- **Video ingestion**: Load any mp4/MOV, detect blur, report FPS
- **Person detection**: YOLOv8 auto-detects hitter in frame
- **Pose estimation**: RTMPose-m (COCO-17 keypoints, ~500MB VRAM)
- **Keypoint smoothing**: Temporal moving average across frames
- **Phase detection**: Rule-based (stance → load → stride → swing → contact → follow-through)
- **Biomechanical metrics**: hip/shoulder angles, x-factor, knee flexion, spine tilt, stride timing, wrist velocity (bat speed proxy), head displacement
- **Annotated video output**: Skeleton overlay + phase labels
- **AI coaching**: Static rule-based coaching cues + optional Ollama Cloud LLM integration

## Quickstart

```bash
pip install -e ".[test]"
python -m baseball_swing_analyzer --video swing.mp4 --output results/ --annotate --coach
```

Outputs:
- `results/metrics.json` — all computed metrics
- `results/annotated.mp4` — skeleton overlay video
- `results/coaching.md` — coaching report

## Metrics Glossary

| Metric | What it measures | Good range |
|--------|-----------------|------------|
| x_factor_at_contact | Hip-shoulder separation (transverse plane) | 5–35° |
| stride_plant_frame | Frame where stride foot plants | ~15–40 |
| wrist_peak_velocity_px_s | Peak bat speed proxy | >1500 px/s |
| left_knee_at_contact | Front knee flexion at contact | 10–45° |
| right_knee_at_contact | Back knee flexion at contact | 10–40° |
| head_displacement_total | Head movement (load→contact) | <60 px |
| lateral_spine_tilt_at_contact | Side-bend at contact | ±15° |

## Architecture

```
Phone Video
    ├─ Quality gate (blur check, fps)
    ├─ YOLOv8 person detect
    ├─ RTMPose-m → 17 keypoints + smoothing
    ├─ Rule-based phase detection
    ├─ 2D metric extraction → JSON
    ├─ Annotated video overlay
    └─ AI coaching report (static rules + optional LLM)
```

## Dependencies

- Python 3.10+
- numpy, opencv-python, ultralytics, rtmlib, filterpy, httpx
- pytest (dev)

## Tests

```bash
pytest
```

49 tests covering ingestion, detection, pose, metrics, phases, visualization, reporter, analyzer, and AI coaching.

## License

MIT
