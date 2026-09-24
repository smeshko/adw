# Validation Summary — 02.2-remove-port-allocation

**Rounds:** 3
**Plan status at validation:** draft
**Run on:** 2026-09-24

## Rounds

| Round | Findings | Applied | Deferred | Rejected |
|-------|----------|---------|----------|----------|
| 1     | 3        | 3       | 0        | 0        |
| 2     | 3        | 1       | 1        | 1        |
| 3     | 3        | 3       | 0        | 0        |

Round 3 still produced applies. They were local corrections (one dependency edge and two test edits), so they were applied and validation stopped there without a fourth round (act-and-stop).

## Applied

### Round 1
- PLAN.md:Acceptance Criteria, PLAN.md:Decisions, TASK-005, TASK-006 — The legacy-config test uses an overlapping `port_range` that the old validator rejected, so it fails RED today and shows the key is ignored. It replaces a `hasattr` check, which ADR-001 counts as a trivial attribute test (round-1 #1)
- TASK-001, TASK-006, PLAN.md:Acceptance Criteria — Hand-written lock JSON carries every key `get_active_runs` reads (`run_id`, `pid`, `start_time`, `worktree_path`). The CLI transcript checks for "Maximum concurrent runs reached (1)", because the CLI prints the message, not the code (round-1 #2)
- TASK-004, PLAN.md:Acceptance Criteria — The wizard evidence is now behavioural: a controller run never visits `ports`, and the uncommented `worktree:` block has exactly `enabled`/`base_dir`/`max_concurrent`. The `len(STEP_SEQUENCE) == 10` assert that the removal would break is dropped (round-1 #3)

### Round 2
- PLAN.md:Acceptance Criteria, PLAN.md:Decisions, TASK-005, TASK-006 — The acceptance grep is gated per file: `src` is empty, and `tests` lists only `tests/unit/models/test_config.py` (round-2 #1)

### Round 3
- TASK-003, PLAN.md:Tasks, PLAN.md:Decisions — TASK-003 also depends on TASK-004, because `cli/wizard/ports.py` imports constants from `adw.worktree.ports`. The task list runs TASK-004 first (round-3 #1)
- TASK-001 — Drop the stale `assert "9100/9200" in captured.out` in `test_list_running.py` (round-3 #2)
- TASK-004 — Delete the ADR-001 enum-existence test `test_step_values_exist` instead of trimming it. This reverses round-2 #3 (round-3 #3)

## Deferred

- (round-2 #2) Simultaneous `adw run` starts can both pass the `max_concurrent` check, because the slot is checked before the worktree is created and registered only after it. Filed as **ADW-64**. The race predates this phase and doesn't involve ports, and the epic's criterion is sequential. The plan's criterion now says "sequential starts".

## Rejected

- (round-2 #3) Keep `test_step_values_exist`, trimmed by one line, for merge-friendliness with phases 2.1 and 2.3. Reversed in round 3 (see Applied).
