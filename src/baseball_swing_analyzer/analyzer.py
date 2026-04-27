"""Main analyzer pipeline: video -> pose -> metrics."""

from collections.abc import Callable
import os
from pathlib import Path
import subprocess
import time

import cv2
import numpy as np
from numpy.typing import NDArray

from .ai.flags import generate_qualitative_flags
from .detection import detect_person, reset_tracker
from .ingestion import get_video_properties
from .phases import classify_phases
from .pose import extract_pose, pose_device, smooth_keypoints
from .reporter import build_report
from .swing_segments import SwingSegment, best_swing_segment, detect_swing_segments
from .swing_events import localize_swing_events
from .swing_validation import SwingCandidate, VisionSwingValidator, extract_clip_features
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
    """Return frame indices to process so the effective rate is ~target_fps."""
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


def _smooth_motion_scores(
    motion_scores: NDArray[np.floating],
    window: int = 9,
) -> NDArray[np.float32]:
    scores = np.asarray(motion_scores, dtype=np.float32).flatten()
    if scores.size <= 2 or window <= 1:
        return scores
    kernel = np.ones(window, dtype=np.float32) / float(window)
    return np.convolve(scores, kernel, mode="same").astype(np.float32)


def _detect_motion_windows(
    motion_scores: NDArray[np.floating],
    fps: float,
    min_duration_s: float = 0.3,
    pre_context_s: float = 0.35,
    post_context_s: float = 0.4,
    merge_gap_s: float = 0.2,
) -> list[SwingCandidate]:
    """Find repeated swing-like motion bursts on the full-rate motion signal."""
    smooth_scores = _smooth_motion_scores(motion_scores)
    if smooth_scores.size < 5 or float(smooth_scores.max()) <= 0:
        return []

    nonzero = smooth_scores[smooth_scores > 0]
    if nonzero.size == 0:
        return []

    threshold = max(
        float(smooth_scores.mean() + smooth_scores.std() * 1.4),
        float(np.percentile(nonzero, 82)),
    )
    active = smooth_scores >= threshold
    raw_runs: list[tuple[int, int]] = []
    min_len = max(3, round(min_duration_s * fps))

    idx = 0
    while idx < len(active):
        if not bool(active[idx]):
            idx += 1
            continue
        start = idx
        while idx + 1 < len(active) and bool(active[idx + 1]):
            idx += 1
        end = idx
        if end - start + 1 >= min_len:
            raw_runs.append((start, end))
        idx += 1

    if not raw_runs:
        return []

    pre_context = max(1, round(pre_context_s * fps))
    post_context = max(1, round(post_context_s * fps))
    expanded = [
        (
            max(0, start - pre_context),
            min(len(smooth_scores) - 1, end + post_context),
        )
        for start, end in raw_runs
    ]

    merge_gap = max(1, round(merge_gap_s * fps))
    merged = [expanded[0]]
    for start, end in expanded[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= merge_gap:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return [
        SwingCandidate(start_frame=start, end_frame=end, source="motion")
        for start, end in merged
    ]


def _window_sample_indices(
    start_frame: int,
    end_frame: int,
    source_fps: float,
    target_fps: float,
    max_frames: int,
) -> list[int]:
    relative = _subsample_indices(end_frame - start_frame + 1, source_fps, target_fps, max_frames)
    return [start_frame + idx for idx in relative]


def _effective_fps(indices: list[int], source_fps: float) -> float:
    """Return the approximate FPS of the sampled analysis sequence."""
    if len(indices) < 2:
        return source_fps
    sampled_duration = (indices[-1] - indices[0] + 1) / source_fps
    return len(indices) / sampled_duration if sampled_duration > 0 else source_fps


def _extract_window_pose_sequence(
    video_path: Path,
    indices: list[int],
    tracker: str | None,
    annotate: bool,
    progress_callback: Callable[[int, int], None] | None = None,
    progress_state: dict[str, int] | None = None,
) -> tuple[NDArray[np.float32], list[tuple[int, int, int, int] | None], list[np.ndarray] | None]:
    if not indices:
        raise RuntimeError("No frame indices provided for window analysis.")

    if tracker is not None:
        reset_tracker()

    keypoints_list: list[NDArray[np.float32]] = []
    bbox_list: list[tuple[int, int, int, int] | None] = []
    frames: list[np.ndarray] | None = [] if annotate else None

    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, float(indices[0]))
    next_index = 0
    frame_idx = indices[0]
    try:
        while cap.isOpened() and next_index < len(indices):
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx == indices[next_index]:
                bbox = detect_person(frame, tracker=tracker) if tracker is not None else None
                kp = extract_pose(frame, bbox) if bbox is not None else extract_pose(frame)
                keypoints_list.append(kp)
                bbox_list.append(bbox)
                if frames is not None:
                    frames.append(frame)
                if progress_callback is not None and progress_state is not None:
                    progress_state["done"] += 1
                    progress_callback(progress_state["done"], progress_state["total"])
                next_index += 1

            frame_idx += 1
    finally:
        cap.release()

    if not keypoints_list:
        raise RuntimeError("No frames were processed.")

    keypoints_seq = smooth_keypoints(np.stack(keypoints_list, axis=0))
    return keypoints_seq, bbox_list, frames


def _window_confidence(
    motion_scores: NDArray[np.floating],
    start_frame: int,
    end_frame: int,
) -> float:
    scores = np.asarray(motion_scores, dtype=float).flatten()
    if scores.size == 0:
        return 0.0
    baseline = float(scores.mean() + scores.std() + 1e-6)
    window_scores = scores[start_frame : end_frame + 1]
    if window_scores.size == 0:
        return 0.0
    return round(min(1.0, float(window_scores.max()) / baseline / 2.0), 3)


def _candidate_clip_features(
    video_path: Path,
    candidate: SwingCandidate,
    source_fps: float,
    tracker: str | None,
) -> dict[str, float | bool]:
    validation_fps = min(max(source_fps, 1.0), 18.0)
    validation_max_frames = 24
    indices = _window_sample_indices(
        candidate.start_frame,
        candidate.end_frame,
        source_fps,
        validation_fps,
        validation_max_frames,
    )
    keypoints_seq, _, _ = _extract_window_pose_sequence(
        video_path,
        indices,
        tracker,
        annotate=False,
    )
    return extract_clip_features(keypoints_seq, fps=_effective_fps(indices, source_fps))


def _build_window_analysis(
    video_path: Path,
    start_frame: int,
    end_frame: int,
    motion_scores: NDArray[np.floating],
    source_fps: float,
    target_fps: float,
    max_frames: int,
    annotate: bool,
    handedness: str,
    tracker: str | None,
    progress_callback: Callable[[int, int], None] | None = None,
    progress_state: dict[str, int] | None = None,
) -> dict:
    indices = _window_sample_indices(start_frame, end_frame, source_fps, target_fps, max_frames)
    keypoints_seq, bbox_list, frames = _extract_window_pose_sequence(
        video_path,
        indices,
        tracker,
        annotate,
        progress_callback,
        progress_state,
    )
    analysis_fps = _effective_fps(indices, source_fps)
    events = localize_swing_events(len(indices))
    phase_labels = classify_phases(
        keypoints_seq,
        fps=analysis_fps,
        forced_contact_frame=events.contact_frame,
    )
    report = build_report(phase_labels, keypoints_seq, analysis_fps)
    report["flags"] = generate_qualitative_flags(
        keypoints_seq,
        phase_labels,
        handedness=handedness,
    )
    local_contact = min(report["contact_frame"], len(indices) - 1)
    segment = SwingSegment(
        start_frame=start_frame,
        end_frame=end_frame,
        contact_frame=indices[local_contact],
        duration_s=round((end_frame - start_frame + 1) / source_fps, 3),
        confidence=_window_confidence(motion_scores, start_frame, end_frame),
    )
    report["swing_segments"] = [segment.to_dict()]
    report["primary_swing_segment"] = segment.to_dict()
    return {
        "indices": indices,
        "analysis_fps": analysis_fps,
        "bbox_list": bbox_list,
        "frames": frames,
        "keypoints_seq": keypoints_seq,
        "phase_labels": phase_labels,
        "report": report,
        "segment": segment,
    }


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
    """Run the full pipeline on a video file."""
    analysis_started = time.perf_counter()
    if tracker is not None:
        reset_tracker()

    props = get_video_properties(video_path)
    target_fps, max_frames = _analysis_budget()
    motion_scores = _compute_motion_scores(video_path, props.total_frames)
    motion_windows = _detect_motion_windows(motion_scores, props.fps)
    validator = VisionSwingValidator()
    accepted_windows: list[SwingCandidate] = []
    for candidate in motion_windows:
        clip_features = _candidate_clip_features(
            video_path,
            candidate,
            props.fps,
            tracker,
        )
        decision = validator.classify_candidate(candidate, clip_features=clip_features)
        if decision.accepted:
            accepted_windows.append(candidate)

    if accepted_windows:
        window_max_frames = max(24, min(max_frames, round(target_fps * 2.0)))
        sampled_windows = [
            _window_sample_indices(candidate.start_frame, candidate.end_frame, props.fps, target_fps, window_max_frames)
            for candidate in accepted_windows
        ]
        total_sampled_frames = sum(len(indices) for indices in sampled_windows)
        progress_state = {"done": 0, "total": total_sampled_frames}

        print(
            f"[Analyzer] Source: {props.total_frames} frames @ {props.fps:.1f} fps "
            f"-> processing {total_sampled_frames} frames across {len(accepted_windows)} motion windows on {pose_device()} "
            f"(target_fps={target_fps:.1f}, per_window_max={window_max_frames}, mode=windowed_motion)"
        )

        pose_started = time.perf_counter()
        window_analyses = [
            _build_window_analysis(
                video_path=video_path,
                start_frame=candidate.start_frame,
                end_frame=candidate.end_frame,
                motion_scores=motion_scores,
                source_fps=props.fps,
                target_fps=target_fps,
                max_frames=window_max_frames,
                annotate=annotate,
                handedness=handedness,
                tracker=tracker,
                progress_callback=progress_callback,
                progress_state=progress_state,
            )
            for candidate in accepted_windows
        ]
        pose_inference_duration_ms = (time.perf_counter() - pose_started) * 1000.0

        segments = [item["segment"] for item in window_analyses]
        primary_segment = best_swing_segment(segments)
        if primary_segment is None:
            raise RuntimeError("No swing segments were detected.")

        primary_index = next(
            index
            for index, item in enumerate(window_analyses)
            if item["segment"] == primary_segment
        )
        primary_window = window_analyses[primary_index]
        report = dict(primary_window["report"])
        report["swing_segments"] = [segment.to_dict() for segment in segments]
        report["primary_swing_segment"] = primary_segment.to_dict()
        report["analysis"] = {
            "pose_device": pose_device(),
            "source_frames": props.total_frames,
            "source_fps": props.fps,
            "sampled_frames": total_sampled_frames,
            "effective_analysis_fps": primary_window["analysis_fps"],
            "sampling_mode": "windowed_motion",
            "analysis_duration_ms": (time.perf_counter() - analysis_started) * 1000.0,
            "pose_inference_duration_ms": pose_inference_duration_ms,
            "motion_windows": len(motion_windows),
            "accepted_motion_windows": len(accepted_windows),
        }
        report["_keypoints_seq"] = primary_window["keypoints_seq"]
        report["_viewer_segments"] = [
            {
                "swing_number": index,
                "keypoints_seq": item["keypoints_seq"],
                "phase_labels": item["phase_labels"],
                "report": item["report"],
            }
            for index, item in enumerate(window_analyses, start=1)
        ]

        if annotate and output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            _write_annotated_frames(
                output_dir / "annotated.mp4",
                primary_window["frames"] or [],
                primary_window["keypoints_seq"],
                primary_window["bbox_list"],
                primary_window["phase_labels"],
            )
            for index, item in enumerate(window_analyses, start=1):
                _write_annotated_frames(
                    output_dir / f"annotated_swing_{index}.mp4",
                    item["frames"] or [],
                    item["keypoints_seq"],
                    item["bbox_list"],
                    item["phase_labels"],
                )

        return report

    indices = _adaptive_sample_indices(
        props.total_frames,
        props.fps,
        target_fps,
        max_frames,
        motion_scores,
    )
    analysis_fps = _effective_fps(indices, props.fps)
    sampling_mode = (
        "adaptive"
        if indices != _subsample_indices(props.total_frames, props.fps, target_fps, max_frames)
        else "uniform"
    )
    print(
        f"[Analyzer] Source: {props.total_frames} frames @ {props.fps:.1f} fps "
        f"-> processing {len(indices)} frames on {pose_device()} "
        f"(target_fps={target_fps:.1f}, max_frames={max_frames}, mode={sampling_mode})"
    )

    progress_state = {"done": 0, "total": len(indices)}
    pose_started = time.perf_counter()
    keypoints_seq, bbox_list, frames = _extract_window_pose_sequence(
        video_path,
        indices,
        tracker,
        annotate,
        progress_callback,
        progress_state,
    )
    pose_inference_duration_ms = (time.perf_counter() - pose_started) * 1000.0

    swing_segments = detect_swing_segments(keypoints_seq, analysis_fps)
    primary_segment = best_swing_segment(swing_segments)
    if primary_segment is not None:
        segment_slice = slice(primary_segment.start_frame, primary_segment.end_frame + 1)
        keypoints_for_metrics = keypoints_seq[segment_slice]
    else:
        segment_slice = slice(0, keypoints_seq.shape[0])
        keypoints_for_metrics = keypoints_seq

    events = localize_swing_events(len(keypoints_for_metrics))
    phase_labels = classify_phases(
        keypoints_for_metrics,
        fps=analysis_fps,
        forced_contact_frame=events.contact_frame,
    )
    report = build_report(phase_labels, keypoints_for_metrics, analysis_fps)
    report["flags"] = generate_qualitative_flags(
        keypoints_for_metrics,
        phase_labels,
        handedness=handedness,
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
    report["_viewer_segments"] = []

    if swing_segments:
        for index, segment in enumerate(swing_segments, start=1):
            per_swing_slice = slice(segment.start_frame, segment.end_frame + 1)
            per_swing_keypoints = keypoints_seq[per_swing_slice]
            per_swing_events = localize_swing_events(len(per_swing_keypoints))
            per_swing_labels = classify_phases(
                per_swing_keypoints,
                fps=analysis_fps,
                forced_contact_frame=per_swing_events.contact_frame,
            )
            per_swing_report = build_report(per_swing_labels, per_swing_keypoints, analysis_fps)
            per_swing_report["flags"] = generate_qualitative_flags(
                per_swing_keypoints,
                per_swing_labels,
                handedness=handedness,
            )
            per_swing_report["swing_segments"] = [segment.to_dict()]
            per_swing_report["primary_swing_segment"] = segment.to_dict()
            report["_viewer_segments"].append(
                {
                    "swing_number": index,
                    "keypoints_seq": per_swing_keypoints,
                    "phase_labels": per_swing_labels,
                    "report": per_swing_report,
                }
            )

    if annotate and output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_annotated_frames(
            output_dir / "annotated.mp4",
            (frames or [])[segment_slice],
            keypoints_for_metrics,
            bbox_list[segment_slice],
            phase_labels,
        )
        if len(report["_viewer_segments"]) > 1:
            for viewer_segment in report["_viewer_segments"]:
                index = viewer_segment["swing_number"]
                segment = swing_segments[index - 1]
                per_swing_slice = slice(segment.start_frame, segment.end_frame + 1)
                _write_annotated_frames(
                    output_dir / f"annotated_swing_{index}.mp4",
                    (frames or [])[per_swing_slice],
                    viewer_segment["keypoints_seq"],
                    bbox_list[per_swing_slice],
                    viewer_segment["phase_labels"],
                )

    return report


def _write_annotated_frames(
    dst_path: Path,
    frames: list[np.ndarray],
    keypoints_seq: NDArray[np.floating],
    bbox_list: list[tuple[int, int, int, int] | None],
    phase_labels: list[str],
) -> None:
    """Write already-read frames with overlay to dst_path."""
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
