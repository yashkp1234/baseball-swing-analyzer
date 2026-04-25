"""Status endpoint — return job progress."""

from fastapi import APIRouter

from .. import db

router = APIRouter()


@router.get("/{job_id}")
async def get_status(job_id: str):
    job = db.get_job(job_id)
    if job is None:
        return {"error": "job not found"}
    return {
        "job_id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "current_step": job["current_step"],
        "error_message": job["error_message"],
    }