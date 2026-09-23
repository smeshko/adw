# TASK-001: Fold PortAllocationError and MaxConcurrentRunsError into WorktreeError

Depends on: None
Suggested commit: `refactor: raise WorktreeError for port and concurrent-run limits`

## Goal

`PortAllocator.allocate` and `ConcurrentRunManager.check_can_start_or_raise` raise `WorktreeError` with their existing codes, messages and suggestions, and the two dedicated classes are gone.

## Files

- `src/adw/worktree/ports.py` — import and raise `WorktreeError` (code `PORT_ALLOCATION_FAILED`, same message and suggestion); fix the `Raises:` docstring.
- `src/adw/worktree/concurrent.py` — raise `WorktreeError` (code `MAX_CONCURRENT_REACHED`, same message and suggestion) without `context`; drop the `active_ids` list that only fed `context`; fix the `Raises:` docstring.
- `src/adw/core/run_lifecycle.py` — the two `Raises: MaxConcurrentRunsError` docstring lines become `WorktreeError`, noting the concurrent-run limit.
- `src/adw/exceptions.py` — delete `PortAllocationError` and `MaxConcurrentRunsError`.
- `tests/unit/worktree/test_ports.py` — `test_allocate_raises_after_max_attempts` expects `WorktreeError`.
- `tests/unit/worktree/test_concurrent.py` — `test_check_can_start_or_raise_raises_at_limit` expects `WorktreeError` and drops the two `context` asserts; delete `TestMaxConcurrentRunsError` (constructor and `to_dict` smoke tests of a deleted class).

## Acceptance

- [ ] Both tests pass and assert `WorktreeError` with the unchanged code and message.
- [ ] `grep -rnw "PortAllocationError\|MaxConcurrentRunsError" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/worktree tests/unit/core/test_run_lifecycle.py -o addopts=""` passes.

Evidence: the pytest summary for the two retargeted tests (RED against the old classes, GREEN after), and the empty grep.

## Steps

### RED
- [ ] Change the two tests to `pytest.raises(WorktreeError)` and drop the `context` asserts. Run them: both fail, because the old classes aren't `WorktreeError` subclasses.

### GREEN
- [ ] Switch both raise sites to `WorktreeError`, then delete the two classes from `exceptions.py`.
- [ ] Delete `TestMaxConcurrentRunsError`.

### REFACTOR
- [ ] Fix the `Raises:` docstrings in `ports.py`, `concurrent.py` and `run_lifecycle.py`.
- [ ] Run the grep and the partial suite above, then `scripts/preflight.sh`.
