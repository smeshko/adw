# TASK-005: Drop RunTrigger's unused project_dir

Depends on: TASK-001
Suggested commit: `refactor(core): drop the unused RunTrigger project_dir`

## Goal

`RunTrigger` takes only `adw_command`, and its docstrings describe the dashboard as its only caller.

## Files

- `src/adw/core/run_trigger.py`:
  - module docstring (`:1-5`): drop "Extracted from `webhook/runner.py`…"; say it starts runs for the dashboard's New Run
  - class docstring (`:36-44`): drop "both the dashboard and webhook modules" and the `_project_dir` attribute line
  - `__init__` (`:46-52`): drop the `project_dir` parameter and `self._project_dir`. `Path` stays imported, because `start_run` uses it.
- `tests/unit/core/test_run_trigger.py`:
  - replace every `RunTrigger(project_dir=Path(...))` with `RunTrigger()`
  - `test_custom_adw_command` keeps `adw_command=`
  - delete `test_default_project_dir` (`:67-70`)
  - delete `test_project_path_overrides_default` (`:152-170`): `test_successful_start` already asserts `cwd == Path(project_path)`, which is the whole contract once there's no default

## Acceptance

- [ ] `grep -rn "project_dir\|webhook" src/adw/core/run_trigger.py tests/unit/core/test_run_trigger.py` returns nothing.
- [ ] `test_successful_start` still asserts `cwd == Path("/projects/test")`, and passes.
- [ ] `uv run pytest tests/unit/core/test_run_trigger.py tests/unit/dashboard/test_mutations.py tests/unit/dashboard/test_abort.py -o addopts=""` passes.

Evidence: the grep and the pytest tail.

## Steps

### RED
- [ ] No new test: the removed parameter had no behaviour. First confirm with `grep -rn "RunTrigger(" src` that the only production caller is `dashboard/dependencies.py:166`, which calls `RunTrigger()`.

### GREEN
- [ ] Remove the parameter and attribute, and rewrite the docstrings.
- [ ] Update the test constructors, and delete the two tests.
- [ ] Run the partial suite and confirm it is green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.
