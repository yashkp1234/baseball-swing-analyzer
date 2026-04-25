"""Upload endpoint — accept video, create job, start analysis in a thread."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from .. import db
from ..tasks.analyze import UPLOAD_DIR, OUTPUT_DIR, run_analysis

_executor = ThreadPoolExecutor(max_workers=2)

router = APIRouter()


@router.post("/")
async def create_job(
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

    _executor.submit(run_analysis, job_id)
    return {"job_id": job_id, "status": "queued"}