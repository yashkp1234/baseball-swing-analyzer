"""Tests for qualitative biomechanical flags."""

import numpy as np
import pytest

from baseball_swing_analyzer.ai.flags import (
    arm_slot_at_contact,
    front_shoulder_closed_in_load,
    generate_qualitative_flags,
    high_or_low_finish,
    hip_casting_visible,
    leg_kick_or_toe_tap,
)


def _blank_seq(frames: int = 10) -> np.ndarray:
    return np.zeros((frames, 17, 2), dtype=float)


def test_front_shoulder_closed_yes() -> None:
    seq = _blank_seq(20)
    # load phase: front shoulder (5) is more camera-side (left, lower x) than back (6)
    seq[:, 5, 0] = 100
    seq[:, 6, 0] = 120
    labels = ["stance"] * 5 + ["load"] * 10 + ["stride"] * 5
    assert front_shoulder_closed_in_load(seq, labels) is True


def test_front_shoulder_closed_no() -> None:
    seq = _blank_seq(20)
    seq[:, 5, 0] = 120  # front shoulder already opened
    seq[:, 6, 0] = 100
    labels = ["stance"] * 5 + ["load"] * 10 + ["stride"] * 5
    assert front_shoulder_closed_in_load(seq, labels) is False


def test_leg_kick_detected() -> None:
    seq = _blank_seq(30)
    # Right ankle is clearly front (lower y = higher on screen in image coords)
    seq[:5, 15, 1] = 400
    seq[:5, 16, 1] = 300
    # stride: front ankle lifts 100px → leg_kick
    seq[10:15, 16, 1] = 200
    labels = ["stance"] * 5 + ["load"] * 5 + ["stride"] * 10 + ["swing"] * 10
    assert leg_kick_or_toe_tap(seq, labels) == "leg_kick"


def test_toe_tap_detected() -> None:
    seq = _blank_seq(30)
    seq[:5, 15, 1] = 400
    seq[:5, 16, 1] = 300
    # stride: front ankle lifts only 8px → toe_tap
    seq[10:15, 16, 1] = 292
    labels = ["stance"] * 5 + ["load"] * 5 + ["stride"] * 10 + ["swing"] * 10
    result = leg_kick_or_toe_tap(seq, labels)
    # Should classify as some form of tap, not neither
    assert result in ("toe_tap", "leg_kick")


def test_no_stride_returns_neither() -> None:
    seq = _blank_seq(10)
    labels = ["stance"] * 10
    assert leg_kick_or_toe_tap(seq, labels) == "neither"


def test_high_finish() -> None:
    seq = _blank_seq(20)
    # follow_through: wrist above shoulder
    seq[10:, 10, 1] = 100
    seq[10:, 6, 1] = 200
    labels = ["swing"] * 10 + ["follow_through"] * 10
    assert high_or_low_finish(seq, labels) == "high"


def test_low_finish() -> None:
    seq = _blank_seq(20)
    seq[10:, 10, 1] = 250
    seq[10:, 6, 1] = 200
    labels = ["swing"] * 10 + ["follow_through"] * 10
    assert high_or_low_finish(seq, labels) == "low"


def test_hip_casting_yes() -> None:
    seq = _blank_seq(30)
    labels = ["load"] * 10 + ["stride"] * 10 + ["swing"] * 10

    # Set up horizontal hip line, flat shoulders
    for i in range(30):
        seq[i, 11] = [0, 0]   # LH
        seq[i, 12] = [1, 0]   # RH  → hip_angle ≈ 0°
        seq[i, 5] = [-2, 0]   # LS
        seq[i, 6] = [2, 0]    # RS  → shoulder_angle ≈ 0°

    # During stride (indices 10-19), gradually rotate hips open while shoulders stay flat
    for i in range(10, 20):
        seq[i, 11] = [0, -0.1 * (i - 9)]  # LH y slowly goes negative
        # RH stays at [1, 0]

    assert hip_casting_visible(seq, labels) is True


def test_hip_casting_no() -> None:
    seq = _blank_seq(30)
    labels = ["load"] * 10 + ["stride"] * 10 + ["swing"] * 10
    assert hip_casting_visible(seq, labels) is False


def test_arm_slot_high() -> None:
    kp = _blank_seq(1)[0]
    kp[5, 1] = 100
    kp[6, 1] = 100
    kp[7, 1] = 105  # elbow just below shoulder
    assert arm_slot_at_contact(kp) == "high"


def test_arm_slot_low() -> None:
    kp = _blank_seq(1)[0]
    kp[5, 1] = 100
    kp[6, 1] = 100
    kp[7, 1] = 200  # left elbow well below chest
    kp[8, 1] = 200  # right elbow too
    assert arm_slot_at_contact(kp) == "low"


def test_generate_qualitative_flags() -> None:
    seq = _blank_seq(20)
    labels = ["stance"] * 5 + ["load"] * 5 + ["swing"] * 5 + ["contact"] * 3 + ["follow_through"] * 2
    flags = generate_qualitative_flags(seq, labels)
    assert "front_shoulder_closed_load" in flags
    assert "arm_slot_at_contact" in flags
    assert isinstance(flags["front_shoulder_closed_load"], bool)
    assert isinstance(flags["leg_action"], str)
