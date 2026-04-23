"""CLI entrypoint: python -m baseball_swing_analyzer --video swing.mp4 --output results/"""

import argparse
import sys
from pathlib import Path

from .analyzer import analyze_swing
from .reporter import summarize_metrics, write_metrics_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a baseball swing from video.")
    parser.add_argument("--video", type=Path, required=True, help="Path to input video file.")
    parser.add_argument("--output", type=Path, default=Path("output"), help="Output directory.")
    parser.add_argument("--fps-scale", type=float, default=1.0, help="Scale factor for video FPS.")
    parser.add_argument(
        "--annotate", action="store_true", help="Write annotated output video."
    )
    args = parser.parse_args(argv)

    if not args.video.exists():
        print(f"Error: video file not found: {args.video}")
        return 1

    args.output.mkdir(parents=True, exist_ok=True)

    result = analyze_swing(args.video, output_dir=args.output, annotate=args.annotate)

    json_path = args.output / "metrics.json"
    write_metrics_json(result, json_path)
    print(f"Metrics written to {json_path}")
    print(summarize_metrics(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())