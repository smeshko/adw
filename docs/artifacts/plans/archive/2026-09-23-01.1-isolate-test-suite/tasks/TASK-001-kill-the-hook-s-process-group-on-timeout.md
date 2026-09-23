# TASK-001: Kill the hook's process group on timeout

Depends on: None
Suggested commit: `fix(hooks): kill the hook's process group on timeout`

## Goal

A timed-out hook is stopped together with every child it started, so `run_hook` raises `HOOK_TIMEOUT` right after the timeout instead of waiting for the children to exit (B9).

## Files

- `src/adw/hooks/runner.py`:
  - `HookRunner._execute_hook` passes `start_new_session=True` to `asyncio.create_subprocess_exec`.
  - The `except TimeoutError` branch replaces `process.kill()` with `os.killpg(process.pid, signal.SIGKILL)` inside `try/except ProcessLookupError: pass`, then `await process.wait()`.
  - Add `import os` and `import signal`, sorted.
- `tests/unit/hooks/test_runner.py`: new `TestHookRunner::test_timeout_kills_hook_children`.
- `tests/fixtures/hooks/slow.sh`: `sleep 30` → `exec sleep 30`.

## Acceptance

- [ ] A hook with a 1 s timeout whose script runs `sleep 30 & echo $! > "$PID_FILE"; wait` raises `HookError` with code `HOOK_TIMEOUT` in under 3 s.
- [ ] The `sleep` child PID no longer exists: `os.kill(pid, 0)` raises `ProcessLookupError` within 2 s of the error.
- [ ] `test_timeout_with_slow_script` (integration) and `test_timeout_raises_hook_error` (unit) each take under 2 s. They took 30.05 s and 10.13 s before.
- [ ] `uv run pytest tests/unit/hooks tests/integration/test_hooks.py -o addopts=""` passes.

Evidence:
- the RED run: the new test fails at about 30 s on the unmodified runner
- the GREEN run: it passes
- `--durations=5` output for the two hook test files

## Steps

### RED
- [ ] Add `test_timeout_kills_hook_children` to `TestHookRunner`, using `run_context` and `tmp_path`:
  - The script is `#!/bin/bash\nsleep 30 &\necho $! > {pid_file}\nwait\n`, with `HookConfig(shell="/bin/bash", timeout_seconds=1)` and `run_hook(script, run_context, "plan", timeout=1)`.
  - Time the call with `time.monotonic()`, assert `HookError` with code `HOOK_TIMEOUT`, and assert the elapsed time is `< 3`.
  - Read the PID, then poll `os.kill(pid, 0)` every 0.1 s for up to 2 s until it raises `ProcessLookupError`, and fail if it never does. The poll tolerates a zombie that is not reaped yet on Linux CI.
- [ ] Run it against the current runner and confirm it fails on the elapsed-time assertion. The prototype failed at 30.1 s.

### GREEN
- [ ] In `_execute_hook`, add `start_new_session=True` to `create_subprocess_exec`, and replace `process.kill()` with the guarded `os.killpg(process.pid, signal.SIGKILL)`.
- [ ] Change `tests/fixtures/hooks/slow.sh` to `exec sleep 30`.
- [ ] Run the hook test files and confirm they are green and fast.

### REFACTOR
- [ ] Add a one-line comment on `start_new_session` saying why it's there (kill the whole group on timeout), matching the comment style in `executors/claude_code.py`.
- [ ] `scripts/preflight.sh` passes.

## Notes

- Do not import `ClaudeCodeExecutor._kill_process_group`: helper consolidation belongs to Epic 02.
- `killpg` can race with a leader that has already exited, hence the `ProcessLookupError` guard. `await process.wait()` must still run, so the transport is reaped.
- With `exec sleep`, `slow.sh` no longer exercises the grandchild case. The new unit test is the only regression test for B9, so keep its script non-`exec`.
