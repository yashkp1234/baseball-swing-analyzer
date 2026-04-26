# Baseball Swing Analyzer

Analyze baseball swings from phone video and extract key biomechanical metrics with AI coaching feedback.

## Features

- **Video ingestion**: Load any mp4/MOV, detect blur, report FPS
- **Person detection**: YOLOv8n auto-detects hitter in frame
- **Pose estimation**: RTMO-m via rtmlib (COCO-17 keypoints)
- **Keypoint smoothing**: Temporal moving average across frames
- **Phase detection**: Rule-based (stance → load → stride → swing → contact → follow-through)
- **Swing segmentation**: Long clips are trimmed to buffered active swing windows, with multiple swings broken out separately
- **Biomechanical metrics**: hip/shoulder angles, x-factor, knee flexion, spine tilt, stride timing, normalized wrist velocity (bat speed proxy), head displacement
- **Swing breakdown viewer**: Heuristic depth lifting with estimated bat/barrel and contact-point visuals
- **Projected fix preview**: Toggle a lower-half timing fix and compare estimated score, EV, and carry
- **Annotated video output**: Trimmed skeleton overlay + phase labels
- **AI coaching**: Static rule-based coaching cues + optional Ollama Cloud LLM integration
- **Async server**: Upload video, poll for status, fetch results — no blocking

## Quickstart

### CLI

```bash
pip install -e ".[test]"
python -m baseball_swing_analyzer --video swing.mp4 --output results/ --annotate --coach --hand auto
```

### Server

```bash
pip install -e .
uvicorn server.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend talks to the server at `http://localhost:8000` by default. Set `VITE_API_URL` to override.

## Server API Flow

1. **Upload** `POST /api/upload` — streaming upload, returns `job_id`
2. **Poll** `GET /api/status/{job_id}` — returns status + progress
3. **Results** `GET /api/results/{job_id}` — metrics, coaching, 3D data URL
4. **Artifact** `GET /api/artifacts/{job_id}/frames_3d.json` — large 3D frame data

Maximum upload size: 500 MB. Allowed extensions: `.mp4`, `.mov`, `.avi`, `.mkv`.

## Metrics Glossary

| Metric | What it measures | Good range |
|--------|-----------------|------------|
| x_factor_at_contact | Hip-shoulder separation (transverse plane) | 5–35° |
| stride_plant_frame | Frame where stride foot plants | ~15–40 |
| wrist_peak_velocity_normalized | Peak bat speed proxy (per torso-length) | >5.0 |
| left_knee_at_contact | Front knee flexion at contact | 10–45° |
| right_knee_at_contact | Back knee flexion at contact | 10–40° |
| head_displacement_total | Head movement (load→contact) | <60 px |
| lateral_spine_tilt_at_contact | Side-bend at contact | ±15° |

Bat position, ball/contact position, projected EV, and projected carry are estimates derived from pose data. They are intended for coaching comparison, not measured bat tracking or measured ball flight.

## Architecture

```
Phone Video
    ├─ Quality gate (blur check, fps)
    ├─ YOLOv8n person detect
    ├─ RTMPose-m → 17 keypoints + smoothing
    ├─ Swing segmentation with pre-swing buffer
    ├─ Rule-based phase detection
    ├─ 2D metric extraction → JSON
    ├─ Heuristic 3D lifting → estimated bat/contact visualization
    ├─ Trimmed annotated video overlay
    └─ AI coaching report (static rules + optional LLM)
```

## Repository Layout

- `src/baseball_swing_analyzer/` - core Python analysis package
- `server/` - FastAPI backend, job queue, artifact APIs
- `frontend/` - React/Vite upload and swing viewer app
- `tests/` - Python tests and fixtures
- `scripts/` - utility scripts and local benchmarking helpers
- `plans/` - active implementation plans intentionally kept at the repo root
- `docs/` - metrics reference, design notes, and session writeups

## Dependencies

- Python 3.10+
- numpy, opencv-python, ultralytics, rtmlib, filterpy, httpx, fastapi, uvicorn
- Node.js 18+ (frontend)
- pytest (dev)

## Tests

```bash
pytest
```

72 tests covering ingestion, detection, pose, metrics, phases, visualization, reporter, energy, analyzer, and AI coaching.

## License

MIT
