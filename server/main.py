"""FastAPI — single synchronous endpoint. Upload a video, get results."""

import json
import logging
import uuid
from pathlib import Path

import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("swingmetrics")

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

app = FastAPI(title="SwingMetrics API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analyze")
def analyze(video: UploadFile = File(...)):
    """Upload a swing video, run the full pipeline, return all results."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    job_id = str(uuid.uuid4())
    ext = Path(video.filename or "video.mp4").suffix or ".mp4"
    saved_path = UPLOAD_DIR / f"{job_id}{ext}"

    logger.info(f"[{job_id[:8]}] Receiving upload: {video.filename} ({video.size if hasattr(video, 'size') else '?'} bytes)")

    content = video.file.read()
    saved_path.write_bytes(content)
    logger.info(f"[{job_id[:8]}] Saved to {saved_path} ({len(content)} bytes)")

    out_dir = OUTPUT_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"[{job_id[:8]}] Step 1/5: Loading analyzer...")
        from baseball_swing_analyzer.analyzer import analyze_swing

        logger.info(f"[{job_id[:8]}] Step 2/5: Running analysis...")
        result = analyze_swing(
            video_path=saved_path,
            output_dir=out_dir,
            annotate=True,
            handedness="auto",
        )
        logger.info(f"[{job_id[:8]}] Step 2/5: Analysis complete — {result.get('frames')} frames, contact at frame {result.get('contact_frame')}")

        logger.info(f"[{job_id[:8]}] Step 3/5: Writing metrics and coaching...")
        from baseball_swing_analyzer.reporter import write_metrics_json
        from baseball_swing_analyzer.ai.knowledge import generate_static_report
        from baseball_swing_analyzer.export_3d import generate_swing_3d_data_from_keypoints

        write_metrics_json(result, out_dir / "metrics.json")

        coaching_lines = generate_static_report(result)
        coaching_html = "".join(f"<p>{line}</p>" for line in coaching_lines)
        (out_dir / "coaching.md").write_text(
            "\n".join(f"- {c}" for c in coaching_lines), encoding="utf-8"
        )
        logger.info(f"[{job_id[:8]}] Step 3/5: Coaching report written ({len(coaching_lines)} lines)")

        logger.info(f"[{job_id[:8]}] Step 4/5: Generating 3D data...")
        kps_path = out_dir / "keypoints.npy"
        if kps_path.exists():
            keypoints_seq = np.load(str(kps_path))
            frame_data = generate_swing_3d_data_from_keypoints(
                keypoints_seq, result.get("phase_labels", []), result.get("fps", 30.0), report=result
            )
        else:
            frame_data = generate_swing_3d_data_from_keypoints.__wrapped__(
                np.zeros((1, 17, 3)), ["idle"], 30.0
            ) if hasattr(generate_swing_3d_data_from_keypoints, "__wrapped__") else {"error": "no keypoints"}

        frames_3d_json = json.dumps(frame_data, default=str)
        (out_dir / "frames_3d.json").write_text(frames_3d_json, encoding="utf-8")
        logger.info(f"[{job_id[:8]}] Step 4/5: 3D data generated ({len(frame_data.get('frames', []))} frames)")

        logger.info(f"[{job_id[:8]}] Step 5/5: Done! Returning results.")
        return {
            "status": "completed",
            "job_id": job_id,
            "metrics": result,
            "coaching_html": coaching_html,
            "frames_3d": frame_data,
        }

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"[{job_id[:8]}] FAILED: {exc}\n{tb}")
        return {
            "status": "failed",
            "job_id": job_id,
            "error": f"{exc}",
            "metrics": None,
            "coaching_html": None,
            "frames_3d": None,
        }


@app.get("/api/artifacts/{job_id}/{filename}")
async def get_artifact(job_id: str, filename: str):
    file_path = OUTPUT_DIR / job_id / filename
    if not file_path.exists():
        logger.warning(f"Artifact not found: {file_path}")
        return {"error": "not found"}
    logger.info(f"Serving artifact: {file_path}")
    media_types = {".mp4": "video/mp4", ".json": "application/json", ".md": "text/markdown"}
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(file_path, media_type=media_type, filename=filename)