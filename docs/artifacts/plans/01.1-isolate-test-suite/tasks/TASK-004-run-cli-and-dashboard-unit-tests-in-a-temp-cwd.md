# TASK-004: Run cli and dashboard unit tests in a temp cwd

Depends on: TASK-003
Suggested commit: `test: run cli and dashboard unit tests in a temp cwd`

## Goal

Every test under `tests/unit/cli/` and `tests/unit/dashboard/` runs with cwd set to its own `tmp_path`. A CLI command such as `adw resume --from-phase plan` (and the other four phases) in `test_resume.py::TestFromPhaseValidation` can then no longer act on the checkout's `.adw/runs`, branches or worktrees.

## Files

- `tests/unit/cli/conftest.py` (new): autouse `isolated_cwd(tmp_path, monkeypatch)` → `monkeypatch.chdir(tmp_path)`, with a docstring that names the hazard (CLI commands act on cwd's `.adw/` and git repo).
- `tests/unit/dashboard/conftest.py` (new): the same fixture.

## Acceptance

- [ ] A test in each directory sees `Path.cwd() == tmp_path`.
- [ ] `uv run pytest tests/unit/cli tests/unit/dashboard -o addopts=""` passes. Module-level fixtures that chdir into `git_repo` (for example `test_run.py`) still work: `git_repo` is the same `tmp_path`.
- [ ] Running those two directories from the checkout leaves unchanged:
  - `git status --short`, `git branch` and `git worktree list`
  - `find .adw/runs -type f | sort | xargs shasum | shasum`

  The main checkout holds real runs.

Evidence:
- the partial pytest summary
- the before/after snapshot diff (empty) around that partial run in the main checkout, or in a clone seeded with its `.adw/runs`

## Steps

### RED
- [ ] Add a check to `tests/unit/cli/test_resume.py::TestFromPhaseValidation`: a fixture-free assertion inside `test_all_valid_phases_accepted` that `not (Path.cwd() / "pyproject.toml").exists()`. It fails today, because cwd is the checkout. Keep it: it's the regression guard for this module.

### GREEN
- [ ] Add both `conftest.py` files.
- [ ] Run the two directories.

### REFACTOR
- [ ] Leave the existing per-module chdir fixtures as they are (out of scope, harmless).
- [ ] `scripts/preflight.sh` passes.
