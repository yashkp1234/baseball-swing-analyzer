# Repository Layout

This project keeps the product code shallow at the top level and pushes notes and utilities into dedicated folders.

## Primary code

- `src/baseball_swing_analyzer/` - Python package for analysis, metrics, segmentation, projection, and export
- `server/` - FastAPI backend, jobs database access, async task entrypoints, artifact APIs
- `frontend/` - React/Vite frontend for upload, results, and the swing viewer
- `tests/` - Python tests and checked-in fixtures

## Project documents

- `docs/metrics.md` - stable metrics reference
- `docs/superpowers/` - generated specs and plans from the agent workflow
- `docs/design/` - longer-form design notes worth keeping
- `docs/notes/` - operational debriefs and session writeups
- `plans/` - active hand-authored implementation plans that intentionally stay at the repo root

## Utilities and support

- `scripts/` - utility scripts, polling helpers, and local benchmark tools
- `agents/` - project-specific agent role prompts
- `.agents/skills/` - local installed skills used by the repo workflow

## Runtime and generated data

These are local artifacts, not source-of-truth files:

- `server/uploads/`
- `server/outputs/`
- `frontend/dist/`
- `frontend/node_modules/`
- `.worktrees/`
- `tests_output_synth/`
- `tests_output_ui/`
