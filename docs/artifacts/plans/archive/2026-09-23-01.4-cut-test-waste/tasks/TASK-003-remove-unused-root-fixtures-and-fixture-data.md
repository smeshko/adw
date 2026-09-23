# TASK-003: Remove unused root fixtures and fixture data

Depends on: None
Suggested commit: `test: remove unused root fixtures and fixture data`

## Goal

`tests/conftest.py` holds only the fixtures something uses (`isolated_home`, `git_repo`), and the fixture data only they read is gone.

## Files

- `tests/conftest.py`:
  - Delete `tmp_adw_dir`, `mock_executor`, `sample_run_context`, `sample_project_config`, `fixtures_path` and `sample_config_yaml`.
  - Delete their lines from the module docstring's fixture list. Drop the "(ISS-024)" from the `git_repo` line and from the `git_repo` docstring.
  - Drop the imports left unused. Likely `MockExecutor`, `ProjectConfig`, `RunContext`, `ULID` and `datetime`; let ruff F401 decide.
  - Keep the module-top `ADW_MOCK_EXECUTOR` and `LINEAR_*` env setup, `isolated_home`, `git_repo` and `_cleanup_worktrees`.
- `tests/fixtures/llm/`, `tests/fixtures/configs/`, `tests/fixtures/runs/`: delete (`git rm -r`).
- `tests/unit/core/test_constants.py`: delete. Its one test asserts `PHASE_SEQUENCE` is a non-empty tuple, an ADR-001 enum-existence test.

## Acceptance

- [ ] `grep -rnwE "tmp_adw_dir|sample_project_config|sample_config_yaml" tests` returns nothing.
- [ ] `grep -rn "fixtures/llm\|fixtures/configs\|fixtures/runs\|\"llm\"\|\"configs\"" tests` returns nothing.
- [ ] The shadowing consumers still pass, because they define their own `mock_executor`, `sample_run_context` and `fixtures_path`: `uv run pytest tests/unit/core/test_phase_runner.py tests/integration/test_document_phase.py tests/integration/core/test_artifact_manager_integration.py tests/integration/test_token_tracking.py tests/integration/test_hooks.py -o addopts=""`.
- [ ] `uv run pytest --collect-only -q -o addopts="" | tail -1` shows **4,130** (4,131 − 1), or 4,295 if run before TASK-001/002.
- [ ] `uv run ruff check tests/ && uv run ruff format --check tests/` pass.

Evidence:
- both grep outputs (empty)
- the partial-suite summary line
- the collected count

## Steps

### RED
- [ ] Record the consumers before deleting: `grep -rnw "mock_executor\|sample_run_context\|fixtures_path" tests | grep "def "`. Every hit outside `tests/conftest.py` must be a local definition, as `RESEARCH.md` lists. If one is a bare consumer instead, stop and keep that fixture.

### GREEN
- [ ] Delete the six fixtures, the three fixture-data dirs and `test_constants.py`.
- [ ] Run the partial suite from Acceptance.

### REFACTOR
- [ ] Tidy imports and the docstring, then run ruff check and format on `tests/`.

## Notes

- A deleted conftest fixture that still has a consumer shows up only at runtime, as `fixture 'x' not found`. Collect-only doesn't catch it. That is why Acceptance runs the shadowing files.
