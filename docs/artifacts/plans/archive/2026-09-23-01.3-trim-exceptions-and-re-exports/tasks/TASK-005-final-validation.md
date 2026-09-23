# TASK-005: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.3-trim-exceptions-and-re-exports`

## Goal

Confirm the plan is fully implemented, and record the evidence in `VALIDATION.md` for the PR.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked.
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest` passes with coverage at or above 80%. Record the summary line and the coverage total.
- [ ] From an empty scratch directory, run `adw status nonexistent-id` and `adw resume` against the final tree (`uv run --project <worktree> adw …`). `diff` each against its baseline (`before-status.txt`, `before-resume.txt`): the panels and exit codes match.
- [ ] `diff` `adw --help` against `before-help.txt`: empty.
- [ ] Re-run the `PLAN.md` greps: the `^class` list, the deleted-name grep, the `to_dict` grep and the package-import grep.
- [ ] Record `find src -name '*.py' | xargs wc -l | tail -1` against the 42,085 baseline.
- [ ] Write `VALIDATION.md` next to `PLAN.md` with every evidence block above, including the before and after CLI panels.
- [ ] Every `PLAN.md` acceptance criterion is met, each with its evidence produced. No criterion is ticked on "the code looks right".

### Epic update

- [ ] Tick phase 1.3's `### Acceptance criteria` in `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`, with evidence notes in the style of the done phases. Add the phase 1.3 line delta to the epic-level `src/adw` LOC criterion.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.3 --plan 01.3-trim-exceptions-and-re-exports --status done`
- [ ] Phase 1.3 is the last open phase of Epic 01. Tick the epic-level criteria that the recorded evidence now meets, set the epic file's `Status:` to `done`, and set the Epic 01 row in `docs/artifacts/epics/EPICS.md` to `Done`. Epic 02 is already `In progress`, so no row needs unblocking.

## Notes

- Strip `uv run`'s venv-creation lines from captured output before diffing.
