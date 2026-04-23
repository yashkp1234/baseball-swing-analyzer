# Orchestrator Playbook

This document defines how the main session (orchestrator) spawns, monitors, and accepts deliverables from specialized sub-agents.

## Agent Roster

| Agent | File | Scope | When to Spawn |
|-------|------|-------|---------------|
| `cv-engineer` | `agents/cv-engineer.md` | YOLO, pose estimation, smoothing, overlays | Every new computer vision module or model swap |
| `metric-engineer` | `agents/metric-engineer.md` | Biomechanical metric functions | Every new metric extractor |
| `swing-theorist` | `agents/swing-theorist.md` | Formula validation, biomechanical sanity | Before a metric graduates to stable; when proxy is weird |
| `qa-harness` | `agents/qa-harness.md` | Tests, fixtures, coverage | After every module is implemented; when coverage is missing |
| `systems-plumber` | `agents/systems-plumber.md` | CLI, API clients, config, wiring | When modules need to integrate; Phase 3 cloud clients |
| `reality-check` | `agents/reality-check.md` | Dependency weight, model benchmarks | Before adding any non-trivial pip dependency or model weight |

## Phase Gates

### Phase 1 — Core Engine (cv-engineer + metric-engineer, parallel)
1. **cv-engineer** implements detection + pose pipeline.
2. **metric-engineer** implements 2D metric suite.
3. **qa-harness** writes tests for both.
4. **swing-theorist** reviews metrics for biological validity.
5. Do **not** proceed to Phase 2 until `pytest` passes and metrics.md is updated.

### Phase 2 — AI Layer (systems-plumber + qa-harness)
1. **systems-plumber** wires Phase 1 modules into CLI and builds cloud API clients.
2. **qa-harness** covers CLI wiring and mocked HTTP.
3. **swing-theorist** reviews coaching prompt templates (not code).
4. Done when `pytest` passes and `python -m baseball_swing_analyzer` runs end-to-end.

### Phase 3 — 3D Lifting (optional, blocked on Phase 1 metrics proving insufficient)
1. **reality-check** confirms CLIFF/alternative is still best.
2. **cv-engineer** adds 3D lifting module.
3. **metric-engineer** adds 3D metrics.
4. **qa-harness** covers new modules.

## Spawn Protocol

For each agent invocation:
1. **Load context.** Before spawning, read the relevant section of `plan.md`, existing source files, and agent instruction file.
2. **Pass contract.** The prompt must contain:
   - Exact scope (one module or one metric).
   - Input/output format expected.
   - How to verify (test command, assertion).
3. **Run parallel.** If two agents have no file overlap, spawn them simultaneously.
4. **Accept or reject.** When agent returns:
   - File paths created → verify they exist.
   - Test results → run `pytest` independently. If fail, return to agent with logs.
   - Missing tests → spawn `qa-harness`.
   - Heavy new dependency → spawn `reality-check` before merge.

## Monitoring Rules
- Only one agent **per file** at a time to avoid conflicts.
- Never let an agent change `pyproject.toml` without orchestrator approval (it affects everyone).
- After every accepted PR, update `AGENTS.md` session notes with what changed.

## Decision Log
(Use this to record why later agents were spawned or skipped.)
- 2026-04-22: Rewrote `plan.md` after `reality-check` found CLIFF/LLM too heavy for MVP. Phase 2 made optional, Phase 3 cloud-only.
- 2026-04-22: Created agent roster and orchestration playbook.
