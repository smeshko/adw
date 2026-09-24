# TASK-008: One runs directory path, created only by adw run

Depends on: TASK-003, TASK-005, TASK-006, TASK-007. Only the `AGENTS.md` bullet needs them. It says every git/gh call goes through `adw.git`, which holds only after TASK-003, and it names the modules the other three add.
Suggested commit: `fix(cli): build the runs path once and create it only in adw run`

## Goal

`project_runs_dir` is the only code that builds the `.adw/runs` path. One CLI guard, `require_runs_dir()`, replaces the three `_get_runs_dir` variants. `adw status`, `abort`, `resume`, `pr`, `cleanup` and `logs` exit 1 with "No .adw directory found" outside a project, and create nothing. Only `adw run` creates `.adw/runs`.

## Files

- `src/adw/cli/bootstrap.py`:
  - Delete `get_runs_dir` (`:64`–`:76`).
  - Add `require_runs_dir(project_root: Path | None = None) -> Path`. When `(root / ".adw").is_dir()` is false, it prints the two lines `logs._get_runs_dir` prints today (`Error: No .adw directory found` / `Suggestion: Run 'adw init' first`) and raises `typer.Exit(1)`. Otherwise it returns `project_runs_dir(root)`. It never calls `mkdir`. `root` is `project_root or get_project_root()`.
  - `create_orchestrator` (`:205`): `runs_dir = project_runs_dir(project_root)` then `runs_dir.mkdir(parents=True, exist_ok=True)`. This is the one place the CLI creates the directory.
- Callers of the old helpers switch to `require_runs_dir()`:
  - `cli/status.py:86`, `cli/abort.py:39`, `cli/resume.py:36`, `cli/pr.py:150`, and `cli/cleanup.py:58` and `:226`.
  - `cli/logs.py`: delete `_get_runs_dir` (`:216`–`:231`); `_get_run_dir` calls `require_runs_dir()`.
- `src/adw/cli/list.py`: delete `_get_runs_dir` (`:297`–`:309`). `list_runs` uses `runs_dir = project_runs_dir(Path.cwd())` and falls back to the global index when `not runs_dir.is_dir()`, as today.
- Hand-built `".adw" / "runs"` paths → `project_runs_dir(...)`:
  - `cli/app.py:242`, `:349`, `:368`
  - `cli/global_commands.py:727`
  - `core/run_directory.py:62`
  - `core/stats_aggregator.py:243`, `:291`, `:341`, `:489`
  - `core/extensions/ship.py:147`–`:155`
  - `worktree/manager.py:184`, `:238`, `:239`
  - `config/initializer.py:116`: `project_runs_dir(self.project_root)`, or its root attribute. Minimal init still creates the directory (out of scope).
- `AGENTS.md`, under "Architecture notes", gets one bullet naming the shared primitives. Load the `writing-for-agents` skill before editing. The bullet says:
  - `adw.git` runs every git/gh call, with timeouts
  - `adw.format` does display formatting and status styles
  - `adw.fs.atomic_write` writes state files
  - `core.constants.project_runs_dir` builds the runs path, and only `adw run` creates it
- Tests:
  - `tests/unit/cli/test_project_guard.py` (new):
    - `test_read_only_commands_outside_a_project_create_nothing`, parametrized over these argument lists:
      - `["status"]`
      - `["status", "01ARZ3NDEKTSV4RRFFQ69G5FAV"]`
      - `["abort", "01ARZ3NDEKTSV4RRFFQ69G5FAV"]`
      - `["resume", "01ARZ3NDEKTSV4RRFFQ69G5FAV"]`
      - `["pr", "01ARZ3NDEKTSV4RRFFQ69G5FAV"]`
      - `["cleanup", "01ARZ3NDEKTSV4RRFFQ69G5FAV"]`
      - `["logs", "state", "01ARZ3NDEKTSV4RRFFQ69G5FAV"]`

      Each runs through `CliRunner` in an empty `tmp_path` (chdir'd). Assert that the exit code is 1, that `No .adw directory found` is in the output, and that `list(tmp_path.iterdir())` holds nothing new: no `.adw`.
    - `test_status_in_a_project_without_runs_creates_nothing`: `tmp_path/.adw` exists without `runs`. `adw status` prints `No runs found`, exits 0, and `tmp_path/.adw/runs` still doesn't exist.
  - Unit-test patch targets move from `get_runs_dir` to `require_runs_dir`:
    - `adw.cli.status.get_runs_dir`: 6 sites in `tests/unit/cli/test_status.py`
    - `adw.cli.abort.get_runs_dir`: 4 sites in `tests/unit/cli/test_abort.py`
    - `adw.cli.resume.get_runs_dir`: 1 site in `tests/unit/cli/test_resume.py`
  - The four integration-fixture patches are deleted, not renamed: `adw.cli.status` / `adw.cli.resume` / `adw.cli.bootstrap.get_runs_dir` in `test_status_integration.py:31`–`:32` and `test_resume_integration.py:31`–`:32`. See the fixture rewrite below (validation round 2, #6).
    - `adw.cli.list._get_runs_dir` (`tests/integration/cli/test_list_integration.py:27`, `:239`): the fixture creates `tmp_path/.adw/runs` and does `monkeypatch.chdir(tmp_path)` instead of patching. `:239` (no runs dir) chdirs into an empty `tmp_path`.
  - `tests/unit/cli/test_list.py:243`–`:258` tests `_get_runs_dir` directly. Delete it; the list fallback is covered by `list_runs` tests.
  - `tests/integration/cli/test_status_integration.py:265`–`:271` (`test_status_no_runs_exist`) accepts either outcome today. Once its fixture builds `.adw/runs` and chdirs (below), tighten it to expect exit 0 and `No runs found`. The outside-a-project case belongs to `test_project_guard` (validation round 2, #6).
  - **The integration fixtures must stop patching and chdir instead (validation round 1, #9).**
    - The `mock_runs_dir` fixtures in `tests/integration/cli/test_resume_integration.py:25`–`:32` and `test_status_integration.py:25`–`:32` patch `adw.cli.bootstrap.get_runs_dir`, so that `create_orchestrator` (reached from `resume.py:139`) uses the tmp runs dir.
    - After this task, `create_orchestrator` calls no helper, so a renamed patch would intercept nothing. The orchestrator would then `mkdir` `.adw/runs` in the checkout, and the tests would still pass on header text.
    - Rewrite both fixtures to build `tmp_path/.adw/runs` and `monkeypatch.chdir(tmp_path)`, and drop the runs-dir patches.

## Acceptance

- [ ] `rg -n '/ "runs"' src` prints only `src/adw/core/constants.py`.
- [ ] `rg -n 'get_runs_dir|_get_runs_dir' src tests` prints nothing.
- [ ] `test_read_only_commands_outside_a_project_create_nothing` passes for all seven argument lists, and `test_status_in_a_project_without_runs_creates_nothing` passes.
- [ ] `uv run pytest tests/unit/cli tests/unit/core tests/integration -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failures (today `adw status` exits 0 and creates `.adw/runs`), then the GREEN tail, the `rg` outputs and the preflight tail.

## Steps

### RED
- [ ] Write `tests/unit/cli/test_project_guard.py`; run it. `status` exits 0 and leaves `.adw/runs`, and `abort`, `resume`, `pr` and `cleanup` create `.adw/runs` before failing. `logs state` already exits 1 and creates nothing, so its case passes before and after; it pins the shared message.

### GREEN
- [ ] Add `require_runs_dir`, delete the three old helpers, and switch their callers; move the `mkdir` into `create_orchestrator`.
- [ ] Replace the hand-built `.adw/runs` paths with `project_runs_dir`.
- [ ] Move the patch targets; run the partial suite: green.

### REFACTOR
- [ ] Add the `AGENTS.md` bullet; re-run the `rg` checks; `scripts/preflight.sh` passes.

## Notes

- `RunLookup._list_runs` already returns an empty list when the runs directory is missing (`run_lookup.py:114`). So `adw status` in an initialised project without runs prints "No runs found" once the guard stops creating the directory.
- `resume` reaches the runs-dir helper first (`resume.py:77` → `_create_resume_manager` at `:36`), so it gets the guard's message like the other commands.
- The live log for `adw run` still creates `.adw/runs/<id>/` lazily (`live_stream.py:130`). That is `adw run` creating its own directory, which is allowed.
