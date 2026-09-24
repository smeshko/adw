# TASK-003: Delete PortAllocator, PortAllocation and the port error code

Depends on: TASK-002, TASK-004
Suggested commit: `refactor: delete PortAllocator and PortAllocation`

## Goal

The port allocator, its model and its error code are gone.

## Files

- `src/adw/worktree/ports.py`: delete with `git rm`.
- `src/adw/models/worktree.py`: delete with `git rm`. It holds only `PortAllocation`.
- `src/adw/worktree/__init__.py`: drop `from adw.worktree.ports import PortAllocator` (`:10`) and `"PortAllocator"` from `__all__` (`:15`).
- `src/adw/models/__init__.py`: drop `from adw.models.worktree import PortAllocation` (`:77`), and the `# Worktree models` comment with `"PortAllocation"` in `__all__` (`:148-149`).
- `src/adw/exceptions.py` (`WorktreeError` docstring): "when a run cannot get ports or a concurrent-run slot" becomes "when a run cannot get a concurrent-run slot" (`:136-137`), and the `PORT_ALLOCATION_FAILED` bullet goes (`:144`).
- `tests/unit/worktree/test_ports.py`: delete with `git rm`.

## Acceptance

- [ ] `src/adw/worktree/ports.py`, `src/adw/models/worktree.py` and `tests/unit/worktree/test_ports.py` no longer exist.
- [ ] `grep -rn "PortAlloc\|PORT_ALLOCATION\|adw.models.worktree\|adw.worktree.ports" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/worktree tests/unit/models tests/unit/hooks -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: `ls` of the three paths (not found), the grep, the pytest tail and the preflight tail.

## Steps

### RED
- [ ] No new test: the allocator has no production caller, so deleting it changes no behaviour. Run the grep above first; it matches the files this task deletes and edits.

### GREEN
- [ ] `git rm src/adw/worktree/ports.py src/adw/models/worktree.py tests/unit/worktree/test_ports.py`.
- [ ] Edit the two `__init__.py` files and the `WorktreeError` docstring.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- `cli/wizard/ports.py` imports `DEFAULT_BACKEND_START`, `DEFAULT_FRONTEND_START` and `DEFAULT_MAX_CONCURRENT` from `adw.worktree.ports`. TASK-004 deletes it, so this task runs after TASK-004.
- `test_stats.py`'s `TestModelExports` doesn't list `PortAllocation`, so no export test changes.
