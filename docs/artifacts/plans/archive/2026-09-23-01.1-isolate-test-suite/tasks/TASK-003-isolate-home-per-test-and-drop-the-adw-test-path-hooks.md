# TASK-003: Isolate HOME per test and drop the ADW_TEST_* path hooks

Depends on: None
Suggested commit: `test: isolate HOME per test and drop the ADW_TEST_* path hooks`

## Goal

Every test runs with `HOME` set to its own temp dir, so nothing reads or writes the real `~/.adw`. The three test-only env-var branches leave production code.

## Files

- `tests/conftest.py`:
  - Replace the autouse `isolated_global_index` with an autouse `isolated_home(tmp_path, monkeypatch) -> Path` that:
    - creates `tmp_path / "home"`
    - sets `HOME` to it
    - sets `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME` and `GIT_COMMITTER_EMAIL`
    - returns the home dir
  - Update the module docstring's fixture list.
- `src/adw/core/index_manager.py`, `src/adw/core/project_registry.py`, `src/adw/core/stats_aggregator.py`:
  - Delete the `ADW_TEST_*` lookup, the `elif` branch and the now-unused `import os`: local in the first two, module-level in `stats_aggregator.py`.
  - Delete the env-var lines from the class and `__init__` docstrings.
- `tests/unit/core/test_index_manager.py`:
  - Delete `test_custom_path_takes_precedence_over_env_var` and `test_env_var_overrides_default`.
  - Drop the `delenv` from `test_default_index_path_uses_home_directory`.
- `tests/unit/core/test_project_registry.py`: the same two deletions, and the same `delenv` drop in `test_default_registry_path_uses_home_directory`.
- `tests/unit/core/test_stats_aggregator.py`:
  - Delete `test_env_var_cache_path` and `test_explicit_path_overrides_env`.
  - `test_default_cache_path` loses its `patch.dict(os.environ, {}, clear=True)` block.
- `tests/integration/cli/test_dashboard_integration.py`: `temp_index` returns `IndexManager()` and `temp_stats` returns `StatsAggregator()`, neither setting env vars.
- `tests/integration/cli/test_global_commands_integration.py`: `temp_index` returns `IndexManager()`, with no env var.
- `tests/integration/cli/test_projects_integration.py`: `temp_registry` returns `Path.home() / ".adw" / "projects.yaml"`, without `patch.dict`.
- `tests/integration/cli/test_feature_description.py`: the two tests that take `isolated_global_index` take `isolated_home` and use `isolated_home / ".adw" / "index.jsonl"`.
- `tests/unit/test_isolation.py` (new): the guard test.
- `AGENTS.md`, `## Code standards` test bullets: add one line saying the root autouse `isolated_home` fixture points `HOME` at a per-test dir, so tests reach `~/.adw` only through `Path.home()`.

## Acceptance

- [ ] `tests/unit/test_isolation.py::test_home_is_isolated` passes. It asserts:
  - `Path.home()` lies under the test's `tmp_path`
  - the default paths of `IndexManager()`, `ProjectRegistryManager()` and `StatsAggregator()` all lie under `Path.home() / ".adw"`
- [ ] `grep -rn "ADW_TEST_" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/core tests/integration/cli tests/unit/test_isolation.py -o addopts=""` passes, including `test_default_cache_path`.
- [ ] A full `uv run pytest` in the checkout leaves `shasum ~/.adw/*` unchanged. The baseline leaked `stats-cache.json`.

Evidence:
- the guard test RED/GREEN output
- the grep output (empty)
- a `shasum ~/.adw/*` diff around a full run (empty)

## Steps

### RED
- [ ] Write `tests/unit/test_isolation.py::test_home_is_isolated(tmp_path)`. It fails today: `StatsAggregator().cache_path` and `ProjectRegistryManager().registry_path` resolve to the real home, because only the index is isolated.

### GREEN
- [ ] Replace the root fixture with `isolated_home`, and update `test_feature_description.py` to use it.
- [ ] Delete the env branches from the three core modules.
- [ ] Update or delete the env-var tests and the integration fixtures listed under Files.
- [ ] Run the partial suite from Acceptance, then the full suite.

### REFACTOR
- [ ] Add the AGENTS.md line.
- [ ] `scripts/preflight.sh` passes, which includes mypy `--strict` on the edited `src` modules.

## Notes

- Use `tmp_path / "home"`, not `tmp_path`: TASK-004 makes cwd `tmp_path`, and the project `.adw/` must not collide with `~/.adw`.
- Never wrap a test in `patch.dict(os.environ, {}, clear=True)`: with `HOME` gone, `Path.home()` falls back to the passwd entry, which is the real home. That is exactly how `test_default_cache_path` escaped isolation in the prototype.
- `IndexManager()` inside `StatsAggregator()` also resolves under the isolated home, so the dashboard integration fixtures need no explicit paths.
