# TASK-002: Remove port variables and .ports.env sourcing from hook environments

Depends on: None
Suggested commit: `refactor(hooks): remove port variables and .ports.env sourcing`

## Goal

Hook scripts get no port variables, and ADW no longer sources a `.ports.env` into their environment.

## Files

- `src/adw/hooks/environment.py`:
  - drop the `TYPE_CHECKING` import of `PortAllocation` (`:11`, `:15-16`), and `from __future__ import annotations` if nothing else needs it
  - delete `_parse_ports_env_file` (`:19-48`)
  - `build_hook_environment`: drop the `port_allocation` and `ports_file` parameters (`:57`, `:59`) and their docstring entries, the port variables block (`:122-126`), and the `.ports.env` auto-detection and sourcing block (`:128-142`)
- `src/adw/hooks/runner.py`:
  - drop the `TYPE_CHECKING` import of `PortAllocation` (`:26-27`), and `TYPE_CHECKING` from the `typing` import (`:19`)
  - `run_hook`: drop the `port_allocation` parameter (`:95`), its docstring line (`:111`) and the pass-through (`:129`)
  - `_execute_hook`: drop the parameter (`:143`), its docstring line (`:156`) and the `build_hook_environment` argument (`:173`)
- `tests/unit/hooks/test_environment.py`: delete `test_includes_port_variables_when_allocation_provided`, `test_no_port_variables_without_allocation` and `test_port_variables_are_strings` (`:89-129`), and the whole `TestPortsEnvAutoSourcing` class (`:234-339`).

## Acceptance

- [ ] `grep -rn "port_allocation\|ports_file\|ports\.env\|ADW_SLOT\|ADW_BACKEND_PORT\|ADW_FRONTEND_PORT\|ADW_PORTS_FILE" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/hooks tests/unit/core/test_phase_runner.py -o addopts=""` passes. The remaining environment tests (run id, phase, paths, branch, PR URL, string values) still pass unchanged.
- [ ] `scripts/preflight.sh` passes.

Evidence: the grep, the pytest tail and the preflight tail.

## Steps

### RED
- [ ] No new test. ADR-001 leaves "a variable is absent" tests unwritten when nothing sets it, and the behaviour that stays (the ADW variables) is already covered. Record the pytest count of `tests/unit/hooks/test_environment.py` before the change.

### GREEN
- [ ] Remove the parameters, blocks and helper listed above.
- [ ] Delete the port tests listed above.
- [ ] Run the partial suite: green, with the count lower by exactly the deleted tests (3 + the `TestPortsEnvAutoSourcing` cases).

### REFACTOR
- [ ] `scripts/preflight.sh` passes: ruff finds no unused imports, and mypy `--strict` is clean.

## Notes

- `phase_runner.py`'s two `run_hook` calls pass no `port_allocation`, so no caller changes.
- `models/worktree.py` still exists after this task. TASK-003 deletes it now that the hooks don't import it.
