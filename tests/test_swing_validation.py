from pathlib import Path

import numpy as np

from baseball_swing_analyzer.benchmarks import load_benchmarks
from baseball_swing_analyzer.swing_validation import (
    extract_clip_features,
    HeuristicSwingValidator,
    SwingCandidate,
    VisionSwingValidator,
)


def test_load_benchmarks_reads_expected_cases() -> None:
    clips = load_benchmarks(Path("data/videos/benchmarks/manifest.json"))
    ids = {clip.id for clip in clips}
    assert "long_multi_swing" in ids
    assert "netted_cage_single_swing" in ids


def test_rejected_candidates_do_not_become_swing_segments() -> None:
    validator = HeuristicSwingValidator()
    decision = validator.classify_candidate(SwingCandidate(0, 3, "motion"))
    assert decision.accepted is False


def test_vision_validator_rejects_load_only_window() -> None:
    validator = VisionSwingValidator()
    decision = validator.classify_candidate(
        SwingCandidate(10, 30, "motion"),
        clip_features={"bat_visible": True, "has_forward_commit": False},
    )
    assert decision.accepted is False
    assert decision.label == "load_only"


def test_extract_clip_features_flags_late_peak_without_follow_through() -> None:
    seq = np.zeros((16, 17, 3), dtype=np.float32)
    seq[:, 5, 0] = -0.3
    seq[:, 6, 0] = 0.3
    seq[:, 11, 0] = -0.25
    seq[:, 12, 0] = 0.25
    seq[:, 5, 1] = seq[:, 6, 1] = 0.2
    seq[:, 11, 1] = seq[:, 12, 1] = 0.8

    seq[:14, 9, 0] = np.linspace(0.0, 0.15, 14)
    seq[:14, 10, 0] = np.linspace(0.1, 0.25, 14)
    seq[14:, 9, 0] = [1.1, 1.15]
    seq[14:, 10, 0] = [1.2, 1.25]
    seq[:, 9, 1] = np.linspace(0.5, 0.35, 16)
    seq[:, 10, 1] = np.linspace(0.55, 0.4, 16)

    features = extract_clip_features(seq, fps=30.0)

    assert features["peak_velocity_frame_ratio"] > 0.8
    assert features["has_follow_through"] is False


def test_vision_validator_accepts_committed_swing_shape_without_bat_detection() -> None:
    validator = VisionSwingValidator()
    decision = validator.classify_candidate(
        SwingCandidate(10, 30, "motion"),
        clip_features={
            "bat_visible": False,
            "has_forward_commit": True,
            "has_follow_through": True,
            "hand_path_arc_ratio": 1.4,
            "net_hand_displacement_ratio": 0.8,
            "peak_velocity_frame_ratio": 0.55,
            "rotation_range_deg": 18.0,
        },
    )

    assert decision.accepted is True
    assert decision.label == "swing"
