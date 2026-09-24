# Validation Summary — 02.6-collapse-init-wizard

**Rounds:** 3
**Plan status at validation:** draft
**Run on:** 2026-09-24

## Rounds

| Round | Reviewer | Findings | Applied | Deferred | Rejected |
|-------|----------|----------|---------|----------|----------|
| 1     | Codex    | 5        | 5       | 0        | 0        |
| 2     | subagent | 7        | 7       | 0        | 0        |
| 3     | subagent | 4        | 4       | 0        | 0        |

Codex ran round 1. It hit its usage limit partway through round 2, so rounds 2 and 3 ran with a clean `general-purpose` subagent, which had the same adversarial framing and focus text. Round 3 still produced applies. They were local test-instruction and evidence fixes, not design changes, so they were applied and validation stopped there without a fourth round (act-and-stop).

## Applied

### Round 1
- PLAN.md:Scope, Decisions, Acceptance Criteria; TASK-005; TASK-006 — Ctrl+C is held off (`SIG_IGN`) while the files are written and the project registered. Before, the `SystemExit` from `init`'s SIGINT handler skipped `atomic_write_config`'s `OSError` rollback and could leave files behind under a "No files created" message (round-1 #1)
- TASK-001 — Narrow the detected language with `or "unknown"`, since `get_defaults` returns `str | None` under `mypy --strict` (round-1 #2)
- TASK-004 — The step list is typed `Callable[[Console], dict[str, Any]]`, and basics is adapted with `lambda c: run_basics_step(c, root)` (round-1 #3)
- TASK-004, PLAN.md:Tasks — TASK-004 depends on TASK-001 too (round-1 #4)
- TASK-006; TASK-004 — TASK-006 is now an acceptance-to-evidence matrix, one row per PLAN.md criterion. It adds `test_customized_ship_commands_reach_ship_config`, which guards removing the dead `ship` merge (round-1 #5)

### Round 2
- RESEARCH.md, TASK-005, TASK-006 — Transcripts call this worktree's `.venv/bin/adw`. A bare `adw` is the main checkout's editable install, which runs `staging` (round-2 #1)
- TASK-004 — Keep `test_accepted_defaults_yield_ship_mapping`, the only B17 regression test, and `test_full_flow_returns_complete_config`. Delete only the state-storage tests (round-2 #2)
- TASK-001 — The detection test also asserts that the confirmation prompt was shown, so the `requirements.txt` case is RED today (round-2 #3)
- TASK-001, PLAN.md, RESEARCH.md — `ProjectTypeDetector.MARKERS` gains `setup.cfg` and `build.gradle.kts`, so Kotlin-DSL Gradle projects are still detected as java (round-2 #4)
- TASK-005, PLAN.md:Decisions — The held block also covers the success message, and the remaining window is stated precisely (round-2 #5)
- PLAN.md, TASK-004, TASK-005 — Factual fixes:
  - end of input already exits 1 with Typer's `Aborted.`; the change adds an honest message
  - the `c\n` note is corrected
  - the write-failure text is a change, not a keep
  - the decline test patches `_prompt_confirmation`, not Rich's shared `Confirm.ask`

  (round-2 #6)
- TASK-005, TASK-006, PLAN.md:Risks — The write-failure test asserts the error text. The accept test asserts the `Step 1/7` … `Step 7/7` headers in order and the absence of `b - Go back` and `c - Cancel wizard` (round-2 #7)

### Round 3
- TASK-001 — The detection assert compares `Text.from_markup(question).plain`, because the prompt carries Rich markup. Round 2's edit had introduced this defect (round-3 #1)
- TASK-005 — The hold-off test enables dashboard registration and asserts exactly three `SIG_IGN` recordings (round-3 #2)
- TASK-005 — RED records the accept and hold-off failures too (round-3 #3)
- PLAN.md, TASK-006 — The acceptance greps use `-I --exclude-dir=__pycache__`, so stale `.pyc` files from `git rm` don't match (round-3 #4)

## Deferred

- None.

## Rejected

- None.
