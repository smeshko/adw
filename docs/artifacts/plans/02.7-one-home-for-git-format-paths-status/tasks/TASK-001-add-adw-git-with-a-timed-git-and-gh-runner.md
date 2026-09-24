# TASK-001: Add adw.git with a timed git() and gh() runner

Depends on: None
Suggested commit: `feat(git): add adw.git with timed git() and gh() runners`

## Goal

`adw.git` provides `git()` and `gh()`, which run the tool with a timeout and raise a recoverable `ADWError` instead of hanging. Nothing calls them yet.

## Files

- `src/adw/git.py` (new). A module docstring says every `git` and `gh` subprocess in ADW goes through this module. Contents:
  - Timeout tiers (PLAN.md Decisions). Later tasks use all four:
    - `DEFAULT_TIMEOUT = 60.0`: local plumbing
    - `NETWORK_TIMEOUT = 300.0`: fetch, `gh pr view`
    - `CHECKOUT_TIMEOUT = 300.0`: `worktree remove`, `add -A`
    - `HOOK_TIMEOUT = 600.0`: commands that run git hooks (commit, amend, checkout, pull, push, `worktree add`)
  - `KILL_GRACE = 5.0`.
  - `git(*args: str, cwd: Path | None = None, check: bool = False, timeout: float = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess[str]`
  - `gh(...)` has the same signature and runs `gh`.
  - Both delegate to `_run(tool, args, *, cwd, check, timeout)`:
    - It starts `subprocess.Popen([tool, *args], cwd=cwd, stdout=PIPE, stderr=PIPE, text=True)` inside `with … as proc:`, then calls `proc.communicate(timeout=timeout)`.
    - There is no `start_new_session`. git stays in the terminal's process group, as it does today, so a Ctrl+C reaches git itself (git removes its own locks), and credential or SSH prompts can still use the terminal (validation round 2, #1 and #2).
    - With `check=True`, a non-zero exit raises `subprocess.CalledProcessError(returncode, cmd, stdout, stderr)`.
    - It returns `subprocess.CompletedProcess(cmd, returncode, stdout, stderr)`.
    - A missing binary raises `FileNotFoundError` from `Popen`, as it does from `subprocess.run` today.
  - `_stop(proc)` stops git gently, then firmly:
    - It sends `proc.terminate()` (SIGTERM).
    - Then: `try: proc.wait(timeout=KILL_GRACE) except subprocess.TimeoutExpired: pass finally: if proc.poll() is None: proc.kill(); proc.wait()`. The `finally` still sends SIGKILL if a second interrupt lands during the grace wait (validation round 3, #5).
    - `KILL_GRACE` is read from the module at call time, never bound as a default argument, so tests can monkeypatch it.
    - It never reads the pipes after the signal. A descendant that inherited them (a daemonizing hook) could keep them open forever, which is why `hooks/runner.py` also uses `wait()` (round 2, #3).
    - git removes `index.lock` and its ref locks on SIGTERM.
  - On `subprocess.TimeoutExpired`, `_run` calls `_stop(proc)` and raises `ADWError(f"{tool.upper()}_TIMEOUT", f"`{label}` timed out after {timeout:g}s", suggestion=..., recoverable=True) from exc`.
  - On any other `BaseException` inside the `with` block (a `KeyboardInterrupt` or `SystemExit` from ADW's SIGINT handlers), `_run` calls `_stop(proc)` and re-raises. `subprocess.run` does the same today, but sends SIGKILL at once.
  - `label` is the tool plus its leading arguments up to the first one that starts with `-`, at most two of them: `git fetch origin`, `git commit` (from `commit -m msg`), `git push` (from `push -u origin b`), `git worktree add`, `gh pr create`, `gh pr view`. `gh pr create`'s title and body come after flags, so they never reach the message.
  - The timeout suggestions:
    - git: "A slow remote, a waiting credential or SSH prompt, or a slow hook can hold git up: check `git remote -v`, your credentials or ssh-agent and the network, remove a stale `.git/index.lock` if one is left, then retry"
    - gh: "Check network access and `gh auth status`, then retry"
- `tests/unit/git/__init__.py` (new, empty) and `tests/unit/git/test_run.py` (new). Every fake-git test passes `cwd=tmp_path`, so a PATH slip can never reach the checkout.
  - A module-local `fake_bin` fixture writes executable scripts into `tmp_path / "bin"`, and prepends that directory to `PATH` with `monkeypatch.setenv`. It never replaces PATH.
  - `test_git_fetch_times_out_against_a_sleeping_git`:
    - The script is `#!/bin/sh\nexec sleep 30\n`.
    - `git("fetch", "origin", cwd=tmp_path, timeout=0.5)` raises `ADWError`. Assert `code == "GIT_TIMEOUT"`, `recoverable`, and "`git fetch origin`" in the message.
    - `time.monotonic()` around the call measures under 5 s. `sleep` dies on SIGTERM, so the grace period isn't spent.
  - `test_gh_times_out_against_a_sleeping_gh`: the same for `gh("pr", "view", "b", "--json", "state", cwd=tmp_path, timeout=0.5)`. It raises `GH_TIMEOUT`, and the message names "`gh pr view`" (the label stops after two arguments).
  - `test_timeout_sends_sigterm_first`:
    - The fake `git` traps TERM: `trap 'echo cleaned > "$MARK"; kill $! 2>/dev/null; exit 143' TERM; sleep 30 & wait`, with `MARK` set through `monkeypatch.setenv`.
    - After `git("commit", "-m", "x", cwd=tmp_path, timeout=1.0)` raises, the marker file exists. This is the path that lets real git remove its locks.
    - The message names "`git commit`".
  - `test_escalates_to_sigkill_only_after_the_grace_period`, parametrized over two triggers:
    - The fake is `trap '' TERM; exec sleep 30`. An ignored signal stays ignored across `exec`.
    - `adw.git.KILL_GRACE` is monkeypatched to 0.5.
    - **Timeout trigger:** `git("fetch", cwd=tmp_path, timeout=1.0)` raises `GIT_TIMEOUT`.
    - **Interrupt trigger:** a `SIGALRM` handler raises `KeyboardInterrupt` at 1.0 s around `git("fetch", cwd=tmp_path, timeout=30)`, and the `KeyboardInterrupt` propagates.
    - In both, `1.0 + 0.5 <= elapsed < 5`. An implementation that sends SIGKILL at once fails the lower bound (validation round 3, #3).
  - `test_interrupt_stops_git_and_propagates`:
    - Uses the TERM-trapping fake from above.
    - A `SIGALRM` handler raises `KeyboardInterrupt`, scheduled with `signal.setitimer(signal.ITIMER_REAL, 1.0)` around `git("fetch", cwd=tmp_path, timeout=30)`.
    - The `KeyboardInterrupt` propagates, and the marker file exists.
  - Every `SIGALRM` test cancels the timer and then restores the handler in `finally`: `signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old)`. An uncancelled alarm that fires after `git()` returns kills pytest with exit 142 (validation round 3, #4). Nothing else in the suite uses SIGALRM (no pytest-timeout or xdist).
  - `test_git_returns_the_completed_process` (real git, `git_repo` fixture): `git("rev-parse", "--is-inside-work-tree", cwd=git_repo)` has `returncode == 0` and `stdout.strip() == "true"`.
  - `test_git_check_raises_called_process_error`: `git("rev-parse", "HEAD", cwd=tmp_path, check=True)`, run in a `tmp_path` that isn't a repository, raises `subprocess.CalledProcessError`.

## Acceptance

- [ ] A `git fetch` through `git()`, against a fake `git` that sleeps 30 s, raises `GIT_TIMEOUT` in under 5 s. The same holds for `gh` and `GH_TIMEOUT`.
- [ ] A timeout or an interrupt sends SIGTERM to git first, and SIGKILL only after the grace period. The TERM-trap test, both escalation cases (elapsed ≥ timeout + grace) and the interrupt test pass.
- [ ] `git()` returns the `CompletedProcess` for a real command, and `check=True` raises `CalledProcessError`.
- [ ] `uv run pytest tests/unit/git -o addopts="" --durations=5` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failure (`ModuleNotFoundError: adw.git`), then the GREEN run with `--durations` showing that the timeout test takes about 0.5 s, and the preflight tail.

## Steps

### RED
- [ ] Write `tests/unit/git/test_run.py`; run it: it fails importing `adw.git`.

### GREEN
- [ ] Write `src/adw/git.py`.
- [ ] Run `uv run pytest tests/unit/git -o addopts="" --durations=5`: green, timeout tests about 0.5 s.

### REFACTOR
- [ ] `scripts/preflight.sh` passes (mypy strict: `CompletedProcess[str]` return type).

## Notes

- **Why `Popen` + `_stop` instead of `subprocess.run(timeout=)`.** `run` sends SIGKILL to the child straight away, which leaves git's lockfiles behind: git removes them on SIGTERM, not on SIGKILL (validation round 1, #4).
- **Why no new session or process-group kill.** Round 1 proposed both, and round 2 showed they cost more than they save:
  - The terminal's SIGINT would no longer reach git.
  - git would lose `/dev/tty`, so every credential and SSH prompt would fail.

  The price of leaving them out is that a hook grandchild can outlive a timed-out git. PLAN.md Risks records it.
- The fast-path fakes use `exec sleep`, so those tests don't wait out the grace period.
- `tests/unit/git/` is a regular test package (`tests.unit.git`), so it doesn't shadow `adw.git`.
