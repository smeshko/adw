# TASK-002: Delete ship placeholder tests and move the ship extension tests to core

Depends on: TASK-001
Suggested commit: `test: delete pass-placeholder ship tests and move ship extension tests to core`

## Goal

No test in the suite has a body of only `pass`. The real ship tests live next to the other core tests, and `tests/unit/ship/` is gone.

## Files

- `tests/unit/ship/test_failure_diagnosis.py`: delete (36 `pass`-only tests).
- `tests/unit/ship/test_command_execution.py`: delete (16 `pass`-only tests).
- `tests/unit/ship/test_ship_phase_fixes.py` → `tests/unit/core/test_ship_extension.py` (`git mv`):
  - delete `TestFlatTemplateVariables` (3 tests)
  - keep `TestShipConfigFormat`, `TestHookChaining` and `TestShipCommandEnvVars`
  - rewrite the module docstring's "Covers:" list without the "Issue 2" line; the "Issue N" labels can go too
  - drop imports left unused (ruff F401)
- `tests/unit/ship/__init__.py`: delete, and with it the directory. Remove a leftover `__pycache__/` by hand; it is untracked.

## Acceptance

- [ ] The pass-only AST scan from `RESEARCH.md` → Useful Commands prints `total 0`.
- [ ] `test -d tests/unit/ship` fails.
- [ ] `uv run pytest tests/unit/core/test_ship_extension.py -o addopts="" -v` passes 13 tests.
- [ ] `uv run pytest --collect-only -q -o addopts="" | tail -1` shows **4,131**: 4,186 − 36 − 16 − 3.
- [ ] `uv run ruff check tests/ && uv run ruff format --check tests/` pass.

Evidence:
- the AST scan output before (`total 52`) and after (`total 0`)
- the `-v` run of `test_ship_extension.py`
- the collected count

## Steps

### RED
- [ ] Run the pass-only AST scan and record `total 52` (36 + 16). This is the failing state of the phase's first acceptance criterion.

### GREEN
- [ ] Delete the two placeholder files.
- [ ] `git mv tests/unit/ship/test_ship_phase_fixes.py tests/unit/core/test_ship_extension.py`, then delete `TestFlatTemplateVariables`.
- [ ] `git rm tests/unit/ship/__init__.py`, then `rm -rf tests/unit/ship`.
- [ ] Re-run the scan (`total 0`), the moved file, and the collect-only count.

### REFACTOR
- [ ] Tidy the moved file's docstring and imports, then run ruff check and format on `tests/`.

## Notes

- `git mv` keeps the history, so do the class deletion in the same commit rather than recreating the file.
- The moved file uses no `Path(__file__)` lookups, so the new depth needs no path changes.
