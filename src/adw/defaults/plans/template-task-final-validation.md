# TASK-00N: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for <plan-slug>`

## Goal

Confirm the plan is fully implemented and production-ready.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] Project analyzer/linter passes with no issues
- [ ] Full test suite passes (or every failing-to-run criterion is explicitly listed as CI-pending — see implement-plan's "When CI is the test gate")
- [ ] Module/import boundaries respected
- [ ] Manual smoke test performed
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced (test output, screenshot, log) — no criterion ticked on "the code looks right"

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick this phase's `### Acceptance criteria` in `docs/artifacts/epics/<NN>-*.md`, plus any epic-level criteria this phase satisfies
- [ ] Mark the phase done: `adw plan link <NN> --phase <NN.M> --plan <plan-slug> --status done`
- [ ] Update the epic's row in `docs/artifacts/epics/EPICS.md` (`In progress` after the first phase merges; `Done` when this is the last phase — then tick the remaining epic-level criteria and note any newly-unblocked epics)
