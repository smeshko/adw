# TASK-002: Pass build_command from ProjectConfig to the ship hook

Depends on: None
Suggested commit: `fix(ship): take build_command from the loaded project config`

## Goal

The ship post-hook gets `ADW_SHIP_BUILD_CMD` from `ProjectConfig.build_command`, whether or not the project overrides the ship phase config (B3).

## Files

- `src/adw/core/extensions/ship.py`:
  - `ShipExtension.__init__(self, project_root: Path | None = None, build_command: str | None = None)` stores `self._build_command`.
  - `get_hook_env` builds `env` from the ship config when there is one, then sets `ADW_SHIP_BUILD_CMD` from `self._build_command` whether or not the ship config loaded.
  - Delete `_load_project_build_command`. Drop `import yaml` only if `_load_ship_config` no longer needs it; it does, so keep it.
  - Update the class docstring and the `get_hook_env` docstring.
- `src/adw/core/extensions/__init__.py`: `create_default_registry(git_config, runs_dir, project_root=None, build_command=None)` passes `build_command` to `ShipExtension`. Update the docstring's Args.
- `src/adw/cli/bootstrap.py:288`: `create_default_registry(git_config, runs_dir, project_root=project_root, build_command=config.build_command if config else None)`.
- `tests/unit/ship/test_ship_phase_fixes.py` (`TestShipCommandEnvVars`):
  - Every `patch.object(ext, "_load_project_build_command", …)` goes.
  - `test_build_cmd_in_env` builds `ShipExtension(build_command="npm run build")`.
  - The rest build `ShipExtension()`.
  - Add `test_build_cmd_in_env_without_ship_config`.
- `tests/unit/cli/test_bootstrap.py`: add `test_ship_hook_env_carries_project_build_command`.

## Acceptance

- [ ] `test_build_cmd_in_env_without_ship_config`: `ShipExtension(project_root=tmp_path, build_command="echo built")`, with no `.adw/commands/ship/config.yaml`, returns `{"ADW_SHIP_BUILD_CMD": "echo built"}` from `get_hook_env`.
- [ ] `test_ship_hook_env_carries_project_build_command`:
  - Setup: in `tmp_path` (already cwd through the cli conftest), write `.adw/project.yaml` with `name: demo` and `build_command: "echo built"`, then call `create_orchestrator()`.
  - The extension registry the orchestrator's `PhaseRunner` holds (`.extension_registry`) returns `ADW_SHIP_BUILD_CMD == "echo built"` from `get_hook_env("ship", context)`.
- [ ] `grep -rn "_load_project_build_command" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/ship tests/unit/cli/test_bootstrap.py tests/unit/core/test_orchestrator.py -o addopts=""` passes.

Evidence:
- the RED run: the two new tests fail on today's code, where the path is wrong and the early return skips the build command
- the GREEN run
- the empty grep

## Steps

### RED
- [ ] Add `test_build_cmd_in_env_without_ship_config` to `TestShipCommandEnvVars`. It passes `build_command` as a constructor kwarg, so on today's code it fails with `TypeError`.
- [ ] Add `test_ship_hook_env_carries_project_build_command` to `tests/unit/cli/test_bootstrap.py`:
  - Build a minimal `RunContext` with its required fields: `run_id`, `feature_description`, `current_phase="ship"` and `started_at`.
  - Reach the registry through `orchestrator._phase_runner.extension_registry`. If a public accessor exists, use it instead.
  - On today's code the env lacks the key.
- [ ] Run both and confirm they fail.

### GREEN
- [ ] Add the `build_command` parameter to `ShipExtension` and `create_default_registry`, and pass it from bootstrap.
- [ ] Move the build-command export above the `config is None` return in `get_hook_env`.
- [ ] Delete `_load_project_build_command`, and update the existing `TestShipCommandEnvVars` tests to the constructor argument.
- [ ] Run the new and updated tests and confirm they are green.

### REFACTOR
- [ ] Update the docstrings: `ShipExtension` "Dependencies" and `get_hook_env`.
- [ ] `scripts/preflight.sh` passes.

## Notes

- `get_config_class` stays imported from `commands/loader.py`. Phase 1.2 moves it.
- `tests/unit/core/test_orchestrator.py:2337` builds `ShipExtension()` with no arguments, and it must keep working. That's why both new parameters default to `None`.
