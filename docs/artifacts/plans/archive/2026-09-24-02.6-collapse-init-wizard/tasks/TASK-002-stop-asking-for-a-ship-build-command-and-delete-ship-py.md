# TASK-002: Stop asking for a ship build command and delete ship.py

Depends on: None
Suggested commit: `refactor(wizard): stop asking for a ship build command`

## Goal

The phases step's ship options ask only for answers that reach `.adw/commands/ship/config.yaml`, and the unused standalone ship step is gone.

## Files

- `src/adw/cli/wizard/phases.py` (`_configure_ship_phase`): delete the "Build command" `Prompt.ask` and its `commands["build"]` line. Update the docstring: the project-level build command comes from the basics step, and `PhaseRunner` passes it to the ship phase.
- `src/adw/cli/wizard/ship.py`: delete with `git rm`. It is not in `STEP_SEQUENCE`; only the package re-exports it.
- `src/adw/cli/wizard/__init__.py`: drop the `ShipStepHandler`/`run_ship_step` docstring lines, import and `__all__` entries.
- `tests/unit/cli/wizard/test_ship.py`: delete with `git rm`.
- `tests/unit/cli/wizard/test_phases.py`: add `test_ship_phase_asks_only_version_bump_and_publish`. Patch `Prompt.ask` with a side effect that records each question and answers `npm version patch` for "Version bump command" and `npm publish` for "Publish command" (empty otherwise), and patch `Confirm.ask` to `False`. Assert no recorded question mentions "Build command", and `config["commands"] == {"version_bump": "npm version patch", "publish": "npm publish"}`.

## Acceptance

- [ ] Configuring the ship phase never prompts "Build command".
- [ ] The ship options still return `version_bump`, `publish` and `wait_for_merge`, and `generate_all_phase_configs` writes them to the ship config as before.
- [ ] `grep -rn "run_ship_step\|ShipStepHandler\|wizard.ship\|wizard/ship" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/cli/wizard tests/unit/config -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failure of `test_ship_phase_asks_only_version_bump_and_publish` (a "Build command" question is recorded), then the GREEN pytest tail, the grep and the preflight tail.

## Steps

### RED
- [ ] Add `test_ship_phase_asks_only_version_bump_and_publish`; run it: it fails on the recorded "Build command" question.

### GREEN
- [ ] Delete the prompt, `ship.py`, `test_ship.py` and the re-exports.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- `_configure_ship_phase` answers go through `_configure_phase`, which only calls it when the user customises the ship phase, so the accept-defaults path never reaches it.
