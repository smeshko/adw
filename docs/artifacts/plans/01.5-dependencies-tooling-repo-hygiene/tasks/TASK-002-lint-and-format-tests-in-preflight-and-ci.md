# TASK-002: Lint and format tests in preflight and CI

Depends on: None
Suggested commit: `ci: lint and format-check tests, drop duplicate coverage flags`

## Goal

`scripts/preflight.sh` and the CI lint job run `ruff check` and `ruff format --check` over `src/` and `tests/`. The CI test step relies on `addopts` for coverage.

## Files

- `tests/unit/cli/test_progress.py`: remove the unused `from pathlib import Path` (`F401`, line 10).
- `scripts/preflight.sh`:
  - `uv run ruff check src/ tests/`
  - `uv run ruff format --check src/ tests/`
  - The `echo` labels stay `==> ruff check` and `==> ruff format --check`.
- `.github/workflows/ci.yml`:
  - The lint job runs `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/`.
  - The test job's `Run pytest with coverage` step runs `uv run pytest`.

## Acceptance

- [ ] `uv run ruff check tests/` and `uv run ruff format --check tests/` pass.
- [ ] `scripts/preflight.sh` passes. Temporarily add an unused import to a test file and preflight fails on it, then revert.
- [ ] `ci.yml` has no `--cov` flag, and both ruff steps name `src/ tests/`.
- [ ] `uv run pytest` alone still prints the coverage report and enforces `--cov-fail-under=80`: its output ends with the `Required test coverage of 80% reached` line.

Evidence:
- preflight output
- the failing preflight run on the planted import
- the `ci.yml` diff
- the coverage line from a bare `uv run pytest`

## Steps

- [ ] Remove the unused import in `tests/unit/cli/test_progress.py`.
- [ ] Update both ruff lines in `scripts/preflight.sh`.
- [ ] Update the two lint steps and the pytest step in `.github/workflows/ci.yml`.
- [ ] Run `scripts/preflight.sh`. Plant `import os` at the top of `tests/unit/cli/test_progress.py`, run preflight again and expect `F401`, then revert the plant.
- [ ] Run the full `uv run pytest` and keep the coverage line.

## Notes

- The planted import is a demonstration only. It must not reach the commit: check `git diff` before staging.
