"""Tests for person detection."""

from unittest.mock import MagicMock

import numpy as np
import pytest
from numpy.typing import NDArray

from baseball_swing_analyzer.detection import detect_person


def _mock_results(boxes: NDArray[np.floating], classes: NDArray[np.floating]) -> list:
    """Build a minimal mock of ultralytics Results."""
    result = MagicMock()
    result.boxes.xyxy.cpu().numpy.return_value = boxes
    result.boxes.cls.cpu().numpy.return_value = classes
    return [result]


def test_detect_person_no_result() -> None:
    mock_model = MagicMock()
    mock_model.predict.return_value = [MagicMock(boxes=MagicMock(xyxy=MagicMock()))]
    mock_model.predict.return_value[0].boxes = None
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    assert detect_person(frame, model=mock_model) is None


def test_detect_person_largest() -> None:
    mock_model = MagicMock()
    # Three boxes; person (cls=0) at index 0 and 2, largest at index 2
    boxes = np.array(
        [
            [10, 10, 20, 20],  # area 100, cls 0
            [100, 100, 110, 110],  # area 100, cls 5 (not person)
            [0, 0, 50, 50],  # area 2500, cls 0
        ],
        dtype=np.float32,
    )
    classes = np.array([0, 5, 0], dtype=np.float32)
    mock_model.predict.return_value = _mock_results(boxes, classes)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    bbox = detect_person(frame, model=mock_model)
    assert bbox == (0, 0, 50, 50)


def test_detect_person_no_person_class() -> None:
    mock_model = MagicMock()
    boxes = np.array([[0, 0, 10, 10]], dtype=np.float32)
    classes = np.array([5], dtype=np.float32)
    mock_model.predict.return_value = _mock_results(boxes, classes)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    assert detect_person(frame, model=mock_model) is None
