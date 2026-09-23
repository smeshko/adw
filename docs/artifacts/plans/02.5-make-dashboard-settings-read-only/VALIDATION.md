# Validation Summary — 02.5-make-dashboard-settings-read-only

**Rounds:** 3
**Plan status at validation:** draft
**Run on:** 2026-09-23

## Rounds

| Round | Findings | Applied | Deferred | Rejected |
|-------|----------|---------|----------|----------|
| 1     | 3        | 3       | 0        | 0        |
| 2     | 2        | 2       | 0        | 0        |
| 3     | 3        | 3       | 0        | 0        |

Round 3 still produced applies. They were precise fixes, so they were applied under the session's autonomy instruction, and no fourth round was run (see `validation/round-3.md`).

## Applied

### Round 1
- PLAN.md:Scope, Out of Scope, Decisions, Risks; RESEARCH.md:Uncertainty; TASK-001; TASK-003 — Phase values are the effective ones, merged the way `PhaseRunner` merges them. That means the resolved tier's (user/bundled) `enabled`/`input_files`/`llm` under the project file, with phase-specific fields from the project file only. Tests pin the merge. (round-1 #1)
- TASK-004 — `$SCRATCH` is created with `mktemp -d` and cleaned up by a trap. (round-1 #2)
- PLAN.md:Decisions, Acceptance Criteria; TASK-002; TASK-004 — The write-surface guard covers every non-GET/HEAD method, not only POST. (round-1 #3)

### Round 2
- TASK-003; PLAN.md:Scope, Risks — Epic phase 2.8's read-site list now points at `dashboard/settings.py`, not `dashboard/partials.py`. (round-2 #1)
- TASK-004 — The smoke test and screenshots run as one ordered block: hash, start the server, curl, screenshot, hash, stop. The server PID is in the EXIT trap. (round-2 #2)

### Round 3
- TASK-002 — The deletion grep matches only the quoted `"has_project_config"` context key, so `settings.py` can keep using the `ConfigLoader` property. (round-3 #1)
- TASK-001 — A parametrized test shows that user-tier `lint_command`/`doc_mappings`/ship fields are ignored and project values win. (round-3 #2)
- TASK-003 — Phase 2.8 (epic and Linear ADW-24) gains the criterion that the dashboard has no direct phase-config loader after consolidation. (round-3 #3)

## Deferred

None.

## Rejected

None.
