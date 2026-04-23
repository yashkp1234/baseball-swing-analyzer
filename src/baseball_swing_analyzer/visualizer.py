"""Visualization helpers for pose and bounding boxes."""

import cv2
import numpy as np
from numpy.typing import NDArray


COCO_SKELETON: list[tuple[int, int]] = [
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 6),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
]


def draw_skeleton(
    frame: NDArray[np.uint8],
    keypoints: NDArray[np.floating],
    color: tuple[int, int, int] = (0, 255, 0),
) -> NDArray[np.uint8]:
    """Draw COCO skeleton on *frame*.

    *keypoints* must have shape ``(17, 3)`` and contain ``(x, y, score)``.
    Only limbs for which both joints have a positive score are drawn.
    """
    out = frame.copy()
    for a, b in COCO_SKELETON:
        xa, ya, sa = keypoints[a]
        xb, yb, sb = keypoints[b]
        if sa <= 0 or sb <= 0:
            continue
        pt_a = (int(round(xa)), int(round(ya)))
        pt_b = (int(round(xb)), int(round(yb)))
        cv2.line(out, pt_a, pt_b, color, 2)
    return out


def draw_bbox(
    frame: NDArray[np.uint8],
    bbox: tuple[int, int, int, int],
    color: tuple[int, int, int] = (255, 0, 0),
) -> NDArray[np.uint8]:
    """Draw a rectangle for *bbox* = ``(x1, y1, x2, y2)``."""
    out = frame.copy()
    x1, y1, x2, y2 = bbox
    cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
    return out


def annotate_frame(
    frame: NDArray[np.uint8],
    keypoints: NDArray[np.floating],
    bbox: tuple[int, int, int, int] | None,
    phase_label: str,
) -> NDArray[np.uint8]:
    """Return a frame with skeleton, bbox, and phase label drawn."""
    out = draw_skeleton(frame, keypoints)
    if bbox is not None:
        out = draw_bbox(out, bbox)
    cv2.putText(
        out,
        phase_label,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2,
    )
    return out
