# Plan: Trim exceptions and re-export surfaces

Status: draft
Branch: feature/adw-9
Risk: small
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.3 — Trim exceptions and re-export surfaces
Linear: ADW-9
Created: 2026-09-23

## Goal

After this phase:

- `src/adw/exceptions.py` defines only the exception classes something raises: `ADWError`, `ConfigError`, `StateError`, `LLMError`, `TaskError`, `HookError` and `WorktreeError`, plus `SecurityError` until phase 2.1 removes the security layer.
- Port-allocation and concurrent-run-limit failures raise `WorktreeError` with their existing codes (`PORT_ALLOCATION_FAILED`, `MAX_CONCURRENT_REACHED`), messages and suggestions.
- No exception carries a `to_dict()` method, a doctest-style example, or an `__init__` that only forwards to `ADWError`.
- The `hooks`, `executors`, `commands`, `logging`, `cli` and `config` package `__init__.py` files re-export only the names `src` imports through the package path, plus `adw.config.ConfigLoader`.
- Every CLI error panel prints the same code, message and suggestion as before.

## Scope

- `src/adw/exceptions.py`:
  - Delete `PortAllocationError` and `MaxConcurrentRunsError`. `worktree/ports.py` and `worktree/concurrent.py` raise `WorktreeError` instead, with the same code, message and suggestion (TASK-001).
  - Delete `CommandError` and `PhaseError`, which nothing in `src` raises (TASK-002).
  - Delete every `to_dict()` (6 methods), the `Example:` blocks and the `__init__` methods of `ConfigError`, `LLMError`, `StateError` and `WorktreeError`, which only forward their arguments to `ADWError.__init__` (TASK-003).
  - Keep `ADWError` (`code`, `message`, `suggestion`, `recoverable`, `__str__`), `HookError` (`phase`, `exit_code`, `stdout`, `stderr`, `duration_ms`), `TaskError` (`task_id`) and `SecurityError` (its fields and `__str__`).
- Docstrings that name the deleted classes: the `Raises:` sections in `core/phase_runner.py` (`CommandError`), `core/run_lifecycle.py` (`MaxConcurrentRunsError`), `worktree/ports.py` and `worktree/concurrent.py`.
- Package `__init__.py` files (TASK-004). "Importers" means `from adw.<pkg> import …` in `src`:
  - `hooks` (20 names, 0 importers), `executors` (5, 0) and `commands` (2, 0): keep the module docstring, drop every import and `__all__`.
  - `logging`: keep `LogManager`, `LogManagerHandler` and `create_redactor_from_config`, which `cli/bootstrap.py` imports. Drop the other re-exports and delete `get_logger`, `reset_logger` and `_default_logger`, which nothing in `src` calls.
  - `cli`: keep `app`, which `adw.__main__` and the `adw = "adw.cli:app"` entry point use. Drop the other seven.
  - `config`: keep `ConfigLoader` only (see Decisions).
- Tests:
  - Retarget the `pytest.raises` and `side_effect` uses of the deleted classes in `test_ports.py`, `test_concurrent.py`, `test_orchestrator.py`, `test_run_lifecycle.py`, `test_phase_runner.py` and `test_progress.py`.
  - Delete the tests that only cover deleted code: `TestMaxConcurrentRunsError` in `test_concurrent.py`, the two `test_security_error_to_dict` tests, and `TestGetLogger`/`TestResetLogger` in `tests/unit/logging/test_package.py`.
  - Point the tests that import through a trimmed package path (`from adw.commands import …` in 6 files, `from adw.executors import LLMExecutor`, `from adw.logging import Redactor`) at the defining module.

## Out of Scope

- `TaskError.task_id`. The epic lists `TaskError` without trimming its fields, and dropping `task_id` would touch 14 raise sites in `task_managers/` for no user-visible change.
- The `__init__.py` files of `core`, `models`, `task_managers` and `worktree`. Each has real importers in `src`, and the epic doesn't list them. Epic 02 consolidates those packages.
- `SecurityError` and the two duplicate test files that cover it (`tests/unit/test_exceptions.py`, `tests/unit/test_security_error.py`). Phase 2.1 deletes the security layer with them; this phase only removes their `to_dict` tests.
- `LLMRateLimitError`: phase 1.6 already removed it, so there is nothing to keep.
- Error codes, messages and suggestions. Every raise site keeps its text.

## Research Summary

- **Raised classes:** `grep -rnw` over `src` finds no `raise CommandError`/`raise PhaseError`; their only `src` mentions are the class bodies and two stale `Raises: CommandError` docstrings in `core/phase_runner.py`. Tests use them as stand-in `ADWError`s in 4 files.
- **Absorbed classes:** `PortAllocationError` is raised once (`worktree/ports.py:167`), in `PortAllocator.allocate`, which no `src` path calls. `MaxConcurrentRunsError` is raised once (`worktree/concurrent.py:213`), from `RunLifecycle._create_worktree_for_run`, outside the `try/except WorktreeError: raise` block, so the new type changes no handler. No `src` handler catches either class by name; the CLI catches `ADWError`.
- **`MaxConcurrentRunsError.context`:** nothing in `src` reads it, and no CLI path prints it. The `active_ids` list in `check_can_start_or_raise` exists only to fill it, so it goes too.
- **`to_dict`:** the six exception methods have no caller in `src`. The other `to_dict` methods (`config/checker.py`, `models/resume.py`) are unrelated and stay.
- **`getattr(error, "phase", None)`** in `RunLifecycle.handle_adw_error` stays: `HookError` still carries `phase`. The tests that passed `PhaseError(phase="build")` set `context.current_phase="build"`, so an error without `phase` hits the same fallback.
- **Package importers:** `src` imports through the package path only `adw.logging` (`LogManager`, `LogManagerHandler`, `create_redactor_from_config` in `cli/bootstrap.py`) and `adw.cli` (`app` in `__main__.py` and the entry point). No `.sh`, `.md`, `.yaml` or template under `src/adw/defaults` imports `adw.*`. The bundled `post.sh` that imported `adw.config.ConfigLoader` was replaced by Python in phase 1.9 (#209).
- **Name shadowing in `cli/__init__.py`:** `from adw.cli.init import init` rebinds `adw.cli.init` from the module to the function. Removing it restores the submodule attribute; no `src` or test code relies on the function binding.
- **Baseline, captured before any change** (scratchpad `before-status.txt`, `before-resume.txt`, `before-help.txt`): `adw status nonexistent-id` prints a `RUN_NOT_FOUND` panel with "Use 'adw list' to see available runs"; `adw resume` in an empty directory prints `NO_INCOMPLETE_RUNS` with `Use 'adw run "feature"' to start a new run`. Both exit 1. `src` is 42,085 lines.

## Decisions

- **`adw.config` keeps `ConfigLoader`, and only it.** Nothing imports through `adw.config` any more, but the epic keeps `ConfigLoader` for shell hooks, and user projects may still carry a copy of the pre-#209 bundled `post.sh` that imports it. Keeping one name costs nothing; the other seven go.
- **Fold into `WorktreeError`, not `ADWError`.** The epic asks for it, and both failures come from `adw.worktree`, so a caller catching `WorktreeError` sees them together.
- **Tests that used `PhaseError`/`CommandError` as a stand-in switch to the error the code path actually raises:** `LLMError` for a failed phase in the orchestrator and lifecycle tests, `ConfigError` for a command-resolution failure in `test_phase_runner.py`, and `LLMError` for the progress-display test.
- **Trim pass-through `__init__` methods.** `ConfigError`, `LLMError`, `StateError` and `WorktreeError` repeat `ADWError`'s exact signature and only call `super().__init__`. Inheriting it keeps every call site and mypy `--strict` happy.
- **All tasks are `impl`, but most have no RED step.** Deleting code can't be driven by a new failing test. Existing tests cover the raise sites; TASK-001 tightens the two absorbed-class tests to assert the new type and unchanged codes, so they fail against the old classes.
- **No `validate-plan` pass.** The plan is `small` risk, every change is a deletion or a type rename at a known site, and the full suite plus the CLI before/after diff prove each step.

## Risks

- **Removing a package re-export breaks an import-time side effect or a circular-import order.** Mitigation: TASK-004 runs the full suite and `adw --help`, and diffs the help output against the baseline.
- **A test outside the grep list constructs a deleted class through a string path, such as a `patch("adw.exceptions.PhaseError")`.** Mitigation: each task ends with `grep -rnw <Class> src tests` returning nothing, then the full suite.
- **Conflicts with open Epic 02 branches (`feature/adw-19`, phase 2.3) that touch `exceptions` importers.** Mitigation: the edits at shared sites are one-line import changes; rebase on `staging` before the PR.

## Acceptance Criteria

- [ ] `exceptions.py` defines exactly `ADWError`, `ConfigError`, `StateError`, `LLMError`, `TaskError`, `HookError`, `WorktreeError` and `SecurityError`. Evidence: `grep -n '^class ' src/adw/exceptions.py`.
- [ ] `grep -rnw "CommandError\|PhaseError\|PortAllocationError\|MaxConcurrentRunsError\|get_logger\|reset_logger" src tests` returns nothing, and `grep -n "def to_dict" src/adw/exceptions.py` returns nothing.
- [ ] `adw status nonexistent-id` and `adw resume` in an empty directory print the same panel (code, message, suggestion) and exit code as the baseline. Evidence: `diff` of before and after output.
- [ ] `adw --help` output is unchanged after the `cli/__init__.py` trim. Evidence: `diff` against `before-help.txt`.
- [ ] The trimmed `__init__.py` files export only the names listed under Scope. Evidence: `grep -rn "from adw\.\(hooks\|executors\|commands\|logging\|cli\|config\) import" src tests` lists only `LogManager`/`LogManagerHandler`/`create_redactor_from_config`, `app`, and `from adw.cli import wizard` (a subpackage import).
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage at or above 80%.
- [ ] `src` line count is recorded against the 42,085 baseline for the epic-level LOC criterion.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [ ] TASK-001: Fold PortAllocationError and MaxConcurrentRunsError into WorktreeError
- [ ] TASK-002: Delete the never-raised CommandError and PhaseError
- [ ] TASK-003: Strip to_dict, docstring examples and pass-through inits from exceptions.py (depends on TASK-001,TASK-002)
- [ ] TASK-004: Trim package re-export lists to what src imports
- [ ] TASK-005: Final Validation
