# TASK-004: Switch to the run's branch on resume and continue

Depends on: TASK-003
Suggested commit: `fix(core): switch to the run's branch on resume and continue`

## Goal

`adw resume <id>` and `adw run --phase <p> --from-run <id>` put a non-worktree run back on its own branch before any phase runs. Contexts written before this phase get their branch name backfilled. A failed switch leaves the run's on-disk state untouched.

## Files

- `src/adw/core/run_lifecycle.py`: new public `switch_to_run_branch(self, context: RunContext) -> RunContext`:
  - If `context.use_worktree`, return `context` unchanged. Worktree runs live in their own checkout.
  - Otherwise `branch_name = context.branch_name or self._feature_branch_name(context.feature_description) or f"adw/{context.run_id}"`.
  - Call `ensure_on_branch(branch_name, working_dir=self.project_path)`.
  - If `context.branch_name` was `None`, return `context.model_copy(update={"branch_name": branch_name})`; else return `context`. The method does not save: the callers already save right after.
- `src/adw/core/orchestrator.py`:
  - `resume()`: `context = self._lifecycle.switch_to_run_branch(context)` immediately after `self.resume_manager.validate_resumable(...)`, and before `prepare_for_resume` and `self.context_manager.save`.
  - `continue_from_run()`: the same call immediately after the `WORKTREE_MISSING` check, and before the feature override, the `status="running"` copy and the save.
- `tests/unit/core/test_run_lifecycle.py`: `TestSwitchToRunBranch`, using the TASK-003 autouse mock.
- `tests/integration/core/test_run_start_branch.py`: resume and continue tests, using real git.

## Acceptance

- [ ] `TestSwitchToRunBranch`:
  - A worktree context: the mock is not called, and the same context is returned.
  - A non-worktree context with `branch_name="feature/a"`: the mock is called with `"feature/a"`, and the result's `branch_name` is unchanged.
  - A non-worktree context with `branch_name=None` and feature `"Add login"`: the mock is called with `"feature/add-login"`, and the result has `branch_name="feature/add-login"`.
- [ ] `test_resume_switches_back_to_run_branch`:
  - Setup:
    1. Record the initial branch with `git branch --show-current`. `git_repo` doesn't pin `init.defaultBranch`, so don't assume `main`.
    2. Run a non-worktree `run_single_phase("plan", …)` in `git_repo`. Before the run, call `configure_failures([LLMError(..., recoverable=False), None])` on the orchestrator's `MockExecutor`, as `test_phase_failure.py` does. The run fails, and is on `feature/<slug>`.
    3. Check out the initial branch.
  - Run `orchestrator.resume(run_id)` on the same orchestrator, so the executor's second, succeeding entry is used.
  - Assert: the resume succeeds, and `git branch --show-current` is `feature/<slug>`.
- [ ] `test_resume_on_dirty_tree_leaves_status_unchanged`: same setup, plus a modified tracked file on the initial branch. `resume` raises `HookError("GIT_UNCOMMITTED_CHANGES")`, and `ContextManager.load(run_id).status` is still `"failed"`.
- [ ] `test_continue_from_run_switches_to_run_branch`: after a completed non-worktree plan run and a checkout of the initial branch, `continue_from_run("build", run_id)` runs on `feature/<slug>`. Record it with a project `.adw/commands/build/pre.sh`, which writes `git branch --show-current` to the artifacts dir.
- [ ] `test_resume_backfills_branch_name`: a failed non-worktree `context.json` with `branch_name: null`. After `resume`, the saved context has `branch_name == "feature/<slug>"`, and HEAD is on it.

Evidence:
- the RED run: resume stays on the initial branch, and the dirty-tree test either doesn't raise or leaves the status `"running"`
- the GREEN run

## Steps

### RED
- [ ] Write `TestSwitchToRunBranch`. It fails with `AttributeError`.
- [ ] Write the four integration tests next to TASK-003's, reusing its `git_repo` project fixture. Build a context that is resumable in `validate_resumable`'s terms: `status="failed"` or `"interrupted"`, with a `current_phase`.
- [ ] Run and confirm the failures.

### GREEN
- [ ] Add `switch_to_run_branch`.
- [ ] Call it from `resume()` and `continue_from_run()` at the two points above.
- [ ] Run `tests/unit/core/test_run_lifecycle.py`, `tests/unit/core/test_orchestrator.py` and `tests/integration/core -o addopts=""`.

### REFACTOR
- [ ] Update the docstrings of `resume()` and `continue_from_run()`, adding the branch switch step and `HookError` under `Raises:`.
- [ ] `scripts/preflight.sh` passes.

## Notes

- `tests/unit/core/test_orchestrator.py` resume tests build non-worktree contexts. TASK-003's autouse mock already covers them, so no extra fixture work is expected. If one fails on the switch itself, the mock is not reaching it: check the patch target.
- `prepare_resume_context` stays as it is (label + `task_info` backfill). The switch is not placed there, because it runs after `save`.
