"""Upload endpoint — stream video to disk, create job, queue analysis."""

import os
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from .. import db
from ..tasks.analyze import UPLOAD_DIR, OUTPUT_DIR

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 500 * 1024 * 1024))
ALLOWED_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

router = APIRouter()


@router.post("/")
async def create_job(video: UploadFile = File(...)):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = video.filename or "video.mp4"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Unsupported extension: {ext}")

    job_id = db.create_job(
        original_filename=filename, video_path="", output_dir=""
    )
    saved_path = UPLOAD_DIR / f"{job_id}{ext}"

    bytes_written = 0
    with open(saved_path, "wb") as f:
        while chunk := await video.read(1 << 20):  # 1 MiB
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                f.close()
                saved_path.unlink(missing_ok=True)
                db.update_job(job_id, status="failed",
                              error_message=f"File exceeds {MAX_UPLOAD_BYTES} bytes")
                raise HTTPException(413, "File too large")
            f.write(chunk)

    out_dir = OUTPUT_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    db.update_job(job_id, video_path=str(saved_path), output_dir=str(out_dir))
    db.run_analysis_in_thread(job_id)
    return {"job_id": job_id, "status": "queued"}
