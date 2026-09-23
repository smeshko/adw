# TASK-005: Strip planning tags from tests

Depends on: TASK-004
Suggested commit: `test: strip planning-ticket tags from test comments and docstrings`

## Goal

No comment, docstring or message in `tests` cites a Story, ISS, Epic, UX, FR, NFR or AC tag. No test changes behaviour, and the collected count is unchanged.

## Files

With TASK-004's `P='Story [0-9]|ISS-[0-9]|Epic [0-9]|\bUX-[A-Z0-9]|\bN?FR-?[0-9]+\b|\bAC ?#?[0-9]+\b|\bAC:'`, it matches 227 lines in 67 files: `git grep -nP "$P" -- tests`.

- Densest files:
  - `unit/core/test_orchestrator.py` (30)
  - `unit/core/test_phase_runner.py` (17)
  - `unit/dashboard/test_llm_log_integration.py` (11)
  - `unit/cli/wizard/test_summary.py` (10)
  - `integration/worktree/test_worktree_cleanup_integration.py` (10)
  - `integration/cli/test_progress_integration.py` (10)
  - `unit/worktree/test_manager.py` (9)
- The one runtime string: `integration/cli/test_run_integration.py:107`, `msg = f"Startup time {elapsed:.2f}s exceeds NFR1 requirement of 2s"` → `f"Startup time {elapsed:.2f}s exceeds the 2 s limit"`.
- Section-header comments in `unit/dashboard/test_llm_log_integration.py`, such as `# ── AC: LLM Interaction Summary (FR25) ──…`, become `# ── LLM Interaction Summary ──…`. Keep the rule length visually consistent.
- Bare trailing tag comments go entirely: `worktree_config=WorktreeConfig(enabled=False),  # ISS-025` in `integration/cli/test_progress_integration.py` (4×) and `integration/core/test_orchestrator_integration.py`. Where the reason isn't obvious, replace the tag with it: `# worktree creation fails outside a git repo`.
- Docstrings that open with a tag (`Story 9.3 AC2: Given …`, `Story UX-FIX-ISS-001 Task 3: …`, `Per AC: Given …`) keep only the Given/When/Then or the behaviour statement.

Leave alone:
- the audit bug IDs `(B1)`–`(B21)` in regression-test docstrings
- the run-id literal `01HQTEST_ISS008_INTEGRATION`
- test-data IDs such as `ENG-42` and `RULE-123`

## Acceptance

- [ ] `git grep -nP "$P" -- src/adw tests` returns nothing.
- [ ] `git grep -nP '\(B[0-9]{1,2}\)' -- tests | wc -l` is unchanged from before the task. The audit IDs survive.
- [ ] The TASK-004 AST check run on `tests` reports only `tests/integration/cli/test_run_integration.py`.
- [ ] `uv run pytest --collect-only -q | tail -1` gives the same count before and after.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage at or above 80%.

Evidence:
- the empty grep
- both `(Bn)` counts
- the AST-check output
- both collect-only lines
- the pytest summary line

## Steps

- [ ] Record the baselines: the collect-only line, the `(Bn)` count, and `git grep -lP "$P" -- tests > "$S/test-tag-files.txt"`.
- [ ] Edit the listed files one directory at a time (`unit/core`, `unit/cli`, `unit/dashboard`, `integration`, then the rest), applying the tag-rewrite rule.
- [ ] Run the grep, the `(Bn)` count, the AST check (`uv run python "$S/ast_check.py" tests`) and collect-only.
- [ ] Run `scripts/preflight.sh`, then `uv run pytest`.

## Notes

- `tests/integration/cli/test_run_integration.py::…startup time…` is a wall-clock check. Only its message changes, not its threshold.
- If `$S/ast_check.py` from TASK-004 is gone, recreate it from TASK-004's Notes.
