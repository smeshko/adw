# TASK-004: Replace the flow controller and WizardState with run_wizard

Depends on: TASK-001, TASK-002, TASK-003
Suggested commit: `refactor(wizard): replace the flow controller with run_wizard`

## Goal

One `run_wizard(root)` calls each step function in order and hands a plain dict to the summary and the YAML generator. The flow controller, step enum, state model, handler classes and navigation helpers are gone. The wizard's output and exit codes stay as they are; TASK-005 changes them.

## Files

- `src/adw/cli/wizard/flow.py`: replace the module body with `run_wizard(root: Path) -> bool`:
  - builds a `Console()`, prints the welcome panel (unchanged text in this task), then walks a local list of `(section, title, step)` tuples in today's order — basics, global_registry, git, task_manager, phases, webhooks — printing the same `Step N/M: <title>` header, and stores each step's dict as `cfg[section]`. The list is typed `list[tuple[str, str, Callable[[Console], dict[str, Any]]]]`; basics joins it as `lambda c: run_basics_step(c, root)`, the other steps as the bare functions, and each is called as `step(console)`.
  - the summary is the last numbered step ("Configuration Summary"); `run_wizard` calls `run_summary_step(cfg, console, root)`, then prints today's completion panel and returns `True`
  - no SIGINT handler of its own: `init._setup_interrupt_handler` already covers the whole command
  - delete `StepHandler`, `WizardStep`, `WizardFlowController`, `STEP_SEQUENCE`, `STEP_TITLES` and `_show_step_placeholder`
- `src/adw/models/wizard.py`: delete with `git rm`. Drop its import, the `wizard: WizardState` docstring line and `"WizardState"` from `__all__` in `models/__init__.py`.
- `src/adw/cli/wizard/navigation.py`: delete with `git rm`. In `phases._prompt_input_files`, `nav_confirm_ask(...)` becomes `Confirm.ask("Add input files?", default=False, console=console)`.
- Step modules — delete each `*StepHandler` class and the `TYPE_CHECKING` import of `WizardState`, and drop the `state` parameter and its docstring line:
  - `basics.py`: `run_basics_step(console, root)`, with `root: Path` required
  - `git.py`: `run_git_step(console)`
  - `global_registry.py`: `run_global_registry_step(console)`
  - `task_manager.py`: `run_task_manager_step(console)`
  - `phases.py`: `run_phases_step(console)`
  - `webhooks.py`: `run_webhooks_step(console)`
- `src/adw/cli/wizard/summary.py`:
  - delete `SummaryStepHandler`
  - `run_summary_step(cfg, console, root)`, `generate_summary_panel(cfg)`, `generate_project_yaml(cfg)`, `generate_phase_configs(cfg)`, `_generate_all_files(cfg)` take `cfg: Mapping[str, dict[str, Any]]` and read sections with `cfg.get(section, {})`
  - drop the `Ship:` block of the summary panel: no step fills a `ship` section (RESEARCH.md, "Dead summary lines"); customised phases, ship included, already show on the `Phases:` line
  - behaviour otherwise unchanged in this task (the start-over prompt and the return dict stay)
- `src/adw/config/yaml_generator.py`:
  - `YAMLWithComments.generate_project_yaml(cfg)` and `generate_all_phase_configs(cfg, registry)` take `cfg: Mapping[str, dict[str, Any]]`; replace `state.get_step_config(x)` with `cfg.get(x, {})`
  - delete the dead `ship` merge in `generate_all_phase_configs` and its docstring paragraph
  - drop the `WizardState` `TYPE_CHECKING` import
- `src/adw/config/initializer.py` (`_write_config`): pass `{"basics": {"project_name": …, **config}}` to `generate_project_yaml`; drop the `WizardState` import.
- `src/adw/cli/init.py` (`_run_wizard_setup`): call `run_wizard(project_root)` from `adw.cli.wizard`; drop the handler imports and registrations.
- `src/adw/cli/wizard/__init__.py`: a two-line docstring, `from adw.cli.wizard.flow import run_wizard` and `__all__ = ["run_wizard"]`.
- Tests:
  - `git rm tests/unit/cli/wizard/test_navigation.py tests/unit/cli/wizard/test_state.py`
  - `test_flow.py`: rewrite. Keep one test, `test_run_wizard_calls_steps_in_order_and_hands_cfg_to_summary`: patch each `run_*_step` in `adw.cli.wizard.flow` to return a marker dict and record its call, and patch `run_summary_step` to capture `cfg`. Assert the call order and `cfg == {"basics": …, "global_registry": …, "git": …, "task_manager": …, "phases": …, "webhooks": …}`.
  - `test_basics.py`, `test_git.py`, `test_global_registry.py`, `test_task_manager.py`, `test_phases.py`, `test_webhooks.py`: drop the `WizardState` import and every `state = WizardState()`; call the step functions without `state`; delete the `Test*StepHandler` and `TestPackageExports` classes (forwarders and import-smoke per ADR-001) and the state-storage tests `test_config_stored_via_flow_controller_pattern` (`test_basics.py`, `test_task_manager.py`) and `test_config_can_be_stored_in_state` (`test_phases.py`, `test_webhooks.py`). Keep the behaviour tests that live in the same `TestStateIntegration` classes: `test_basics.py::test_full_flow_returns_complete_config`, and `test_task_manager.py::test_accepted_defaults_yield_ship_mapping`, the only B17 regression test, which moves from `WizardState` to `cfg = {"basics": {…}, "task_manager": {…}}`. Import from the submodules, not `adw.cli.wizard`.
  - `test_phases.py`: every `patch("adw.cli.wizard.phases.nav_confirm_ask", …)` folds into the test's `Confirm.ask` patch, with the input-files answer placed in call order (it follows "Enabled?")
  - `test_summary.py`: fixtures become plain dicts; delete `TestSummaryStepHandler` and the `Ship:` asserts. Add `test_customized_ship_commands_reach_ship_config`: `cfg = {"phases": {"customized": True, "phases": {"ship": {"enabled": True, "commands": {"version_bump": "npm version patch", "publish": "npm publish"}}}}}`; the parsed `commands/ship/config.yaml` from `generate_phase_configs(cfg)` has both commands. It guards the removal of the dead `ship` merge; nothing tests that path today.
  - `test_yaml_generator.py`: `MockWizardState` becomes a `_cfg(**overrides) -> dict[str, dict[str, Any]]` helper returning the same defaults

## Acceptance

- [ ] `run_wizard` runs the six steps in today's order, passes their dicts to the summary under their section names, and the summary writes the same files as before.
- [ ] Ship commands set in the phases step still reach `commands/ship/config.yaml` (`test_customized_ship_commands_reach_ship_config`).
- [ ] `grep -rn "WizardFlowController\|WizardState\|StepHandler\|nav_prompt_ask\|nav_confirm_ask\|WizardStep\|STEP_TITLES\|NavigationError" src tests` returns nothing.
- [ ] `ls src/adw/cli/wizard` shows no `navigation.py`, and `src/adw/models/wizard.py` is gone.
- [ ] `uv run pytest tests/unit/cli tests/unit/config tests/unit/models -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failure of `test_run_wizard_calls_steps_in_order_and_hands_cfg_to_summary` (`ImportError: run_wizard`), then the GREEN pytest tail, the grep, the `ls` and the preflight tail.

## Steps

### RED
- [ ] Rewrite `test_flow.py` with the single `run_wizard` test; run it: it fails on the missing `run_wizard`.

### GREEN
- [ ] Write `run_wizard` in `flow.py` and switch `init.py` to it.
- [ ] Move the summary, generator and initializer to `cfg`; drop the handlers, `state` parameters, `navigation.py` and `models/wizard.py`; trim `wizard/__init__.py`.
- [ ] Update the step, summary and generator tests as listed; delete `test_navigation.py` and `test_state.py`.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- Patch targets move with the imports: `flow.py` imports each `run_*_step` by name, so the flow test patches `adw.cli.wizard.flow.run_basics_step` and so on.
- `test_init.py::test_wizard_flag_forces_wizard_mode` feeds `c\n`. In its empty directory the first prompt is `Prompt.ask("Language")`, which takes `c` as a custom language, and stdin ends at "Platform" — as it does today. Typer turns that `EOFError` into `Aborted.` and exit 1. The test asserts only that wizard output appears, so it stays green; TASK-005 replaces the `Aborted.` with a message that says nothing was written.
- If PR #212 has merged by now, rebase first and leave the webhook step out of the list.
