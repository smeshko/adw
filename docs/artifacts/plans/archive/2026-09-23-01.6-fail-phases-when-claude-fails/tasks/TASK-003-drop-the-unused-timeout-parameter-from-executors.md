# TASK-003: Drop the unused timeout parameter from executors

Depends on: TASK-001
Suggested commit: `refactor(executor): drop the unused timeout parameter`

## Goal

`LLMExecutor.execute` and its implementations no longer take a `timeout` that no caller passes.

## Files

- `src/adw/executors/base.py`: remove `timeout: int | None = None` from `LLMExecutor.execute`, its `Args:` entry, and the `timeout` in the class docstring example.
- `src/adw/executors/claude_code.py`: remove the `timeout` parameter and its `Args:` line from `execute`. Fix the `__init__` docstring's "path, timeout, and other settings" to say "path and retry settings". Keep the `asyncio.wait_for(..., timeout=5.0)` pipe drain and the "Runs without a timeout" note in `_stream_subprocess`.
- `src/adw/executors/mock.py`: remove the `timeout` parameter and its `Args:` line from `execute`.
- `tests/unit/executors/test_claude_code.py`: delete `test_execute_with_timeout_parameter`.
- `tests/unit/executors/test_protocol.py`:
  - `MinimalExecutor.execute` drops `timeout` and takes `phase`, `cwd` and `model` as keyword-only instead
  - `test_llm_executor_execute_has_correct_signature` asserts `"timeout" not in hints`, replacing `hints.get("timeout") == (int | None)`

## Acceptance

- [ ] `grep -rn "timeout: int\|timeout=timeout" src/adw/executors` returns nothing.
- [ ] mypy `--strict` (through `scripts/preflight.sh`) passes. This proves `ClaudeCodeExecutor` and `MockExecutor` still satisfy `LLMExecutor` where `bootstrap.py` assigns them to `llm_executor: LLMExecutor`.
- [ ] `uv run pytest` is green with coverage ≥ 80%.

Evidence: the empty grep, the `preflight: ok` line, and the pytest summary line.

## Steps

### RED
- [ ] Change `test_llm_executor_execute_has_correct_signature` to assert `"timeout" not in hints`, run it, and see it fail.

### GREEN
- [ ] Remove the parameter from the Protocol, `ClaudeCodeExecutor` and `MockExecutor`, with their docstrings.
- [ ] Delete `test_execute_with_timeout_parameter`, and update `MinimalExecutor`.
- [ ] Run `uv run pytest tests/unit/executors -o addopts="" -q`.

### REFACTOR
- [ ] Run `scripts/preflight.sh` and the full `uv run pytest`.

## Notes

- `PhaseRunner._execute_llm` is the only production caller, and it passes `phase`, `cwd` and `model` only. It depends on TASK-001 because `RetryExecutor.execute` forwards `timeout=timeout`, and mypy fails while that file exists.
- Phase 1.2 deletes other `MockExecutor` helpers. Touch only the `execute` signature here, to keep the merge clean.
