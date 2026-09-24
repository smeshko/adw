# TASK-002: Delete the never-raised CommandError and PhaseError

Depends on: None
Suggested commit: `refactor: delete the never-raised CommandError and PhaseError`

## Goal

`CommandError` and `PhaseError` are gone, and the tests that used them as stand-in errors raise the error their code path really produces.

## Files

- `src/adw/exceptions.py` — delete `CommandError` and `PhaseError`.
- `src/adw/core/phase_runner.py` — the two `Raises: CommandError` docstring lines (`run` and `_load_and_render_prompt`) become `ConfigError`, which `CommandResolver.resolve` (`COMMAND_NOT_FOUND`) and `TemplateEngine` raise.
- `tests/unit/core/test_orchestrator.py` — the four `PhaseError(...)` uses become `LLMError(...)` without `phase=`; update the import and the local import at line 1608.
- `tests/unit/core/test_run_lifecycle.py` — the four `PhaseError(...)` uses become `LLMError(...)`; the contexts already set `current_phase="build"`, so the `failed_phase` fallback gives the same value.
- `tests/unit/core/test_phase_runner.py` — `test_command_error_adds_phase_context` raises and expects `ConfigError` (code `COMMAND_NOT_FOUND`); rename it to `test_resolution_error_propagates_unchanged` to match what it asserts.
- `tests/unit/cli/test_progress.py` — `test_on_phase_error_shows_phase_name` builds an `LLMError`.

## Acceptance

- [ ] `grep -rnw "CommandError\|PhaseError" src tests` returns nothing.
- [ ] The four touched test files pass.

Evidence: the empty grep and the partial pytest summary.

## Steps

### RED
- [ ] None: the deleted classes are never raised by `src`, so no behaviour changes. The retargeted tests keep asserting the same handler behaviour.

### GREEN
- [ ] Retarget the tests, then delete the two classes.
- [ ] `uv run pytest tests/unit/core/test_orchestrator.py tests/unit/core/test_run_lifecycle.py tests/unit/core/test_phase_runner.py tests/unit/cli/test_progress.py -o addopts=""`

### REFACTOR
- [ ] Fix the two `phase_runner.py` docstrings; in `_load_and_render_prompt`, merge the new line with the existing `ConfigError` one.
- [ ] Run the grep, then `scripts/preflight.sh`.
