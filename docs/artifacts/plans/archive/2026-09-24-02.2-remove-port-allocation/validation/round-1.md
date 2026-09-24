# Adversarial Validation — Round 1

**Run:** 2026-09-24 03:58 UTC
**Plan:** 02.2-remove-port-allocation
**Status at start:** draft
**Reviewer:** Codex (`/codex-local:adversarial-review --wait --scope working-tree`)

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

No-ship: the plan contains impossible acceptance gates, a smoke test that cannot produce its promised evidence, and a wizard task that leaves tests failing while relying on prohibited test shapes.

Findings:
- [medium] Legacy-config test makes the required empty grep impossible (docs/artifacts/plans/02.2-remove-port-allocation/tasks/TASK-005-drop-worktreeconfig-port-range-and-keep-old-configs-loading.md:29-38)
  TASK-005 requires a compatibility test containing `port_range`, `backend_start`, and `frontend_start`, then requires those strings to be absent from all of `src tests`. The proposed RED assertion, `not hasattr(..., "port_range")`, also contradicts RESEARCH.md's rule against tests that merely assert an attribute is gone. Consequently TASK-005 and final validation cannot both pass, and the test demonstrates implementation shape rather than meaningful compatibility behavior.
  Recommendation: Apply — use a formerly invalid legacy range to prove the obsolete key is ignored while `max_concurrent` survives, remove the `hasattr` assertion, and restrict production-removal greps to `src` or explicitly exclude the compatibility fixture. Change PLAN.md, RESEARCH.md, TASK-005, and TASK-006.
- [medium] Runtime smoke test cannot produce the specified concurrency evidence (docs/artifacts/plans/02.2-remove-port-allocation/tasks/TASK-006-final-validation.md:34-36)
  The hand-written lock instructions omit the required JSON `run_id` key. Current `get_active_runs()` reads `data["run_id"]`; a missing key is treated as corruption and the lock is deleted, so the subsequent run may proceed instead of being refused. Even with a valid lock, the CLI catches `ADWError` and prints only `e.message`, not `e.code`, so its transcript cannot contain the required `MAX_CONCURRENT_REACHED` token.
  Recommendation: Apply — specify the complete lock JSON including `run_id`, and expect non-zero exit plus `Maximum concurrent runs reached (1)` from the CLI; retain the existing manager unit test as evidence for the exact error code. Change TASK-001, TASK-006, and PLAN.md.
- [medium] Wizard task neither keeps the suite green nor follows the test ADR (docs/artifacts/plans/02.2-remove-port-allocation/tasks/TASK-004-remove-the-ports-step-from-the-init-wizard.md:21-45)
  TASK-004 plans to update `test_step_values_exist`, an enum-membership test explicitly prohibited by ADR-001, but misses `test_step_sequence_defined`, whose current hard-coded length is 10. Removing the ports step makes it 9, so the promised green partial suite fails even if every listed edit is performed. The cited acceptance evidence also verifies enum shape rather than the observable claim that the wizard asks no port questions.
  Recommendation: Apply — delete the enum existence/count tests and replace the acceptance evidence with controller or wizard behavior showing that no ports handler executes, while retaining generated-YAML verification. Change TASK-004 and PLAN.md.

Next steps:
- Repair the compatibility test and grep scopes before implementation.
- Correct the lock fixture and CLI-output expectations in final validation.
- Replace wizard enum-shape assertions with behavioral coverage, then recheck task-level green sequencing.

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | The legacy-config test must contain `port_range`, which contradicts the "grep returns nothing" gates, and its `hasattr` assert only checks that an attribute is gone | med | apply | Confirmed. The epic's grep and its back-compat criterion conflict literally. Keep a regression test built on a formerly *invalid* range (overlapping starts), which fails RED today on the overlap validator, and document it as the grep's one allowed hit | PLAN.md:Acceptance Criteria, PLAN.md:Decisions, RESEARCH.md:Constraints, TASK-005, TASK-006 |
| 2 | The smoke-test lock JSON omits `run_id`, so the lock is deleted as corrupt; the CLI prints `e.message`, not `e.code` | med | apply | Confirmed: `get_active_runs` reads `data["run_id"]` and drops the lock on `KeyError`, and `cli/app.py` prints only `e.message`/`e.suggestion`. Spell out the full lock JSON, and expect the message plus a non-zero exit, with the code coming from the unit test | TASK-001, TASK-006, PLAN.md:Acceptance Criteria |
| 3 | TASK-004 misses `test_step_sequence_defined`'s hard-coded `len == 10`, and it evidences the change with an enum-shape test that ADR-001 lists as waste | med | apply | Confirmed. Drop the count assert (an ADR-001 "enum count" test that every removal phase must bump), and make the behavioural RED `test_run_marks_steps_completed` assert the controller run never visits `ports`. Keep `test_step_values_exist`, trimmed by one line, so it still merges cleanly with 2.3's one-line edit | TASK-004, PLAN.md:Acceptance Criteria |
