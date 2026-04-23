"""Video ingestion utilities."""

from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np


class VideoProperties(NamedTuple):
    width: int
    height: int
    fps: float
    total_frames: int


def load_video(path: Path) -> Iterator[np.ndarray]:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {path}")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            yield frame
    finally:
        cap.release()


def get_video_properties(path: Path) -> VideoProperties:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {path}")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return VideoProperties(width, height, fps, total_frames)
    finally:
        cap.release()


def is_blurry(frame: np.ndarray, threshold: float = 100.0) -> bool:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return bool(variance < threshold)
