"""Artifact endpoint — serve annotated video and output files."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from .. import db

router = APIRouter()


@router.get("/{job_id}/artifacts/{filename}")
async def get_artifact(job_id: str, filename: str):
    job = db.get_job(job_id)
    if job is None:
        return {"error": "job not found"}

    file_path = Path(job["output_dir"]) / filename
    if not file_path.exists():
        return {"error": "file not found"}

    media_types = {
        ".mp4": "video/mp4",
        ".json": "application/json",
        ".md": "text/markdown",
        ".html": "text/html",
        ".png": "image/png",
        ".jpg": "image/jpeg",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(file_path, media_type=media_type, filename=filename)