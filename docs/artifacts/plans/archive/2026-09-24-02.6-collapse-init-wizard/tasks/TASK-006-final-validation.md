# TASK-006: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: finalize 02.6-collapse-init-wizard`

## Goal

Confirm the plan is fully implemented and production-ready.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] `scripts/preflight.sh` passes with no issues
- [ ] `uv run pytest` passes with coverage ≥ 80%; record the pass/skip counts against the baseline (3354 passed, 5 skipped, 84.81%)
- [ ] Scratch-repo transcripts, run with this worktree's binary (`/Users/A1E6E98/Developer/Projects/adw/adw-final/.worktrees/adw-22/.venv/bin/adw`, not a bare `adw`, which is the main checkout's `staging` install) under the session scratchpad with `git init -q` and `HOME` pointed at a scratch dir, saved under the plan's `evidence/` for the PR. Feed the decline transcript exact answers (one line per prompt, `n` at "Create configuration?"); send SIGINT to the `.venv/bin/adw` process directly, not through `uv run`: accept-defaults then `adw validate`; decline at the summary with `echo $?` and `ls -a`; SIGINT at a prompt with its exit code and `ls -a`

### Acceptance-to-evidence matrix (one per `PLAN.md` criterion)

- [ ] **Accept defaults → files `adw validate` accepts.** `test_accept_defaults_writes_files_that_validate` passes; the accept transcript shows `Configuration written` once and `adw validate` reports `0 errors`.
- [ ] **Decline at the summary writes nothing and exits non-zero.** `test_decline_at_summary_writes_nothing` passes; the decline transcript shows `Nothing was written`, `exit=1` and no `.adw`.
- [ ] **A write failure says so and exits non-zero.** `test_write_failure_exits_non_zero` passes (exit 1, the error text `disk full`, `No files were written`, no `Configuration written`).
- [ ] **Ctrl+C exits 130 and cannot interrupt the write.** `test_write_holds_off_ctrl_c` passes; the SIGINT transcript shows `exit=130` and no `.adw`.
- [ ] **The acceptance grep is empty.** `grep -rn -I --exclude-dir=__pycache__ "WizardFlowController\|WizardState\|StepHandler\|nav_prompt_ask" src tests` prints nothing, and so do the per-task greps: `grep -rn -I --exclude-dir=__pycache__ "LANGUAGE_MARKERS\|DEFAULT_TEST_COMMANDS\|detect_language\|detect_test_command\|run_ship_step\|ShipStepHandler\|run_retry_step\|RetryStepHandler\|llm_retry\|retry_custom\|nav_confirm_ask\|WizardStep\|STEP_TITLES\|NavigationError" src tests`.
- [ ] **No retry questions, no ship build command, no back/cancel promise.** The accept transcript's headers run `Step 1/7` … `Step 7/7` with no `LLM Retry` step, and it has no `b - Go back` or `c - Cancel wizard` text; `test_ship_phase_asks_only_version_bump_and_publish` passes; `test_retry_defaults_are_commented_and_round_trip` passes. A customised ship phase still serialises its commands: `test_customized_ship_commands_reach_ship_config` passes.
- [ ] **Detection matches `ProjectTypeDetector`.** `test_detected_defaults_match_project_type_detector` and `test_chosen_language_sets_test_command_default` pass.
- [ ] **Lint and tests pass.** The preflight and full-suite tails above.

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick this phase's `### Acceptance criteria` in `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`, plus any epic-level criteria this phase satisfies
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 02 --phase 2.6 --plan 02.6-collapse-init-wizard --status done`
- [ ] Update the epic's row in `docs/artifacts/epics/EPICS.md` if its status changes (epic 02 stays `In progress`: phases 2.3 and 2.7–2.12 remain)
