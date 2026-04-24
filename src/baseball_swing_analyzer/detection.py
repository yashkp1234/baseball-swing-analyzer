"""Person detection using YOLOv8."""

from typing import cast

import numpy as np
from numpy.typing import NDArray

from ultralytics import YOLO

_model: YOLO | None = None


def _get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO("yolov8l.pt")
    return _model


def detect_person(
    frame: NDArray[np.uint8], model: YOLO | None = None
) -> tuple[int, int, int, int] | None:
    """Return bounding box of the largest person detected in *frame*.

    Returns ``(x1, y1, x2, y2)`` or ``None`` if no person is found.
    """
    m = model if model is not None else _get_model()
    results = m.predict(frame, verbose=False)
    if not results or not results[0].boxes:
        return None

    boxes = results[0].boxes.xyxy.cpu().numpy()
    classes = results[0].boxes.cls.cpu().numpy().astype(int)

    person_indices = np.where(classes == 0)[0]
    if person_indices.size == 0:
        return None

    person_boxes = boxes[person_indices]
    areas = (person_boxes[:, 2] - person_boxes[:, 0]) * (
        person_boxes[:, 3] - person_boxes[:, 1]
    )
    largest = person_boxes[np.argmax(areas)]
    return cast(tuple[int, int, int, int], tuple(largest.astype(int)))


def crop_person(frame: NDArray[np.uint8], bbox: tuple[int, int, int, int]) -> NDArray[np.uint8]:
    """Crop *frame* to the bounding box (x1, y1, x2, y2)."""
    x1, y1, x2, y2 = bbox
    return frame[y1:y2, x1:x2]
