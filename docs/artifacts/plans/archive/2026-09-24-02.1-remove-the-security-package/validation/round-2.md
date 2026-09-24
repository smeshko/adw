# Adversarial Validation — Round 2

**Run:** 2026-09-24 04:20 UTC
**Plan:** 2026-09-24-02.1-remove-the-security-package
**Status at start:** draft
**Reviewer:** Codex (`/codex-local:adversarial-review --wait --scope working-tree`)
**Prior rounds in scope:** validation/round-1.md

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

```
# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

Do not ship the plan yet: round-1’s bytecode fix stops short of the epic criterion, and final validation contains a self-dependency.

Findings:
- [medium] Round-1 grep remediation does not cover the epic criterion (docs/artifacts/plans/2026-09-24-02.1-remove-the-security-package/tasks/TASK-004-final-validation.md:24-27)
  TASK-004 requires marking the phase acceptance criteria complete, but the referenced epic still prescribes `grep -rn ... src tests` without excluding `__pycache__`. After TASK-001 deletes the tracked security package, its ignored bytecode can remain and make that exact criterion fail. Reusing the corrected PLAN grep would not constitute evidence for the unchanged epic command.
  Recommendation: Update the phase criterion in `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md` to use `--exclude-dir=__pycache__`, and require TASK-004 to execute that corrected command before ticking it.
- [medium] Final-validation task depends on its own completion (docs/artifacts/plans/2026-09-24-02.1-remove-the-security-package/tasks/TASK-004-final-validation.md:12)
  The first step requires every PLAN task checkbox to be ticked, which includes TASK-004 itself. Under the plan’s stated task-state convention, TASK-004 cannot be marked complete until its validation steps finish, so strict execution either deadlocks or records the task as complete before its evidence exists.
  Recommendation: Change this step to require all prior task checkboxes (TASK-001 through TASK-003) to be ticked; mark TASK-004 complete only after validation and evidence generation finish.

Next steps:
- Fix the epic’s grep criterion and the TASK-004 self-dependency, then rerun the second-pass review.
```

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | The epic's literal phase-2.1 grep can still hit stale bytecode, so ticking it needs evidence from that exact command | med | apply | Real gap. Applied as a variant: TASK-004 clears `__pycache__` under `src` and `tests`, then runs the epic's command verbatim. Editing only 2.1's criterion would leave phases 2.2–2.12, which use the same `grep -rn … src tests` shape, inconsistent; and a clean checkout (CI) has no bytecode, so the epic command is correct as a spec. | `TASK-004` |
| 2 | TASK-004's first step requires all task checkboxes ticked, including its own | med | apply | Real self-reference from the stamped template. The step now requires TASK-001 to TASK-003 and says TASK-004 is ticked only after its evidence exists. | `TASK-004` |
