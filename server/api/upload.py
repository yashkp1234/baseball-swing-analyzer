"""Upload endpoint — accept video, create job, start analysis."""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, BackgroundTasks

from .. import db
from ..tasks.analyze import UPLOAD_DIR, OUTPUT_DIR, run_analysis

router = APIRouter()


@router.post("/")
async def create_job(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ext = Path(video.filename or "video.mp4").suffix or ".mp4"
    job_id = db.create_job(
        original_filename=video.filename or "video.mp4",
        video_path="",
        output_dir="",
    )

    saved_path = UPLOAD_DIR / f"{job_id}{ext}"
    content = await video.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    out_dir = OUTPUT_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    db.update_job(job_id, video_path=str(saved_path), output_dir=str(out_dir))

    background_tasks.add_task(run_analysis, job_id)
    return {"job_id": job_id, "status": "queued"}