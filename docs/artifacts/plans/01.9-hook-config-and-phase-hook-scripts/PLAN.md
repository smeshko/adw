# Plan: Hook config and phase-hook scripts

Status: done
Branch: feature/adw-15
Risk: medium
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.9 — Hook config and phase-hook scripts
Linear: ADW-15
Created: 2026-09-23

## Goal

After this phase:

- `project.yaml`'s `hooks:` settings (`timeout_seconds`, `shell`) reach the hook runner (B10).
- No bundled hook script shells out to `python3 -c "from adw…"`. That call did nothing whenever the interpreter on `PATH` lacked adw, which is the normal case for a `uv tool install` (B16).
- Non-worktree runs create and switch to their feature branch in Python, at run start, on resume and on `--from-run` continue. Failures raise instead of passing silently.
- The ship, document and build hooks keep only steps whose output something reads.

## Scope

- **B10.** `cli/bootstrap.py` builds `HookRunner(config=config.hooks)` from the loaded `ProjectConfig`, falling back to `HookConfig()` only when no config loads.
- **`build/post.sh`.** Delete step 2, the `python3 -c` auto-commit. `PhaseRunner._auto_commit_changes` runs right after the post-hook and also checks the expected branch. Step 1, story-output extraction, stays.
- **`document/post.sh`.** Delete step 2, which overwrites the `pr_description.md` that `DocumentExtension.extra_artifacts` already stored. That overwrite happens after capture and before `on_complete` opens the PR, so today it silently decides the PR body.
- **Branch switch at run start**, ported from `plan/pre.sh`:
  - `hooks/git_branch.py`:
    - `check_uncommitted_changes` and `create_or_switch_branch` gain a keyword-only `working_dir`, the convention `git_commit.py` already uses.
    - New `ensure_on_branch(branch_name, *, working_dir=None)` carries `pre.sh`'s logic. Already on the branch: no-op. Otherwise a dirty tree raises `HookError("GIT_UNCOMMITTED_CHANGES")`, and a clean one gets `create_or_switch_branch`. Outside a git repo, `get_current_branch` raises `HookError("GIT_BRANCH_CHECK_FAILED")`.
  - `core/run_lifecycle.py`:
    - `_feature_branch_name(feature)` is extracted and used by both `_create_worktree_for_run` and the new non-worktree path.
    - `create_run_context` calls `ensure_on_branch(..., working_dir=self.project_path)` for every non-worktree run, whatever the starting phase. It runs before `_initialize_run`, and the branch lands on `context.branch_name`.
  - Delete `defaults/commands/plan/pre.sh`.
- **Resume and continue.** `RunLifecycle.switch_to_run_branch(context)` is a no-op for worktree runs. For non-worktree runs it switches to `context.branch_name`, deriving and backfilling that name for runs created before this phase.
  - `Orchestrator.resume` calls it right after `validate_resumable`, and `Orchestrator.continue_from_run` right after the worktree-missing check. Both calls come before any context mutation or save.
- **Ship hooks:**
  - `ship/pre.sh` looks the PR up by `${ADW_PR_URL:-$current_branch}`, and drops the step-8 subshell `export`s, which never reach anything.
  - `ship/post.sh` takes the PR number from `ADW_PR_URL` (`${ADW_PR_URL##*/}`, digits only) when the LLM output has no `PR_NUMBER:`. It drops `ADW_PR_NUMBER`, the `ship_status.json` block, and the `ADW_TASK_ID` step. Python never sets `ADW_TASK_ID`.
  - `pre_hook_vars.json` and `merge_record.json` stay: `PhaseRunner` and `ShipExtension` read them.
- **D6.** Delete `build/dev-story/checklist.md`, `plan/create-story/template.md` and `plan/create-story/validation-prompt.md`.
- **Docs** follow each change in the task that makes it:
  - `docs/architecture/deep-dive/`: `phase-runner.md`, `build-phase.md`, `document-phase.md`, `plan-phase.md`
  - epic 04's pointer at `plan/pre.sh`

## Out of Scope

- Branch *naming* (`<prefix>/<issue>-<slug>`, the Type-label prefix): phase 4.1. This plan keeps `branch_prefix + sanitize_branch_name(feature)`, and puts it in one function for 4.1 to replace.
- Worktree runs. Their branch comes from `WorktreeManager` as it does today.
- Trimming `hooks/__init__.py` re-exports (phase 1.3). `ensure_on_branch` is imported from `adw.hooks.git_branch` directly and not re-exported.
- The `phase="pre-hook"` literals that the existing `git_branch.py` helpers put on their `HookError`s. The new error uses `phase="run-start"`.
- User- or project-tier copies of `plan/pre.sh` in target projects' `.adw/commands/`. They still run, and are harmless once the branch is already switched.
- The rest of `ship/post.sh`: merge, deploy commands, remote branch deletion, and the `--admin`/`--auto` logic.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). Every item below was confirmed in code or reproduced:

- **B10**: `bootstrap.py:241` is `HookRunner(config=HookConfig())`, and no `run_hook` call passes `timeout`. Every hook therefore runs with a 60 s timeout and `/bin/bash`, whatever `project.yaml` says.
- **B16**: `plan/pre.sh` and `build/post.sh` step 2 run `python3 -c "from adw…"` and `sys.exit(0)` on `ImportError`. Under `uv run pytest`, `python3` is the venv's, so tests saw the branch switch work. In production it never ran. So non-worktree runs never switched branches, and `context.branch_name` stays `None` for them.
- **Dead ship steps**:
  - `ADW_PR_NUMBER` is exported only inside `pre.sh`'s own process, so `post.sh` always falls back to an empty value.
  - Nothing in `src/` sets `ADW_TASK_ID` or reads `ship_status.json` or `task_update_request.json`.
  - `build_hook_environment` sets `ADW_PR_URL` from `context.pr_url`, which phase 1.7 made reliable.
- **Document PR body**: `document-feature/instructions.xml` step 5 makes the final message the raw PR description, starting at `## Summary`. That is what `final_output` captures, so dropping the shell re-extraction keeps the same body.
- **D6**: no `{{include:}}` references the three BMAD files. The two `workflow.yaml` references resolve under `{project-root}/_bmad/…` in target projects, not to the bundled copies.
- **Test fallout**: a prototype made non-worktree run start raise outside git, then ran the full suite on a scratch copy. 85 tests failed, all from that one check (81 direct, 4 downstream), in four files:
  - `tests/unit/core/test_orchestrator.py` (57)
  - `tests/unit/core/test_run_lifecycle.py` (12)
  - `tests/integration/core/test_orchestrator_integration.py` (11)
  - `tests/integration/cli/test_progress_integration.py` (5)

  None of them reaches the checkout.

## Decisions

See [DECISIONS.md](./DECISIONS.md). In short:

- A non-git project dir fails the run (user's choice).
- The switch runs at every non-worktree run start (user's choice).
- `ADW_PR_URL` is used in both ship hooks (user's choice).
- Resume and continue switch too (user's choice).
- The git logic lives in `git_branch.ensure_on_branch`. The lifecycle only decides *when* and *which* branch.
- Unit tests mock `ensure_on_branch`, and the integration tests move to `git_repo`.
- The automated timeout test uses 1 s/10 s. The 5 s/10 s acceptance run is a manual transcript.

## Risks

- **Test churn**: 85 tests break once run start requires git. Mitigation:
  - An autouse fixture in `test_orchestrator.py` and `test_run_lifecycle.py` patches `adw.core.run_lifecycle.ensure_on_branch`.
  - The two integration files build their project root on `git_repo`, with a committed `.gitignore` for `home/` and `.adw/runs/`, the way `tests/integration/core/test_phase_failure.py` does.
  - The prototype counts are the check: TASK-003 should touch no other file's tests.
- **A test running the real lifecycle against the checkout would now switch the checkout's branch.** The orchestrator derives the project root as `runs_dir.parent.parent`. Mitigation:
  - `test_progress_integration.py` passes `runs_dir=tmp_path`, which puts the project root two levels above `tmp_path`. TASK-003 moves it into `git_repo`.
  - TASK-007 repeats phase 1.1's no-touch snapshot (`git branch`, `git status`, `git worktree list`) around a full run.
- **Behaviour change for `--no-worktree` users**:
  - A dirty tree or a non-git directory now fails at run start.
  - Commits are now checked against the run's branch, since `branch_name` is set.
  - After a merge, ship deletes the remote branch, since `ADW_BRANCH_NAME` is set.

  This is what `pre.sh` meant to do, and B16 hid it. Mitigation: a clear message plus suggestion (`commit or stash`, `run inside a git repository`), printed by `adw run`'s `ADWError` handler.
- **A resume that fails on the branch switch must not leave the run marked `running`.** Mitigation: the switch runs before `prepare_for_resume` and `context_manager.save`, and a test asserts the on-disk status is unchanged.
- **Phase 1.3 (unplanned) trims `hooks/__init__.py` and the exception set.** Mitigation: no new re-exports. `HookError` is kept by 1.3.

## Acceptance Criteria

- [x] With `hooks: {timeout_seconds: 5}`, a post-hook that sleeps 10 s fails after about 5 s. Evidence:
  - `test_project_hook_timeout_stops_post_hook` (1 s/10 s, via `create_orchestrator`) RED on today's code, then GREEN
  - a manual 5 s/10 s scratch-repo transcript with timing
- [x] `grep -rn "python3 -c" src/adw/defaults` returns nothing.
- [x] A non-worktree `adw run` in a scratch repo creates and switches to the feature branch before the plan phase. Evidence:
  - an integration test where a project plan pre-hook records `git branch --show-current` as `feature/<slug>`
  - a scratch-repo CLI transcript (`ADW_MOCK_EXECUTOR=1 adw run --phase plan --no-worktree`)
- [x] Resuming or continuing a non-worktree run from another branch switches back to the run's branch. A dirty tree or a non-git dir raises, and the run's status on disk is unchanged. Evidence: TASK-004 tests.
- [x] `tests/integration/test_ship_post_hook.py` and `tests/integration/test_git_hooks.py` pass against the trimmed scripts. `grep -rn "ADW_PR_NUMBER\|ADW_TASK_ID\|ship_status\|task_update_request" src tests` returns nothing.
- [x] The three D6 files are gone, and `plan/pre.sh` is gone.
- [x] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.
- [x] A full `uv run pytest` leaves the checkout's `git branch`, `git status --short` and `git worktree list` unchanged.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Build HookRunner from project.yaml hooks config
- [x] TASK-002: Drop hook steps that redo Python's work
- [x] TASK-003: Switch non-worktree runs to the feature branch at run start
- [x] TASK-004: Switch to the run's branch on resume and continue (depends on TASK-003)
- [x] TASK-005: Trim ship hooks to live steps and read ADW_PR_URL
- [x] TASK-006: Delete unused bundled BMAD copies
- [x] TASK-007: Final Validation
