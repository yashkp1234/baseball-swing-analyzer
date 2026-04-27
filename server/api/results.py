"""Results endpoint — return completed metrics, coaching, and 3D data."""

import json

from fastapi import APIRouter

from baseball_swing_analyzer.analysis_version import ANALYSIS_VERSION

from .. import db

router = APIRouter()


def _coaching_lines(lines: list[str] | None) -> list[dict[str, str]] | None:
    if lines is None:
        return None

    out: list[dict[str, str]] = []
    for line in lines:
        lower = line.lower()
        if any(word in lower for word in ("good", "solid", "strong")):
            tone = "good"
        elif any(word in lower for word in ("improvement", "consider", "watch", "focus")):
            tone = "warn"
        else:
            tone = "info"
        out.append({"tone": tone, "text": line})
    return out


@router.get("/{job_id}/results")
async def get_results(job_id: str):
    job = db.get_job(job_id)
    if job is None:
        return {"error": "job not found"}
    if job["status"] not in ("completed", "failed"):
        return {"error": "job not ready", "status": job["status"]}

    metrics = json.loads(job["metrics_json"]) if job["metrics_json"] else None
    coaching = metrics.pop("_coaching_lines", None) if metrics else None
    analysis = metrics.pop("analysis", None) if metrics else None
    sport_profile = metrics.pop("sport_profile", None) if metrics else None
    return {
        "job_id": job["id"],
        "status": job["status"],
        "metrics": metrics,
        "analysis": analysis,
        "sport_profile": sport_profile,
        "coaching": _coaching_lines(coaching),
        "frames_3d_url": f"/api/jobs/{job['id']}/artifacts/frames_3d.json",
        "analysis_version": job.get("analysis_version"),
        "is_current_analysis": job.get("analysis_version") == ANALYSIS_VERSION,
    }
