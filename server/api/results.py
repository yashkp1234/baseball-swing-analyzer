"""Results endpoint — return completed metrics, coaching, and 3D data."""

import json

from fastapi import APIRouter

from .. import db

router = APIRouter()


@router.get("/{job_id}/results")
async def get_results(job_id: str):
    job = db.get_job(job_id)
    if job is None:
        return {"error": "job not found"}
    if job["status"] not in ("completed", "failed"):
        return {"error": "job not ready", "status": job["status"]}

    metrics = json.loads(job["metrics_json"]) if job["metrics_json"] else None
    return {
        "job_id": job["id"],
        "status": job["status"],
        "metrics": metrics,
        "coaching": metrics.pop("_coaching_lines", None) if metrics else None,
        "frames_3d_url": f"/api/jobs/{job['id']}/artifacts/frames_3d.json",
    }
