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

    assert result["baseline"]["estimate_basis"] == "pose_proxy"
    assert result["baseline"]["exit_velocity_mph_low"] < result["baseline"]["exit_velocity_mph_high"]
    assert result["baseline"]["carry_distance_ft_low"] < result["baseline"]["carry_distance_ft_high"]
    assert result["projection"]["exit_velocity_mph"] > result["baseline"]["exit_velocity_mph"]
    assert result["projection"]["carry_distance_ft"] > result["baseline"]["carry_distance_ft"]
    assert result["viewer"]["frames"][viewer["contact_frame"]]["keypoints"][6][2] != baseline_contact


def test_projection_clamps_extreme_inputs() -> None:
    viewer = _viewer_fixture()
    request = ProjectionRequest(x_factor_delta_deg=999.0, head_stability_delta_norm=999.0)

    result = project_swing_viewer_data(viewer, request)

    assert result["projection"]["exit_velocity_mph"] < 140
    assert result["projection"]["carry_distance_ft"] < 500


def test_projection_head_stability_moves_nose_toward_baseline() -> None:
    viewer = _viewer_fixture()
    initial_nose = viewer["frames"][0]["keypoints"][0]
    contact_nose = viewer["frames"][viewer["contact_frame"]]["keypoints"][0]
    request = ProjectionRequest(head_stability_delta_norm=0.08)

    result = project_swing_viewer_data(viewer, request)

    projected_nose = result["viewer"]["frames"][viewer["contact_frame"]]["keypoints"][0]
    baseline_drift = abs(contact_nose[0] - initial_nose[0]) + abs(contact_nose[2] - initial_nose[2])
    projected_drift = abs(projected_nose[0] - initial_nose[0]) + abs(projected_nose[2] - initial_nose[2])

    assert projected_drift < baseline_drift


def test_named_lower_half_fix_returns_metadata() -> None:
    viewer = _viewer_fixture()
    request = ProjectionRequest(fix_id="lower_half_timing")

    result = project_swing_viewer_data(viewer, request)

    assert result["fix"]["id"] == "lower_half_timing"
    assert "lower half" in result["fix"]["label"].lower()
    assert result["projection"]["score"] >= result["baseline"]["score"]
