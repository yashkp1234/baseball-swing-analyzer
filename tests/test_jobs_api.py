"""Tests for job status, progress telemetry, artifact serving, and projections."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi import HTTPException, Request

from server.api.artifacts import build_artifact_response
from server.api.projection import ProjectionPayload, project_job
from server.api.results import get_results
from server.api.status import get_status
from server.tasks.analyze import run_analysis


@pytest.mark.asyncio
async def test_status_endpoint_returns_progress_detail_fields() -> None:
    with patch("server.api.status.db.get_job", return_value={
        "id": "job-123",
        "status": "processing",
        "progress": 0.42,
        "current_step": "pose_inference",
        "progress_detail_current": 12,
        "progress_detail_total": 48,
        "progress_detail_label": "frames",
        "error_message": None,
    }):
        body = await get_status("job-123")

    assert body["progress_detail_current"] == 12
    assert body["progress_detail_total"] == 48
    assert body["progress_detail_label"] == "frames"


def test_run_analysis_emits_detail_progress_fields(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    updates: list[dict] = []

    def capture_update(_job_id: str, **fields):
        updates.append(fields)

    fake_result = {
        "phase_labels": ["load", "contact"],
        "fps": 24.0,
        "_keypoints_seq": MagicMock(),
    }

    def fake_analyze_swing(**kwargs):
        progress_callback = kwargs["progress_callback"]
        progress_callback(12, 48)
        return fake_result

    with patch("server.tasks.analyze.db.get_job", return_value={
        "id": "job-123",
        "video_path": str(tmp_path / "video.mp4"),
        "output_dir": str(out_dir),
    }), \
         patch("server.tasks.analyze.db.update_job", side_effect=capture_update), \
         patch("baseball_swing_analyzer.analyzer.analyze_swing", side_effect=fake_analyze_swing), \
         patch("baseball_swing_analyzer.reporter.write_metrics_json"), \
         patch("baseball_swing_analyzer.ai.knowledge.generate_static_report", return_value=["Good move"]), \
         patch("baseball_swing_analyzer.export_3d.generate_swing_3d_data_from_keypoints", return_value={"frames": []}):
        run_analysis("job-123")

    assert any(
        update.get("current_step") == "pose_inference" and update.get("progress_detail_label") == "frames"
        for update in updates
    )


def test_run_analysis_writes_per_swing_viewer_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"

    fake_result = {
        "phase_labels": ["load", "contact"],
        "fps": 24.0,
        "contact_frame": 1,
        "_keypoints_seq": np.zeros((2, 17, 3)).tolist(),
        "_viewer_segments": [
            {
                "swing_number": 1,
                "keypoints_seq": np.zeros((3, 17, 3)).tolist(),
                "phase_labels": ["load", "contact", "finish"],
                "report": {"fps": 24.0, "frames": 3, "contact_frame": 1},
            },
            {
                "swing_number": 2,
                "keypoints_seq": np.zeros((4, 17, 3)).tolist(),
                "phase_labels": ["load", "stride", "contact", "finish"],
                "report": {"fps": 24.0, "frames": 4, "contact_frame": 2},
            },
        ],
    }

    def fake_generate(keypoints_seq, phase_labels, fps, report):
        return {
            "total_frames": len(keypoints_seq),
            "phase_labels": phase_labels,
            "contact_frame": report["contact_frame"],
        }

    with patch("server.tasks.analyze.db.get_job", return_value={
        "id": "job-123",
        "video_path": str(tmp_path / "video.mp4"),
        "output_dir": str(out_dir),
        "original_filename": "swing.mp4",
    }), \
         patch("server.tasks.analyze.db.update_job"), \
         patch("baseball_swing_analyzer.analyzer.analyze_swing", return_value=fake_result), \
         patch("baseball_swing_analyzer.reporter.write_metrics_json"), \
         patch("baseball_swing_analyzer.sport.detect_sport_profile", return_value={"label": "baseball"}), \
         patch("baseball_swing_analyzer.ai.knowledge.generate_static_report", return_value=["Good move"]), \
         patch("baseball_swing_analyzer.export_3d.generate_swing_3d_data_from_keypoints", side_effect=fake_generate):
        run_analysis("job-123")

    assert (out_dir / "frames_3d_swing_1.json").exists()
    assert (out_dir / "frames_3d_swing_2.json").exists()


@pytest.mark.asyncio
async def test_results_endpoint_returns_analysis_summary() -> None:
    metrics = {
        "contact_frame": 12,
        "sport_profile": {
            "label": "softball",
            "confidence": 0.92,
            "context_confidence": 0.95,
            "mechanics_confidence": 0.5,
            "reasons": ["Filename strongly suggests softball"],
        },
        "analysis": {
            "pose_device": "cuda",
            "sampled_frames": 72,
            "effective_analysis_fps": 23.4,
            "analysis_duration_ms": 5100.0,
        },
        "_coaching_lines": ["Good move"],
    }

    with patch("server.api.results.db.get_job", return_value={
        "id": "job-123",
        "status": "completed",
        "metrics_json": __import__("json").dumps(metrics),
    }):
        body = await get_results("job-123")

    assert body["analysis"]["pose_device"] == "cuda"
    assert body["analysis"]["sampled_frames"] == 72
    assert body["sport_profile"]["label"] == "softball"
    assert "analysis" not in body["metrics"]


@pytest.mark.asyncio
async def test_results_endpoint_returns_analysis_freshness_metadata() -> None:
    metrics = {
        "contact_frame": 12,
        "analysis": {"pose_device": "cuda"},
        "_coaching_lines": ["Good move"],
    }

    with patch("server.api.results.db.get_job", return_value={
        "id": "job-123",
        "status": "completed",
        "metrics_json": __import__("json").dumps(metrics),
        "analysis_version": "2026-04-swing-redesign-v1",
    }):
        body = await get_results("job-123")

    assert body["analysis_version"] == "2026-04-swing-redesign-v1"
    assert body["is_current_analysis"] is True


@pytest.mark.asyncio
async def test_artifact_response_honors_byte_range_requests(tmp_path: Path) -> None:
    artifact_path = tmp_path / "annotated.mp4"
    artifact_path.write_bytes(b"0123456789")
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/jobs/job-123/artifacts/annotated.mp4",
            "headers": [(b"range", b"bytes=2-5")],
        }
    )

    response = await build_artifact_response(
        request=request,
        file_path=artifact_path,
        media_type="video/mp4",
        filename="annotated.mp4",
    )

    assert response.status_code == 206
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == "bytes 2-5/10"
    assert response.headers["content-length"] == "4"


@pytest.mark.asyncio
async def test_projection_endpoint_returns_projected_viewer(tmp_path: Path) -> None:
    fixture = Path("tests/fixtures/viewer_fixture.json")
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    viewer = __import__("json").loads(fixture.read_text())
    (out_dir / "frames_3d.json").write_text(__import__("json").dumps(viewer))
    sport_profile = {
        "label": "unknown",
        "confidence": 0.35,
        "context_confidence": 0.2,
        "mechanics_confidence": 0.45,
        "reasons": ["No strong baseball or softball signal detected"],
    }

    with patch("server.api.projection.db.get_job", return_value={
        "id": "job-123",
        "status": "completed",
        "output_dir": str(out_dir),
        "metrics_json": __import__("json").dumps({"sport_profile": sport_profile}),
    }):
        payload = ProjectionPayload(x_factor_delta_deg=6, head_stability_delta_norm=0.06)
        body = await project_job("job-123", payload)

    assert "baseline" in body
    assert "projection" in body
    assert "viewer" in body
    assert body["sport_profile"]["label"] == "unknown"
    assert any("generic hitting calibration" in note.lower() for note in body["projection"]["notes"])
    assert body["projection"]["exit_velocity_mph"] > body["baseline"]["exit_velocity_mph"]


@pytest.mark.asyncio
async def test_projection_endpoint_uses_requested_swing_artifact(tmp_path: Path) -> None:
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    primary_viewer = {"frames": [{"keypoints": [[0.0, 0.0, 0.0]] * 17}], "contact_frame": 0, "phase_labels": ["contact"], "metrics": {}}
    swing_two_viewer = {"frames": [{"keypoints": [[1.0, 1.0, 1.0]] * 17}, {"keypoints": [[2.0, 2.0, 2.0]] * 17}], "contact_frame": 1, "phase_labels": ["load", "contact"], "metrics": {}}
    (out_dir / "frames_3d.json").write_text(__import__("json").dumps(primary_viewer))
    (out_dir / "frames_3d_swing_2.json").write_text(__import__("json").dumps(swing_two_viewer))

    with patch("server.api.projection.db.get_job", return_value={
        "id": "job-123",
        "status": "completed",
        "output_dir": str(out_dir),
        "metrics_json": __import__("json").dumps({}),
    }):
        body = await project_job("job-123", ProjectionPayload(), 2)

    assert body["viewer"]["contact_frame"] == 1
    assert len(body["viewer"]["frames"]) == 2


@pytest.mark.asyncio
async def test_projection_endpoint_404_for_missing_job() -> None:
    with patch("server.api.projection.db.get_job", return_value=None):
        payload = ProjectionPayload(x_factor_delta_deg=6, head_stability_delta_norm=0.06)
        with pytest.raises(HTTPException) as exc_info:
            await project_job("not-a-real-job", payload)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_projection_endpoint_409_without_artifacts(tmp_path: Path) -> None:
    with patch("server.api.projection.db.get_job", return_value={
        "id": "job-123",
        "status": "completed",
        "output_dir": str(tmp_path / "missing-output"),
    }):
        payload = ProjectionPayload(x_factor_delta_deg=6, head_stability_delta_norm=0.06)
        with pytest.raises(HTTPException) as exc_info:
            await project_job("job-123", payload)

    assert exc_info.value.status_code == 409
