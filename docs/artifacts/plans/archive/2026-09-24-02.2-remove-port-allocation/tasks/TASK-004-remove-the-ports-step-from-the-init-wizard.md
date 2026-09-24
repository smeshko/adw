# TASK-004: Remove the ports step from the init wizard

Depends on: None
Suggested commit: `refactor(cli): remove the ports step from the init wizard`

## Goal

`adw init --wizard` asks no port questions, and the `project.yaml` it writes has no `port_range`.

## Files

- `src/adw/cli/wizard/ports.py`: delete with `git rm`.
- `src/adw/cli/wizard/flow.py`: drop `PORTS = "ports"` from `WizardStep` (`:44`), `WizardStep.PORTS` from `STEP_SEQUENCE` (`:72`), and its `STEP_TITLES` entry (`:86`).
- `src/adw/cli/init.py` (`_run_wizard_setup`): drop `PortsStepHandler` from the import (`:162`) and its `register_step_handler` line (`:189`).
- `src/adw/cli/wizard/__init__.py`: drop the two docstring lines (`:18-19`), the `from adw.cli.wizard.ports import (...)` block (`:68-74`), and `"PortsStepHandler"`, `"check_port_overlap"`, `"is_common_port"`, `"run_ports_step"` and `"validate_port"` from `__all__`.
- `src/adw/cli/wizard/summary.py` (`generate_summary_panel`): drop `ports = state.get_step_config("ports")` (`:177`) and the `# Ports section` block (`:206-213`).
- `src/adw/config/yaml_generator.py` (`generate_project_yaml`):
  - drop `ports = state.get_step_config("ports")` (`:124`)
  - replace the `# === Worktree & Ports ===` block (`:178-200`) with a `# === Worktree ===` header and the always-commented `# worktree:` block, which has `enabled`, `base_dir` and `max_concurrent` and no `port_range` lines
- `tests/unit/cli/wizard/test_ports.py`: delete with `git rm`.
- `tests/unit/cli/wizard/test_flow.py`:
  - `test_run_marks_steps_completed` (`:211`): `assert "ports" in …` becomes `assert "ports" not in controller.state.completed_steps`. This is the behavioural check that a full controller run never visits a ports step.
  - `test_step_values_exist` (`:18-34`): delete it. It checks the full `WizardStep` member list, an enum-existence test that ADR-001 lists as waste, and the controller-run assert above covers the behaviour.
  - `test_step_sequence_defined` (`:62`): delete the `assert len(WizardFlowController.STEP_SEQUENCE) == 10` line. ADR-001 lists enum-count asserts as waste, and every removed step breaks it. Keep the first, second and last-step asserts.
- `tests/unit/cli/wizard/test_summary.py`:
  - drop every `"ports": {...}` fixture entry
  - drop the `"Ports:"` assert in `test_summary_panel_shows_all_sections` (`:107`)
  - delete `test_generate_project_yaml_custom_ports` (`:294`) and `test_generate_project_yaml_omits_default_ports` (`:314`)
- `tests/unit/config/test_yaml_generator.py`:
  - drop `"ports": {}` from `MockWizardState` (`:26`)
  - `test_generate_project_yaml_has_all_sections` (`:119`): the `# === Worktree & Ports ===` assert becomes `# === Worktree ===`
  - `test_generate_project_yaml_commented_settings_are_valid_yaml` (`:124`): after parsing the uncommented YAML, assert `set(parsed["worktree"]) == {"enabled", "base_dir", "max_concurrent"}`. This checks behaviour, not strings: the worktree block a user uncomments has no port settings.
  - delete `test_generate_project_yaml_custom_ports` (`:156`)

## Acceptance

- [ ] A full `WizardFlowController.run()` completes without visiting a `ports` step.
- [ ] The generated `project.yaml` has a `# === Worktree ===` section, and its uncommented `worktree:` block has exactly `enabled`, `base_dir` and `max_concurrent`.
- [ ] `grep -rn "PortsStepHandler\|run_ports_step\|WizardStep.PORTS\|backend_port_start\|Worktree & Ports" src tests` returns nothing, and `grep -rn "port_range" tests/unit/cli tests/unit/config` returns nothing. New asserts must not add port literals, which would break the plan's acceptance grep.
- [ ] `uv run pytest tests/unit/cli tests/unit/config -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failures of `test_run_marks_steps_completed`, `test_generate_project_yaml_has_all_sections` and `test_generate_project_yaml_commented_settings_are_valid_yaml`, then the GREEN pytest tail, the greps and the preflight tail.

## Steps

### RED
- [ ] Flip the `test_run_marks_steps_completed` assert to `"ports" not in controller.state.completed_steps`.
- [ ] Change the `test_generate_project_yaml_has_all_sections` header assert to `"# === Worktree ===" in yaml_content`.
- [ ] Add the `set(parsed["worktree"]) == {"enabled", "base_dir", "max_concurrent"}` assert to `test_generate_project_yaml_commented_settings_are_valid_yaml`.
- [ ] Run both test files: all three tests fail.

### GREEN
- [ ] `git rm src/adw/cli/wizard/ports.py tests/unit/cli/wizard/test_ports.py`.
- [ ] Edit `flow.py`, `init.py`, `wizard/__init__.py`, `summary.py` and `yaml_generator.py` as listed.
- [ ] Delete `test_step_values_exist`, trim `test_step_sequence_defined` as listed, and delete the port tests and fixture entries in `test_summary.py` and `test_yaml_generator.py`.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- `test_generate_project_yaml_commented_settings_are_valid_yaml` uncomments every `# key: value` line and parses the result. The new worktree block must stay valid YAML once uncommented, so keep its two-space nesting under `# worktree:`.
- `tests/unit/cli/wizard/test_state.py` uses `"ports"` as an arbitrary step name for `WizardState` navigation. It stays as it is (see PLAN.md, Out of Scope).
- Deleting `test_step_values_exist` and the count assert means phases 2.1 and 2.3 hit a conflict in `test_flow.py` when they rebase. Resolve it by keeping the deletion.
- `test_init.py` only cancels the wizard with `c\n` at the first prompt, so removing a step doesn't shift its input.
