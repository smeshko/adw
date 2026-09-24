# TASK-003: Route the remaining git and gh calls through adw.git

Depends on: TASK-002
Suggested commit: `refactor(git): route every git and gh call through adw.git`

## Goal

The last 11 direct `git` / `gh` subprocess calls go through `git()` / `gh()`. Afterwards only `adw/git.py` and `core/run_trigger.py` import `subprocess`. Each caller keeps its error contract, and a timeout now maps onto the error the caller already raises for a failure.

## Files

- **Wrap only the `git()` call in `except ADWError`, never an existing `try` block (validation round 2, #4).** `WorktreeError` is an `ADWError`, so a wider `except ADWError` would re-map the `WorktreeError`s those blocks raise themselves, such as `BRANCH_NOT_CREATED`. The pattern is `try: result = git(...) except ADWError as exc: raise WorktreeError(...) from exc`, then the existing `returncode` handling.
- `src/adw/core/run_lifecycle.py` (the fetch at `:580`): `git("fetch", "origin", base_branch, cwd=self.project_path, timeout=NETWORK_TIMEOUT)`.
  - A non-zero exit still raises `WorktreeError` `GIT_FETCH_FAILED`, now with `recoverable=True`, so both fetch failures agree (validation round 1, #22).
  - Catch `ADWError` (the timeout) and raise the same `WorktreeError("GIT_FETCH_FAILED", f"Failed to fetch '{base_branch}' from origin: {exc.message}", suggestion=exc.suggestion, recoverable=True) from exc`, so the method's documented `Raises: WorktreeError` holds.
    - The timeout keeps `adw.git`'s suggestion, which names credentials and ssh-agent. git writes its prompts to `/dev/tty`, not stderr, so that suggestion is the user's only hint (validation round 3, #2).
  - Drop `import subprocess`.
- `src/adw/core/pr.py`:
  - `create_pr` calls `gh(*args, timeout=60)`, with no `cwd`, as today. The argv list loses its leading `"gh"`.
    - `FileNotFoundError` → `GH_NOT_INSTALLED` stays.
    - Delete the `subprocess.TimeoutExpired` branch: `gh()` raises `GH_TIMEOUT` itself.
  - `_push_branch` calls `git("push", "-u", "origin", branch_name, cwd=working_dir, timeout=HOOK_TIMEOUT)`. Push runs pre-push hooks, so it moves from 120 s to the hook tier (round 2, #8).
    - `except ADWError as exc:` replaces the `TimeoutExpired` branch. It raises `GIT_PUSH_FAILED` with the timeout's message and `suggestion=exc.suggestion`, keeping the credentials hint.
    - `OSError` and non-zero exits map to `GIT_PUSH_FAILED` as before.
  - Drop `import subprocess`.
- `src/adw/core/extensions/build.py` (the `git diff --stat` at `:181`): `git(*stat_args, cwd=worktree_path or None)`, where `stat_args` is today's `stat_cmd` without `"git"`. Its catch-all still logs at debug and returns `None`. Drop `import subprocess`.
- `src/adw/core/extensions/ship.py` (`:192`, `:198`): `git("checkout", base_branch, cwd=self._project_root, check=True, timeout=HOOK_TIMEOUT)` and `git("pull", "origin", base_branch, cwd=self._project_root, check=True, timeout=HOOK_TIMEOUT)`. Checkout runs post-checkout hooks; pull goes over the network and runs post-merge hooks.
  - `ExtensionRegistry.call_on_complete` still logs a failure as a non-blocking warning. That covers `CalledProcessError` and now `GIT_TIMEOUT`.
  - Drop `import subprocess`.
- `src/adw/worktree/manager.py`:
  - `:465` `git worktree add` → `git("worktree", "add", *rest, cwd=self.project_root, timeout=HOOK_TIMEOUT)`. It checks out a full tree and runs the post-checkout hook (round 2, #8).
    - A non-zero exit still runs `_cleanup_partial_worktree` and raises `WORKTREE_CREATE_FAILED`.
    - Catch `ADWError` (the timeout) around the `git(...)` call only, run the same cleanup, and raise `WorktreeError("WORKTREE_CREATE_FAILED", …) from exc`. `BRANCH_NOT_CREATED` (`:488`), raised later in the same block, keeps its code.
    - `FileNotFoundError` → `ConfigError` `GIT_NOT_FOUND` stays.
  - `:438`, the branch pre-check: `branch_exists` now lets a `GIT_TIMEOUT` through. Catch `ADWError` around that call only, and raise `WorktreeError("WORKTREE_CREATE_FAILED", …, recoverable=True) from exc` without cleanup, because nothing has been created yet. The `:487` check maps it the same way after the existing cleanup (validation round 3, #1). Otherwise a timed-out check could read as "absent", and `_cleanup_partial_worktree` would force-delete a branch that already existed.
  - `_cleanup_partial_worktree`: before its branch delete, run `git("worktree", "prune", cwd=self.project_root)` inside `contextlib.suppress(OSError, ADWError)`. A killed `worktree add` leaves `.git/worktrees/<id>` behind, and `branch -D` refuses to delete a branch still registered to a worktree (validation round 1, #4).
  - `:603` `git worktree remove` → `git("worktree", "remove", *rest, cwd=self.project_root, timeout=CHECKOUT_TIMEOUT)`. A non-zero exit and `FileNotFoundError` map as today. Catch `ADWError` (the timeout) around the `git(...)` call only, and raise `WorktreeError("WORKTREE_REMOVE_FAILED", …) from exc`. The `except WorktreeError` in the cleanup-orphans loop (`cli/cleanup.py:258`) then keeps going (validation round 1, #22). The later branch delete never raises a timeout, because TASK-002's `delete_branch` returns `False` instead.
  - `:671` `git status --porcelain` → `git("status", "--porcelain", cwd=worktree_path)`. `except (OSError, ADWError): return False`.
  - `:711` `git branch -D` → `delete_local_branch(branch_name, working_dir=self.project_root)` inside `contextlib.suppress(OSError, ADWError)`.
  - Drop `import subprocess`.
- `src/adw/cli/wizard/git.py` (`:136`): `git("rev-parse", "--is-inside-work-tree", timeout=5)`. `except (ADWError, OSError): return False` replaces `(subprocess.SubprocessError, FileNotFoundError)`. Drop `import subprocess`.
- Tests. Every patch target below moves:
  - `tests/unit/core/test_run_lifecycle.py` (`:415`, `:1188`, `:1220`, `:1252`, `:1277`, `:1307`, `:1346`, `:1381`, `:1410`): `patch("adw.core.run_lifecycle.subprocess.run")` becomes `patch("adw.core.run_lifecycle.git")`.
    - The `assert_called_once_with([...], cwd=tmp_path, capture_output=True, text=True, check=False)` asserts at `:1193` and `:1225` become `assert_called_once_with("fetch", "origin", "main", cwd=tmp_path, timeout=NETWORK_TIMEOUT)`.
    - The argv assert at about `:1257` (`call_args[0][0] == ["git", "fetch", …]`) becomes `call_args.args == ("fetch", "origin", …)`.
    - Add `test_fetch_timeout_raises_git_fetch_failed`: `git` raises `ADWError("GIT_TIMEOUT", …, suggestion="… credentials …")`, and the result is a `WorktreeError` with `code == "GIT_FETCH_FAILED"`, `recoverable`, and "credential" in its suggestion.
  - `tests/unit/core/test_phase_runner.py` (`:627`, `:669`): `adw.core.extensions.build.subprocess.run` becomes `adw.core.extensions.build.git`.
  - `tests/unit/core/test_ship_extension.py:227`: `adw.core.extensions.ship.subprocess.run` becomes `adw.core.extensions.ship.git`. The asserted argv moves from `c.args[0] == ["git", "checkout", …]` to `c.args == ("checkout", …)`.
  - `tests/unit/core/test_pr.py`:
    - `:214`'s `TimeoutExpired` side effect becomes `patch("adw.core.pr.gh", side_effect=ADWError("GH_TIMEOUT", …, recoverable=True))`, and still expects `GH_TIMEOUT`. Patching `subprocess.run` no longer intercepts anything, because `_run` uses `Popen` (see TASK-002).
    - Add `test_push_timeout_raises_git_push_failed`: patch `adw.core.pr.git` to raise `ADWError("GIT_TIMEOUT", "`git push` timed out after 600s")`. Expect `GIT_PUSH_FAILED` with "timed out" in the message and "credential" in the suggestion.
  - `tests/unit/cli/wizard/test_git.py` (`:34`–`:61`): `adw.cli.wizard.git.subprocess.run` becomes `adw.cli.wizard.git.git`. The timeout case raises `ADWError("GIT_TIMEOUT", …)` and still returns `False`.
  - `tests/unit/worktree/test_manager.py:606`: the global `patch("subprocess.run", side_effect=FileNotFoundError)` becomes `patch("adw.worktree.manager.git", side_effect=FileNotFoundError)`. It still expects `ConfigError` `GIT_NOT_FOUND`.
  - Add `test_worktree_remove_timeout_raises_worktree_remove_failed` to `test_manager.py`: patch `adw.worktree.manager.git` to raise `ADWError("GIT_TIMEOUT", …)` on `worktree remove`. Expect `WorktreeError` `WORKTREE_REMOVE_FAILED`.
  - Add `test_branch_check_timeout_creates_nothing` to `test_manager.py`: `branch_exists` raises `GIT_TIMEOUT` at the pre-check. Expect `WorktreeError` `WORKTREE_CREATE_FAILED`, no `worktree add` call, and no `branch -D` call.
  - Add `test_branch_not_created_keeps_its_code` to `test_manager.py`: `worktree add` exits 0, but `branch_exists` returns `False`. Expect `WorktreeError` `BRANCH_NOT_CREATED`, not `WORKTREE_CREATE_FAILED`, which guards the narrow `except`.
  - Run `rg -n 'patch\("subprocess\.(run|Popen)"' tests` and check every remaining hit. None may exercise code that now calls `adw.git`. Move each such hit to the module's `git` / `gh` name.

## Acceptance

- [ ] `rg -U 'subprocess\.(run|Popen)\(\s*\[\s*"(git|gh)"' src` prints nothing.
- [ ] `rg -l 'import subprocess' src` prints only `src/adw/git.py` and `src/adw/core/run_trigger.py`.
- [ ] A fetch timeout raises `GIT_FETCH_FAILED` (recoverable), a push timeout raises `GIT_PUSH_FAILED`, and a `worktree remove` timeout raises `WORKTREE_REMOVE_FAILED`.
- [ ] `rg -n 'patch\("subprocess\.(run|Popen)"' tests` lists only tests of code that doesn't call `adw.git`. Record the list in the evidence.
- [ ] `uv run pytest tests/unit/core tests/unit/worktree tests/unit/cli tests/unit/git tests/integration -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failures of the two new timeout tests, the GREEN pytest tail, both `rg` outputs and the preflight tail.

## Steps

### RED
- [ ] Add `test_fetch_timeout_raises_git_fetch_failed` and `test_push_timeout_raises_git_push_failed` (both patch the module-level `git`); run them: they fail because the modules still call `subprocess.run`.

### GREEN
- [ ] Switch the six modules to `git()` / `gh()` as listed, keeping each caller's error mapping.
- [ ] Move the patch targets in the existing tests; run the partial suite: green.

### REFACTOR
- [ ] Both `rg` checks give the expected output; `scripts/preflight.sh` passes.

## Notes

- `adw.cli.wizard.git` is the wizard's git step module. `from adw.git import git` inside it is an absolute import, so the two names don't collide.
- Hook shell scripts (`ship/pre.sh`, `ship/post.sh`) keep calling `git` / `gh` directly. They run under `hooks/runner.py`'s timeout (out of scope).
