# TASK-003: Port the plan state updates

Depends on: TASK-002
Suggested commit: `feat(plans): port the plan state updates`

## Goal

ADW ticks a task, sets a plan's status and records its branch, making the same edits as `mark_task_done.py`, `set_plan_status.py` and `set_plan_branch.py`. `adw plan tasks` and `mark_task_done` round-trip on this plan's fixture.

## Files

- `src/adw/plans/state.py`: new.
  - `mark_task_done(root, slug, task_id) -> bool`:
    - `True` when it ticked the box, `False` when the box was already ticked.
    - `INVALID_PLAN` for an id that isn't `TASK-\d+`, `TASK_NOT_FOUND` for a missing line, `PLAN_NOT_FOUND` for a missing plan.
    - It uses the script's multiline regex `^(- \[)(?P<box>[ xX])(\]\s+{id}:.*)$` and replaces the first match only.
  - `VALID_STATUSES = ("draft", "ready", "in-progress", "done")`.
  - `set_plan_status(root, slug, status)` raises `INVALID_PLAN` for an unknown status or a missing `Status:` line.
  - `set_plan_branch(root, slug, branch)` replaces an existing `Branch:` line, or else inserts one right after `Status:`. It raises `INVALID_PLAN` when there is no `Status:` line.
- `tests/unit/plans/test_state.py`: new.
- `tests/unit/cli/test_plan.py`: the round-trip test.

## Acceptance

- [ ] `test_tasks_and_mark_task_done_round_trip` copies `tests/fixtures/plans/04.1-adw-plans-module/` into `tmp_path`, then:
  1. `adw plan tasks` shows `TASK-002\tpending`.
  2. `mark_task_done(root, slug, "TASK-002")` returns `True`, and `adw plan tasks` now shows `TASK-002\tdone`.
  3. PLAN.md differs from the fixture only on the TASK-002 line: `- [ ]` became `- [x]`.
  4. A second call returns `False` and leaves the bytes unchanged.
- [ ] `mark_task_done("TASK-2")` does not tick `TASK-20` (the `:` anchors the id).
- [ ] The error paths raise the listed codes and leave PLAN.md unchanged.
- [ ] `set_plan_branch` on the golden PLAN.md puts `Branch:` on the line after `Status:`, and a second call with another branch replaces it.
- [ ] `uv run pytest tests/unit/plans tests/unit/cli/test_plan.py -o addopts=""` and `scripts/preflight.sh` pass.

Evidence:
- the RED failure (`No module named 'adw.plans.state'`), then the GREEN pytest tail;
- one scratch run: `mark_task_done.py`, `set_plan_status.py` and `set_plan_branch.py` on one copy of the fixture, the ADW functions on another, then `diff -r` (empty).

## Steps

### RED
- [ ] Write `test_state.py` and the round-trip test. Run them: they fail.

### GREEN
- [ ] Add `state.py`.
- [ ] Run the partial suite, then the scratch `diff -r` against the scripts.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.
