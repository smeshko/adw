# TASK-005: Delete dead model symbols and schema examples

Depends on: TASK-004
Suggested commit: `refactor(models): delete unused context, artifact and config helpers`

## Goal

The unused model classes and methods, and the `json_schema_extra` example blocks, are gone from `src/adw/models`. Tests that used `from_yaml` or `is_success` only as a shortcut now go through the surviving API.

## Files

- `src/adw/models/context.py`: delete `class SessionContext`, `class ProjectContext`, `RunContext.resolve_artifact_path` and `RunContext.get_runs_dir`.
- `src/adw/models/phase.py`: delete `class ArtifactType` and `class Artifact`, and the `Enum` import if nothing else uses it.
- `src/adw/models/config.py`:
  - Delete `ProjectConfig.from_yaml` and `ProjectConfig.from_yaml_file`.
  - Rewrite the class-docstring example at L509 to `ProjectConfig.model_validate(yaml.safe_load(...))`.
  - `ruff --fix` drops the now-unused `yaml` and `Path` imports.
- `src/adw/models/hook.py`: delete `HookResult.is_success` and the `result.is_success` docstring example line.
- `json_schema_extra` example blocks: delete all 10.
  - Files: `models/phase.py`, `index.py`, `registry.py` (2), `worktree.py`, `logging.py` (2), `config.py`, `hook.py`, `context.py`.
  - Where the block was the only key in `model_config`, delete `model_config` as well.
  - Where `model_config` has other keys, such as `frozen` or `extra`, keep those.
- `src/adw/models/__init__.py`: drop `SessionContext`, `ProjectContext`, `Artifact` and `ArtifactType` from the imports, `__all__`, and the module docstring.
- Tests:
  - `tests/unit/models/test_context.py`: delete `TestSessionContext`, `TestProjectContext` and `TestRunContextArtifactPathResolution`.
  - `tests/unit/commands/test_template.py`: delete `TestContextObjectRendering::test_session_context_as_context`.
  - `tests/unit/models/test_config.py`:
    - Add a module helper `_from_yaml(text: str) -> ProjectConfig` that returns `ProjectConfig.model_validate(yaml.safe_load(text))`.
    - Point the 7 `TestProjectConfig` tests that call `ProjectConfig.from_yaml` at it. These are `test_from_yaml_*`, `test_empty_yaml_fails` and `test_with_git_config`.
    - Rename the `test_from_yaml_*` tests to `test_yaml_*`.
    - They keep asserting the same required-field validation.
  - `tests/unit/models/test_config_task_manager.py::test_project_config_yaml_with_task_manager` and `tests/unit/webhook/test_server.py::TestWebhookConfigInYAML` (2 tests): switch to `ProjectConfig.model_validate(yaml.safe_load(...))`.
  - `tests/conftest.py:209`: rewrite the fixture docstring example the same way.
  - `tests/unit/hooks/test_hook_result.py`: delete `test_is_success_property`.
  - `result.is_success` becomes `result.exit_code == 0`, and `not result.is_success` becomes `result.exit_code != 0`, in `tests/unit/hooks/test_runner.py` (4 tests) and `tests/integration/test_hooks.py` (6 tests).

## Acceptance

- [ ] `grep -rnE "SessionContext|ProjectContext|resolve_artifact_path|ArtifactType|from_yaml_file|\.from_yaml\(|is_success|json_schema_extra" src tests` returns nothing.
- [ ] `grep -rn "def get_runs_dir" src/adw/models` returns nothing. `cli/bootstrap.get_runs_dir` is unrelated and stays.
- [ ] `grep -rnE "\bArtifact\b" src/adw/models` finds no class definition or re-export named `Artifact`.
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/models tests/unit/commands/test_template.py tests/unit/hooks tests/unit/webhook tests/integration/test_hooks.py -o addopts=""` passes.
- [ ] The `vulture` diff against this task's start shows no new entry, or each new entry is handled per the cascade rule.

Evidence: the empty greps and the pytest summary line.

## Steps

### RED
- [ ] Save the `vulture` baseline.
- [ ] Rewrite the `from_yaml` and `is_success` call sites in the tests onto the surviving API first. They pass at HEAD, which shows the rewrite keeps the behaviour under test.

### GREEN
- [ ] Delete the model classes and methods, and the re-exports.
- [ ] Delete the 10 `json_schema_extra` blocks.
- [ ] Delete the tests listed under Files.
- [ ] Run the targeted pytest command.

### REFACTOR
- [ ] Run `uv run ruff check src/ --fix` and `uv run ruff format src/`.
- [ ] Take the `vulture` diff and apply the cascade rule.
- [ ] Run `scripts/preflight.sh`.

## Notes

- Nothing reads the examples: no test or `src` code calls `model_json_schema()` on these models. The one assertion on an example (`ValidationResult`) left with TASK-001.
- `models/phase.py` keeps `PhaseStatus` and `PhaseResult`. Only `Artifact` and `ArtifactType` go.
