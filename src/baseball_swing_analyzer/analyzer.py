"""Main analyzer pipeline: video → pose → metrics."""

from collections.abc import Callable
import os
from pathlib import Path
import subprocess
import time

import cv2
import numpy as np
from numpy.typing import NDArray

from .detection import detect_person, reset_tracker
from .ingestion import get_video_properties, load_video
from .phases import classify_phases
from .pose import extract_pose, pose_device, smooth_keypoints
from .reporter import build_report
from .ai.flags import generate_qualitative_flags
from .swing_segments import best_swing_segment, detect_swing_segments
from .visualizer import annotate_frame


_CPU_TARGET_ANALYSIS_FPS = float(os.environ.get("SWING_ANALYSIS_TARGET_FPS_CPU", "8"))
_GPU_TARGET_ANALYSIS_FPS = float(os.environ.get("SWING_ANALYSIS_TARGET_FPS_GPU", "30"))
_CPU_MAX_ANALYSIS_FRAMES = int(os.environ.get("SWING_ANALYSIS_MAX_FRAMES_CPU", "6"))
_GPU_MAX_ANALYSIS_FRAMES = int(os.environ.get("SWING_ANALYSIS_MAX_FRAMES_GPU", "120"))


def _analysis_budget() -> tuple[float, int]:
    if pose_device() == "cuda":
        return _GPU_TARGET_ANALYSIS_FPS, _GPU_MAX_ANALYSIS_FRAMES
    return _CPU_TARGET_ANALYSIS_FPS, _CPU_MAX_ANALYSIS_FRAMES


def _subsample_indices(
    total_frames: int,
    source_fps: float,
    target_fps: float,
    max_frames: int,
) -> list[int]:
    """Return frame indices to process so the effective rate is ~*target_fps*."""
    if source_fps <= target_fps:
        indices = list(range(total_frames))
    else:
        step = max(1, round(source_fps / target_fps))
        indices = list(range(0, total_frames, step))

    if len(indices) > max_frames:
        indices = np.linspace(0, total_frames - 1, max_frames, dtype=int).tolist()
    return indices


def _motion_window(motion_scores: NDArray[np.floating]) -> tuple[int, int] | None:
    scores = np.asarray(motion_scores, dtype=float).flatten()
    if scores.size < 5 or float(scores.max()) <= 0:
        return None

    peak = float(scores.max())
    mean = float(scores.mean())
    std = float(scores.std())
    if peak <= mean + std:
        return None

    threshold = max(peak * 0.35, mean + std * 0.8)
    active = scores >= threshold
    if not np.any(active):
        return None

    peak_idx = int(np.argmax(scores))
    start = peak_idx
    end = peak_idx
    while start > 0 and active[start - 1]:
        start -= 1
    while end < len(scores) - 1 and active[end + 1]:
        end += 1

    return start, end


def _adaptive_sample_indices(
    total_frames: int,
    source_fps: float,
    target_fps: float,
    max_frames: int,
    motion_scores: NDArray[np.floating] | None,
) -> list[int]:
    uniform = _subsample_indices(total_frames, source_fps, target_fps, max_frames)
    if motion_scores is None:
        return uniform

    window = _motion_window(motion_scores)
    if window is None:
        return uniform

    start, end = window
    if end <= start:
        return uniform

    if total_frames <= max_frames:
        return list(range(total_frames))

    focus_frames = min(max_frames - 8, max(40, int(max_frames * 0.65)))
    context_frames = max_frames - focus_frames

    inside = np.linspace(start, end, focus_frames, dtype=int).tolist()
    pre_count = context_frames // 2
    post_count = context_frames - pre_count
    outside: list[int] = []
    if start > 0 and pre_count > 0:
        outside.extend(np.linspace(0, start - 1, pre_count, dtype=int).tolist())
    if end < total_frames - 1 and post_count > 0:
        outside.extend(np.linspace(end + 1, total_frames - 1, post_count, dtype=int).tolist())

    indices = sorted(set([*inside, *outside]))
    if len(indices) < max_frames:
        for idx in uniform:
            if idx not in indices:
                indices.append(idx)
            if len(indices) == max_frames:
                break
        indices.sort()

    return indices[:max_frames]


def _compute_motion_scores(video_path: Path, total_frames: int) -> NDArray[np.float32]:
    cap = cv2.VideoCapture(str(video_path))
    scores = np.zeros(total_frames, dtype=np.float32)
    prev_small: NDArray[np.uint8] | None = None
    idx = 0
    try:
        while cap.isOpened() and idx < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, (96, 54), interpolation=cv2.INTER_AREA)
            if prev_small is not None:
                scores[idx] = float(np.mean(cv2.absdiff(small, prev_small)))
            prev_small = small
            idx += 1
    finally:
        cap.release()
    return scores


def _effective_fps(indices: list[int], source_fps: float) -> float:
    """Return the approximate FPS of the sampled analysis sequence."""
    if len(indices) < 2:
        return source_fps
    sampled_duration = (indices[-1] - indices[0] + 1) / source_fps
    return len(indices) / sampled_duration if sampled_duration > 0 else source_fps


def _transcode_video_for_browser(src_path: Path, dst_path: Path) -> None:
    import imageio_ffmpeg

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [
            ffmpeg_exe,
            "-y",
            "-i",
            str(src_path),
            "-movflags",
            "+faststart",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            str(dst_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def analyze_swing(
    video_path: Path,
    output_dir: Path | None = None,
    annotate: bool = False,
    handedness: str = "auto",
    tracker: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
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
    analysis_started = time.perf_counter()
    if tracker is not None:
        reset_tracker()
    props = get_video_properties(video_path)
    target_fps, max_frames = _analysis_budget()
    motion_scores = _compute_motion_scores(video_path, props.total_frames)
    indices = _adaptive_sample_indices(
        props.total_frames,
        props.fps,
        target_fps,
        max_frames,
        motion_scores,
    )
    analysis_fps = _effective_fps(indices, props.fps)
    sampling_mode = "adaptive" if indices != _subsample_indices(props.total_frames, props.fps, target_fps, max_frames) else "uniform"
    print(
        f"[Analyzer] Source: {props.total_frames} frames @ {props.fps:.1f} fps "
        f"-> processing {len(indices)} frames on {pose_device()} "
        f"(target_fps={target_fps:.1f}, max_frames={max_frames}, mode={sampling_mode})"
    )

    keypoints_list: list[NDArray[np.floating]] = []
    bbox_list: list[tuple[int, int, int, int] | None] = []
    all_frames: list[np.ndarray] | None = [] if annotate else None

    cap = cv2.VideoCapture(str(video_path))
    pose_started = time.perf_counter()
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
                if progress_callback is not None:
                    progress_callback(processed_idx + 1, len(indices))
                processed_idx += 1

            frame_idx += 1
    finally:
        cap.release()
    pose_inference_duration_ms = (time.perf_counter() - pose_started) * 1000.0

    if not keypoints_list:
        raise RuntimeError("No frames were processed.")

    keypoints_seq = np.stack(keypoints_list, axis=0)  # (T, 17, 3)
    keypoints_seq = smooth_keypoints(keypoints_seq)

    swing_segments = detect_swing_segments(keypoints_seq, analysis_fps)
    primary_segment = best_swing_segment(swing_segments)
    if primary_segment is not None:
        segment_slice = slice(primary_segment.start_frame, primary_segment.end_frame + 1)
        keypoints_for_metrics = keypoints_seq[segment_slice]
    else:
        segment_slice = slice(0, keypoints_seq.shape[0])
        keypoints_for_metrics = keypoints_seq

    phase_labels = classify_phases(keypoints_for_metrics, fps=analysis_fps)
    report = build_report(phase_labels, keypoints_for_metrics, analysis_fps)
    report["flags"] = generate_qualitative_flags(
        keypoints_for_metrics, phase_labels, handedness=handedness
    )
    report["swing_segments"] = [segment.to_dict() for segment in swing_segments]
    report["primary_swing_segment"] = primary_segment.to_dict() if primary_segment else None
    report["analysis"] = {
        "pose_device": pose_device(),
        "source_frames": props.total_frames,
        "source_fps": props.fps,
        "sampled_frames": len(indices),
        "effective_analysis_fps": analysis_fps,
        "sampling_mode": sampling_mode,
        "analysis_duration_ms": (time.perf_counter() - analysis_started) * 1000.0,
        "pose_inference_duration_ms": pose_inference_duration_ms,
    }
    report["_keypoints_seq"] = keypoints_for_metrics

    if annotate and output_dir is not None and all_frames is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "annotated.mp4"
        segment_frames = all_frames[segment_slice]
        segment_bboxes = bbox_list[segment_slice]
        _write_annotated_frames(out_path, segment_frames, keypoints_for_metrics, segment_bboxes, phase_labels)
        if len(swing_segments) > 1:
            for index, segment in enumerate(swing_segments, start=1):
                per_swing_slice = slice(segment.start_frame, segment.end_frame + 1)
                per_swing_keypoints = keypoints_seq[per_swing_slice]
                per_swing_labels = classify_phases(per_swing_keypoints, fps=analysis_fps)
                _write_annotated_frames(
                    output_dir / f"annotated_swing_{index}.mp4",
                    all_frames[per_swing_slice],
                    per_swing_keypoints,
                    bbox_list[per_swing_slice],
                    per_swing_labels,
                )

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
    raw_path = dst_path.with_suffix(".raw.mp4")
    writer = cv2.VideoWriter(
        str(raw_path),
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
    _transcode_video_for_browser(raw_path, dst_path)
    raw_path.unlink(missing_ok=True)
