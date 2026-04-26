from baseball_swing_analyzer.sport import detect_sport_profile


def test_detect_sport_profile_prefers_softball_keyword() -> None:
    profile = detect_sport_profile(
        original_filename="slowmo_softball_swing.mp4",
        metrics={"flags": {}, "pose_confidence_mean": 0.8},
    )

    assert profile["label"] == "softball"
    assert float(profile["context_confidence"]) > 0.8


def test_detect_sport_profile_prefers_baseball_keyword() -> None:
    profile = detect_sport_profile(
        original_filename="batting_practice_baseball.mov",
        metrics={"flags": {}, "pose_confidence_mean": 0.8},
    )

    assert profile["label"] == "baseball"
    assert float(profile["context_confidence"]) > 0.8


def test_detect_sport_profile_falls_back_to_unknown_without_strong_signal() -> None:
    profile = detect_sport_profile(
        original_filename="clip_001.mp4",
        metrics={"flags": {}, "pose_confidence_mean": 0.8},
    )

    assert profile["label"] == "unknown"
    assert profile["reasons"]


def test_detect_sport_profile_can_infer_baseball_from_mechanics() -> None:
    profile = detect_sport_profile(
        original_filename="clip_001.mp4",
        metrics={
            "flags": {"leg_action": "leg_kick", "finish_height": "high"},
            "x_factor_at_contact": 24.0,
            "wrist_peak_velocity_normalized": 3.1,
            "head_displacement_total": 11.0,
            "pose_confidence_mean": 0.91,
        },
    )

    assert profile["label"] == "baseball"
    assert float(profile["mechanics_confidence"]) > float(profile["context_confidence"])


def test_detect_sport_profile_can_infer_softball_from_mechanics() -> None:
    profile = detect_sport_profile(
        original_filename="clip_001.mp4",
        metrics={
            "flags": {"leg_action": "toe_tap", "finish_height": "low"},
            "x_factor_at_contact": 8.0,
            "wrist_peak_velocity_normalized": 1.1,
            "head_displacement_total": 28.0,
            "pose_confidence_mean": 0.9,
        },
    )

    assert profile["label"] == "softball"
    assert float(profile["mechanics_confidence"]) > float(profile["context_confidence"])
