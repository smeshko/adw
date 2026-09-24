# TASK-001: Drop port fields from active runs and adw list --running

Depends on: None
Suggested commit: `refactor(cli): drop port fields from active runs and adw list --running`

## Goal

`ActiveRun`, its lock files and `adw list --running` carry no port fields, and lock files written by an older ADW still list.

## Files

- `src/adw/worktree/concurrent.py`:
  - `ActiveRun`: drop the `backend_port`/`frontend_port` docstring lines (`:32-33`) and fields (`:50-53`)
  - the `ConcurrentRunManager` docstring: drop "and allocated ports" (`:76`)
  - `get_active_runs`: drop the two `data.get(...)` port arguments (`:160-161`)
  - `register_run`: drop the two parameters (`:220-221`), their docstring lines (`:231-232`) and the two lock-data keys (`:244-245`)
- `src/adw/cli/list.py`:
  - the `list` docstring: "with worktree and port info" becomes "with their worktree" (`:78`), and the `--running` example comment drops "with ports" (`:87`)
  - `_list_running_runs` docstring: drop "allocated ports," (`:338`)
  - `_display_running_runs`: drop the `Ports` column (`:373`), the port formatting (`:383-389`) and the `ports_str` cell
  - `_output_json_running`: drop the `backend_port`/`frontend_port` keys (`:452-453`)
- `tests/unit/worktree/test_concurrent.py`:
  - delete `test_active_run_with_ports` (`:36`) and the port asserts in `test_active_run_creation` (`:33-34`)
  - drop the port arguments and asserts in `test_register_run_creates_lock_file` (`:106`) and `test_get_active_runs_returns_active_runs` (`:144`)
  - add `test_get_active_runs_reads_legacy_lock_with_ports`
- `tests/unit/cli/test_list_running.py`: drop the port arguments (`:62-63`, `:88-89`, `:134-135`), the rendered-cell assert `assert "9100/9200" in captured.out` in `test_list_running_shows_active_runs` (`:72`), and the JSON port asserts (`:101-102`). Keep that test's run-id and `"1 of 15"` asserts. Add `test_list_running_has_no_ports_column`, and assert the JSON run has no port keys.

## Acceptance

- [ ] `adw list --running` renders `Run ID`, `Elapsed` and `Worktree` columns and no `Ports` column.
- [ ] `adw list --running --json` runs carry no `backend_port`/`frontend_port` keys.
- [ ] A lock file that still has `backend_port`/`frontend_port` keys is listed as an active run.
- [ ] `grep -n "backend_port\|frontend_port" src/adw/worktree/concurrent.py src/adw/cli/list.py` returns nothing.
- [ ] `uv run pytest tests/unit/worktree tests/unit/cli/test_list_running.py -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failure of `test_list_running_has_no_ports_column` and of the JSON-key assert, then the GREEN pytest tail, the grep, and the preflight tail.

## Steps

### RED
- [ ] Add `test_list_running_has_no_ports_column`. Register one run with the current PID, call `_list_running_runs(json_output=False)`, and assert that the captured output has `Run ID` and no `Ports`. Use a wide console, or patch `adw.cli.list.console` with a `Console(width=200)`, so Rich doesn't wrap the headers.
- [ ] In `test_list_running_json_output`, replace the port asserts with `assert "backend_port" not in data["runs"][0]` and the same for `frontend_port`.
- [ ] Add `test_get_active_runs_reads_legacy_lock_with_ports`. Write `<locks_dir>/<run_id>.lock` by hand as JSON with every key `get_active_runs` reads: `run_id`, `pid` (the current PID), `start_time` (`datetime.now(UTC).isoformat()`) and `worktree_path`, plus the old `"backend_port": 9100, "frontend_port": 9200`. Assert `get_active_runs()` returns exactly that run and the lock file still exists. A missing key would count as corruption and delete the lock. The test passes before and after the change, and guards the old lock-file format.
- [ ] Run the two test files. The new column test and the JSON assert fail.

### GREEN
- [ ] Remove the port fields, parameters, lock keys, column and JSON keys listed above.
- [ ] Drop the port arguments and asserts from the existing tests, including `"9100/9200"` at `test_list_running.py:72`, and delete `test_active_run_with_ports`.
- [ ] Run the two test files: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.
