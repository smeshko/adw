# TASK-004: Define the default state mapping once

Depends on: None
Suggested commit: `fix(task-managers): define the default state mapping once`

## Goal

One `DEFAULT_STATE_MAPPING` (plan, build, validate, document, ship, failed) backs `TaskManagerConfig` and every consumer, so a wizard-configured mapping includes `ship` (B17).

## Files

- `src/adw/models/config.py`:
  - Add a module-level `DEFAULT_STATE_MAPPING: dict[str, str]` above `TaskManagerConfig`, with the 6 current keys.
  - `TaskManagerConfig.state_mapping` uses `default_factory=lambda: dict(DEFAULT_STATE_MAPPING)`.
- `src/adw/cli/wizard/task_manager.py`: delete `DEFAULT_STATE_MAPPINGS` and its "must match" comment. `_prompt_state_mapping` iterates `DEFAULT_STATE_MAPPING.items()`, imported from `adw.models.config`.
- `src/adw/task_managers/sync.py`: delete the local `DEFAULT_STATE_MAPPING`, and import it from `adw.models.config` for the empty-mapping fallback.
- `src/adw/task_managers/__init__.py`: remove `DEFAULT_STATE_MAPPING` from the import and from `__all__`.
- `src/adw/config/yaml_generator.py`: delete `_DEFAULT_STATE_MAPPING`, and use the imported `DEFAULT_STATE_MAPPING` in the comparison and in both commented blocks.
- `src/adw/dashboard/partials.py:~1173` and `src/adw/dashboard/routes.py:~2019`: the literal dicts become `dict(DEFAULT_STATE_MAPPING)`.
- `tests/unit/cli/wizard/test_task_manager.py`:
  - `test_state_mapping_accepts_defaults` feeds 6 `Prompt.ask` values (add `ship`) and compares against `DEFAULT_STATE_MAPPING`.
  - Delete `TestConstants::test_default_state_mappings_covers_all_phases`, which asserts that `ship` is missing.
  - Add `test_accepted_defaults_yield_ship_mapping`.
- `tests/unit/task_managers/test_sync.py`: delete `TestPhaseStatusMapping`'s five `test_default_mapping_*` constant tests (ADR-001), and update the import.

## Acceptance

- [ ] `test_accepted_defaults_yield_ship_mapping`:
  - Setup: patch `Confirm.ask` → `True` and `Prompt.ask` to return each prompt's `default`, then run `_prompt_state_mapping`.
  - Put the result in a `WizardState` `task_manager` step, `{"enabled": True, "type": "linear", "state_mapping": result}`, with basics `{"project_name": "p", "language": "python"}`.
  - Generate with `YAMLWithComments` and load with `yaml.safe_load` into `ProjectConfig`. `config.task_manager.state_mapping["ship"] == "Done"`.
- [ ] `grep -rn '"In Review"' src/adw --include='*.py'` lists only `models/config.py` (the constant, plus its docstring example).
- [ ] `grep -rn "DEFAULT_STATE_MAPPINGS\|_DEFAULT_STATE_MAPPING" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/cli/wizard tests/unit/task_managers tests/unit/config tests/unit/dashboard tests/dashboard -o addopts=""` passes.

Evidence:
- the RED run: the new test fails because the loaded mapping has no `ship` key
- the GREEN run
- the two grep outputs

## Steps

### RED
- [ ] Add `test_accepted_defaults_yield_ship_mapping`. Use `side_effect=lambda *a, **kw: kw["default"]` for `Prompt.ask`, so the test is independent of the number of prompts.
- [ ] Run it and confirm that it fails with a `KeyError` or an assertion on `"ship"`.

### GREEN
- [ ] Add `DEFAULT_STATE_MAPPING` to `models/config.py` and use it in `TaskManagerConfig`.
- [ ] Point the wizard at it, and delete `DEFAULT_STATE_MAPPINGS`.
- [ ] Run the new test and confirm it is green.

### REFACTOR
- [ ] Replace the copies in `sync.py`, `yaml_generator.py`, `partials.py` and `routes.py`, and drop the `task_managers/__init__.py` re-export.
- [ ] Update `test_state_mapping_accepts_defaults`, and delete the constant-value tests named under Files.
- [ ] Run the two greps.
- [ ] `scripts/preflight.sh` passes.

## Notes

- `dashboard/partials.py` and `routes.py` mutate their context dict, so they must take `dict(DEFAULT_STATE_MAPPING)`, never the constant itself.
- `yaml_generator` compares the user's mapping with `!=`. With `ship` in both, accepting all defaults again writes the commented block, and the loaded config gets `TaskManagerConfig`'s default, which includes `ship`. The new test covers either rendering, because it asserts on the loaded config and not on the YAML text.
