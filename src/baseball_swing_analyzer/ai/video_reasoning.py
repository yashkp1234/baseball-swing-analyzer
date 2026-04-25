"""Vision reasoning layer: send key frames + metrics to a cloud vision model."""

import base64
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from baseball_swing_analyzer.ai.client import AiClient


def _encode_frame(frame: np.ndarray) -> str:
    """Encode a frame as a base64 JPEG data URI."""
    _, buf = cv2.imencode(".jpg", frame)
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def _select_phase_frames(video_path: Path, phase_labels: list[str], n_per_phase: int = 2) -> tuple[list[np.ndarray], list[str]]:
    """Pick representative frames for each phase."""
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frames: list[np.ndarray] = []
    captions: list[str] = []
    unique_phases = []
    for phase in phase_labels:
        if not unique_phases or unique_phases[-1] != phase:
            unique_phases.append(phase)

    for phase in unique_phases:
        indices = [i for i, label in enumerate(phase_labels) if label == phase]
        if not indices:
            continue
        # Pick evenly-spaced frames from this phase
        picks = np.linspace(indices[0], indices[-1], min(n_per_phase, len(indices)), dtype=int)
        for p in picks:
            cap.set(cv2.CAP_PROP_POS_FRAMES, float(p))
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
                captions.append(f"Frame {p}: {phase}")

    cap.release()
    return frames, captions


def build_vision_prompt(metrics: dict, captions: list[str]) -> str:
    """Construct a biomechanics prompt for the vision model."""
    metrics_text = "\n".join(
        f"  {k}: {v}" for k, v in metrics.items()
        if k != "flags" and isinstance(v, (int, float))
    )

    flags = metrics.get("flags", {})
    flags_text = "\n".join(f"  {k}: {v}" for k, v in flags.items()) if isinstance(flags, dict) else ""

    caption_text = "\n".join(f"  {c}" for c in captions)

    return (
        "You are an expert MLB hitting coach analysing a baseball swing from video frames.\n\n"
        "IMPORTANT: Do not think out loud. Output ONLY the structured answers below. "
        "No chain-of-thought. No explanations of how you arrived at the answer.\n\n"
        "The swing has already been processed by a computer-vision pipeline that outputs these metrics:\n"
        f"{metrics_text}\n\n"
        "Qualitative flags from the pose pipeline:\n"
        f"{flags_text}\n\n"
        "The attached images are key frames from the swing, each captioned with its phase.\n"
        "Frame captions:\n"
        f"{caption_text}\n\n"
        "Please answer exactly in this format:\n"
        "1. Foot plant frame: \u003cframe number or 'not visible'\u003e\n"
        "2. Missed faults: \u003cone or two faults, or 'none detected'\u003e\n"
        "3. Top drill/cue: \u003cone specific drill or cue in one sentence\u003e\n"
    )


def reason_about_swing(
    video_path: Path,
    metrics: dict,
    phase_labels: list[str],
    client: AiClient | None = None,
) -> str:
    """Select key frames, send to vision LLM, and return qualitative coaching text."""
    client = client or AiClient()
    frames, captions = _select_phase_frames(video_path, phase_labels)
    if not frames:
        return "No frames available for vision analysis."

    images = [_encode_frame(f) for f in frames]
    prompt = build_vision_prompt(metrics, captions)
    return client.vision(prompt=prompt, images=images, max_tokens=600)
