# TASK-007: Final Validation

Depends on: all prior tasks
Suggested commit: `chore: final validation for 01.9-hook-config-and-phase-hook-scripts`

## Goal

Confirm the plan is fully implemented and production-ready, and record the evidence in `VALIDATION.md` next to `PLAN.md`.

## Steps

- [ ] All task checkboxes in `PLAN.md` are ticked
- [ ] `scripts/preflight.sh` passes (ruff, format, mypy `--strict`)
- [ ] `uv run pytest` passes with coverage ≥ 80%; record the summary line and coverage total. If `test_stats_display_with_real_data` fails, rerun it once (known flake).
- [ ] No-touch snapshot: record the following before and after the full run, then diff the two:
  - `git status --short`
  - `git branch`
  - `git worktree list`
  - `ls .adw/runs | wc -l`

  The diff must be empty. Run start now calls git, so this is the check that no test's project root resolved to the checkout.
- [ ] `grep -rn "python3 -c" src/adw/defaults` returns nothing, and so does `grep -rn "ADW_PR_NUMBER\|ADW_TASK_ID\|ship_status\|task_update_request" src tests`.
- [ ] Manual 5 s/10 s hook timeout, in a scratch repo (`cd "$(mktemp -d)" && git init -q`, never the checkout):
  - Setup:
    - `.adw/project.yaml`, with `hooks: {timeout_seconds: 5}` and `worktree: {enabled: false}`
    - `.adw/commands/plan/post.sh` containing `exec sleep 10`
    - a `.gitignore` for `.adw/runs/`
    - everything committed
  - Run `time ADW_MOCK_EXECUTOR=1 adw run "timeout check" --phase plan --no-worktree`.
  - Record the `Hook timed out after 5s` error and a `real` time of about 5 s.
- [ ] Manual non-worktree branch switch, in a fresh scratch repo:
  1. Commit an ADW config, with `.adw/runs/` gitignored.
  2. Run `git branch --show-current`, then `ADW_MOCK_EXECUTOR=1 adw run "Add login" --phase plan --no-worktree`, then `git branch --show-current` again, then `git log --oneline -3`.
  3. Record the transcript. It shows the switch to `feature/add-login` and the plan-phase auto-commit landing on it.
  4. Dirty a tracked file on the initial branch, and run again with a different feature. Record the `Cannot switch to branch …` error and its suggestion.
- [ ] Module and import boundaries are respected:
  - `adw.hooks.git_branch` imports only `adw.exceptions` and `adw.hooks.git_commit`.
  - `hooks/__init__.py` gained no re-exports.
- [ ] `PLAN.md` acceptance criteria are all met, each with its Evidence produced (test output, transcript, grep). No criterion is ticked on "the code looks right".

### Epic update (only if `PLAN.md`'s `Epic:`/`Phase:` are not `none`)

- [ ] Tick phase 1.9's `### Acceptance criteria` in `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`.
- [ ] In the epic-level "Bugs … each have a regression test" criterion, add the tests for this phase:
  - B10: `test_runner_uses_project_hook_config`, `test_project_hook_timeout_stops_post_hook`
  - B16: `test_non_worktree_run_switches_branch_before_plan`, `test_build_post_hook_extracts_story_and_leaves_changes_uncommitted`
- [ ] Mark the phase done: `python3 ~/.claude/skills/create-epic/scripts/link_plan.py 01 --phase 1.9 --plan 01.9-hook-config-and-phase-hook-scripts --status done`.
- [ ] Update the epic's row in `docs/artifacts/epics/EPICS.md`. It stays `In progress` unless this is the last phase of Epic 01 to merge. In that case, set it to `Done`, tick the remaining epic-level criteria, and note any newly unblocked epics.
