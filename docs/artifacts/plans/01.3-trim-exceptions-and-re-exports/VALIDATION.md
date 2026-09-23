# Validation: Trim exceptions and re-export surfaces

Validated: 2026-09-23 at `faf136b7`, the last code commit of PR #213.

| Criterion | Result |
|---|---|
| `exceptions.py` defines exactly `ADWError`, `ConfigError`, `StateError`, `LLMError`, `TaskError`, `HookError`, `WorktreeError` and `SecurityError` | Met: `^class` grep below |
| No `CommandError`, `PhaseError`, `PortAllocationError`, `MaxConcurrentRunsError`, `get_logger` or `reset_logger` in `src` or `tests`, and no `def to_dict` in `exceptions.py` | Met: both greps are empty |
| `adw status nonexistent-id` and `adw resume` in an empty directory print the same panel and exit code as before | Met: `diff` of before and after is empty for both; panels below |
| `adw --help` is unchanged after the `cli/__init__.py` trim | Met: `diff` against the baseline is empty (38 lines, including `python -m adw --version` → `adw version 0.1.67`) |
| Trimmed `__init__.py` files export only the listed names | Met: the package-import grep lists only `app`, the three `cli/bootstrap.py` logging names, `create_redactor_from_config` in its own test, and the `wizard` subpackage import |
| `scripts/preflight.sh` passes; `uv run pytest` green, coverage ≥ 80% | Met: 3722 passed, 5 skipped, 85.55% |
| `src` line count recorded against the 42,085 baseline | 42,085 → 41,474 (−611) |

## CLI error paths, before and after

The baseline was captured on `ce4c1530` (unchanged `staging`) before any edit, and the after output on `faf136b7`. Both come from an empty scratch directory via `uv run --project <worktree> adw …`, with `uv`'s venv-creation lines stripped. `diff` of each pair is empty.

```
$ adw status nonexistent-id
╭─────────────────────────────── RUN_NOT_FOUND ────────────────────────────────╮
│ Error: Run nonexistent-id not found                                          │
│                                                                              │
│ Suggestion: Use 'adw list' to see available runs                             │
╰──────────────────────────────────────────────────────────────────────────────╯
exit=1

$ adw resume
╭───────────────────────────── NO_INCOMPLETE_RUNS ─────────────────────────────╮
│ Error: No incomplete runs found                                              │
│                                                                              │
│ Suggestion: Use 'adw run "feature"' to start a new run                       │
╰──────────────────────────────────────────────────────────────────────────────╯
exit=1

$ diff before-status after-status && diff before-resume after-resume && diff before-help after-help
(no output)
```

## Preflight and full suite

```
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
365 files already formatted
==> mypy
Success: no issues found in 153 source files
preflight: ok

$ uv run pytest
Required test coverage of 80% reached. Total coverage: 85.55%
================= 3722 passed, 5 skipped in 180.29s (0:03:00) ==================
```

## Greps

```
$ grep -n "^class " src/adw/exceptions.py
8:class ADWError(Exception):
52:class ConfigError(ADWError):
64:class HookError(ADWError):
114:class LLMError(ADWError):
121:class StateError(ADWError):
133:class WorktreeError(ADWError):
149:class TaskError(ADWError):
189:class SecurityError(ADWError):

$ grep -rnw "CommandError\|PhaseError\|PortAllocationError\|MaxConcurrentRunsError\|get_logger\|reset_logger" src tests
(no output)

$ grep -n "def to_dict" src/adw/exceptions.py
(no output)

$ grep -rn "from adw\.\(hooks\|executors\|commands\|logging\|cli\|config\) import" src tests
src/adw/__main__.py:3:from adw.cli import app
src/adw/cli/bootstrap.py:34:from adw.logging import LogManager, LogManagerHandler, create_redactor_from_config
tests/unit/cli/wizard/test_flow.py:153:        from adw.cli import wizard
tests/unit/logging/test_package.py:3:from adw.logging import create_redactor_from_config

$ find src -name '*.py' | xargs wc -l | tail -1
   41474 total
```

## Task evidence

- TASK-001: `test_check_can_start_or_raise_raises_at_limit` and `test_allocate_raises_after_max_attempts`, retargeted to `WorktreeError`, failed against the old classes (`2 failed`) and passed after the switch (`2 passed`). `tests/unit/worktree` plus `test_run_lifecycle.py`: 145 passed.
- TASK-002: the four touched test files: 234 passed.
- TASK-003: full suite 3725 passed, 5 skipped, 85.57%.
- TASK-004: full suite 3722 passed, 5 skipped, 85.55%; `adw --help` diff empty.

## Divergence from the plan: ADW-63

The plan retargeted every stand-in `PhaseError` to `LLMError`. For `test_sync_run_failed_called_on_error`, that switch exposed a bug that predates this branch. `Orchestrator.run()` and `resume()` pass their pre-loop `RunContext` to `RunLifecycle.handle_adw_error`, so an error without a `phase` attribute is reported against the phase the run started in. The same handler then saves that stale context over `context.json`. A scratch run with a real `ContextManager` in a throwaway git repo (plan completes, build raises `LLMError`) printed:

```
phases attempted: ['plan', 'build']
sync_run_failed phase: plan
index phase_reached / phases_completed: plan []
context.json status/current_phase/phase_history: failed plan []
```

This phase is a behaviour-preserving refactor, so it doesn't fix the bug. That test now raises `HookError(phase="build")`, which keeps its original intent: the synced phase comes from the error. The bug is filed as ADW-63 (Backlog, labels `bug`, `core`, `code-review`), with this repro.

## Epic 01 close-out

Phase 1.3 is the last open phase of Epic 01, so this commit ticks the epic-level criteria, sets the epic's `Status:` to `done` and moves its `EPICS.md` row to `Done`.

- B-bug regression tests: criterion 403 had no entries for B2 and B9. Both have RED-verified tests in their phases' VALIDATION.md files, now linked: B2 `test_fake_claude_exit_fails_run` (phase 1.6) and B9 `test_timeout_kills_hook_children` (phase 1.1). All 17 named tests still exist in `tests/`.
- Suite speed: the criterion rests on phase 1.1's measurement (210.2 s → 157.1 s). This phase's full-suite runs took about 180 s, but the load average was about 19 on a 10-core machine shared with other sessions, so those timings can't be compared with the phase 1.1 numbers.
- LOC: 47,016 at `cdb2003f` → 41,474 now (−5,542).
