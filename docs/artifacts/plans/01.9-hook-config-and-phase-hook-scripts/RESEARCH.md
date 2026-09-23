# Research: Hook config and phase-hook scripts

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

- `src/adw/cli/bootstrap.py:241` — `HookRunner(config=HookConfig())` ignores the `config.hooks` that `ConfigLoader` loaded a few lines above. This is B10.
- `src/adw/hooks/runner.py` — `_resolve_timeout` works out the timeout in this order:
  1. the `timeout` argument
  2. `config.timeout_seconds`
  3. `DEFAULT_HOOK_TIMEOUT` (60)

  `PhaseRunner._run_pre_hook` and `_run_post_hook` never pass `timeout`, so the config is the only lever. The runner already kills the process group on timeout (phase 1.1).
- `src/adw/models/config.py:130` — `HookConfig(shell="/bin/bash", timeout_seconds=60)`. `ProjectConfig.hooks` defaults to it.
- `src/adw/core/phase_runner.py`:
  - `run()` works through these steps in order:
    1. pre-hook
    2. render
    3. LLM
    4. capture, which calls `extension_registry.call_extra_artifacts`
    5. post-hook
    6. `_auto_commit_changes`
  - Hooks run with `working_dir=context.worktree_path`, which is `None`, and so the cwd, for non-worktree runs.
  - `_auto_commit_changes` calls `create_commit(expected_branch=context.branch_name)`, and `validate_branch_matches` skips when that is `None`.
- `src/adw/core/run_lifecycle.py`:
  - `create_run_context` creates the worktree when enabled; otherwise `branch_name` stays `None`.
  - `_create_worktree_for_run` computes `git_config.branch_prefix + sanitize_branch_name(feature)`; `WorktreeManager` falls back to `adw/<run_id>` when that is `None`.
  - `prepare_resume_context` sets the running label.
  - `self.project_path` comes from `Orchestrator._project_path = runs_dir.parent.parent`.
- `src/adw/core/orchestrator.py` — `run()` and `run_single_phase()` both go through `create_run_context`, so the switch reaches every new run. The two other entry points need their own call:

  | Entry point | Existing sequence | Where the switch goes |
  |---|---|---|
  | `resume()` | `validate_resumable` → `prepare_for_resume` → `save` → `prepare_resume_context` | between `validate_resumable` and `prepare_for_resume` |
  | `continue_from_run()` | load → worktree-missing check → `model_copy(status="running")` → `save` | after the worktree-missing check |

  A switch placed any later would leave a failed resume marked `running` on disk.
- `src/adw/hooks/git_branch.py`:
  - `sanitize_branch_name`, `check_uncommitted_changes()` and `create_or_switch_branch(branch)` exist.
  - Neither of the last two takes a `working_dir`: both run in the process cwd.
  - Errors are `HookError` with `phase="pre-hook"`.
- `src/adw/hooks/git_commit.py:26` — `get_current_branch(*, working_dir)` raises `HookError("GIT_BRANCH_CHECK_FAILED", suggestion="Ensure you are in a git repository")` outside git, and returns `None` on a detached HEAD.
- `src/adw/hooks/environment.py` — sets these, among others:
  - `ADW_BRANCH_NAME`, when `context.branch_name` is set
  - `ADW_PR_URL`, when `context.pr_url` is set

  It never sets `ADW_PR_NUMBER` or `ADW_TASK_ID`.
- `src/adw/core/extensions/document.py`:
  - `extra_artifacts` stores `pr_description.md` = `final_output or content` at capture.
  - `on_complete` reads it through `load_pr_description` and calls `create_pr`.

  `document/post.sh` step 2 runs between the two, and overwrites the file.
- `src/adw/core/extensions/ship.py:143` — `on_complete` is gated on `context.use_worktree`, so a non-worktree `branch_name` triggers no worktree cleanup. `cli/cleanup.py` works only on worktree paths.
- `src/adw/cli/app.py` `run` — any `ADWError` out of the orchestrator, `create_run_context` included, prints `Error: <message>` and `Suggestion: <suggestion>`, then exits 1.
- `src/adw/defaults/commands/plan/create-story/workflow.yaml:17`, `build/dev-story/workflow.yaml:11` — `installed_path` points under the target project's `_bmad/`, so the bundled `template.md`/`checklist.md`/`validation-prompt.md` are never read.

## Architecture Facts

- **Hook tiers**: `CommandResolver._collect_hook_paths` runs the bundled, user (`~/.adw/commands/<phase>/`) and project (`.adw/commands/<phase>/`) hooks, in that order. Deleting the bundled `plan/pre.sh` leaves user and project plan pre-hooks working. A project-tier `pre.sh` is how the integration test observes the branch "before the plan phase".
- **Ship data flow**:
  - `pre.sh` writes `pre_hook_vars.json` into the ship artifacts dir, and `PhaseRunner._load_and_render_prompt` merges it into the template variables. That flow is live.
  - `post.sh` writes `merge_record.json`, which `ShipExtension.on_complete` reads. Also live.
  - `ship_status.json` and `task_update_request.json` have no reader.
- **Test environment**:
  - `uv run pytest` puts the venv's `python3` first on `PATH`, so `python3 -c "from adw…"` hooks work in tests and not in a `uv tool install`. That's why tests never caught B16.
  - `isolated_home` puts HOME at `tmp_path/home`, so under `git_repo` (which is `tmp_path`) HOME is an untracked directory inside the repo, and the tree is dirty unless `home/` is gitignored.

## Constraints

- Phase 1.3 (unplanned) will trim `hooks/__init__.py` and keep `HookError`. Add no re-exports.
- Phase 4.1 will replace the branch naming. Keep it in a single `_feature_branch_name`.
- AGENTS.md: a test that touches git runs in `git_repo` or `tmp_path` via `monkeypatch.chdir`. Never run the real lifecycle with a project root that could resolve to the checkout.
- ADR-001: test behaviour, error paths and I/O. Shell-script tests assert on files written and on stdout, not on prose.

## Useful Commands

```bash
# B10: every hook uses the default config
grep -n "HookRunner(" src/adw/cli/bootstrap.py

# B16 surface
grep -rn "python3 -c" src/adw/defaults

# dead ship names (should be empty after TASK-005)
grep -rn "ADW_PR_NUMBER\|ADW_TASK_ID\|ship_status\|task_update_request" src tests

# partial runs without the coverage gate
uv run pytest tests/unit/core/test_run_lifecycle.py tests/unit/core/test_orchestrator.py -o addopts=""
uv run pytest tests/integration/test_git_hooks.py tests/integration/test_ship_post_hook.py -o addopts=""

# scratch-repo non-worktree run (TASK-007 evidence)
ADW_MOCK_EXECUTOR=1 adw run "Add login" --phase plan --no-worktree && git branch --show-current
```

## Uncertainty

- **How many tests break when run start requires git.** Resolved by prototype: on a scratch copy (`git archive HEAD`), a three-line patch made non-worktree `create_run_context`, `prepare_resume_context` and `continue_from_run` call `get_current_branch(working_dir=project_path)`. The full suite then gave 85 failed / 3732 passed, all from `GIT_BRANCH_CHECK_FAILED`, in the four files listed in PLAN.md. The prototype did not model dirty-tree refusals. The integration files' new `git_repo` fixtures commit a `.gitignore` for that reason.
- **Whether dropping `document/post.sh` step 2 changes the PR body.** Resolved: `instructions.xml` step 5 makes the final message the raw PR description starting at `## Summary`. `final_output` is that message.
- **Whether `jq` exists on CI for a `ship/pre.sh` test.** `ubuntu-latest` ships `jq`, and so does macOS 15+ (`/usr/bin/jq`). The new test puts a fake `gh` first on `PATH` and relies on the system `jq`. If `shutil.which("jq")` is `None`, it skips with a reason instead of failing.

## References

- [Epic 01, phase 1.9](../../epics/01-cleanup-safety-dead-code-bugs.md)
- [PhaseRunner deep dive](../../../architecture/deep-dive/phase-runner.md)
- [Simplification audit report](https://claude.ai/artifact/P59fUpiUcp7rATwMUSjjmp) (private): B10, B16, D6
- Prior art: `tests/integration/core/test_phase_failure.py` — the `create_orchestrator` + `git_repo` + gitignored-HOME fixture pattern
