"""AI coaching layer — cloud LLM integration and knowledge base."""

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from baseball_swing_analyzer.reporter import summarize_metrics


_PROMPT_TEMPLATE = """You are an expert hitting coach. A swing analysis pipeline has extracted the following biomechanical metrics from a phone video of a swing:

{metrics_summary}

Please provide a concise, actionable coaching report (3-5 bullet points) covering:
1. What looked good mechanically
2. The most important area for improvement
3. One specific drill or cue to address it

Keep each bullet to 1-2 sentences. Use plain language a youth player can understand."""


def build_coaching_prompt(metrics: dict) -> str:
    """Build an LLM prompt from a metrics dict."""
    summary = summarize_metrics(metrics)
    return _PROMPT_TEMPLATE.format(metrics_summary=summary)


def parse_coaching_text(response: str) -> list[str]:
    """Split raw LLM response into bullet points."""
    lines = [line.strip(" -•*") for line in response.splitlines() if line.strip()]
    return [line for line in lines if line]


def encode_image_for_api(frame: np.ndarray, fmt: str = ".jpg") -> str:
    """Encode a frame to base64 for vision API, returning a data URI."""
    import base64

    buf = cv2.imencode(fmt, frame)[1]
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"
