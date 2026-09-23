# Plan: Isolate the test suite from the checkout

Status: done
Branch: feature/adw-7
Risk: medium
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.1 — Isolate the test suite from the checkout
Linear: ADW-7
Created: 2026-09-23

## Goal

`uv run pytest` never touches the checkout, `~/.adw` or real wall-clock time. A hook timeout kills the hook and every child it started.

## Scope

- `hooks/runner.py`: start hooks in their own session and `os.killpg` the group on timeout (B9). The fixture `tests/fixtures/hooks/slow.sh` uses `exec sleep`.
- `tests/unit/core/test_orchestrator.py`: patch the retry backoff sleep in `TestRetryLogic`, and delete the two wall-clock tests in `TestTransitionPerformance`.
- Root autouse fixture `isolated_home` in `tests/conftest.py`: `HOME` points at `tmp_path / "home"`, and `GIT_AUTHOR_*`/`GIT_COMMITTER_*` are set.
- Delete the `ADW_TEST_INDEX_PATH`, `ADW_TEST_REGISTRY_PATH` and `ADW_TEST_STATS_CACHE_PATH` branches from `core/index_manager.py`, `core/project_registry.py` and `core/stats_aggregator.py`, with the tests and fixtures that use them.
- Autouse `monkeypatch.chdir(tmp_path)` for `tests/unit/cli/` and `tests/unit/dashboard/` through a `conftest.py` in each.
- One line in `AGENTS.md` about the home isolation.

## Out of Scope

- Reusing `ClaudeCodeExecutor._kill_process_group` from the hook runner. Consolidating helpers is Epic 02, so the runner inlines its own `os.killpg`.
- Orphan children of a hook that exits 0 while a background child still holds its pipes. The acceptance criteria cover only the timeout path.
- Hook config wiring (`timeout_seconds` from `project.yaml`, B10): phase 1.9.
- Deduplicating `git_repo`/`sample_context` fixtures and deleting unused root fixtures: phase 1.4.
- The `chdir` fixtures that already exist per module (`test_run.py`, `test_logs.py`, `test_env_loading.py`, …). They stay as they are.
- `tests/dashboard/` (top level) and `tests/integration/`. They are not named in the epic, and a full run showed neither writing outside `tmp_path`.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). Every change was prototyped in a throwaway clone, with a fake `HOME` and 44 real runs seeded into `.adw/runs`:

- **Baseline** (`cdb2003f`): 216.6 s. Four items account for 67 s:
  - the hook timeout tests: 30.1 s + 10.1 s
  - `TestRetryLogic`: ≈26 s of real backoff sleeps
  - `test_slow_transition_logs_debug`: 1.1 s
- **Prototype**: 152.0 s (−64.6 s). The before/after snapshot diff is empty: git status, branches, worktrees, run hashes, and every file under the outer `HOME`. The baseline had leaked `~/.adw/stats-cache.json`.
- The new hook regression test fails on today's runner after 30.1 s and passes in about 1.1 s with the fix.
- The prototype's only failure was `test_default_cache_path`, which clears the whole environment, `HOME` included. TASK-003 fixes it.

## Decisions

- **Rely on `HOME` and delete the three `ADW_TEST_*` hooks.** The user chose this over setting all three env vars. It gives one mechanism, removes test-only branches from production code, and also covers `commands/resolver.py`'s `~/.adw/commands` lookup.
- **`HOME` goes to `tmp_path / "home"`, not to `tmp_path` itself.** TASK-004 makes cwd `tmp_path`, so `~/.adw` would land on the project's `.adw/`. Many tests assert what `tmp_path/.adw` does or doesn't contain.
- **Rename the fixture from `isolated_global_index` to `isolated_home`, returning the home dir.** It no longer isolates only the index. Its one external user, `tests/integration/cli/test_feature_description.py`, switches to `isolated_home / ".adw" / "index.jsonl"`.
- **Delete both wall-clock tests in `TestTransitionPerformance`.** They are `test_transition_under_1_second` and `test_slow_transition_logs_debug`. The "exceeded 1s" branch is a debug log, not behaviour (ADR-001). `test_transition_logs_duration` stays.
- **Patch `adw.core.orchestrator.time.sleep`, not the global `time.sleep`.** The patch is scoped to the module under test, through a class-level autouse fixture in `TestRetryLogic`.
- **The hook runner inlines `os.killpg`.** It doesn't import the executor's static helper, which would add a cross-module dependency that Epic 02 is going to consolidate anyway.
- **Measure timing back to back in throwaway clones** (baseline commit vs HEAD, same machine, same session). This controls for machine variance. The real checkout and real `~/.adw` are snapshotted around one real `uv run pytest` for the no-touch criterion.

## Risks

- **A per-test `HOME` hides the global git identity.** Commits in tests would fail. Mitigation: the fixture sets `GIT_AUTHOR_NAME/EMAIL` and `GIT_COMMITTER_NAME/EMAIL`. The prototype passed the full suite.
- **`os.killpg` after the leader has exited raises `ProcessLookupError`.** Mitigation: catch it and still `await process.wait()`.
- **The regression test's "child gone" check can see a zombie that is not yet reaped** (CI on Linux). Mitigation: poll `os.kill(pid, 0)` for up to 2 s before failing.
- **A test that clears `os.environ` falls back to the real home** through the passwd database. Mitigation: TASK-003 removes the only such case (`test_default_cache_path`), and the guard test `tests/unit/test_isolation.py` asserts that all three default paths resolve under the temp home.
- **The flaky `test_stats_display_with_real_data` (AGENTS.md) now depends on a clean home.** Mitigation: rerun it once before investigating, as AGENTS.md says.

## Acceptance Criteria

- [x] A full `uv run pytest` in the checkout leaves these unchanged:
  - `git status`, `git branch` and `git worktree list`
  - the contents of `.adw/runs/` (count and hashes)
  - every file under `~/.adw/`

  Evidence: the before/after snapshot diff (empty) in `VALIDATION.md`.
- [x] A hook with a 1 s timeout whose script starts `sleep 30` raises `HookError` within 3 s, and the `sleep` child is gone. Evidence: `test_timeout_kills_hook_children` output, RED at 30 s and GREEN after the fix.
- [x] Full-suite wall-clock time drops by at least 50 s against the baseline. Evidence: back-to-back `--durations=15` runs at `cdb2003f` and HEAD in `VALIDATION.md` (prototype: 216.6 s → 152.0 s).
- [x] `grep -rn "ADW_TEST_" src tests` returns nothing.
- [x] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Kill the hook's process group on timeout
- [x] TASK-002: Patch retry backoff and drop wall-clock transition tests
- [x] TASK-003: Isolate HOME per test and drop the ADW_TEST_* path hooks
- [x] TASK-004: Run cli and dashboard unit tests in a temp cwd
- [x] TASK-005: Final Validation
