# AGENTS.md — rocket-lab-launch-hold-receipt

**Company:** Rocket Lab
**Domain:** Command Authority & Mission Assurance

## Quick Rules
- **Test command:** `PYTHONPATH=src pytest tests/ -v`
- **Lint:** `ruff check src/ tests/`
- **No drive-by edits** — load the skill first.

## Architecture
- `src/rocket_lab_launch_hold_receipt/core.py` — Domain logic (Command Authority & Mission Assurance)
- `tests/` — Verified test suite
- `.github/workflows/ci.yml` — Enforced CI pipeline
