# TASK-001: Read and write live.log through shared path constants

Depends on: None
Suggested commit: `fix(dashboard): read live.log where runs write it`

## Goal

The dashboard's log search and SSE log stream read `runs/<id>/live.log`, the file runs actually write (B4). Every `live.log` reader and writer, and every `.adw/runs` join in the dashboard, builds its path from one set of constants.

## Files

- `src/adw/core/constants.py`: add `from pathlib import Path` and these names:
  - `LIVE_LOG = "live.log"`
  - `CONTEXT_FILE = "context.json"`
  - `def project_runs_dir(project_root: Path) -> Path`, returning `project_root / ".adw" / "runs"`
- `src/adw/dashboard/routes.py`:
  - `_load_log_entries` and `log_stream_sse` use `runs_dir / run_id / LIVE_LOG`. This is the bug fix: the `"logs"` segment goes.
  - Every `project_path / ".adw" / "runs"` becomes `project_runs_dir(project_path)`, at 536, 925, 1014, 1060, 1124, 1281, 1387 and 1532. Also 555, `ctx.worktree_path / ".adw" / "runs"`, which becomes `project_runs_dir(ctx.worktree_path)`.
- `src/adw/dashboard/partials.py`:
  - `terminal_mode` (~954) and `terminal_logs` (~994) use `project_runs_dir(project_path) / run_id / LIVE_LOG`.
  - The `.adw/runs` joins at ~703, ~881 and ~1096 use `project_runs_dir`.
- `src/adw/dashboard/mutations.py:244`: `project_runs_dir(project_path)`.
- `src/adw/cli/bootstrap.py`: `get_runs_dir` builds its path with `project_runs_dir(root)`. Both `LiveStreamTransport(run_dir / "live.log")` calls (134, 260) use `LIVE_LOG`.
- `src/adw/cli/logs.py`:
  - `_get_runs_dir` returns `project_runs_dir(cwd)`, keeping its `.adw`-missing exit.
  - `"live.log"` → `LIVE_LOG` at 566, 702 and 733.
  - `"context.json"` → `CONTEXT_FILE` at 380, 567, 696 and 726.
- `src/adw/core/context_manager.py:72/133`: `"context.json"` → `CONTEXT_FILE`.
- These 6 tests write their fixture at `run_dir / "logs" / "live.log"`; move it to `run_dir / "live.log"`:
  - `tests/unit/dashboard/test_log_viewer.py`, `TestLoadLogEntries`: `test_parses_live_log_file`, `test_filters_by_phase`, `test_phase_filter_uses_word_boundary` and `test_handles_malformed_lines`
  - `tests/unit/dashboard/test_llm_log_integration.py`: `test_log_entries_parses_real_log_with_ansi` and `test_log_entries_multiple_phases`
- `tests/unit/dashboard/test_log_viewer.py`: add `TestLoadLogEntries::test_reads_log_written_by_run`.
- `tests/unit/dashboard/test_active_failed_runs.py`: add `test_log_stream_emits_live_log_lines`, next to `test_log_stream_endpoint_exists`.

## Acceptance

- [ ] `test_reads_log_written_by_run`:
  - `create_log_manager(run_dir=project_runs_dir(tmp_path) / run_id)` logs one INFO event.
  - `_load_log_entries(project_runs_dir(tmp_path), run_id)` returns an entry whose message contains that event's text.
- [ ] `test_log_stream_emits_live_log_lines`:
  - Setup: a run whose `live.log` holds two `[ts] [TOOL] …` lines, with `ContextManager` patched to return `status="completed"`.
  - `GET /runs/{id}/logs/stream` returns a body with two `event: log-line` events that carry those messages.
- [ ] The updated `TestLoadLogEntries` tests pass with the fixture at `run_dir / "live.log"`.
- [ ] `grep -rn '"logs" / "live.log"' src` returns nothing.
- [ ] `grep -rn '"live.log"' src/adw --include='*.py'` returns only `core/constants.py`.
- [ ] `grep -rn '".adw" / "runs"' src/adw/dashboard` returns nothing.
- [ ] `uv run pytest tests/unit/dashboard tests/unit/cli/test_logs.py tests/unit/cli/test_bootstrap.py tests/unit/core/test_context_manager.py -o addopts=""` passes.

Evidence:
- the RED run: the 6 moved-fixture tests plus the 2 new tests fail on the unfixed routes
- the GREEN run
- the three grep outputs

## Steps

### RED
- [ ] Move the `live.log` fixture in the 6 existing `_load_log_entries` tests to `run_dir / "live.log"`. Use the literal here; `LIVE_LOG` doesn't exist yet.
- [ ] Add `test_reads_log_written_by_run`:
  - Call `create_log_manager(run_dir=…)` and log through the returned `LogManager`: `.info(LogCategory.PHASE, "phase plan started")`.
  - Close its transports, then assert that `_load_log_entries` returns the entry.
  - Build `run_dir` as `tmp_path / ".adw" / "runs" / run_id` for now.
- [ ] Add `test_log_stream_emits_live_log_lines`, modelled on `test_log_stream_endpoint_exists`:
  - Point the index entry's `project_path` at `tmp_path`.
  - Write `tmp_path/.adw/runs/<id>/live.log`.
  - Patch `adw.dashboard.routes.ContextManager` so `load()` returns a context with `status="completed"`.
  - Assert that the response text contains both messages and two `event: log-line`.
- [ ] Run them and confirm they fail: `_load_log_entries` returns `[]`, and the stream emits no `log-line`.

### GREEN
- [ ] Add `LIVE_LOG`, `CONTEXT_FILE` and `project_runs_dir` to `core/constants.py`.
- [ ] Fix `_load_log_entries` and `log_stream_sse` to use `runs_dir / run_id / LIVE_LOG`.
- [ ] Run the new tests and confirm they are green.

### REFACTOR
- [ ] Replace the remaining hand-built paths listed under Files. Import only the names each module uses.
- [ ] Switch the new tests to `project_runs_dir` and `LIVE_LOG`.
- [ ] Run the three greps above.
- [ ] `scripts/preflight.sh` passes.

## Notes

- Never write `runs_dir = runs_dir(...)`: most call sites already have a local variable called `runs_dir`. The helper is called `project_runs_dir` for exactly this reason.
- `bootstrap.get_runs_dir` keeps its `mkdir`, and `logs._get_runs_dir` keeps its "Run 'adw init' first" exit. Only the path expression changes.
- `test_log_stream_endpoint_exists` mocks a context without a real `live.log`. It stays as it is.
