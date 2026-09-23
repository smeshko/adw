# TASK-003: Strip to_dict, docstring examples and pass-through inits from exceptions.py

Depends on: TASK-001, TASK-002
Suggested commit: `refactor: strip to_dict and boilerplate from the exception classes`

## Goal

`exceptions.py` holds the eight remaining classes with short docstrings, no `to_dict()`, no `Example:` blocks, and no `__init__` that only forwards to `ADWError`.

## Files

- `src/adw/exceptions.py`:
  - delete `to_dict()` on `ADWError`, `HookError`, `TaskError` and `SecurityError`, and the `from typing import Any` import if nothing else needs it
  - delete every `Example:` block
  - delete the `__init__` of `ConfigError`, `LLMError`, `StateError` and `WorktreeError`
  - keep the one-line class docstrings and the "common error codes" lists, which document the codes callers pass
  - `HookError`, `TaskError` and `SecurityError` keep their `__init__`, which set extra fields
- `tests/unit/test_exceptions.py` — delete `test_security_error_to_dict`.
- `tests/unit/test_security_error.py` — delete `test_security_error_to_dict`.

## Acceptance

- [ ] `grep -n '^class ' src/adw/exceptions.py` lists exactly `ADWError`, `ConfigError`, `HookError`, `LLMError`, `StateError`, `WorktreeError`, `TaskError` and `SecurityError`.
- [ ] `grep -n "to_dict\|>>>" src/adw/exceptions.py` returns nothing.
- [ ] Keyword construction still works for every subclass: mypy `--strict` passes through `scripts/preflight.sh`, and the full suite passes. Its tests build `ConfigError`, `LLMError`, `StateError` and `WorktreeError` with `code=`, `message=`, `suggestion=` and `recoverable=`.

Evidence: both greps, the preflight output, and the full-suite summary line.

## Steps

### RED
- [ ] None: the deleted methods have no caller, and the inherited `__init__` has the same signature.

### GREEN
- [ ] Rewrite `exceptions.py` and delete the two `to_dict` tests.

### REFACTOR
- [ ] `scripts/preflight.sh`, then `uv run pytest` (full suite, since every package imports `exceptions`).
