# TASK-002: Delete SchemaValidator, ValidationError and jsonschema

Depends on: TASK-001
Suggested commit: `refactor(commands): delete the unused schema validator and jsonschema dependency`

## Goal

`SchemaValidator`, the `adw.exceptions.ValidationError` that only it raises, and the `jsonschema`/`types-jsonschema` dependencies are gone.

## Files

- `src/adw/commands/validator.py`: delete.
- `src/adw/commands/__init__.py`: remove `from adw.commands.validator import SchemaValidator` and its `__all__` entry.
- `src/adw/exceptions.py`: delete `class ValidationError(ADWError)` (L435 onwards, with its docstring example). This is a cascade; phase 1.3 lists it too, and its final list of classes is unchanged.
- `pyproject.toml`: remove `"jsonschema>=4.20.0"` from `dependencies` and `"types-jsonschema>=4.20.0"` from the dev group.
- `uv.lock`: regenerate with `uv lock`. In the prototype, `jsonschema` leaves the lock entirely.
- `tests/unit/commands/test_validator.py`: delete.

## Acceptance

- [ ] `grep -rn "jsonschema\|SchemaValidator" src tests pyproject.toml uv.lock` returns nothing.
- [ ] `grep -rn "adw.exceptions import.*ValidationError\|exceptions.ValidationError" src tests` returns nothing, and every remaining `except ValidationError` in `src` imports it from `pydantic`.
- [ ] `uv sync --locked` succeeds, and `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/commands tests/unit/test_exceptions.py -o addopts=""` passes.
- [ ] The `vulture` diff against this task's start shows no new entry, or each new entry is handled per the cascade rule in TASK-001's Notes.

Evidence: the empty greps, the `uv sync --locked` output, the preflight output, and the pytest summary line.

## Steps

### RED
- [ ] Save the `vulture` baseline as in TASK-001.
- [ ] Confirm that `ValidationError` from `adw.exceptions` has no raiser other than `commands/validator.py`. Check with `grep -rn "raise ValidationError" src`, then check each file's import line.

### GREEN
- [ ] `git rm src/adw/commands/validator.py tests/unit/commands/test_validator.py`.
- [ ] Edit `commands/__init__.py`, `exceptions.py` and `pyproject.toml`.
- [ ] Run `uv lock`, then `uv sync --locked`.
- [ ] Run the targeted pytest command from Acceptance.

### REFACTOR
- [ ] Take the `vulture` diff. Run `uv run ruff check src/ --fix` and `scripts/preflight.sh`.

## Notes

- `PhaseRunner` still reads `schema.json` and passes it to the prompt as `{{schema}}` (`core/phase_runner.py:494`). That is template input, not validation, and it stays.
