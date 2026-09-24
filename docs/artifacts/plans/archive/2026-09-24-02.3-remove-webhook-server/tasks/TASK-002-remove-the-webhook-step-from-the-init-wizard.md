# TASK-002: Remove the webhook step from the init wizard

Depends on: None
Suggested commit: `refactor(wizard): remove the webhook step`

## Goal

`adw init --wizard` asks no webhook questions. Its summary and the `project.yaml` it generates carry no webhook section.

## Files

- `src/adw/cli/wizard/webhooks.py`: delete it.
- `src/adw/cli/wizard/flow.py`: drop `WizardStep.WEBHOOKS` (`:50`), its `STEP_SEQUENCE` entry (`:78`) and its `STEP_TITLES` entry (`:92`).
- `src/adw/cli/init.py`: drop the `WebhooksStepHandler` import (`:171`) and `controller.register_step_handler(WizardStep.WEBHOOKS, …)` (`:199`).
- `src/adw/cli/wizard/__init__.py`: drop the docstring lines (`:26-27`), the import block (`:108-111`), and `"WebhooksStepHandler"` and `"run_webhooks_step"` from `__all__` (`:131`, `:156`).
- `src/adw/cli/wizard/summary.py:generate_summary_panel`: drop `webhooks = state.get_step_config("webhooks")` (`:183`) and the "Webhooks:" block (`:274-286`).
- `src/adw/config/yaml_generator.py:generate_project_yaml`: drop the state read (`:127`), the `# === Webhook ===` call and its trailing blank line (`:232-235`), and `_add_webhook_section` (`:327-387`). Keep `_format_yaml_value`, which has other callers.
- `tests/unit/cli/wizard/test_webhooks.py`: delete it.
- `tests/unit/cli/wizard/test_flow.py:30`: drop `"webhooks"` from the expected step list.
- `tests/unit/cli/wizard/test_summary.py`:
  - flip `:114` to `assert "Webhooks:" not in output`
  - delete `test_generate_project_yaml_with_webhooks` (`:426-457`)
  - drop the `"webhooks": …` keys from the state fixtures
- `tests/unit/config/test_yaml_generator.py`:
  - flip `:123` to `assert "# === Webhook Server ===" not in yaml_content`, and add `assert "webhook" not in yaml.safe_load(yaml_content)` if the test already parses the YAML
  - delete `TestWebhookFieldEmission` (`:520-623`)
  - drop `"webhooks": {}` (`:31`)

## Acceptance

- [ ] `test_flow.py`'s step-order test passes with no `webhooks` step.
- [ ] The summary-panel test asserts that "Webhooks:" is absent, and passes.
- [ ] The section-headers test asserts that `# === Webhook Server ===` is absent, and passes.
- [ ] `grep -rni "webhook" src/adw/cli src/adw/config/yaml_generator.py tests/unit/cli tests/unit/config/test_yaml_generator.py` returns nothing.
- [ ] `uv run pytest tests/unit/cli tests/unit/config -o addopts=""` passes.

Evidence:
- the RED run: the three changed tests fail on today's code
- the GREEN run of the same tests
- the grep

## Steps

### RED
- [ ] Edit the three assertions first: the `test_flow.py` step list, and the `not in` flips in `test_summary.py` and `test_yaml_generator.py`.
- [ ] Run them and confirm all three fail, because the step, the panel line and the header still exist.

### GREEN
- [ ] `git rm src/adw/cli/wizard/webhooks.py tests/unit/cli/wizard/test_webhooks.py`.
- [ ] Remove the step from `flow.py`, `init.py` and `wizard/__init__.py`.
- [ ] Remove the summary and generator sections.
- [ ] Delete `TestWebhookFieldEmission` and `test_generate_project_yaml_with_webhooks`.
- [ ] Run the partial suite and confirm it is green.

### REFACTOR
- [ ] Drop the stale `"webhooks"` fixture keys in `test_summary.py` and `test_yaml_generator.py`.
- [ ] `scripts/preflight.sh` passes.

## Notes

- Keep the edits to webhook lines only. Phases 2.1 (security) and 2.2 (ports) remove their own sections from the same files later, so reformatting the code around them would turn their rebases into real conflicts.
- `test_init.py::test_wizard_flag_forces_wizard_mode` cancels at the first prompt with `c\n`, so removing a later step doesn't affect it.
