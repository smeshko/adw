# TASK-005: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.1-isolate-test-suite`

## Goal

Confirm the plan is fully implemented and production-ready, and write the PR evidence to `docs/artifacts/plans/01.1-isolate-test-suite/VALIDATION.md`.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] `scripts/preflight.sh` passes with no issues
- [ ] Full test suite passes: `uv run pytest`, green, coverage ≥ 80%. Rerun `test_stats_display_with_real_data` once if it flakes.
- [ ] Module/import boundaries respected: `hooks/runner.py` imports nothing from `adw.executors`
- [ ] **No-touch check, real checkout and real home.** In the worktree, snapshot before and after one full `uv run pytest`, and diff the two. The diff must be empty.
  - `git status --short`, `git branch` and `git worktree list`
  - `ls .adw/runs 2>/dev/null | wc -l` and `find .adw/runs -type f 2>/dev/null | sort | xargs shasum | shasum`
  - `shasum ~/.adw/*`
- [ ] **Timing, back to back.** Build two throwaway clones with the method in `RESEARCH.md` → Useful Commands: one at `cdb2003f` and one at HEAD. Each gets a fake `HOME`, `GIT_*` identity, no `origin`, and the main checkout's `.adw/{project.yaml,runs}`. Run `--durations=15` in each, one after the other. HEAD's pytest time must be ≥ 50 s lower. The prototype went from 216.6 s to 152.0 s.
- [ ] Write `VALIDATION.md` with:
  - the no-touch snapshot diff
  - both `--durations=15` blocks and summary lines
  - the delta
  - the RED/GREEN lines for `test_timeout_kills_hook_children`
  - the empty `grep -rn "ADW_TEST_" src tests`
- [ ] `PLAN.md` acceptance criteria all met, each with its Evidence produced (test output, snapshot diff, durations). No criterion is ticked on "the code looks right".

### Epic update

- [ ] Tick phase 1.1's `### Acceptance criteria` in `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`. The epic-level "full suite runs without touching the checkout or `~/.adw`, and is at least 50 s faster" stays open until the epic closes, but note this phase's measured delta next to it.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.1 --plan 01.1-isolate-test-suite --status done`
- [ ] Update epic 01's row in `docs/artifacts/epics/EPICS.md` to `In progress` once this first phase merges.
