# TASK-002: Stop closing tickets at run completion

Depends on: None
Suggested commit: `fix(task-managers): stop closing tickets at run completion`

## Goal

A completed run never closes its ticket (B1). `auto_close` still loads but does nothing, and it logs one deprecation warning per completed run. The closer, the GitHub merge client and `is_pr_merged` are gone.

## Files

- Delete these files:
  - `src/adw/task_managers/closer.py`
  - `src/adw/task_managers/github_client.py`
  - `tests/unit/task_managers/test_closer.py`
  - `tests/unit/task_managers/test_github_client.py`
- `src/adw/task_managers/base.py`, `linear.py`, `null.py`: remove `is_pr_merged` (base 118–131, linear 409–424, null 91–100). `close_task` stays.
- `src/adw/core/run_lifecycle.py`:
  - Delete `_maybe_close_task` (815–863) and its call in `finalize_success` (321–325).
  - Remove the `task_uuid` parameter and its docstring lines (274, 291), and step 6 in the docstring.
  - `finalize_success` logs `logger.warning(...)` once when `self.task_manager_config.auto_close` is true. The message says `task_manager.auto_close` is deprecated and ignored, that tickets move through `state_mapping`, and that the key can be removed.
- `src/adw/core/orchestrator.py`: remove `task_uuid` from `run()` (294, 313) and from the `finalize_success` call (341). Remove the auto-close mentions in the docstrings (165, 198, 306, 313–315).
- `src/adw/cli/app.py`:
  - Stop computing `task_uuid` (316, 322) and stop passing it (435–441).
  - `task_info` is still fetched and kept.
  - Fix the comments that mention issue closing (273, 314–315, 325).
- `src/adw/models/config.py:430`: the `auto_close` description becomes `"Deprecated and ignored; tickets move through state_mapping."`, and the class docstring (374, 400) says the same.
- `src/adw/cli/wizard/task_manager.py`:
  - Delete `_prompt_auto_close` (254–268) and its call (128–129).
  - Drop `auto_close` from both returned dicts (141, 159).
- `src/adw/config/yaml_generator.py:298, 329`: stop writing the `# auto_close:` comment line.
- `src/adw/task_managers/sync.py:164, 172`: drop the auto-close mentions in the `sync_run_complete` docstring.
- Docs:
  - `docs/features/complex-field-editors-task-manager-security.md:88, 101`
  - `docs/features/settings-page-config-viewing.md:32`

  Mark `auto_close` as deprecated and ignored.
- Tests:
  - `tests/unit/core/test_run_lifecycle.py` (new tests in `TestFinalizeSuccess`)
  - `tests/unit/task_managers/test_base.py`, `test_null.py`, `test_linear.py`
  - `tests/unit/cli/wizard/test_task_manager.py`
  - `tests/unit/config/test_yaml_generator.py`

## Acceptance

- [ ] `test_auto_close_leaves_ticket_open_and_warns_once`:
  - Setup: `RunLifecycle(task_manager_config=TaskManagerConfig(type="linear", auto_close=True, …))` and a context with `task_info` set.
  - `finalize_success(context)` never calls `LinearTaskManager.close_task` (patched at class level), and never builds a task manager through `TaskManagerFactory` (patched).
  - `caplog` holds exactly one record whose message contains `auto_close` at `WARNING`.
- [ ] With `auto_close` false (the default), `finalize_success` logs no `auto_close` warning.
- [ ] A `project.yaml` with `task_manager: {type: linear, auto_close: true}` still loads through `ConfigLoader`.
- [ ] `adw init --wizard`'s task-manager step no longer asks "Auto-close task when PR merged?", and the generated YAML has no `auto_close` line. This is covered by the wizard and generator tests.
- [ ] `grep -rn "IssueCloser\|GitHubClient\|is_pr_merged\|task_uuid" src` returns nothing.
- [ ] `uv run pytest tests/unit/core/test_run_lifecycle.py tests/unit/core/test_orchestrator.py tests/unit/task_managers tests/unit/cli tests/unit/config tests/unit/models -o addopts=""` passes.

Evidence:
- the RED run: on today's code, the new test fails because `TaskManagerFactory` is called and no warning is logged
- the GREEN run
- the grep output

## Steps

### RED
- [ ] In `TestFinalizeSuccess`, add `test_auto_close_leaves_ticket_open_and_warns_once` as described above. Patch `adw.task_managers.TaskManagerFactory` and `adw.task_managers.linear.LinearTaskManager.close_task`, and use `caplog.at_level(logging.WARNING, logger="adw.core.run_lifecycle")`.
- [ ] Add `test_no_auto_close_warning_by_default`.
- [ ] Run both and confirm the first fails on today's code, where `finalize_success(context, task_uuid=…)` reaches the factory. Call it with `task_uuid` for the RED run only, then drop the argument in GREEN.

### GREEN
- [ ] Delete the two modules and their tests, and `is_pr_merged` from the Protocol and both implementations, together with their test cases (`TestLinearTaskManagerIsPrMerged`, the `hasattr(manager, "is_pr_merged")` check, `test_is_pr_merged_returns_false`, and `MinimalTaskManager.is_pr_merged` in `test_base.py`).
- [ ] Delete `_maybe_close_task` and the `task_uuid` plumbing in `run_lifecycle.py`, `orchestrator.py` and `app.py`.
- [ ] Add the one-line deprecation warning in `finalize_success`, right where the close call was.
- [ ] Wizard: remove the prompt and the dict keys, and update `tests/unit/cli/wizard/test_task_manager.py`:
  - Delete `test_enabled_with_auto_close`.
  - Drop `auto_close` from the expected dicts and the mocked `Confirm.ask` side effects (lines 104, 120, 143, 164, 211, 232, 263, 310).
- [ ] Generator: remove the `auto_close` comment line, and update `test_yaml_generator.py`.
- [ ] Run the partial suite until it's green.

### REFACTOR
- [ ] Update the `auto_close` description and docstrings, the feature docs, and the stale comments in `app.py`, `orchestrator.py` and `sync.py`.
- [ ] Run the grep, then `scripts/preflight.sh`.

## Notes

- **Log the warning at the use site, not in a pydantic validator.** A single run validates `ProjectConfig` at least three times, and the first time is before the log manager exists.
- **Leave the dashboard `auto_close` toggle and its tests** (`tests/dashboard/test_settings_*.py`) alone. Epic 02 removes settings editing. The toggle still round-trips the key, which now only produces the warning.
- **`resume()` never passed `task_uuid`,** so it needs no change beyond the shared `finalize_success` signature.
- **`finalize_success` still takes `pr_result` after this task.** TASK-004 removes it.
