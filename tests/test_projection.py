import json
from pathlib import Path

from baseball_swing_analyzer.projection import ProjectionRequest, project_swing_viewer_data


def _viewer_fixture() -> dict:
    fixture_path = Path("tests/fixtures/viewer_fixture.json")
    return json.loads(fixture_path.read_text())


def test_projection_changes_frames_and_returns_estimates() -> None:
    viewer = _viewer_fixture()
    baseline_contact = viewer["frames"][viewer["contact_frame"]]["keypoints"][6][2]
    request = ProjectionRequest(x_factor_delta_deg=8.0, head_stability_delta_norm=0.08)

    result = project_swing_viewer_data(viewer, request)

    assert result["baseline"]["exit_velocity_mph"] > 0
    assert result["projection"]["exit_velocity_mph"] > result["baseline"]["exit_velocity_mph"]
    assert result["projection"]["carry_distance_ft"] > result["baseline"]["carry_distance_ft"]
    assert result["viewer"]["frames"][viewer["contact_frame"]]["keypoints"][6][2] != baseline_contact


def test_projection_clamps_extreme_inputs() -> None:
    viewer = _viewer_fixture()
    request = ProjectionRequest(x_factor_delta_deg=999.0, head_stability_delta_norm=999.0)

    result = project_swing_viewer_data(viewer, request)

    assert result["projection"]["exit_velocity_mph"] < 140
    assert result["projection"]["carry_distance_ft"] < 500
