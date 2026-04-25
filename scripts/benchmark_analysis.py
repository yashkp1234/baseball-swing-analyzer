"""Benchmark local swing analysis latency and sampling density."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from baseball_swing_analyzer.analyzer import analyze_swing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Path to the input swing video")
    parser.add_argument("--repeat", type=int, default=1, help="Number of benchmark runs")
    args = parser.parse_args()

    results = []
    for run_idx in range(args.repeat):
        started = time.perf_counter()
        report = analyze_swing(args.video, annotate=False)
        analysis = dict(report.get("analysis", {}))
        analysis["wall_clock_s"] = time.perf_counter() - started
        analysis["run"] = run_idx + 1
        results.append(analysis)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
