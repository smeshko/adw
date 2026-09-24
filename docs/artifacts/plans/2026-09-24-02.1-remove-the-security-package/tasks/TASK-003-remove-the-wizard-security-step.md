# TASK-003: Remove the wizard security step

Depends on: TASK-002
Suggested commit: `refactor(cli): drop the wizard's security step`

## Goal

`adw init --wizard` asks no security questions and its summary panel has no Security line. The step's module, enum member, registration, re-exports and tests are gone.

## Files

- `src/adw/cli/wizard/security.py`: delete.
- `src/adw/cli/wizard/flow.py`: delete `SECURITY = "security"` (L49), `WizardStep.SECURITY,` from `STEP_SEQUENCE` (L77) and its `STEP_TITLES` entry (L91).
- `src/adw/cli/init.py`: delete `SecurityStepHandler,` from the import (L164) and its `register_step_handler` call (L194).
- `src/adw/cli/wizard/__init__.py`: delete the two docstring lines (L22–23), the `from adw.cli.wizard.security import (...)` block (L83–89) and its five `__all__` entries (`BUILTIN_BLOCKED_COMMANDS`, `BUILTIN_BLOCKED_ENV_FILES`, `SecurityStepHandler`, `run_security_step`, `validate_regex`).
- `src/adw/cli/wizard/summary.py`: delete `security = state.get_step_config("security")` (L182) and the `# Security section` block (L263–272).
- `tests/unit/cli/wizard/test_security.py`: delete.
- `tests/unit/cli/wizard/test_flow.py`: delete `TestWizardStep.test_step_values_exist` (L18–33) and `TestWizardFlowController.test_step_sequence_defined` (L60–65). Both assert enum members, order or count, which ADR-001 classifies as waste; editing them would only churn them until phase 2.6 deletes the flow controller. If `TestWizardStep` is left with only `test_step_enum_members`, delete that too (same category) and the empty class.
- `tests/unit/cli/wizard/test_summary.py`: delete every `"security": ...` key from the state dicts (about 22 sites, including `{"security_allow_dangerous": False}` at L89); change `assert "Security:" in output` (L113) to `not in`.

## Acceptance

- [ ] `grep -rn -i --exclude-dir=__pycache__ "security" src/adw/cli tests/unit/cli` returns nothing.
- [ ] `grep -rn --exclude-dir=__pycache__ "SecurityInterceptor\|SecurityConfig\|SecurityError\|allow_dangerous\|allow-dangerous\|security_interceptor\|adw\.security" src tests` returns nothing (the plan's acceptance grep).
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/cli tests/unit/config -o addopts=""` passes.

Evidence: both empty greps, the preflight output and the pytest summary line, plus the RED run of the flipped assertions.

## Steps

### RED
- [ ] Flip the summary assertion to `assert "Security:" not in output`.
- [ ] Run `uv run pytest tests/unit/cli/wizard/test_summary.py -o addopts=""` and confirm that test fails.

### GREEN
- [ ] `git rm src/adw/cli/wizard/security.py tests/unit/cli/wizard/test_security.py`.
- [ ] Edit `flow.py`, `init.py`, `wizard/__init__.py` and `summary.py` as listed in Files.
- [ ] Delete the `"security"` keys from `test_summary.py`'s state dicts, and the enum tests from `test_flow.py`.
- [ ] Run the targeted pytest command from Acceptance.

### REFACTOR
- [ ] Check the wizard `__init__.py` docstring and `__all__` stay alphabetical where they were.
- [ ] Run `scripts/preflight.sh` and both greps from Acceptance.

## Notes

- Line numbers refer to `ad704a17`.
- Phase 2.6 replaces `WizardFlowController`, `WizardStep` and `STEP_TITLES`. Here, drop only the security member; keep the structure.
- The generator never read the step's answers, so the generated `project.yaml` doesn't change here (TASK-002 already removed its commented block).
