# TASK-005: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: finalize 02.9-logging-on-stdlib`

## Goal

Confirm the plan is fully implemented and production-ready.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] `scripts/preflight.sh` passes with no issues
- [ ] `uv run pytest` passes with coverage ≥ 80%; record the pass/skip counts against the baseline (2982 passed, 5 skipped, 84.77%)
- [ ] Scratch-repo transcripts under the session scratchpad, saved under the plan's `evidence/` for the PR. Run them with this worktree's binary (`/Users/A1E6E98/Developer/Projects/adw/adw-final/.worktrees/adw-25/.venv/bin/adw`, not a bare `adw`, which is the main checkout's `staging` install), with `git init -q`, `HOME` pointed at a scratch dir, and `git config user.name/email` set:
  - `adw run -v --dry-run "x"` (the epic's spelling: "No such option: -v") and `adw -v run --dry-run "x"` (DEBUG lines), with `ADW_MOCK_EXECUTOR=1`
  - a planted-secret run:
    - `adw init --no-interactive`, then set `llm.path` in `.adw/project.yaml` to a scratch `fake-claude` script
    - the script ignores its arguments and prints stream-json: an assistant text block carrying `sk-ant-api03-` + 24 characters, a `Bash` `tool_use` whose command carries `ghp_` + 36 characters, and a `result` line
    - run `adw run --phase plan --no-worktree "Planted secret demo"` without `ADW_MOCK_EXECUTOR`, then save `ls -a .adw/runs/<id>/` (no `live.log.lock`) and the `live.log` excerpt (`[REDACTED]`, UTC stamps, and no secret: `grep -c "sk-ant-api03-\|ghp_" live.log` prints `0`)
- [ ] Grep the evidence files for the username and scratchpad paths before committing, and redact them

### Acceptance-to-evidence matrix (one per `PLAN.md` criterion)

- [ ] **`adw -v run --dry-run "x"` prints DEBUG lines.** `test_verbose_dry_run_prints_debug_lines` passes; the transcript shows `[DEBUG] Input treated as feature string`.
- [ ] **A planted secret in mocked LLM output is `[REDACTED]` in `live.log`.** `test_llm_output_secrets_are_redacted_in_live_log` and `test_llm_stream_is_redacted` pass; the fake-claude run's `live.log` excerpt shows `[REDACTED]`, and the secret count is `0`.
- [ ] **One writer, no file lock.** `test_run_hands_the_one_live_log_handler_to_the_orchestrator`, `test_executor_writes_through_the_given_live_stream` and `test_live_log_needs_no_lock_file` pass; `grep -rn "FileLock\|filelock" src/adw/logging` prints nothing; the run directory listing has no `live.log.lock`.
- [ ] **`logging/` holds only the four files.** `ls src/adw/logging` lists them, and TASK-003's acceptance grep prints nothing.
- [ ] **UTC timestamps.** `test_live_log_timestamps_are_utc` passes; the excerpt's stamps match `date -u` at run time.
- [ ] **Lint and tests pass.** The preflight and full-suite tails above.

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick phase 2.9's `### Acceptance criteria` in `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`. Under the `-v` criterion, add a sub-bullet: "`-v` is a root option: checked as `adw -v run --dry-run "x"` (plan 02.9, Decisions)."
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 02 --phase 2.9 --plan 02.9-logging-on-stdlib --status done`
- [ ] Update the epic's row in `docs/artifacts/epics/EPICS.md` if its status changes (epic 02 stays `In progress`: other phases remain)
