# TASK-006: Document adw.plans for agents

Depends on: TASK-001, TASK-002, TASK-003, TASK-004, TASK-005
Suggested commit: `docs(agents): document adw.plans and its golden test`

## Goal

An agent that changes the plan format knows where ADW's copy lives, and knows that the templates and the golden tree move together.

## Files

- `AGENTS.md` gets one bullet under `## Architecture notes`. It says:
  - `adw.plans` (`src/adw/plans/`) is ADW's copy of the plan skills' directory format, and `adw plan` exposes it to prompts.
  - `src/adw/defaults/plans/` copies the skills' templates. The one deliberate change is that final validation calls `adw plan link`.
  - When a plan skill's script or template changes, update the copy and regenerate `tests/fixtures/plans/golden/` with the commands in its README.

## Acceptance

- [ ] The bullet is in `AGENTS.md`, follows the `writing-for-agents` skill, and every path it names exists.

Evidence: `git diff AGENTS.md`, and `ls` of each named path.

## Steps

- [ ] Load the `writing-for-agents` skill.
- [ ] Add the bullet.
- [ ] Check each path with `ls`.
