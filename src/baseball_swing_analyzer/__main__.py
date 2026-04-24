"""CLI entrypoint: python -m baseball_swing_analyzer --video swing.mp4 --output results/"""

import argparse
import sys
from pathlib import Path

from baseball_swing_analyzer.analyzer import analyze_swing
from baseball_swing_analyzer.reporter import summarize_metrics, write_metrics_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze baseball swings from video.")
    parser.add_argument("--video", type=Path, default=None, help="Path to input video file.")
    parser.add_argument("--batch", type=Path, default=None, help="Directory of videos for session analysis.")
    parser.add_argument("--output", type=Path, default=Path("output"), help="Output directory.")
    parser.add_argument("--fps-scale", type=float, default=1.0, help="Scale factor for video FPS.")
    parser.add_argument("--hand", choices=["auto", "right", "left"], default="auto", help="Batter handedness (default: auto-detect).")
    parser.add_argument("--annotate", action="store_true", help="Write annotated output video(s).")
    parser.add_argument("--coach", action="store_true", help="Generate coaching report.")
    parser.add_argument("--ollama-url", default=None, help="Ollama Cloud API base URL.")
    parser.add_argument("--ollama-key", default=None, help="Ollama Cloud API key.")
    args = parser.parse_args(argv)

    args.output.mkdir(parents=True, exist_ok=True)

    if args.batch:
        return _run_batch(args)

    if not args.video or not args.video.exists():
        print("Error: --video must point to an existing file, or use --batch for session mode.")
        return 1

    return _run_single(args)


def _run_single(args: argparse.Namespace) -> int:
    result = analyze_swing(args.video, output_dir=args.output, annotate=args.annotate, handedness=args.hand)

    json_path = args.output / "metrics.json"
    write_metrics_json(result, json_path)
    print(f"Metrics written to {json_path}")
    print(summarize_metrics(result))

    if args.coach:
        _write_coaching_report(result, args)
    return 0


def _run_batch(args: argparse.Namespace) -> int:
    from baseball_swing_analyzer.session import build_session_report, write_session_report

    videos = sorted(args.batch.glob("*.mp4")) + sorted(args.batch.glob("*.mov")) + sorted(args.batch.glob("*.avi"))
    if not videos:
        print(f"No video files found in {args.batch}")
        return 1

    reports: list[dict] = []
    for vid in videos:
        out = args.output / vid.stem
        out.mkdir(parents=True, exist_ok=True)
        result = analyze_swing(vid, output_dir=out, annotate=args.annotate, handedness=args.hand)
        write_metrics_json(result, out / "metrics.json")
        reports.append(result)
        if args.coach:
            _write_coaching_report(result, args)
        print(f"Analyzed {vid.name}")

    session = build_session_report(reports)
    session_path = args.output / "session.json"
    write_session_report(session, session_path)
    print(f"Session report written to {session_path}")
    print(f"Swings analyzed: {session['swing_count']}")
    return 0


def _write_coaching_report(result: dict, args: argparse.Namespace) -> None:
    from baseball_swing_analyzer.ai.knowledge import generate_static_report

    static_cues = generate_static_report(result)
    report_path = args.output / "coaching.md"
    report_lines = ["## Coaching Report", "", "### Biomechanical Cues", ""]
    for cue in static_cues:
        report_lines.append(f"- {cue}")

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
    except Exception:
        report_lines.extend(
            ["", "*Note: Cloud AI unavailable — showing offline coaching cues only.*"]
        )

    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nCoaching report written to {report_path}")
    print("\n".join(f"- {c}" for c in static_cues))


if __name__ == "__main__":
    sys.exit(main())