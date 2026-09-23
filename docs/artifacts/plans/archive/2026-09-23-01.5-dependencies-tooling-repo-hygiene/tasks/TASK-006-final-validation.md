# TASK-006: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.5-dependencies-tooling-repo-hygiene`

## Goal

Confirm the plan is fully implemented and production-ready. Record the evidence in `VALIDATION.md` for the PR.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked.
- [ ] `scripts/preflight.sh` passes, and its output shows the `tests/` checks.
- [ ] `uv run pytest` passes with coverage at or above 80%. Record the summary line and the coverage total.
- [ ] Clean-clone check:
  - `git clone -q /Users/A1E6E98/Developer/Projects/adw/adw-final/.worktrees/adw-11 "$S/clean-clone"`, then `git -C "$S/clean-clone" checkout feature/adw-11`
  - `uv sync --locked` and `scripts/preflight.sh` inside it
  - record the transcript
- [ ] Re-run each TASK-001–005 evidence command against the final tree: the `uv.lock` grep, the dashboard `--reload` check, the collect-only count, the tag grep over `src/adw tests`, both `--help` greps, and the isolated install's `which adw && adw --version`.
- [ ] Main-checkout housekeeping, outside git, with no commit. In `/Users/A1E6E98/Developer/Projects/adw/adw-final`:
  - list the `__pycache__`-only directories under `src/` and `tests/` (loop in the Notes)
  - delete them: `rm -rf` each directory
  - then delete the emptied parents `src/adw/validation` and `tests/unit/validation`
  - re-run the loop and confirm it prints nothing
  - record the before and after listings
- [ ] Write `VALIDATION.md` next to `PLAN.md` with every evidence block above.
- [ ] Every `PLAN.md` acceptance criterion is met, each with its evidence produced (command output or log). No criterion is ticked on "the code looks right".

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick phase 1.5's `### Acceptance criteria` in `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`, adding evidence notes in the style of the done phases. Add the phase 1.5 line delta to the epic-level `src/adw` LOC criterion if it moved.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.5 --plan 01.5-dependencies-tooling-repo-hygiene --status done`
- [ ] The Epic 01 row in `docs/artifacts/epics/EPICS.md` stays `In progress`, because phases 1.3, 1.9 and 1.10 are still open.

## Notes

- `$S` is the session scratchpad directory.
- The `__pycache__`-only loop (use `find`, not `ls`, whose colour codes break matching):

  ```bash
  for d in $(find src tests -type d ! -name __pycache__ ! -path '*/__pycache__/*'); do
    [ "$(find "$d" -mindepth 1 -maxdepth 1 ! -name __pycache__ | wc -l)" -eq 0 ] && echo "$d"
  done; true
  ```
- Switching the real install happens after merge, not here. `PLAN.md` → Post-merge lists the three commands. Put them in the PR description's follow-up section too.
