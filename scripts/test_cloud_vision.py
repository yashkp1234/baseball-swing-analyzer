"""Test Ollama Cloud vision (qwen3-vl) on a local swing video.

Usage:
    export OLLAMA_URL=https://... OLLAMA_API_KEY=...
    python scripts/test_cloud_vision.py [path/to/video.mp4] [--model qwen3-vl]

Extracts evenly spaced frames, sends to Ollama Cloud vision model, prints
qualitative biomechanical observations for each frame.
"""

import argparse
import base64
import sys
from pathlib import Path

import cv2
import numpy as np

from baseball_swing_analyzer.ai.client import AiClient

PROMPT = """You are an expert baseball hitting coach analyzing a video frame.

Describe what you see in terms of:
1. Phase of swing (stance/load/stride/swing/contact/follow-through) — or "unknown"
2. Shoulder alignment (closed/open/square to plate)
3. Hip position and rotation
4. Head position (steady/drifting)
5. Front knee and stride foot position
6. Arm slot and hand path if visible

Be specific and concise. Use bullet points. If the frame is unclear, say so."""


def extract_frames(video_path: Path, n: int = 6) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = np.linspace(0, total - 1, n, dtype=int)
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append(frame)
    cap.release()
    return frames


def frame_to_data_uri(frame: np.ndarray, max_dim: int = 768) -> str:
    h, w = frame.shape[:2]
    scale = min(max_dim / h, max_dim / w, 1.0)
    if scale < 1.0:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    b64 = base64.standard_b64encode(buf.tobytes()).decode()
    return f"data:image/jpeg;base64,{b64}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?", help="Path to video file")
    parser.add_argument("--model", default="qwen3-vl", help="Ollama Cloud model name")
    parser.add_argument("--url", default=None, help="Ollama Cloud base URL (overrides OLLAMA_URL)")
    parser.add_argument("--key", default=None, help="Ollama Cloud API key (overrides OLLAMA_API_KEY)")
    parser.add_argument("--frames", type=int, default=6, help="Number of frames to sample")
    args = parser.parse_args()

    if args.video:
        video_path = Path(args.video)
    else:
        videos = sorted(Path("data/videos").glob("*.mp4")) + sorted(Path("data/videos").glob("*.mov"))
        if not videos:
            print("No videos found in data/videos/. Pass a path as argument.")
            sys.exit(1)
        video_path = videos[0]

    print(f"Video : {video_path.name}")
    print(f"Model : {args.model}\n")

    client = AiClient(base_url=args.url, api_key=args.key, model=args.model)

    frames = extract_frames(video_path, n=args.frames)
    if not frames:
        print("Failed to extract frames — check the video file.")
        sys.exit(1)

    print(f"Extracted {len(frames)} frames. Sending to Ollama Cloud...\n")
    print("=" * 60)

    for i, frame in enumerate(frames):
        uri = frame_to_data_uri(frame)
        print(f"\n--- Frame {i + 1}/{len(frames)} ---")
        result = client.vision(PROMPT, uri, max_tokens=512)
        print(result)

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
