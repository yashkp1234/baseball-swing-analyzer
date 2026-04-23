"""Basic tests for the swing analyzer."""

import pytest
from baseball_swing_analyzer.analyzer import analyze_swing


def test_analyze_swing_not_implemented():
    with pytest.raises(NotImplementedError):
        analyze_swing({})

