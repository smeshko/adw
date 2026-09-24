# Adversarial Validation — Round 2

**Run:** 2026-09-24 04:03 UTC
**Plan:** 02.2-remove-port-allocation
**Status at start:** draft
**Reviewer:** Codex (`/codex-local:adversarial-review --wait --scope working-tree`)
**Prior rounds in scope:** validation/round-1.md

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

No-ship: round 1’s grep fix remains internally impossible, and the plan overclaims concurrency enforcement without testing the existing start/register race.

Findings:
- [medium] The revised grep gate still cannot produce its promised single hit (docs/artifacts/plans/02.2-remove-port-allocation/tasks/TASK-005-drop-worktreeconfig-port-range-and-keep-old-configs-loading.md:29-38)
  The planned test is named `test_legacy_port_range_is_ignored`, its YAML contains `port_range`, and the instructions explicitly require a comment containing `port_range`. The final grep will therefore report at least three matching lines, contradicting PLAN.md’s “one hit” decision and TASK-006’s final gate. Round 1’s applied edit changed the exception but did not make it executable as written.
  Recommendation: Define the gate by file rather than match count, such as asserting no matches in `src` and that `rg -l` over `tests` returns only `tests/unit/models/test_config.py`; update PLAN.md, TASK-005, TASK-006, and the epic note consistently.
- [medium] The max-concurrent evidence misses the non-atomic start race (docs/artifacts/plans/02.2-remove-port-allocation/PLAN.md:77-79)
  The plan claims `max_concurrent` remains enforced, but its unit and smoke evidence only tests a pre-existing live lock. In the current lifecycle, `check_can_start_or_raise()` runs before worktree creation and `register_run()` occurs afterward, with no atomic reservation; two simultaneous starts can both observe capacity and both proceed. The proposed validation therefore cannot support the stated invariant under concurrency and can hide resource-limit violations.
  Recommendation: Either narrow the criterion explicitly to preserving sequential/live-lock behavior, or add an atomic reservation mechanism and a concurrent-start test proving only one run crosses a limit of one.
- [low] Round 1’s ADR finding was only partially applied (docs/artifacts/plans/02.2-remove-port-allocation/tasks/TASK-004-remove-the-ports-step-from-the-init-wizard.md:21-24)
  TASK-004 deliberately retains and edits `test_step_values_exist`, even though that test compares the complete enum membership list and ADR-001 explicitly classifies enum-existence tests as waste to eliminate. The triage marked the finding applied, but preserving this test for merge convenience leaves the documented violation and recurring cross-phase churn intact.
  Recommendation: Delete `test_step_values_exist` and rely on the planned controller-run behavior plus generated-YAML assertions; do not retain a prohibited test solely to minimize a neighboring branch diff.

Next steps:
- Repair the grep contract so its expected output is mechanically attainable.
- Clarify or prove the concurrency guarantee before treating final validation as complete.
- Finish applying the round-1 ADR correction by removing the enum-membership test.

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | The "one hit" grep exception is unattainable: the test name, comment and YAML all contain `port_range` | med | apply | Confirmed; round 1 counted hits where it meant files. The gate is now per file: `src` is empty, and `grep -rln … tests` lists only `tests/unit/models/test_config.py` | PLAN.md:Acceptance Criteria, PLAN.md:Decisions, TASK-005, TASK-006 |
| 2 | The `max_concurrent` evidence ignores the start/register race: two simultaneous starts can both pass the check | med | defer | Real, but it predates this phase and doesn't involve ports. The epic's criterion ("a second run past the limit is refused") is sequential, and an atomic reservation is new behaviour. The criterion wording is narrowed to sequential starts, and the race is recorded in Out of Scope and filed as ADW-64 | PLAN.md:Acceptance Criteria, PLAN.md:Out of Scope (wording only) |
| 3 | Round-1 #3 was only partly applied: `test_step_values_exist`, an ADR-001 enum-membership test, is kept | low | reject | Phase 2.6 deletes `WizardStep`, and this test with it. Culling pre-existing tests beyond the port lines is outside this phase. The one-line trim follows the plan's explicit Risk mitigation (line-local edits) for the parallel 2.1 and 2.3 branches, which edit the same list. The count assert was the line that broke on every removal, and it is gone | |
