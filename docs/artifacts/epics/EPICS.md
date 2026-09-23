# Implementation Epics

This document tracks the implementation epics for **ADW**. Each epic is a
self-contained unit of functionality; each phase within an epic is sized to fit a
small-to-medium pull request and maps to exactly one plan under
[`../plans/`](../plans/).

## Status legend

| Status | Meaning |
|---|---|
| Planned | Defined but not started |
| Ready for dev | All dependencies met; can be picked up |
| In progress | At least one phase has been merged |
| Done | All phases complete and validated against the acceptance criteria |
| Blocked | Waiting on a prerequisite epic |

## Epic status

| # | Epic | Phases | Dependencies | Status |
|---|------|--------|--------------|--------|
| 1 | [Cleanup: test safety, dead code and bug fixes](./01-cleanup-safety-dead-code-bugs.md) | 10 | — | In progress |
| 2 | [Cleanup: remove inert features and consolidate](./02-cleanup-remove-and-consolidate.md) | 12 | Epic 01 | In progress |
| 3 | [Cleanup: run-loop consolidation and docs](./03-cleanup-run-loop-and-docs.md) | 5 | Epic 02 | Blocked |
| 4 | [Plan-driven runs](./04-plan-driven-runs.md) | 4 | Epic 03 | Blocked |
| 5 | [Plan-workflow phase prompts](./05-plan-workflow-phase-prompts.md) | 8 | Epic 04 | Blocked |
| 6 | [Autonomous landing and the Linear flow](./06-autonomous-landing-linear-flow.md) | 3 | Epic 05 | Blocked |
| 7 | [Run observability from Loop](./07-run-observability.md) | 5 | Epic 03 | Blocked |
| 8 | [Continuous intake](./08-continuous-intake.md) | 4 | Epic 06, Epic 07 | Blocked |

## How to work with these epics

1. Confirm this epic's dependencies are `Done` in the table above.
2. Open the epic file and start with its first phase.
3. Turn a phase into a plan: `create-plan` with `--epic <NN> --phase <NN>.<M>`
   (links the plan to the phase both ways). Then `validate-plan` →
   `implement-plan` → `review-plan` → `create-pr` → `archive-plan`.
4. Each phase lands as its own pull request.
5. The plan's final-validation task ticks the phase + epic-level acceptance
   criteria and updates this table — promote the row to `In progress` after the
   first phase merges, and to `Done` when the last one does.
