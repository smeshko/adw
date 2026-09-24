# TASK-003: Drop the LLM retry step

Depends on: None
Suggested commit: `refactor(wizard): drop the LLM retry step`

## Goal

`adw init --wizard` asks no retry questions, and the generated `project.yaml` shows `RetryConfig`'s defaults as a commented `llm.retry` block (D5).

## Files

- `src/adw/cli/wizard/retry.py`: delete with `git rm`.
- `src/adw/cli/wizard/flow.py`: drop `LLM_RETRY` from `WizardStep`, `STEP_SEQUENCE` and `STEP_TITLES`.
- `src/adw/cli/init.py` (`_run_wizard_setup`): drop `RetryStepHandler` from the import and its `register_step_handler` line.
- `src/adw/cli/wizard/__init__.py`: drop the retry docstring lines, the `from adw.cli.wizard.retry import (...)` block, and `RetryStepHandler`, `run_retry_step` and the four `validate_*` retry validators from `__all__`.
- `src/adw/cli/wizard/summary.py` (`generate_summary_panel`): drop `llm_retry = …` and the `# LLM Retry section` block.
- `src/adw/config/yaml_generator.py` (`generate_project_yaml`):
  - drop `llm_retry = state.get_step_config("llm_retry")` and the `retry_custom` branch
  - the `# === LLM Configuration ===` block is always commented: `# llm:`, `#   path: "claude"  # …`, `#   retry:`, then one `#     <field>: <default>` line per `RetryConfig` field, read from `RetryConfig.model_fields` (`max_retries`, `base_delay_seconds`, `max_delay_seconds`, `multiplier`), with each field's description as the trailing comment
- `tests/unit/cli/wizard/test_retry.py`: delete with `git rm`.
- `tests/unit/cli/wizard/test_flow.py`: drop `llm_retry` from any step list it asserts, if present.
- `tests/unit/cli/wizard/test_summary.py`: drop the `"llm_retry"` fixture entries, the `LLM Retry` asserts, and `test_generate_project_yaml_with_llm_retry`.
- `tests/unit/config/test_yaml_generator.py`:
  - drop `"llm_retry": {}` from `MockWizardState`
  - replace `TestYAMLGeneratorRetryKeys` (both tests) with one `test_retry_defaults_are_commented_and_round_trip`: `llm:` does not appear as an active (uncommented) line, and after the uncomment pass used by `test_generate_project_yaml_commented_settings_are_valid_yaml`, `RetryConfig.model_validate(parsed["llm"]["retry"]) == RetryConfig()`

## Acceptance

- [ ] A controller run never visits an `llm_retry` step.
- [ ] The generated `project.yaml` has no active `llm:` key, and its uncommented `llm.retry` block equals `RetryConfig()`.
- [ ] `grep -rn "run_retry_step\|RetryStepHandler\|llm_retry\|retry_custom\|LLM_RETRY" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/cli tests/unit/config -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failure of `test_retry_defaults_are_commented_and_round_trip` (no `retry` key in the uncommented `llm` block), then the GREEN pytest tail, the grep and the preflight tail.

## Steps

### RED
- [ ] Add `test_retry_defaults_are_commented_and_round_trip`; run it: it fails.

### GREEN
- [ ] Delete `retry.py` and `test_retry.py`, and edit `flow.py`, `init.py`, `wizard/__init__.py`, `summary.py` and `yaml_generator.py` as listed.
- [ ] Update the summary and generator tests as listed.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- The uncomment pass in `test_generate_project_yaml_commented_settings_are_valid_yaml` strips one `"# "` prefix. Keep two-space nesting after the `#` (`#   retry:`, `#     max_retries: 3`) so the block parses once uncommented.
- A `project.yaml` written by an older wizard with an active `llm.retry` block still loads: `ProjectConfig.llm.retry` is unchanged.
