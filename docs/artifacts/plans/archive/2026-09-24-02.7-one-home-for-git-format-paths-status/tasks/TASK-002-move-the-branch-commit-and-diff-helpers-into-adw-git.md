# TASK-002: Move the branch, commit and diff helpers into adw.git

Depends on: TASK-001
Suggested commit: `refactor(git): move the branch, commit and diff helpers into adw.git`

## Goal

The git helpers spread across `hooks/git_branch.py`, `hooks/git_commit.py`, `hooks/git_diff.py` and `worktree/branch.py` live in `adw.git`, and they run every command through `git()` / `gh()`. The four modules are gone. Behaviour is unchanged apart from the new timeouts and the removal of the dead unpushed-commits path.

## Files

- `src/adw/git.py`: add these, with names, signatures and `working_dir` keywords unchanged. Each `subprocess.run([...], cwd=working_dir, capture_output=True, text=True, check=False)` becomes `git(..., cwd=working_dir)`.
  - From `hooks/git_commit.py`:
    - `DEFAULT_COMMIT_TEMPLATE` and `MAX_HOOK_RETRIES`
    - `get_current_branch`, `validate_branch_matches` and `format_commit_message`
    - `stage_changes`: `git add -A` passes `timeout=CHECKOUT_TIMEOUT`, because LFS clean filters and large untracked trees can be slow
    - `has_staged_changes` and `get_unstaged_modifications`
    - `create_commit`: both `git commit` calls (the commit and the `--amend --no-edit`) pass `timeout=HOOK_TIMEOUT`
  - From `hooks/git_branch.py`:
    - `MAX_BRANCH_LENGTH`, `sanitize_branch_name` and `check_uncommitted_changes`
    - `create_or_switch_branch`: both `checkout` calls pass `timeout=HOOK_TIMEOUT` (post-checkout hooks, LFS smudge)
    - `ensure_on_branch`
  - From `hooks/git_diff.py`:
    - `BINARY_FILE_PATTERN`, `has_commits`, `count_binary_files`, `capture_diff` and `capture_staged_diff`, keeping `cwd = working_dir or Path.cwd()`
    - `truncate_diff` and `get_diff_stats`
  - From `worktree/branch.py`: `WorktreeBranchManager` becomes three functions:
    - `branch_exists(branch_name: str, *, working_dir: Path) -> bool` runs `git branch --list <b>` and returns `bool(stdout.strip())`. `FileNotFoundError` gives `False`, as today.
      - A `GIT_TIMEOUT` propagates. "Unknown" must never read as "absent", because callers delete or recreate branches on `False` (validation round 3, #1).
    - `delete_branch(branch_name: str, *, working_dir: Path) -> bool` returns `True` when the branch doesn't exist. Otherwise it runs `git branch -D <b>` and returns `True` on exit 0.
      - On a non-zero exit it logs a warning and returns `False`.
      - Its whole body sits in `except ADWError`, which logs a warning and returns `False`. That covers a timeout in either the existence check or the delete, so it never raises one into callers that have already removed the worktree, and it never reports a delete it didn't do (rounds 2 and 3).
    - `pr_exists(branch_name: str, *, working_dir: Path) -> bool | None` runs `gh pr view <b> --json state` with `timeout=NETWORK_TIMEOUT`. A non-zero exit, `FileNotFoundError` or a `GH_TIMEOUT` `ADWError` gives `None`. Otherwise it returns whether `OPEN` or `MERGED` appears in stdout.
    - `has_unpushed_commits` and the `force=False` / `-d` path are dropped. Every caller passes `force=True` (`manager.py:643`, `cli/cleanup.py:138`).
  - Keep the moved docstrings, but cut the per-function `Example:` blocks and restated argument lists, so each docstring is a one-line summary plus `Raises:` where it matters.
- `git rm src/adw/hooks/git_branch.py src/adw/hooks/git_commit.py src/adw/hooks/git_diff.py src/adw/worktree/branch.py`. `src/adw/hooks/__init__.py`'s docstring stops saying the package handles branches, commits and diffs. What is left there is the hook runner and its environment.
- **Name clashes (validation round 1, #1).** The new function names collide with existing names at three sites:
  - In `worktree/manager.py` and `cli/cleanup.py`, `delete_branch` is already a `bool` parameter (`remove_worktree(..., delete_branch: bool)` at `manager.py:520`, `cleanup_command(delete_branch: bool)` at `cleanup.py:27`). Both modules import the function as `from adw.git import delete_branch as delete_local_branch`.
  - `remove_worktree` has a local `pr_exists = …` (`manager.py:627`), which would shadow the imported function (ruff F823). Rename the local to `has_pr`.
  - `create_or_switch_branch` has a local `branch_exists = …` (`hooks/git_branch.py:155`). Once it moves into `adw.git`, next to the new `branch_exists()` function, rename it to `exists` (round 2, #9c).
  - Patch targets follow the import names: `adw.worktree.manager.pr_exists`, `adw.worktree.manager.delete_local_branch` and `adw.cli.cleanup.delete_local_branch`.
- `src/adw/core/run_lifecycle.py:31`: `from adw.git import ensure_on_branch, sanitize_branch_name`.
- `src/adw/core/phase_runner.py:22`: `from adw.git import create_commit, stage_changes`.
- `src/adw/core/extensions/build.py:12`: `from adw.git import capture_diff, capture_staged_diff, get_diff_stats, has_commits, truncate_diff`.
- `src/adw/worktree/manager.py`:
  - drop `WorktreeBranchManager`, `self._branch_manager` and the `branch_manager` property
  - `get_branch_name(run_id)` returns `f"adw/{run_id}"`
  - these calls switch to the `adw.git` functions with `working_dir=self.project_root`:
    - `branch_exists` at `:438` and `:487`
    - `has_pr = pr_exists(branch_name, …)` at `:627`
    - `delete_local_branch` at `:643`
  - `:553` uses `self.get_branch_name(run_id)`
- `src/adw/worktree/__init__.py`: drop the `WorktreeBranchManager` import and `__all__` entry. Nothing imports it from the package.
- `src/adw/cli/cleanup.py:135-139`: `delete_local_branch(context.branch_name or worktree_manager.get_branch_name(run_id), working_dir=worktree_manager.project_root)`.
- `docs/artifacts/epics/04-plan-driven-runs.md:167`: `hooks/git_branch.py` becomes `adw/git.py` (`sanitize_branch_name`).
- Tests:
  - `git mv` the three hooks tests:
    - `tests/unit/hooks/test_git_branch.py` → `tests/unit/git/test_branch.py`
    - `test_git_commit.py` → `tests/unit/git/test_commit.py`
    - `test_git_diff.py` → `tests/unit/git/test_diff.py`

    Change the imports to `adw.git`, and change `patch("adw.hooks.git_commit.has_staged_changes")` / `get_unstaged_modifications` to `patch("adw.git.…")`.
  - **Patch the `adw.git.git` seam, not `subprocess.run` (validation round 1, #4).** TASK-001's `_run` uses `Popen`, so a global `patch("subprocess.run")` no longer intercepts anything. The moved tests would then run real git in the cwd.
    - Every `patch("subprocess.run", …)` in the moved files becomes `patch("adw.git.git", …)`: 8 in `test_branch.py`, 15 in `test_commit.py`, 11 in `test_diff.py`. The helpers call the module-global `git()`, so this seam catches every call.
    - `return_value` and `side_effect` keep returning `CompletedProcess` / `MagicMock(returncode=…, stdout=…, stderr=…)`.
    - Argv assertions drop the leading `"git"` and move from `call[0][0] == ["git", "add", "-A"]` to `call.args == ("add", "-A")`. `cwd` assertions read `call.kwargs["cwd"]`.
  - `git mv tests/unit/worktree/test_branch.py tests/unit/git/test_worktree_branch.py`. Rewrite it against the three functions:
    - exists and missing
    - force delete
    - deleting a missing branch returns `True`
    - `pr_exists` returns `None` on `FileNotFoundError`, now `patch("adw.git.gh", side_effect=FileNotFoundError)`, and on a `GH_TIMEOUT` `ADWError`
    - `test_delete_branch_reports_failure_when_the_check_times_out`: with `adw.git.git` raising `ADWError("GIT_TIMEOUT", …)` on `branch --list`, `delete_branch` returns `False`, not `True`
    - `test_branch_exists_propagates_a_timeout`

    Delete the unpushed-commits and `force=False` tests, whose code is gone.
  - `tests/unit/worktree/test_manager.py:606`'s global `patch("subprocess.run", side_effect=FileNotFoundError)` becomes `patch("adw.worktree.manager.git", side_effect=FileNotFoundError)`. TASK-003 routes `manager.py` through `git()`. Until then it still calls `subprocess.run` and the old patch works, so move this patch in TASK-003.
  - `tests/unit/worktree/test_manager.py`:
    - delete the whole `branch_manager` property test at `:854`–`:861`, which imports `WorktreeBranchManager`
    - `patch.object(manager._branch_manager, "check_pr_exists", …)` at `:740`, `:774` and `:808` becomes `patch("adw.worktree.manager.pr_exists", …)`
  - `tests/integration/test_git_hooks.py:14,20` and `tests/integration/test_git_diff.py:10`: import from `adw.git`.
  - `tests/unit/cli/test_cleanup.py` (new): `test_cleanup_deletes_branch_when_worktree_is_gone`. `cleanup_command` has no tests today, and the name clash in #1 lives in its `WORKTREE_NOT_FOUND` branch.
    - Set up `git_repo` (chdir'd) with branch `adw/<run_id>` and a run context under `.adw/runs/<run_id>/` whose `worktree_path` doesn't exist.
    - Run `adw cleanup <run_id> --delete-branch --force` through `CliRunner`.
    - Assert exit 0, `Branch deleted` in the output, and an empty `git branch --list adw/<run_id>`.
  - Run `rg -n "branch_manager|WorktreeBranchManager|adw\.hooks\.git_|adw\.worktree\.branch" tests` and move each remaining hit to the new names.
- `docs/architecture/deep-dive/build-phase.md:210-211`: the two `hooks/git_*.py` rows become one `src/adw/git.py` row ("Every git and gh call: commit, diff, branch helpers").

## Acceptance

- [ ] `ls src/adw/hooks src/adw/worktree` shows no `git_branch.py`, `git_commit.py`, `git_diff.py` or `branch.py`.
- [ ] `rg -n "adw\.hooks\.git_|adw\.worktree\.branch|WorktreeBranchManager|has_unpushed_commits" src tests docs/architecture` prints nothing.
- [ ] `rg -n 'subprocess\.(run|Popen)\(' src/adw/git.py` prints exactly one line, the `Popen` in `_run`.
- [ ] `create_commit` passes `timeout=HOOK_TIMEOUT` to both commit calls. `test_commit.py` has a test that asserts the `timeout` kwarg on the `git commit` call.
- [ ] `test_cleanup_deletes_branch_when_worktree_is_gone` passes.
- [ ] `rg -n 'patch\("subprocess\.(run|Popen)"' tests/unit/git` prints nothing, so no moved test can reach real git through an unpatched seam.
- [ ] `uv run pytest tests/unit/git tests/unit/worktree tests/unit/core tests/unit/cli/test_cleanup.py tests/integration/test_git_hooks.py tests/integration/test_git_diff.py -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failure of the moved test files (`ImportError` from `adw.git`) before the move, then the GREEN pytest tail, the `ls`, the `rg` output and the preflight tail.

## Steps

### RED
- [ ] `git mv` the four test files and point their imports at `adw.git`. Add the commit-timeout assertion. Run them: they fail on the missing names.
- [ ] Write `test_cleanup_deletes_branch_when_worktree_is_gone` against today's code. It should pass, which pins the behaviour before the rename.

### GREEN
- [ ] Move the helpers into `adw.git` on top of `git()` / `gh()`, and fold `WorktreeBranchManager` into the three functions.
- [ ] Switch the importers (`run_lifecycle`, `phase_runner`, `build`, `worktree/manager`, `worktree/__init__`, `cli/cleanup`) and `git rm` the four modules.
- [ ] Update the remaining tests found by the `rg`; run the partial suite: green.

### REFACTOR
- [ ] Trim the moved docstrings; update `build-phase.md`; `scripts/preflight.sh` passes.

## Notes

- `create_or_switch_branch` / `ensure_on_branch` call `get_current_branch`. Inside one module they call it directly, so the old `git_branch` → `git_commit` import goes away.
- `test_git_commit.py`'s `side_effect` lists depend on the number and order of the git calls. The move keeps both. The lists now feed `adw.git.git` instead of `subprocess.run`.
- Consumer-level patch targets (`adw.core.phase_runner.create_commit`, `adw.core.run_lifecycle.ensure_on_branch`, `adw.core.extensions.build.capture_diff`, …) keep working, because the consumers import the names into their own namespace.
