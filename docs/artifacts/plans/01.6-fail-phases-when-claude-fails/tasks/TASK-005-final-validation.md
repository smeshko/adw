# TASK-005: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.6-fail-phases-when-claude-fails`

## Goal

Confirm the plan is fully implemented and production-ready, and record the evidence in `VALIDATION.md`.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] `scripts/preflight.sh` passes with no issues
- [ ] The full `uv run pytest` passes with coverage ≥ 80%. Rerun `test_stats_display_with_real_data` once if it flakes (AGENTS.md).
- [ ] Module and import boundaries are respected: `grep -rn "RetryExecutor\|LLMRateLimitError" src` and `grep -rn "timeout: int\|timeout=timeout" src/adw/executors` both return nothing
- [ ] Manual smoke test in a scratch repo, run from the plan checkout. Follow the recipe in `RESEARCH.md` → Useful Commands: scratch `HOME`, fake `bin/claude` that exits 1, committed `.adw/project.yaml` with `worktree.enabled: false`, and `.adw/runs/` gitignored. Run `adw run --phase plan "noop feature"`. Expect:
  - `adw` exits non-zero
  - two yellow `retrying in 1s (2/3)` / `2s (3/3)` lines
  - `calls.log` has 3 lines (the default `max_retries`)
  - `context.json` and the index both have `status failed`
  - the error panel shows `Claude Code exited with code 1: fatal: simulated failure`
- [ ] `PLAN.md` acceptance criteria are all met, each with its evidence produced (test output or transcript). No criterion is ticked on "the code looks right".
- [ ] Write `VALIDATION.md` next to `PLAN.md` with:
  - the smoke-test transcript
  - the B2 regression evidence: `test_fake_claude_exit_fails_run` output, RED at the TASK-001 commit (`DID NOT RAISE`) and GREEN at HEAD
  - `test_mock_executor_fails_twice_then_succeeds` output
  - both grep outputs
  - the pytest summary line with the coverage total

### Epic update

- [ ] Tick phase 1.6's `### Acceptance criteria` in `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`. Leave the epic-level "Bugs B1–B5 … regression test" criterion unticked (it needs every listed bug), but note `test_fake_claude_exit_fails_run` as B2's regression test in `VALIDATION.md`.
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.6 --plan 01.6-fail-phases-when-claude-fails --status done`
- [ ] Update the epic's row in `docs/artifacts/epics/EPICS.md` to `In progress` if it isn't already. Epic 01 has phases left after 1.6.
