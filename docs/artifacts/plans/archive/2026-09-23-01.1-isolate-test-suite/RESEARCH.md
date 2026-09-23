# Research: Isolate the test suite from the checkout

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

- `src/adw/hooks/runner.py`:
  - `HookRunner._execute_hook` starts the hook with `asyncio.create_subprocess_exec(shell, hook_path, …)` and no `start_new_session`.
  - On `TimeoutError` it calls `process.kill()` and then `await process.wait()`.
  - `wait()` only resolves once every pipe closes, so a grandchild (`sleep`) that holds stdout blocks it for the child's full lifetime (B9).
- `src/adw/executors/claude_code.py`:
  - The reference pattern is `start_new_session=True` (around line 187) plus `_kill_process_group(pid)`, which calls `os.killpg(pid, SIGKILL)` and tolerates `ProcessLookupError`/`PermissionError` (around line 616).
- `src/adw/core/index_manager.py`, `core/project_registry.py`, `core/stats_aggregator.py`:
  - Each `__init__` reads `ADW_TEST_INDEX_PATH`, `ADW_TEST_REGISTRY_PATH` or `ADW_TEST_STATS_CACHE_PATH`, and falls back to `Path.home() / ".adw" / …`.
  - `index_manager` and `project_registry` import `os` locally inside `__init__`; `stats_aggregator` imports it at module level, and the env lookup is its only use.
  - The class docstrings document the env vars.
- `src/adw/commands/resolver.py` (lines 62 and 165): the user-level command lookup at `Path.home() / ".adw" / "commands"` is not isolated today.
- `tests/conftest.py`:
  - Sets `ADW_MOCK_EXECUTOR=1` and dummy Linear credentials at import.
  - Its autouse `isolated_global_index` sets only `ADW_TEST_INDEX_PATH`.
  - `git_repo` yields `tmp_path` itself and sets its identity with a local `git config`.
- `src/adw/core/orchestrator.py`:
  - `_execute_phase_with_retry` sleeps `2**attempt` through the module-level `time.sleep` (line 1106).
  - `_execute_phase_with_transitions` logs "Transition exceeded 1s" at debug level (line 1033).
- `src/adw/cli/resume.py`: `adw resume` with no run id resumes the most recent incomplete run in cwd's `.adw/runs`. That is why `TestFromPhaseValidation`, which runs `adw resume --from-phase` once for each of the 5 phases, is dangerous in the checkout.

## Tests That Change

| File | Change |
|---|---|
| `tests/unit/hooks/test_runner.py` | new `test_timeout_kills_hook_children` |
| `tests/fixtures/hooks/slow.sh` | `sleep 30` → `exec sleep 30` |
| `tests/unit/core/test_orchestrator.py` | `TestRetryLogic` autouse sleep patch; delete `test_transition_under_1_second`, `test_slow_transition_logs_debug` |
| `tests/conftest.py` | `isolated_global_index` → `isolated_home` |
| `tests/unit/core/test_index_manager.py` | delete `test_custom_path_takes_precedence_over_env_var`, `test_env_var_overrides_default`; drop `delenv` in `test_default_index_path_uses_home_directory` |
| `tests/unit/core/test_project_registry.py` | same two deletions plus the `delenv` drop in `test_default_registry_path_uses_home_directory` |
| `tests/unit/core/test_stats_aggregator.py` | delete `test_env_var_cache_path`, `test_explicit_path_overrides_env`; `test_default_cache_path` loses its `patch.dict(os.environ, {}, clear=True)` |
| `tests/integration/cli/test_dashboard_integration.py` | `temp_index` / `temp_stats` stop setting env vars and use the default paths under the isolated home |
| `tests/integration/cli/test_global_commands_integration.py` | `temp_index` likewise |
| `tests/integration/cli/test_projects_integration.py` | `temp_registry` yields `Path.home() / ".adw" / "projects.yaml"` without `patch.dict` (10 users) |
| `tests/integration/cli/test_feature_description.py` | `isolated_global_index` → `isolated_home / ".adw" / "index.jsonl"` (lines 166 and 188) |
| `tests/unit/test_isolation.py` | new guard test |
| `tests/unit/cli/conftest.py`, `tests/unit/dashboard/conftest.py` | new autouse `isolated_cwd` |

## Baseline and Prototype Measurements (2026-09-23)

Method: `git clone --local` into a scratch dir, with the `origin` remote removed. The clone gets:

- `.adw/project.yaml` and all 44 runs copied from the main checkout
- `HOME=$S/home` (`$S` = a scratch dir) and `GIT_AUTHOR_*`/`GIT_COMMITTER_*` set
- a full suite run through `.venv/bin/python -m pytest --durations=N -p no:cacheprovider -q`

| | Baseline `cdb2003f` | Prototype (all four tasks) |
|---|---|---|
| pytest time | 216.58 s | 152.01 s (−64.6 s) |
| wall (incl. startup) | 220 s | 154 s |
| result | 1 failed, 4296 passed | 1 failed, 4295 passed |
| coverage | 84% | 84% |
| snapshot diff | `+ ~/.adw/stats-cache.json` written to HOME | empty |

The single failure in both runs is `test_stats_aggregator.py::TestStatsAggregatorInit::test_default_cache_path`. It passes only when `HOME` is the passwd home, because `clear=True` removes `HOME`, and TASK-003 removes the `clear=True`.

Top baseline durations that this phase removes:

```
30.05s  tests/integration/test_hooks.py::TestHookIntegration::test_timeout_with_slow_script
15.62s  tests/unit/core/test_orchestrator.py::TestRetryLogic::test_retry_with_custom_max_retries
10.13s  tests/unit/hooks/test_runner.py::TestHookRunner::test_timeout_raises_hook_error
 3.28s  …TestRetryLogic::test_spinner_stopped_before_error_logging
 3.24s  …TestRetryLogic::test_retry_exhaustion_raises_error
 3.19s  …TestRetryLogic::test_recoverable_error_triggers_retry
 1.14s  …TestRetryLogic::test_retry_success_after_failures
 1.11s  …TestTransitionPerformance::test_slow_transition_logs_debug
```

After the change, the slowest test is 1.18 s (a git-hook integration test), and the three hook timeout tests take about 1.1 s each.

Regression test RED: `test_timeout_kills_hook_children` on the unmodified runner fails `assert elapsed < 3` at 30.1 s. GREEN: passes in 1.09 s with `start_new_session=True` plus `os.killpg`.

Pollution check: with 44 seeded runs, `tests/unit/cli/test_resume.py` against the baseline left the run hashes, branches and worktrees unchanged. `TestFromPhaseValidation` did not actually resume anything with this data, so TASK-004 is a guard against a latent hazard, not a fix for an observed leak.

## Architecture Facts

- `Path.home()` reads `HOME` first. It falls back to the passwd entry only when `HOME` is unset, so `monkeypatch.setenv("HOME", …)` isolates every `Path.home()` caller and every subprocess that inherits the env.
- With `HOME` redirected, git loses the user's global config (identity, `commit.template`, excludes). The `GIT_*` identity env vars cover commits. Nothing in the suite relies on the other keys: CI runs with an empty home.
- asyncio: `Process.wait()` resolves in `_call_connection_lost`, which runs only after the process exits *and* every pipe disconnects. That is why `kill()` on the shell alone doesn't unblock it.

## Constraints

- AGENTS.md: a test that touches git, runs `adw run` or executes a phase hook runs in `git_repo` or `tmp_path` via `monkeypatch.chdir`. This phase generalises that for `tests/unit/cli` and `tests/unit/dashboard`.
- ADR-001: no trivial attribute tests. The new guard test is justified because it checks isolation, a safety property, not a default value.
- Partial runs: `uv run pytest tests/unit/cli -o addopts=""` (any path).

## Useful Commands

```bash
# Throwaway clone with fake HOME and seeded runs (repeat per commit under test)
S=$(mktemp -d); MAIN=$(git worktree list | head -1 | cut -d" " -f1)
git clone -q --local . $S/c && git -C $S/c remote remove origin && git -C $S/c checkout -q ${REF:-HEAD}  # REF=cdb2003f for the baseline
mkdir -p $S/c/.adw && cp -R $MAIN/.adw/{project.yaml,runs} $S/c/.adw/
(cd $S/c && uv sync -q && HOME=$S/h GIT_AUTHOR_NAME=T GIT_AUTHOR_EMAIL=t@t \
  GIT_COMMITTER_NAME=T GIT_COMMITTER_EMAIL=t@t \
  .venv/bin/python -m pytest --durations=15 -p no:cacheprovider -q)

# Snapshot (run before and after, then diff)
{ git status --short; git branch; git worktree list; ls .adw/runs | wc -l;
  find .adw/runs -type f | sort | xargs shasum | shasum; shasum ~/.adw/*; } > snap.txt
```

## Uncertainty

- Whether any test relied on the user's real `~/.adw` contents: resolved. The prototype's full suite passed with an empty per-test home, apart from the `clear=True` test.
- CI zombie reaping for the regression test's "child gone" check: mitigated by polling up to 2 s.

## References

- Epic 01, phase 1.1: `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`
- Commits `9ab939bd` (per-module chdir for `test_run.py`/`test_ship_post_hook.py`) and `cdb2003f` (registry mocking for the overview tests)
- `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`
