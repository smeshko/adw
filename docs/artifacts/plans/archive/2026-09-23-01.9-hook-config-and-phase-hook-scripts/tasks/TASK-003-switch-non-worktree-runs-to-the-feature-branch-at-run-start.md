# TASK-003: Switch non-worktree runs to the feature branch at run start

Depends on: None
Suggested commit: `fix(core): switch non-worktree runs to the feature branch at run start`

## Goal

Every non-worktree run creates or switches to `branch_prefix + sanitize_branch_name(feature)` in Python before its first phase, and records it on `context.branch_name`. A dirty tree or a non-git project dir fails the run. `plan/pre.sh`, and with it the last `python3 -c` hook, is deleted (B16).

## Files

- `src/adw/hooks/git_branch.py`:
  - `check_uncommitted_changes(*, working_dir: Path | None = None)` and `create_or_switch_branch(branch_name, *, working_dir: Path | None = None)` pass `cwd=working_dir` to every `subprocess.run`.
  - New `ensure_on_branch(branch_name: str, *, working_dir: Path | None = None) -> None`:
    1. If `get_current_branch(working_dir=…)` (imported from `adw.hooks.git_commit`) equals `branch_name`, return. Outside git this raises `HookError("GIT_BRANCH_CHECK_FAILED")`.
    2. If `check_uncommitted_changes(working_dir=…)` is true, raise `HookError(code="GIT_UNCOMMITTED_CHANGES", phase="run-start", message=f"Cannot switch to branch '{branch_name}': the working tree has uncommitted changes", suggestion="Commit or stash your changes, or run with worktree isolation (drop --no-worktree)")`.
    3. Otherwise call `create_or_switch_branch(branch_name, working_dir=…)`.
  - Update the module docstring.
- `src/adw/core/run_lifecycle.py`:
  - Import `ensure_on_branch` from `adw.hooks.git_branch`.
  - New `_feature_branch_name(self, feature_description: str) -> str | None`: returns `self.git_config.branch_prefix + sanitized`, or `None` when the sanitized name is empty. `_create_worktree_for_run` uses it in place of its inline computation.
  - In `create_run_context`, when `should_use_worktree` is false:
    - `branch_name = self._feature_branch_name(feature_description) or f"adw/{run_id}"`, the same fallback `WorktreeManager` uses.
    - Then `ensure_on_branch(branch_name, working_dir=self.project_path)`.
    - Both run before the `RunContext` is built, so a failure leaves no run dir and no index entry.
  - Update the docstring's numbered steps and `Raises:`.
- Delete `src/adw/defaults/commands/plan/pre.sh`.
- Test fixtures, per the prototype's four files:
  - `tests/unit/core/test_orchestrator.py` and `tests/unit/core/test_run_lifecycle.py`: add a module-level autouse fixture that patches `adw.core.run_lifecycle.ensure_on_branch` and yields the mock.
  - `tests/integration/core/test_orchestrator_integration.py`: the `project_root` fixture builds on `git_repo` and commits a `.gitignore` with `home/` and `.adw/runs/`.
  - `tests/integration/cli/test_progress_integration.py`: pass `runs_dir=git_repo / ".adw" / "runs"` instead of `runs_dir=tmp_path`, with the same committed `.gitignore`.
  - `tests/integration/core/test_phase_failure.py:60`: the docstring names `plan/pre.sh`. Reword it to "run start refuses to switch branches on a dirty tree".
- New tests:
  - `tests/integration/test_git_hooks.py`: a `TestEnsureOnBranch` class, using real git.
  - `tests/unit/core/test_run_lifecycle.py`: `TestCreateRunContextBranch`, using the mock.
  - `tests/integration/core/test_run_start_branch.py` (new): the end-to-end test.
- Docs:
  - `docs/architecture/deep-dive/plan-phase.md:171`: drop the `plan/pre.sh` row. Add a sentence under run setup: "Non-worktree runs switch to the feature branch at run start (`RunLifecycle.create_run_context`)."
  - `docs/artifacts/epics/04-plan-driven-runs.md:167`: the pointer `(hooks/git_branch.py, plan/pre.sh)` becomes `(hooks/git_branch.py, RunLifecycle._feature_branch_name)`.

## Acceptance

- [ ] `TestEnsureOnBranch`, in `git_repo`, with `working_dir=git_repo` and the process cwd left at `tmp_path`:
  - `test_creates_and_switches`: HEAD becomes `feature/x`.
  - `test_already_on_branch_ignores_dirty_tree`: on `feature/x` with an untracked file, the call is a no-op.
  - `test_refuses_dirty_tree`: on the initial branch with a modified file, it raises `GIT_UNCOMMITTED_CHANGES` and HEAD is unchanged. Capture the initial branch with `git branch --show-current`, since `git_repo` doesn't pin `init.defaultBranch`.
  - `test_non_git_dir_raises`: in a bare `tmp_path / "plain"`, it raises `GIT_BRANCH_CHECK_FAILED`.
- [ ] `TestCreateRunContextBranch`, using the autouse mock:
  - With `GitConfig(branch_prefix="feat/")`, the mock is called once with `("feat/add-login", working_dir=project_path)`, and `context.branch_name == "feat/add-login"`.
  - A feature that sanitizes to empty (`"!!!"`) switches to `adw/<run_id>`.
  - When the mock raises `HookError`, `create_run_context` re-raises, and neither `run_directory_manager.create` nor `index_manager.register_run` is called.
  - With worktrees enabled and a mocked `WorktreeManager`, the mock is not called.
- [ ] `test_non_worktree_run_switches_branch_before_plan` (new integration file):
  - Setup:
    - In `git_repo`, commit these files:
      - `.adw/project.yaml`, with `worktree: {enabled: false}`
      - a project `.adw/commands/plan/pre.sh` that writes `git branch --show-current` to `$ADW_ARTIFACTS_DIR/branch.txt`
      - `.gitignore` with `home/` and `.adw/runs/`
    - `monkeypatch.chdir(git_repo)`.
  - Run `create_orchestrator(with_progress=False).run_single_phase("plan", "Add login", use_worktree=False)`.
  - Assert:
    - `branch.txt` reads `feature/add-login`
    - `git branch --show-current` is `feature/add-login`
    - `context.json` has `branch_name: "feature/add-login"`
- [ ] `test_non_worktree_run_outside_git_fails`: the same call in a non-git `tmp_path` with a `project.yaml` raises `HookError` (`GIT_BRANCH_CHECK_FAILED`), and `.adw/runs/` holds no run.
- [ ] `grep -rn "python3 -c" src/adw/defaults` returns nothing, and `src/adw/defaults/commands/plan/pre.sh` is gone.
- [ ] `uv run pytest tests/unit/core tests/integration -o addopts=""` passes, and no test file outside the four prototype files plus the new tests changed.

Evidence:
- RED output: `ensure_on_branch` does not exist, and `branch_name` is `None` for non-worktree runs
- GREEN output for the four new test groups
- the grep
- `git diff --stat` for the test tree, which lists only the expected files

## Steps

### RED
- [ ] Write `TestEnsureOnBranch` and `TestCreateRunContextBranch`. Both fail at import or attribute lookup.
- [ ] Write `tests/integration/core/test_run_start_branch.py`. The outside-git test fails today because the run proceeds. Delete the bundled `plan/pre.sh` locally to confirm the before-plan test also fails without the port (`branch.txt` shows the default branch), then restore it until GREEN.
- [ ] Run and confirm the failures.

### GREEN
- [ ] Add `working_dir` to the two helpers, then `ensure_on_branch`.
- [ ] Add `_feature_branch_name`, and route `_create_worktree_for_run` through it.
- [ ] Add the non-worktree switch to `create_run_context`.
- [ ] Delete `plan/pre.sh`.
- [ ] Add the autouse `ensure_on_branch` patch to the two unit files, and move the two integration files onto `git_repo`.
- [ ] Run `tests/unit/core`, `tests/integration` and `tests/unit/cli`. Only the prototype's four files should need fixture changes; investigate any other failure rather than patching it away.

### REFACTOR
- [ ] Update the two docs and the `test_phase_failure.py` docstring.
- [ ] `scripts/preflight.sh` passes.

## Notes

- Why a fixture per file and not in `tests/unit/core/conftest.py`: other `tests/unit/core` files, such as `test_phase_runner.py`, never build a `RunLifecycle`. Patching the name everywhere would hide real calls from future tests.
- The unit mock must patch `adw.core.run_lifecycle.ensure_on_branch`, the name bound in the lifecycle module, not `adw.hooks.git_branch.ensure_on_branch`.
- `test_progress_integration.py` passes `runs_dir=tmp_path` today, which puts the orchestrator's project root at `tmp_path.parent.parent`, outside the test's own directory. Moving it into `git_repo` is a safety fix as well as a fixture fix.
- `context.branch_name` is now set for non-worktree runs. `ShipExtension.on_complete` and `cli/cleanup.py` are gated on `use_worktree`/`worktree_path`, so neither acts on it. The ship post-hook now receives `ADW_BRANCH_NAME` and deletes the remote branch after a merge. That is intended.
