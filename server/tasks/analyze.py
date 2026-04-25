"""Background analysis task — calls the existing analyzer pipeline."""

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

from server import db

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


def run_analysis(job_id: str) -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    job = db.get_job(job_id)
    if job is None:
        return

    try:
        db.update_job(job_id, status="processing", progress=0.1, current_step="detecting_hitter")

        from baseball_swing_analyzer.analyzer import analyze_swing
        from baseball_swing_analyzer.reporter import write_metrics_json

        video_path = Path(job["video_path"])
        out_dir = Path(job["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)

        result = analyze_swing(
            video_path=video_path,
            output_dir=out_dir,
            annotate=True,
            handedness="auto",
        )

        db.update_job(job_id, progress=0.6, current_step="computing_metrics")
        write_metrics_json(result, out_dir / "metrics.json")

        db.update_job(job_id, progress=0.75, current_step="generating_coaching")

        from baseball_swing_analyzer.ai.flags import generate_qualitative_flags
        from baseball_swing_analyzer.ai.knowledge import generate_static_report

        coaching_lines = generate_static_report(result)
        coaching_html = "".join(f"<p>{line}</p>" for line in coaching_lines)
        (out_dir / "coaching.md").write_text(
            "\n".join(f"- {c}" for c in coaching_lines), encoding="utf-8"
        )

        db.update_job(job_id, progress=0.85, current_step="generating_3d_data")

        from baseball_swing_analyzer.export_3d import generate_swing_3d_data

        frame_data = generate_swing_3d_data(result)
        frames_3d_json = json.dumps(frame_data)
        (out_dir / "frames_3d.json").write_text(frames_3d_json, encoding="utf-8")

        db.update_job(
            job_id,
            status="completed",
            progress=1.0,
            current_step="done",
            metrics_json=json.dumps(result),
            coaching_html=coaching_html,
            frames_3d_json=frames_3d_json,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        db.update_job(
            job_id,
            status="failed",
            error_message=f"{exc}\n{traceback.format_exc()}",
        )