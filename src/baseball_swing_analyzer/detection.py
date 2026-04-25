"""Person detection and tracking using YOLOv8 + ByteTrack."""

from typing import cast

import numpy as np
from numpy.typing import NDArray
from ultralytics import YOLO

_model: YOLO | None = None
_target_track_id: int | None = None


def _get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO("yolov8l.pt")
    return _model


def reset_tracker() -> None:
    """Reset the persistent track target so the next video starts fresh."""
    global _target_track_id
    _target_track_id = None


def detect_person(
    frame: NDArray[np.uint8],
    model: YOLO | None = None,
    tracker: str | None = "bytetrack.yaml",
) -> tuple[int, int, int, int] | None:
    """Return bounding box of the tracked (or largest) person in *frame*.

    When *tracker* is provided, YOLOv8's built-in tracker (ByteTrack, etc.)
    is used. The first frame's largest person becomes the persistent target.
    Subsequent frames return the same track if still visible, falling back
    to the last known bbox briefly, then reassigning if the track is lost.

    Parameters
    ----------
    frame :
        Input BGR image.
    model :
        Optional pre-loaded YOLO model.
    tracker :
        Tracker config YAML (e.g. ``"bytetrack.yaml"``). Pass ``None`` for
        per-frame detection (old behavior).

    Returns
    -------
    ``(x1, y1, x2, y2)`` or ``None``.
    """
    global _target_track_id
    m = model if model is not None else _get_model()

    if tracker is not None:
        results = m.track(frame, tracker=tracker, persist=True, verbose=False)
    else:
        results = m.predict(frame, verbose=False)

    if not results or not results[0].boxes:
        return None

    boxes = results[0].boxes.xyxy.cpu().numpy()
    classes = results[0].boxes.cls.cpu().numpy().astype(int)

    person_indices = np.where(classes == 0)[0]
    if person_indices.size == 0:
        return None

    person_boxes = boxes[person_indices]

    # Tracking mode: use persistent track ID
    if tracker is not None and results[0].boxes.id is not None:
        track_ids = results[0].boxes.id.int().cpu().numpy()
        person_tids = track_ids[person_indices]

        # First frame: pick largest person as target
        if _target_track_id is None:
            areas = (person_boxes[:, 2] - person_boxes[:, 0]) * (
                person_boxes[:, 3] - person_boxes[:, 1]
            )
            _target_track_id = int(person_tids[np.argmax(areas)])

        # Search for the target track
        for box, tid in zip(person_boxes, person_tids):
            if int(tid) == _target_track_id:
                return cast(tuple[int, int, int, int], tuple(box.astype(int)))

        # Target lost — fall back to largest person and reassign
        areas = (person_boxes[:, 2] - person_boxes[:, 0]) * (
            person_boxes[:, 3] - person_boxes[:, 1]
        )
        best_idx = int(np.argmax(areas))
        _target_track_id = int(person_tids[best_idx])
        return cast(tuple[int, int, int, int], tuple(person_boxes[best_idx].astype(int)))

    # No tracker: always return largest person
    areas = (person_boxes[:, 2] - person_boxes[:, 0]) * (
        person_boxes[:, 3] - person_boxes[:, 1]
    )
    largest = person_boxes[np.argmax(areas)]
    return cast(tuple[int, int, int, int], tuple(largest.astype(int)))


def crop_person(
    frame: NDArray[np.uint8], bbox: tuple[int, int, int, int]
) -> NDArray[np.uint8]:
    """Crop *frame* to the bounding box (x1, y1, x2, y2)."""
    x1, y1, x2, y2 = bbox
    return frame[y1:y2, x1:x2]
