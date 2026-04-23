"""CLI entrypoint: python -m baseball_swing_analyzer --video swing.mp4 --output results/"""

import argparse
import sys
from pathlib import Path

from baseball_swing_analyzer.analyzer import analyze_swing
from baseball_swing_analyzer.reporter import summarize_metrics, write_metrics_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a baseball swing from video.")
    parser.add_argument("--video", type=Path, required=True, help="Path to input video file.")
    parser.add_argument("--output", type=Path, default=Path("output"), help="Output directory.")
    parser.add_argument("--fps-scale", type=float, default=1.0, help="Scale factor for video FPS.")
    parser.add_argument(
        "--annotate", action="store_true", help="Write annotated output video."
    )
    parser.add_argument(
        "--coach", action="store_true", help="Generate coaching report (static rules + optional LLM)."
    )
    parser.add_argument(
        "--ollama-url", default=None, help="Ollama Cloud API base URL."
    )
    parser.add_argument(
        "--ollama-key", default=None, help="Ollama Cloud API key."
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

    if args.coach:
        # Static knowledge base (always works offline)
        from baseball_swing_analyzer.ai.knowledge import generate_static_report

        static_cues = generate_static_report(result)
        report_path = args.output / "coaching.md"
        report_lines = ["## Coaching Report", "", "### Biomechanical Cues", ""]
        for cue in static_cues:
            report_lines.append(f"- {cue}")

        # Optional: augment with cloud LLM
        try:
            from baseball_swing_analyzer.ai import (
                AiClient,
                build_coaching_prompt,
                parse_coaching_text,
            )

            client = AiClient(
                base_url=args.ollama_url, api_key=args.ollama_key, model="mistral"
            )
            prompt = build_coaching_prompt(result)
            raw = client.chat(
                system="You are an MLB-level hitting coach. Be concise and actionable.",
                user=prompt,
            )
            bullets = parse_coaching_text(raw)
            report_lines.extend(["", "### AI-Generated Insights", ""])
            for b in bullets:
                report_lines.append(f"- {b}")
        except Exception as exc:
            report_lines.extend(
                ["", "*Note: Cloud AI unavailable — showing offline coaching cues only.*"]
            )

        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"\nCoaching report written to {report_path}")
        print("\n".join(f"- {c}" for c in static_cues))
    return 0


if __name__ == "__main__":
    sys.exit(main())