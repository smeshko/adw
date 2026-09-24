# TASK-007: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 04.1-adw-plans-module`

## Goal

Confirm the plan is fully implemented and production-ready.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] `scripts/preflight.sh` passes
- [ ] `uv run pytest` passes with coverage ≥ 80%; record the tail
- [ ] Module boundaries: `adw.plans` imports nothing from `adw.cli`, and runs no subprocess (`grep -rn "subprocess\|adw.cli" src/adw/plans` is empty)
- [ ] `grep -rn "\.claude/skills" src/adw` returns nothing
- [ ] Smoke test, in a scratch `git init` repo under the session scratchpad, using the worktree's `.venv/bin/adw`. Run `adw plan init` → `add-task` ×2 → `add-final` → `tasks` → `list`, with an archived plan present so `list` shows it is excluded. Save the transcript to `docs/artifacts/plans/04.1-adw-plans-module/evidence/scratch-repo-transcript.txt`, with the scratchpad path and username redacted (grep the file for the username before committing)
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced (test output, transcript, grep) — no criterion ticked on "the code looks right"

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick phase 4.1's `### Acceptance criteria` in `docs/artifacts/epics/04-plan-driven-runs.md`
- [ ] Mark the phase done with this phase's own command: `.venv/bin/adw plan link 04 --phase 4.1 --plan 04.1-adw-plans-module --status done`
- [ ] Update Epic 4's row in `docs/artifacts/epics/EPICS.md` to `In progress` (its first phase merges with this PR)
