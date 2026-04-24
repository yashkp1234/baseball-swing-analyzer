"""Main analyzer pipeline: video → pose → metrics."""

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from .detection import detect_person
from .ingestion import get_video_properties, load_video
from .phases import classify_phases
from .pose import extract_pose, smooth_keypoints
from .reporter import build_report
from .ai.flags import generate_qualitative_flags


def analyze_swing(
    video_path: Path,
    output_dir: Path | None = None,
    annotate: bool = False,
    handedness: str = "auto",
) -> dict:
    """Run the full Phase 1 pipeline on a video file.

    Parameters
    ----------
    video_path :
        Path to input video.
    output_dir :
        If given and *annotate* is True, the annotated video is written here.
    annotate :
        Whether to produce an annotated output video.

    Returns
    -------
    metrics dict
    """
    props = get_video_properties(video_path)

    keypoints_list: list[NDArray[np.floating]] = []
    bbox_list: list[tuple[int, int, int, int] | None] = []

    for frame in load_video(video_path):
        bbox = detect_person(frame)
        if bbox is not None:
            kp = extract_pose(frame, bbox)
        else:
            kp = extract_pose(frame)
        keypoints_list.append(kp)
        bbox_list.append(bbox)

    keypoints_seq = np.stack(keypoints_list, axis=0)  # (T, 17, 3)
    keypoints_seq = smooth_keypoints(keypoints_seq)

    phase_labels = classify_phases(keypoints_seq, fps=props.fps)
    report = build_report(phase_labels, keypoints_seq, props.fps)
    report["flags"] = generate_qualitative_flags(keypoints_seq, phase_labels, handedness=handedness)

    if annotate and output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "annotated.mp4"
        _write_annotated_video(video_path, out_path, keypoints_seq, bbox_list, phase_labels)

    return report


def _write_annotated_video(
    src_path: Path,
    dst_path: Path,
    keypoints_seq: NDArray[np.floating],
    bbox_list: list[tuple[int, int, int, int] | None],
    phase_labels: list[str],
) -> None:
    """Read *src_path* again and write annotated frames to *dst_path*."""
    src_props = get_video_properties(src_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        str(dst_path),
        fourcc,
        max(1.0, src_props.fps),
        (src_props.width, src_props.height),
    )
    try:
        for idx, frame in enumerate(load_video(src_path)):
            label = phase_labels[idx] if idx < len(phase_labels) else ""
            bbox = bbox_list[idx] if idx < len(bbox_list) else None
            kp = keypoints_seq[idx] if idx < keypoints_seq.shape[0] else None
            if kp is not None:
                out = annotate_frame(frame, kp, bbox, label)
            else:
                out = frame
            writer.write(out)
    finally:
        writer.release()
