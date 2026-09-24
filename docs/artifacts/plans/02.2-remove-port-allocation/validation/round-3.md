# Adversarial Validation — Round 3

**Run:** 2026-09-24 04:09 UTC
**Plan:** 02.2-remove-port-allocation
**Status at start:** draft
**Reviewer:** Codex (`/codex-local:adversarial-review --wait --scope working-tree`)
**Prior rounds in scope:** validation/round-1.md, validation/round-2.md

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

No-ship: the revised plan still has a broken task dependency, leaves a guaranteed test failure in TASK-001, and rejects a directly applicable repository standard without adequate justification.

Findings:
- [high] TASK-003 deletes a module still required by TASK-004 (docs/artifacts/plans/02.2-remove-port-allocation/tasks/TASK-003-delete-portallocator-portallocation-and-the-port-error-code.md:3)
  TASK-003 depends only on TASK-002 and deletes `adw.worktree.ports`, but the still-present wizard imports three constants from that module through `cli/wizard/ports.py`. Those wizard files are not removed until TASK-004. Executing tasks in the documented order therefore breaks imports, makes TASK-003's grep non-empty, and prevents its tests/preflight from passing, contradicting PLAN.md's claim that every commit remains green.
  Recommendation: Make TASK-003 depend on TASK-004, or reorder/split the deletions so `cli/wizard/ports.py` and its exports disappear before `worktree/ports.py`.
- [medium] TASK-001 leaves an assertion for the removed Ports cell (docs/artifacts/plans/02.2-remove-port-allocation/tasks/TASK-001-drop-port-fields-from-active-runs-and-adw-list-running.md:22-26)
  The task removes port arguments and replaces the JSON assertions, but it does not instruct removal of the existing `assert "9100/9200" in captured.out` at `tests/unit/cli/test_list_running.py:72`. Removing the table's Ports cell makes that assertion fail, so the promised GREEN partial suite cannot pass as written.
  Recommendation: Explicitly remove the stale rendered-port assertion and retain assertions for the run ID, capacity title, worktree, and absence of the Ports column.
- [low] Round-2 rejection preserves a prohibited enum-existence test (docs/artifacts/plans/02.2-remove-port-allocation/tasks/TASK-004-remove-the-ports-step-from-the-init-wizard.md:21-24)
  TASK-004 deliberately edits rather than deletes `test_step_values_exist`, which compares the complete `WizardStep` membership list. ADR-001 explicitly categorizes such enum-existence tests as waste. The rejection's scope and merge-convenience rationale is unpersuasive because this phase already changes that exact test, and the new controller-run and generated-YAML tests provide behavioral coverage.
  Recommendation: Delete `test_step_values_exist` in TASK-004 instead of trimming its expected list.

Next steps:
- Repair TASK-003's dependency/order and re-evaluate every task boundary for a green commit.
- Add removal of the stale `9100/9200` assertion to TASK-001.
- Apply the ADR-001 finding by deleting `test_step_values_exist`.

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | TASK-003 deletes `adw.worktree.ports` while `cli/wizard/ports.py` still imports three constants from it; that file is deleted only in TASK-004 | high | apply | Confirmed (`cli/wizard/ports.py:16-18`). TASK-003 now depends on TASK-004 too, and the `## Tasks` list runs TASK-004 before TASK-003 | TASK-003, PLAN.md:Tasks, PLAN.md:Decisions |
| 2 | TASK-001 misses `assert "9100/9200" in captured.out` (`test_list_running.py:72`), which breaks once the cell goes | med | apply | Confirmed. Its removal is now listed, and the run-id and capacity-title asserts are kept | TASK-001 |
| 3 | Round-2 #3's rejection keeps an ADR-001 enum-existence test | low | apply | Reversing round-2 #3. Deleting the count assert already means `test_flow.py` conflicts for 2.1 and 2.3 when they rebase, so trimming the list saves no merge cost. Delete `test_step_values_exist`, and note how to resolve the conflict | TASK-004 |

Round 3 still produced `apply` rows. Per the protocol this goes to the user, who asked for full autonomy on this run. All three are local corrections (one dependency edge and two test edits), not structural defects, so they were applied and validation stops here (act-and-stop). No fourth round.
