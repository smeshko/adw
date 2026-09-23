# TASK-001: Delete adw.validation and adw.utils

Depends on: None
Suggested commit: `refactor: delete the unused validation and utils packages`

## Goal

The `adw.validation` and `adw.utils` packages, and the tests that only cover them, are gone. Nothing in `src` or `tests` imports either package.

## Files

- `src/adw/validation/`: delete the whole package: `__init__`, `models`, `phase`, `report`, `state_manager`.
- `src/adw/utils/`: delete the whole package: `__init__`, `diff`, `ulid`.
- `src/adw/models/__init__.py`: remove `from adw.validation.models import ValidationResult`, the `"ValidationResult"` entry in `__all__`, and the `- validation: ValidationResult` docstring line.
- `tests/unit/validation/`: delete the directory.
- `tests/unit/utils/`: delete the directory. That includes `test_diff.py`, which the epic doesn't list; it only covers `adw.utils.diff`.
- `tests/unit/core/test_run_directory.py` and `tests/integration/core/test_run_directory_integration.py`: replace `from adw.utils.ulid import generate_run_id` with `from ulid import ULID`, and every `generate_run_id()` with `str(ULID())`.
- `AGENTS.md`: delete the Architecture-notes line "`ValidationConfig` is an alias of `ValidateCommandConfig`, re-exported from `adw.validation`." The alias no longer exists anywhere.
- `docs/architecture/deep-dive/validate-phase.md`: delete the two table rows at L225–226 that point at `src/adw/validation/phase.py` and `models.py`.

## Acceptance

- [ ] `grep -rn "adw\.validation\|adw\.utils\|adw/validation\|adw/utils" src tests AGENTS.md docs/architecture` returns nothing.
- [ ] `uv run python -c "import adw.models, adw.cli.app"` exits 0.
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/core/test_run_directory.py tests/integration/core/test_run_directory_integration.py tests/unit/models -o addopts=""` passes.
- [ ] The `vulture` diff against this task's start shows no new entry, or each new entry is deleted or recorded (see Notes).

Evidence: the empty grep, the preflight output, and the pytest summary line.

## Steps

### RED
- [ ] Save the cascade baseline for this task: `uvx vulture src/adw --min-confidence 60 | sed -E 's/:[0-9]+:/:/' | sort > "$SCRATCH/vulture-before.txt"`.
- [ ] Re-verify by grep that nothing outside the two packages imports them: `grep -rn "adw.validation\|adw.utils" src tests`. At HEAD this shows `models/__init__.py:84` and the two `test_run_directory` files.

### GREEN
- [ ] `git rm -r src/adw/validation src/adw/utils tests/unit/validation tests/unit/utils`.
- [ ] Edit `models/__init__.py` (import, `__all__`, docstring line).
- [ ] Switch both `test_run_directory` files to `str(ULID())`.
- [ ] Edit `AGENTS.md` and `validate-phase.md`.
- [ ] Run the targeted pytest command from Acceptance.

### REFACTOR
- [ ] Run `uv run ruff check src/ --fix` for any import left unused.
- [ ] Take the `vulture` diff, `comm -13` against the baseline. Handle each new entry as Notes describes.
- [ ] Run `scripts/preflight.sh`.

## Notes

- Cascade rule, shared by every task: an entry that shows up in the `vulture` diff is newly dead.
  - First grep it across `src/adw` with no `--include` filter.
  - If nothing in `src` references it, delete it, together with the tests whose only subject it is.
  - Otherwise, add it to the PR description's "kept" list with the reason.
  - `MockExecutor` API counts as live while any test uses it.
- Leave the untracked `__pycache__`-only directories (`tests/unit/validation/validators`, `src/adw/evidence`) alone. `git rm` doesn't see them, and phase 1.5 deletes them.
