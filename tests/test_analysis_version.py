from baseball_swing_analyzer.analysis_version import ANALYSIS_VERSION


def test_analysis_version_constant_is_nonempty() -> None:
    assert ANALYSIS_VERSION.startswith("2026-04-")
