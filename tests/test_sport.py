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
