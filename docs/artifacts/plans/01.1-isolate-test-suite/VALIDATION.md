# Validation: Isolate the test suite from the checkout

Validated: 2026-09-23 at `cce9eb4c`. CI is green on every task commit of PR #202.

| Criterion | Result |
|---|---|
| Full run leaves the checkout, `.adw/runs` and `~/.adw` unchanged | Met: empty diffs, below |
| 1 s hook timeout raises `HookError` within 3 s and kills the `sleep` child | Met: RED 30.08 s → GREEN 1.02 s |
| Full suite ≥ 50 s faster than the baseline | Met: 210.19 s → 157.07 s (**−53.12 s**) |
| `grep -rn "ADW_TEST_" src tests` is empty | Met |
| `scripts/preflight.sh` passes; `uv run pytest` green, coverage ≥ 80% | Met: 4291 passed, 5 skipped, 84.33% |

## No-touch check: real checkout, real home

One full `uv run pytest -p no:cacheprovider` in the worktree. The snapshot was taken before and after, then diffed.

```
== 4291 passed, 5 skipped in 144.69s (0:02:24) ==
Required test coverage of 80% reached. Total coverage: 84.33%

$ diff nt-before.txt nt-after.txt
(empty, exit 0)
```

What the snapshot covered, with its values before the run:

| Item | Before (= after) |
|---|---|
| `git status --short` | empty |
| `git branch` | `feature/adw-7`, `main`, `staging` |
| `git worktree list` | 2 entries: the main checkout on `staging` and this worktree on `feature/adw-7` |
| `.adw/runs` | 0 runs in this worktree |
| `~/.adw` | 491 files: mtime, size and `shasum` of each; aggregate `14f37b62…` before and after |

The worktree's own `.adw/runs` is empty. So `.adw/runs` was also checked in clones seeded with the main checkout's 44 real runs (below).

- **Full suite:** both timing clones kept the seeded runs byte-identical. The runs hash was `08943d05…` in the main checkout, the baseline clone and the HEAD clone.
- **`tests/unit/cli` and `tests/unit/dashboard`:** TASK-004 ran these two directories in a seeded clone. Result: 1526 passed, and the diff of git status, branches, worktrees, run count and runs hash was empty.
- **Outer `HOME`:** after the run, the baseline clone's fake outer `HOME` held `~/.adw/stats-cache.json`: the leak this phase fixes. The HEAD clone's held no files.

## Timing, back to back

Method (RESEARCH.md → Useful Commands):

- two `git clone --local` copies, with `origin` removed: one at `cdb2003f` (baseline) and one at `cce9eb4c` (HEAD)
- each clone seeded with the main checkout's `.adw/{project.yaml,runs}` (44 runs)
- each clone given its own fake `HOME` and a `GIT_*` identity
- `.venv/bin/python -m pytest --durations=15 -p no:cacheprovider -q`, run in the baseline clone and then in the HEAD clone, same machine, same session

| | Baseline `cdb2003f` | HEAD `cce9eb4c` | Delta |
|---|---|---|---|
| pytest time | 210.19 s | 157.07 s | **−53.12 s** |
| wall (incl. startup) | 214 s | 162 s | −52 s |
| result | 1 failed, 4296 passed, 5 skipped | 4291 passed, 5 skipped | |
| coverage | 84.36% | 84.34% | |

The baseline failure is `test_default_cache_path`. That test cleared `os.environ`, so it passed only when `HOME` was the real passwd home. TASK-003 fixed it.

The test count dropped by 6:

- 8 tests deleted:
  - 2 wall-clock tests from `TestTransitionPerformance`
  - 6 `ADW_TEST_*` env-var tests: 2 each for the index, the registry and the stats cache
- 2 tests added: `test_timeout_kills_hook_children` and `test_home_is_isolated`

Baseline:

```
30.11s call     tests/integration/test_hooks.py::TestHookIntegration::test_timeout_with_slow_script
15.42s call     tests/unit/core/test_orchestrator.py::TestRetryLogic::test_retry_with_custom_max_retries
10.10s call     tests/unit/hooks/test_runner.py::TestHookRunner::test_timeout_raises_hook_error
3.26s call     tests/unit/core/test_orchestrator.py::TestRetryLogic::test_spinner_stopped_before_error_logging
3.24s call     tests/unit/core/test_orchestrator.py::TestRetryLogic::test_retry_exhaustion_raises_error
3.21s call     tests/unit/core/test_orchestrator.py::TestRetryLogic::test_recoverable_error_triggers_retry
1.14s call     tests/unit/core/test_orchestrator.py::TestRetryLogic::test_retry_success_after_failures
1.11s call     tests/unit/core/test_orchestrator.py::TestTransitionPerformance::test_slow_transition_logs_debug
0.96s call     tests/integration/test_git_hooks.py::TestBuildCommitDiffFlowIntegration::test_subsequent_phases_create_commits
0.84s call     tests/integration/test_git_hooks.py::TestPreCommitHookIntegration::test_pre_commit_hook_modifies_files
0.79s call     tests/unit/worktree/test_manager.py::TestWorktreeForceCleanup::test_delete_branch_parameter_works
0.73s call     tests/integration/cli/test_init_integration.py::TestInitRunIntegration::test_run_command_loads_config_after_init
0.70s call     tests/unit/worktree/test_manager.py::TestWorktreeManagerRemoval::test_remove_worktree_delete_branch
0.70s call     tests/integration/cli/test_init_integration.py::TestInitRunIntegration::test_run_help_works_after_init
0.65s call     tests/integration/worktree/test_single_phase_preservation.py::TestSinglePhaseWorktreePreservation::test_worktree_preserved_after_single_phase_concept
FAILED tests/unit/core/test_stats_aggregator.py::TestStatsAggregatorInit::test_default_cache_path
============ 1 failed, 4296 passed, 5 skipped in 210.19s (0:03:30) =============
```

HEAD:

```
1.10s call     tests/unit/hooks/test_runner.py::TestHookRunner::test_timeout_kills_hook_children
1.10s call     tests/unit/hooks/test_runner.py::TestHookRunner::test_timeout_raises_hook_error
1.05s call     tests/integration/test_hooks.py::TestHookIntegration::test_timeout_with_slow_script
0.88s call     tests/integration/cli/test_init_integration.py::TestInitRunIntegration::test_run_command_loads_config_after_init
0.83s call     tests/integration/test_git_hooks.py::TestBuildCommitDiffFlowIntegration::test_subsequent_phases_create_commits
0.82s call     tests/integration/test_git_hooks.py::TestPreCommitHookIntegration::test_pre_commit_hook_modifies_files
0.78s call     tests/integration/test_git_hooks.py::TestPreCommitHookIntegration::test_pre_commit_hook_rejects
0.71s call     tests/unit/worktree/test_manager.py::TestWorktreeForceCleanup::test_delete_branch_parameter_works
0.67s call     tests/integration/cli/test_init_integration.py::TestInitRunIntegration::test_run_help_works_after_init
0.67s call     tests/unit/worktree/test_manager.py::TestWorktreeManagerRemoval::test_remove_worktree_delete_branch
0.65s call     tests/integration/worktree/test_single_phase_preservation.py::TestSinglePhaseWorktreePreservation::test_worktree_preserved_after_single_phase_concept
0.59s call     tests/unit/worktree/test_manager.py::TestWorktreeManagerRemoval::test_remove_worktree_force_delete_branch_when_gh_unavailable
0.57s setup    tests/unit/worktree/test_manager.py::TestWorktreeManagerBranchIntegration::test_branch_manager_property_returns_manager
0.55s call     tests/unit/worktree/test_manager.py::TestWorktreeManagerRemoval::test_remove_worktree_preserve_branch_when_gh_unavailable
0.51s call     tests/unit/worktree/test_manager.py::TestWorktreeManagerCreation::test_create_worktree_from_source_branch
================= 4291 passed, 5 skipped in 157.07s (0:02:37) ==================
```

## Hook timeout regression test (B9)

`tests/unit/hooks/test_runner.py::TestHookRunner::test_timeout_kills_hook_children`. The hook script runs `sleep 30 &`, writes the child PID and then calls `wait`. The hook times out after 1 s.

RED, on the unmodified runner:

```
>       assert elapsed < 3
E       assert 30.082328125019558 < 3
30.08s call     tests/unit/hooks/test_runner.py::TestHookRunner::test_timeout_kills_hook_children
1 failed in 30.17s
```

GREEN, with `start_new_session=True` and `os.killpg(process.pid, SIGKILL)`. The test also polls until `os.kill(child_pid, 0)` raises `ProcessLookupError`.

```
1.02s call     tests/unit/hooks/test_runner.py::TestHookRunner::test_timeout_kills_hook_children
1.01s call     tests/integration/test_hooks.py::TestHookIntegration::test_timeout_with_slow_script
1.01s call     tests/unit/hooks/test_runner.py::TestHookRunner::test_timeout_raises_hook_error
132 passed in 3.52s
```

`src/adw/hooks/runner.py` imports nothing from `adw.executors`.

## Leftover test hooks

```
$ grep -rn "ADW_TEST_" src tests
(no output, exit 1)
```

## Static checks

```
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
166 files already formatted
==> mypy
Success: no issues found in 166 source files
preflight: ok
```
