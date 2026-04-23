---
project: baseball-swing-analyzer
goal: Analyze baseball swings and extract all key biomechanical metrics
stack: ["python3.10+", "pytest", "hatchling"]
last_session: "2026-04-22"
status: scaffolded — core analysis engine is a stub
---

# Baseball Swing Analyzer — Agent Memory

## Project Goal
Build a Python package that ingests baseball swing data (video, pose/sensor data, or tracked bat path) and extracts key metrics.

## What "Key Metrics" Means Here
Non-exhaustive list the analyzer should eventually compute:
- Bat speed (peak, at contact)
- Swing plane / attack angle
- Time to contact
- Hip-shoulder separation
- Hand path efficiency
- Launch metrics derivation (if ball tracking is available)
Agents should add metrics as the analysis engine matures; document them in `docs/metrics.md` once stabilized.

## Code Conventions
- Python 3.10+ with type hints.
- Source lives in `src/baseball_swing_analyzer/`.
- Tests live in `tests/` and run via `pytest`.
- Prefer small, pure functions for metric extraction; I/O and parsing are separate layers.

## Orchestration Protocol

This project uses a multi-agent architecture. The orchestrator (main session) spawns domain-specific sub-agents via the `task` tool. Each agent has a focused scope defined below.

### Agent Contracts

| Agent Type | Scope | Input Contract | Output Contract |
|-----------|-------|----------------|-----------------|
| `cv-engineer` | Computer vision pipeline: YOLO, pose estimation, image processing | "implement X.py that uses model Y to do Z" | PR-ready `.py` file + test file + `pytest` passes |
| `metric-engineer` | Biomechanical metric extraction: angles, velocities, phase detection | "compute metric X from pose array shape (T, K, 2)" | Pure function + unit tests + validation against known cases |
| `swing-theorist` | Baseball biomechanics validation: does this metric make sense? | "review metric X and its calculation" | Verdict: keep / modify / drop, with biomechanical justification |
| `qa-harness` | Test infrastructure, CI, fixtures, property-based tests | "add tests for X" | Test file(s) that run with `pytest` + coverage note |
| `systems-plumber` | API clients, config management, CLI, dependency wiring | "add a client for X API" or "wire module Y into main flow" | Working integration + env var docs + no new heavy local deps |
| `reality-check` | External research, model benchmarks, dataset availability | "find the best X for Y" or "is claim Z actually true?" | Concise verdict with citations + risk flags |

### Orchestration Rules
1. **One agent per domain at a time.** Don't ask a `cv-engineer` to write tests; spawn `qa-harness` for that.
2. **Agents run in parallel when tasks don't overlap.** e.g. `cv-engineer` building pose.py while `metric-engineer` designs metrics.py.
3. **Every agent PR must include tests.** If tests are missing, the orchestrator sends the work back to `qa-harness`.
4. **No agent adds heavy local dependencies without `reality-check` approval.** If an agent wants to add `torch`, `reality-check` must verify it's the lightest option.
5. **Phase gates exist:** Phase 1 = `cv-engineer` + `metric-engineer`. Phase 3 = `systems-plumber` + `qa-harness`. No Phase 2 agents spawn unless Phase 1 metrics prove insufficient.

## Session Notes
- 2026-04-22: Basic repo scaffold created (`pyproject.toml`, `src/`, `tests/`, stub `analyzer.py`).
- Next: Implement input parsing layer and first metric extractor.

## How to Validate
```bash
# Install in editable mode
pip install -e ".[test]"

# Run tests
pytest
```
