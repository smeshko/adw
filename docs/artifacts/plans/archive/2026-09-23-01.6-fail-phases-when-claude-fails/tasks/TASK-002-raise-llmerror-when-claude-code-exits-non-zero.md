# TASK-002: Raise LLMError when Claude Code exits non-zero

Depends on: TASK-001
Suggested commit: `fix(executor): fail the phase when claude code exits non-zero`

## Goal

A non-zero Claude Code exit raises a recoverable `LLMError` that carries the reason. The orchestrator retries it, and a run that keeps failing is recorded as `failed` (B2).

## Files

- `src/adw/executors/claude_code.py`:
  - `_parse_output`: in the `msg_type == "result"` branch, set `error_result = str(data.get("result") or "")` when `data.get("is_error")` is truthy, and add `"error_result"` to the returned dict (default `""`).
  - `_build_result`: after parsing, if `returncode != 0`:
    - build the message: `f"Claude Code exited with code {returncode}"`, then `f": {detail}"` when `detail` is non-empty. `detail` is the last 20 lines of `stderr.strip()`, or `parsed["error_result"]` when stderr is empty.
    - call `live_stream.write_error(message)` if one is set
    - raise `LLMError(code="CLAUDE_EXIT_NONZERO", message=message, suggestion="See the run's live.log. The phase is retried per llm.retry in .adw/project.yaml.", recoverable=True)`

    The zero-exit path is unchanged for now: it still returns `LLMResult(success=True, ...)`, and TASK-004 removes `success`.
  - Update the `_build_result` and `execute` docstrings (`Raises:`).
- `tests/unit/executors/test_claude_code.py`, in the non-zero-exit tests:
  - merge `test_execute_returns_failure_on_non_zero_exit` and `test_subprocess_error_returns_failure_result` into `test_non_zero_exit_raises_recoverable_llm_error`. It uses `pytest.raises(LLMError)` and asserts `code == "CLAUDE_EXIT_NONZERO"` and `recoverable is True`.
  - `test_stderr_included_in_error_message` asserts the stderr text is in `exc.message`.
  - `test_fallback_error_message_when_no_stderr` (exit 42, no `is_error` result) asserts the message is exactly `"Claude Code exited with code 42"`.
  - add `test_error_result_text_used_when_stderr_empty`: stdout holds `{"type":"result","is_error":true,"result":"API Error: 529 overloaded"}`, and stderr is empty.
  - add `test_stderr_tail_limited_to_20_lines`: 30 lines of stderr keep lines 11–30 only.
  - add `test_non_zero_exit_writes_error_to_live_stream`: a `MagicMock` live stream gets `write_error` called with the message.
  - delete `TestDurationOnFailure` (≈ line 1412). Its premise, a failure result that carries `duration_ms`, no longer exists, because a failure is now an exception.
- `tests/integration/core/test_phase_failure.py`: add `test_fake_claude_exit_fails_run`, which uses the `retry_project` fixture from TASK-001:
  - Write `bin/claude` into the repo (gitignored), `chmod 0o755`. The script appends one line per call to `bin/calls.log`, prints the `is_error` result line to stdout and `fatal: simulated failure` to stderr, and then `exit 1`.
  - `monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")` and `monkeypatch.delenv("ADW_MOCK_EXECUTOR")`.
  - `create_orchestrator(with_progress=False)`, then `pytest.raises(LLMError)` around `run_single_phase("plan", "noop feature", use_worktree=False)`. Assert:
    - `exc.value.code == "CLAUDE_EXIT_NONZERO"` and `"simulated failure" in exc.value.message`
    - `bin/calls.log` has exactly 4 lines, the configured `max_retries`
    - the sleeps were `[call(0.5), call(1.0), call(1.0)]`
    - the only `.adw/runs/*/context.json` has `status == "failed"`
    - `IndexManager().get_recent_runs()[0].status == "failed"`

## Acceptance

- [ ] `test_fake_claude_exit_fails_run` fails on the TASK-001 code (no `LLMError` raised, 1 call, run `completed`) and passes after the change.
- [ ] The rewritten and new `test_claude_code.py` tests pass.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.

Evidence: the RED and GREEN output of `uv run pytest tests/integration/core/test_phase_failure.py -o addopts="" -v`. The RED run shows `DID NOT RAISE` (the B2 regression test fails on pre-fix code).

## Steps

### RED
- [ ] Add `test_fake_claude_exit_fails_run`, run it, and save the `DID NOT RAISE` failure. It is the B2 regression evidence for `VALIDATION.md`.
- [ ] Rewrite and add the `test_claude_code.py` tests above. They fail while `_build_result` still returns a result.

### GREEN
- [ ] Capture `error_result` in `_parse_output`, and raise in `_build_result` as described under Files.
- [ ] Run `uv run pytest tests/unit/executors/test_claude_code.py tests/integration/core/test_phase_failure.py -o addopts="" -q`.

### REFACTOR
- [ ] Pull the message building into a small `_exit_error_message(returncode, stderr, error_result)` static helper if `_build_result` gets long.
- [ ] Run `scripts/preflight.sh` and the full `uv run pytest`.

## Notes

- The raise passes through `_stream_subprocess`'s `except Exception`, which logs "Claude Code execution failed" and re-raises. The process has already exited, so its kill branch is skipped. Leave that block as it is.
- `execute()` only calls `write_llm_end` after a successful `_stream_subprocess`. On a failure, live.log gets the `write_error` line instead, which is intended.
- Keep the fake-script lines in `bin/`: `tmp_path` is the repo, and anything untracked outside the gitignored paths makes `plan/pre.sh` exit 1.
- `IndexManager.get_recent_runs()` returns `list[IndexEntry]`, newest first, and `IndexEntry.status` holds `running|completed|failed|interrupted|aborted`. The test runs exactly one run, so `[0]` is it. Also assert `len(...) == 1`.
