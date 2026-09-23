# TASK-001: Replace prompt-wording tests with one bundled-phase check

Depends on: None
Suggested commit: `test: replace prompt-wording tests with one bundled-phase check`

## Goal

One parametrized test per bundled phase checks the phase's structure: `config.yaml` validates, `prompt.md` exists, and every `instructions.xml` parses. It replaces the tests that assert prompt and instruction prose.

## Files

- `tests/unit/commands/test_bundled_commands.py`:
  - Add `test_bundled_phase_files_are_well_formed(phase: str)`, parametrized over `PHASE_SEQUENCE` (`adw.core.constants`), as a module-level function or in a new `TestBundledPhaseFiles` class. For each phase, with `phase_dir = Path(str(files("adw") / "defaults" / "commands" / phase))`:
    - `config.yaml`: `data = yaml.safe_load(path.read_text()) or {}`, then `get_config_class(phase).model_validate(data)` must not raise
    - `prompt.md` exists
    - `sorted(phase_dir.rglob("instructions.xml"))` is non-empty, and `ET.parse(p)` succeeds for each file
  - Delete `TestShipPhaseInstructionsXml` (11 tests).
  - In `TestBundledCommands`, delete the six existence tests: `test_bundled_plan_exists`, `test_bundled_build_exists`, `test_bundled_validate_exists`, `test_bundled_document_exists`, `test_bundled_ship_exists` and `test_bundled_ship_has_instructions_xml`, plus the `# ISS-019` comment between them.
  - Keep the three `test_resolve_bundled_*` tests. Delete the `isolated_resolver` fixture if nothing uses it.
  - Update the module docstring: drop "(Task 6)", and describe resolution plus bundled-file structure.
- `tests/unit/commands/test_validate_prompt.py`: delete (12 tests).
- `tests/unit/ship/test_release_notes.py`: delete (42 tests).
- `tests/unit/ship/test_report_generation.py`: delete (44 tests).

## Acceptance

- [ ] `uv run pytest tests/unit/commands/test_bundled_commands.py -o addopts="" -v` passes, with 5 `test_bundled_phase_files_are_well_formed[...]` items (one per phase) and the 3 resolver tests.
- [ ] The check fails in each of these temporary mutations, reverted straight after:
  - an unknown key appended to `src/adw/defaults/commands/validate/config.yaml`
  - `ship/instructions.xml` truncated so it no longer parses
- [ ] `uv run pytest tests/unit/commands tests/unit/ship -o addopts=""` passes.
- [ ] `uv run pytest --collect-only -q -o addopts="" | tail -1` shows 4,296 − 110 = **4,186**. That is −12 validate prompt, −11 ship XML, −42 release notes, −44 report generation, −6 existence tests, +5 new.
- [ ] `uv run ruff check tests/ && uv run ruff format --check tests/` pass.

Evidence:
- the RED output of both mutations (the failing item and the assertion or exception line)
- the GREEN `-v` run
- the collected count

## Steps

### RED
- [ ] Write `test_bundled_phase_files_are_well_formed`. It passes against today's files, so demonstrate that it catches breakage:
  - Append `bogus_key: 1` to `validate/config.yaml`, and see `[validate]` fail with a pydantic `extra_forbidden` error. Revert with `git checkout -- src/adw/defaults/commands/validate/config.yaml`.
  - Truncate the last line of `ship/instructions.xml`, and see `[ship]` fail with `ParseError`. Revert with `git checkout`.
- [ ] Confirm `git status --short src/` is empty afterwards.

### GREEN
- [ ] Delete `TestShipPhaseInstructionsXml`, the six existence tests, `test_validate_prompt.py`, `test_release_notes.py` and `test_report_generation.py`.
- [ ] Run the commands and ship test dirs, then the collect-only count.

### REFACTOR
- [ ] Drop imports left unused (`patch` if the resolver tests no longer need it, and the in-method `importlib.resources` imports, moved to module level).
- [ ] Run ruff check and format on `tests/`.

## Notes

- `get_config_class` lives in `adw.commands.loader` today. Phase 1.2 moves it to `adw.models.command` and deletes `loader.py`. Import it from whichever module exists when this task runs; if phase 1.2 lands later, it updates this import.
- Don't glob `**/*.xml` for the parse check. The epic scopes it to `instructions.xml`, and each phase has exactly one. The "non-empty" assertion stops the check passing vacuously if a file moves.
- Resolve files through `importlib.resources.files("adw")`, not `Path(__file__).parents[3] / "src"`, so the test checks the packaged location that `CommandResolver` reads.
- `tests/unit/ship/` keeps `test_failure_diagnosis.py`, `test_command_execution.py` and `test_ship_phase_fixes.py` after this task; TASK-002 empties it.
