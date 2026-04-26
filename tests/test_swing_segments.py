import numpy as np

from baseball_swing_analyzer.swing_segments import detect_swing_segments


def _pose_sequence(speed_peaks: list[tuple[int, int]], frames: int = 120) -> np.ndarray:
    seq = np.zeros((frames, 17, 3), dtype=float)
    seq[:, :, 2] = 1.0
    for start, end in speed_peaks:
        for t in range(start, end):
            seq[t, 9, 0] = (t - start) * 0.08
            seq[t, 10, 0] = (t - start) * 0.1
    return seq


def test_detects_single_swing_inside_long_clip() -> None:
    seq = _pose_sequence([(40, 62)])

    segments = detect_swing_segments(seq, fps=30.0)

    assert len(segments) == 1
    assert 20 <= segments[0].start_frame <= 30
    assert 60 <= segments[0].end_frame <= 72
    assert segments[0].contact_frame >= segments[0].start_frame
    assert segments[0].confidence > 0.5


def test_detects_multiple_swings() -> None:
    seq = _pose_sequence([(20, 38), (78, 96)])

    segments = detect_swing_segments(seq, fps=30.0)

    assert len(segments) == 2
    assert segments[0].end_frame < segments[1].start_frame
