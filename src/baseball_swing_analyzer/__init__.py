"""Baseball swing analyzer package."""

__version__ = "0.1.0"

from baseball_swing_analyzer.ingestion import (
    VideoProperties,
    get_video_properties,
    is_blurry,
    load_video,
)
from baseball_swing_analyzer.detection import detect_person
from baseball_swing_analyzer.pose import extract_pose, smooth_keypoints
from baseball_swing_analyzer.visualizer import (
    annotate_frame,
    draw_bbox,
    draw_skeleton,
)

__all__ = [
    "VideoProperties",
    "get_video_properties",
    "is_blurry",
    "load_video",
    "detect_person",
    "extract_pose",
    "smooth_keypoints",
    "annotate_frame",
    "draw_bbox",
    "draw_skeleton",
]
