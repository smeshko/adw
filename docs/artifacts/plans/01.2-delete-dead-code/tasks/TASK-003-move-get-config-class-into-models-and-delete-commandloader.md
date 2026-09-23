# TASK-003: Move get_config_class into models and delete CommandLoader

Depends on: TASK-002
Suggested commit: `refactor(commands): move get_config_class to models and delete CommandLoader`

## Goal

`get_config_class` and `PHASE_CONFIG_CLASSES` live in `models/command.py`, and all five callers import them from there. `commands/loader.py` and `LoadedCommand` are gone, and so are the `ResolvedCommand.has_pre_hook`/`has_post_hook` properties that only the loader read.

## Files

- `src/adw/models/command.py`:
  - Add `PHASE_CONFIG_CLASSES` and `get_config_class`, verbatim from `commands/loader.py:32-56`, after `DocumentCommandConfig` is defined.
  - Delete `class LoadedCommand`.
  - Delete the two `@computed_field` properties `has_pre_hook` and `has_post_hook` on `ResolvedCommand`, and their two lines in the class docstring.
- `src/adw/commands/loader.py`: delete.
- `src/adw/commands/__init__.py`: remove `CommandLoader` from the imports and `__all__`.
- `src/adw/models/__init__.py`: remove `LoadedCommand` from the imports, `__all__`, and the module docstring.
- Point these imports of `get_config_class` at `adw.models.command`:
  - `core/phase_runner.py:19`
  - `core/extensions/ship.py:16`
  - `config/checker.py:19`
  - `dashboard/partials.py:1313` (function-local)
  - `dashboard/mutations.py:750` (function-local)
- Tests:
  - `tests/unit/commands/test_loader.py`: move `TestPhaseConfigClasses` (L625–661) to `tests/unit/models/test_command.py`, importing from `adw.models.command`. Then delete the file.
  - `tests/unit/commands/test_module_structure.py`: delete. It holds import-smoke tests (ADR-001), and half of them import `CommandLoader`.
  - `tests/integration/test_document_phase.py`: delete `TestDocumentPhaseDocMappings` (L518 to end) and the `CommandLoader` import.
  - Rewrite `cmd.has_pre_hook` / `cmd.has_post_hook` assertions to `cmd.pre_hook_path is not None` / `cmd.post_hook_path is not None`, and their `not …` forms to `… is None`, in:
    - `tests/unit/commands/test_directory_validation.py` (6 tests)
    - `tests/unit/commands/test_resolved_command.py` (2)
    - `tests/unit/commands/test_resolver.py` (5)
    - `tests/unit/ship/test_ship_phase_fixes.py::TestHookChaining::test_resolved_command_has_pre_hook_paths_list`
  - `tests/unit/core/test_artifact_passing.py:294-295`: drop the `has_pre_hook=False, has_post_hook=False` kwargs.

## Acceptance

- [ ] `grep -rn "commands.loader\|CommandLoader\|LoadedCommand\|has_pre_hook\|has_post_hook" src tests` returns nothing.
- [ ] `get_config_class("validate") is ValidateCommandConfig` still holds, now tested in `tests/unit/models/test_command.py`.
- [ ] In a scratch repo (commands in RESEARCH.md), `adw validate` lists plan, build, validate, document and ship as `OK`.
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/commands tests/unit/models tests/unit/core/test_phase_runner.py tests/unit/core/test_artifact_passing.py tests/unit/ship tests/unit/config tests/integration/test_document_phase.py tests/dashboard -o addopts=""` passes.
- [ ] The `vulture` diff against this task's start shows no new entry, or each new entry is handled per the cascade rule.

Evidence: the empty grep, the `adw validate` transcript, and the pytest summary line.

## Steps

### RED
- [ ] Save the `vulture` baseline.
- [ ] Move `TestPhaseConfigClasses` into `tests/unit/models/test_command.py` with `from adw.models.command import PHASE_CONFIG_CLASSES, get_config_class`. It fails with `ImportError`.

### GREEN
- [ ] Add `PHASE_CONFIG_CLASSES`/`get_config_class` to `models/command.py`; the moved tests pass.
- [ ] Switch the five callers' imports.
- [ ] `git rm src/adw/commands/loader.py tests/unit/commands/test_loader.py tests/unit/commands/test_module_structure.py`. Edit `commands/__init__.py` and `models/__init__.py`.
- [ ] Delete `LoadedCommand` and the two `ResolvedCommand` properties.
- [ ] Rewrite the hook-property assertions, and delete `TestDocumentPhaseDocMappings`.
- [ ] Run the targeted pytest command, then `adw validate` in the scratch repo.

### REFACTOR
- [ ] Take the `vulture` diff. Run `uv run ruff check src/ --fix` and `scripts/preflight.sh`.

## Notes

- `get_config_class` must stay a plain function next to the config classes. Don't create a new module for it: `models/command.py` already defines every class in the mapping, so there is no import cycle.
- `ResolvedCommand` is never serialized (`model_dump` isn't called on it anywhere), so dropping the computed fields changes no output.
