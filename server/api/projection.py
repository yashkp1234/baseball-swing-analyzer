import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from baseball_swing_analyzer.projection import ProjectionRequest, project_swing_viewer_data

from .. import db

router = APIRouter()


class ProjectionPayload(BaseModel):
    x_factor_delta_deg: float = 0.0
    head_stability_delta_norm: float = 0.0
    fix_id: str | None = None


@router.post("/{job_id}/projection")
async def project_job(job_id: str, payload: ProjectionPayload):
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="job artifacts unavailable")

    file_path = Path(job["output_dir"]) / "frames_3d.json"
    if not file_path.exists():
        raise HTTPException(status_code=409, detail="job artifacts unavailable")

    viewer_data = json.loads(file_path.read_text())
    metrics_payload = json.loads(job["metrics_json"]) if job.get("metrics_json") else {}
    sport_profile = metrics_payload.get("sport_profile")
    if sport_profile is not None:
        viewer_data.setdefault("metrics", {})["sport_profile"] = sport_profile
    request = ProjectionRequest(
        x_factor_delta_deg=payload.x_factor_delta_deg,
        head_stability_delta_norm=payload.head_stability_delta_norm,
        fix_id=payload.fix_id,
    )
    projected = project_swing_viewer_data(viewer_data, request)
    projected["sport_profile"] = sport_profile
    return projected
