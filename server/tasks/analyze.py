"""Background analysis task — calls the existing analyzer pipeline."""

import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from server import db
from baseball_swing_analyzer.analysis_version import ANALYSIS_VERSION

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


def _job_progress(base: float, span: float, current: int, total: int) -> float:
    if total <= 0:
        return base
    ratio = min(max(current / total, 0.0), 1.0)
    return base + span * ratio


def run_analysis(job_id: str) -> None:
    logger.info(f"[Job {job_id[:8]}] Starting analysis")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    job = db.get_job(job_id)
    if job is None:
        logger.error(f"[Job {job_id[:8]}] Not found in DB")
        return

    try:
        db.update_job(
            job_id,
            status="processing",
            progress=0.02,
            current_step="queued",
            progress_detail_current=None,
            progress_detail_total=None,
            progress_detail_label=None,
        )

        from baseball_swing_analyzer.analyzer import analyze_swing

        video_path = Path(job["video_path"])
        out_dir = Path(job["output_dir"])

        logger.info(f"[Job {job_id[:8]}] Video: {video_path}, Output: {out_dir}")
        out_dir.mkdir(parents=True, exist_ok=True)

        db.update_job(job_id, progress=0.08, current_step="loading_video")

        def on_pose_progress(current: int, total: int) -> None:
            db.update_job(
                job_id,
                progress=_job_progress(0.15, 0.5, current, total),
                current_step="pose_inference",
                progress_detail_current=current,
                progress_detail_total=total,
                progress_detail_label="frames",
            )

        result = analyze_swing(
            video_path=video_path,
            output_dir=out_dir,
            annotate=True,
            handedness="auto",
            progress_callback=on_pose_progress,
        )

        logger.info(f"[Job {job_id[:8]}] Analysis complete, computing metrics")
        db.update_job(job_id, progress=0.7, current_step="computing_metrics")

        from baseball_swing_analyzer.reporter import write_metrics_json
        write_metrics_json(result, out_dir / "metrics.json")

        db.update_job(job_id, progress=0.8, current_step="generating_coaching")

        from baseball_swing_analyzer.sport import detect_sport_profile

        result["sport_profile"] = detect_sport_profile(job["original_filename"], result)
        result["analysis_version"] = ANALYSIS_VERSION

        from baseball_swing_analyzer.ai.knowledge import generate_static_report

        coaching_lines = generate_static_report(result)
        coaching_html = "".join(f"<p>{line}</p>" for line in coaching_lines)
        (out_dir / "coaching.md").write_text(
            "\n".join(f"- {c}" for c in coaching_lines), encoding="utf-8"
        )
        result["_coaching_lines"] = coaching_lines

        db.update_job(job_id, progress=0.9, current_step="generating_3d_data")

        from baseball_swing_analyzer.export_3d import generate_swing_3d_data_from_keypoints

        keypoints_seq = result.pop("_keypoints_seq")
        viewer_segments = result.pop("_viewer_segments", [])
        phase_labels = result.get("phase_labels", [])
        fps = result.get("fps", 30.0)
        frame_data = generate_swing_3d_data_from_keypoints(
            keypoints_seq, phase_labels, fps, report=result
        )

        frames_3d_json = json.dumps(frame_data, default=str)
        (out_dir / "frames_3d.json").write_text(frames_3d_json, encoding="utf-8")
        for viewer_segment in viewer_segments:
            segment_frame_data = generate_swing_3d_data_from_keypoints(
                viewer_segment["keypoints_seq"],
                viewer_segment["phase_labels"],
                fps,
                report=viewer_segment["report"],
            )
            filename = f"frames_3d_swing_{viewer_segment['swing_number']}.json"
            (out_dir / filename).write_text(json.dumps(segment_frame_data, default=str), encoding="utf-8")

        logger.info(f"[Job {job_id[:8]}] All steps complete")
        db.update_job(
            job_id,
            status="completed",
            progress=1.0,
            current_step="done",
            progress_detail_current=None,
            progress_detail_total=None,
            progress_detail_label=None,
            metrics_json=json.dumps(result, default=str),
            analysis_version=ANALYSIS_VERSION,
            analysis_family="swing_detection",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        logger.error(f"[Job {job_id[:8]}] FAILED: {exc}\n{traceback.format_exc()}")
        db.update_job(
            job_id,
            status="failed",
            error_message=f"{exc}\n{traceback.format_exc()}",
        )
