# TASK-007: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.4-cut-test-waste`

## Goal

Confirm the plan is fully implemented and write the PR evidence to `docs/artifacts/plans/01.4-cut-test-waste/VALIDATION.md`.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked.
- [ ] `scripts/preflight.sh`, `uv run ruff check tests/` and `uv run ruff format --check tests/` pass.
- [ ] Full suite: `uv run pytest` is green with coverage ≥ 80 %. Compare the `TOTAL` line with the 84.33 % baseline, and explain any drop larger than 0.1 pt. Rerun `test_stats_display_with_real_data` once if it flakes.
- [ ] No `src/` file changed: `git diff --stat staging... -- src/` is empty.
- [ ] **Count.** `uv run pytest --collect-only -q | tail -1` at HEAD vs 4,296. The drop must be ≥ 150; the expected figure is 4,124, a drop of 172.
- [ ] **Placeholders.**
  - The pass-only AST scan (`RESEARCH.md` → Useful Commands) prints `total 0`.
  - `grep -rn "^\s*pass$" tests/unit` hits only the stub-class and `except` lines listed in `RESEARCH.md`. Line numbers may shift; confirm each remaining hit sits outside a test function body.
- [ ] **Fixtures.** The duplicate-fixture scan shows:
  - one `git_repo`
  - two `executor`
  - `sample_context 2b1f6c` ×2
- [ ] **No-touch check** (from phase 1.1): `git status --short`, `git branch` and `git worktree list` are unchanged around the full run. The root `git_repo` now serves 4 more files.
- [ ] Write `VALIDATION.md` with:
  - the collect-only lines before (4,296) and after
  - the full-run summary and `TOTAL` coverage lines
  - the TASK-001 RED output (both mutations)
  - the AST scan and grep output
  - the fixture-scan output
  - the `claude_code.py` coverage comparison from TASK-005
- [ ] `PLAN.md` acceptance criteria all met, each with its evidence produced. No criterion is ticked on "the code looks right".

### Epic update

- [ ] Tick phase 1.4's `### Acceptance criteria` in `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.4 --plan 01.4-cut-test-waste --status done`
- [ ] Epic 01's row in `docs/artifacts/epics/EPICS.md` is already `In progress` once phase 1.1 merges; set it if it isn't. This isn't the last phase, so it doesn't go to `Done`.
