"""Main analyzer pipeline: video → pose → metrics."""

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from .detection import detect_person, reset_tracker
from .ingestion import get_video_properties, load_video
from .phases import classify_phases
from .pose import extract_pose, smooth_keypoints
from .reporter import build_report
from .ai.flags import generate_qualitative_flags
from .visualizer import annotate_frame


# Target frame rate for analysis. Source at 30fps is downsampled to ~8fps (stride=4).
_TARGET_ANALYSIS_FPS = 8.0
_MAX_ANALYSIS_FRAMES = 6


def _subsample_indices(total_frames: int, source_fps: float, target_fps: float = _TARGET_ANALYSIS_FPS) -> list[int]:
    """Return frame indices to process so the effective rate is ~*target_fps*."""
    if source_fps <= target_fps:
        indices = list(range(total_frames))
    else:
        step = max(1, round(source_fps / target_fps))
        indices = list(range(0, total_frames, step))

    if len(indices) > _MAX_ANALYSIS_FRAMES:
        indices = np.linspace(0, total_frames - 1, _MAX_ANALYSIS_FRAMES, dtype=int).tolist()
    return indices


def _effective_fps(indices: list[int], source_fps: float) -> float:
    """Return the approximate FPS of the sampled analysis sequence."""
    if len(indices) < 2:
        return min(source_fps, _TARGET_ANALYSIS_FPS)
    sampled_duration = (indices[-1] - indices[0] + 1) / source_fps
    return len(indices) / sampled_duration if sampled_duration > 0 else source_fps


def analyze_swing(
    video_path: Path,
    output_dir: Path | None = None,
    annotate: bool = False,
    handedness: str = "auto",
    tracker: str | None = None,
) -> dict:
    """Run the full pipeline on a video file.

    Parameters
    ----------
    video_path :
        Path to input video.
    output_dir :
        If given and *annotate* is True, the annotated video is written here.
    annotate :
        Whether to produce an annotated output video.
    handedness :
        Batter handedness: ``"auto"``, ``"right"``, or ``"left"``.
    tracker :
        YOLO tracker config (e.g. ``"bytetrack.yaml"``). Pass ``None`` for
        per-frame detection without tracking.
    """
    if tracker is not None:
        reset_tracker()
    props = get_video_properties(video_path)

    indices = _subsample_indices(props.total_frames, props.fps)
    analysis_fps = _effective_fps(indices, props.fps)
    print(f"[Analyzer] Source: {props.total_frames} frames @ {props.fps:.1f} fps -> processing {len(indices)} frames")

    keypoints_list: list[NDArray[np.floating]] = []
    bbox_list: list[tuple[int, int, int, int] | None] = []
    all_frames: list[np.ndarray] | None = [] if annotate else None

    cap = cv2.VideoCapture(str(video_path))
    try:
        frame_idx = 0
        processed_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if processed_idx >= len(indices):
                break

            if frame_idx == indices[processed_idx]:
                bbox = detect_person(frame, tracker=tracker) if tracker is not None else None
                if bbox is not None:
                    kp = extract_pose(frame, bbox)
                else:
                    kp = extract_pose(frame)
                keypoints_list.append(kp)
                bbox_list.append(bbox)
                if all_frames is not None:
                    all_frames.append(frame)
                processed_idx += 1

            frame_idx += 1
    finally:
        cap.release()

    if not keypoints_list:
        raise RuntimeError("No frames were processed.")

    keypoints_seq = np.stack(keypoints_list, axis=0)  # (T, 17, 3)
    keypoints_seq = smooth_keypoints(keypoints_seq)

    phase_labels = classify_phases(keypoints_seq, fps=analysis_fps)
    report = build_report(phase_labels, keypoints_seq, analysis_fps)
    report["flags"] = generate_qualitative_flags(
        keypoints_seq, phase_labels, handedness=handedness
    )
    report["_keypoints_seq"] = keypoints_seq

    if annotate and output_dir is not None and all_frames is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "annotated.mp4"
        _write_annotated_frames(out_path, all_frames, keypoints_seq, bbox_list, phase_labels)

    return report


def _write_annotated_frames(
    dst_path: Path,
    frames: list[np.ndarray],
    keypoints_seq: NDArray[np.floating],
    bbox_list: list[tuple[int, int, int, int] | None],
    phase_labels: list[str],
) -> None:
    """Write already-read frames with overlay to *dst_path*."""
    if not frames:
        return
    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(
        str(dst_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        30.0,
        (w, h),
    )
    try:
        for idx, frame in enumerate(frames):
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
