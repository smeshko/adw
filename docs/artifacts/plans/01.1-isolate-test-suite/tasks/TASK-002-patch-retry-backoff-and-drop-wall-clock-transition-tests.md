# TASK-002: Patch retry backoff and drop wall-clock transition tests

Depends on: None
Suggested commit: `test: patch retry backoff and drop wall-clock transition tests`

## Goal

`tests/unit/core/test_orchestrator.py` no longer sleeps in real time, and no longer asserts on wall-clock duration.

## Files

- `tests/unit/core/test_orchestrator.py`:
  - `TestRetryLogic` gets a class-level autouse fixture `no_backoff` that patches `adw.core.orchestrator.time.sleep` and yields the mock.
  - `test_retry_uses_exponential_backoff` drops its `@patch("time.sleep")` decorator and asserts through `no_backoff`: 2 calls, `(1)` and `(2)`.
  - `TestTransitionPerformance` loses `test_transition_under_1_second` and `test_slow_transition_logs_debug`. `test_transition_logs_duration` stays.
  - Add `from collections.abc import Generator` for the fixture's return type.

## Acceptance

- [ ] `uv run pytest tests/unit/core/test_orchestrator.py -o addopts="" --durations=5` passes, and no test in the file takes ≥ 0.5 s. Before the change, `TestRetryLogic` took about 26 s and `test_slow_transition_logs_debug` 1.1 s.
- [ ] `test_retry_uses_exponential_backoff` still asserts the 1 s and 2 s backoff calls.
- [ ] `grep -n "time.sleep(1.1)\|time.monotonic()" tests/unit/core/test_orchestrator.py` returns nothing.

Evidence: `--durations=5` output for the file, before and after.

## Steps

### RED
- [ ] Record `uv run pytest tests/unit/core/test_orchestrator.py -o addopts="" --durations=8` as the before-evidence: the six slow `TestRetryLogic`/`TestTransitionPerformance` entries.

### GREEN
- [ ] Add the `no_backoff` autouse fixture to `TestRetryLogic`: `with patch("adw.core.orchestrator.time.sleep") as m: yield m`.
- [ ] Rewrite `test_retry_uses_exponential_backoff` to take `no_backoff: MagicMock` in place of the decorator-injected `mock_sleep`.
- [ ] Delete `test_transition_under_1_second` and `test_slow_transition_logs_debug`.
- [ ] Re-run the file with `--durations=5`.

### REFACTOR
- [ ] Remove any now-unused imports (for example a local `import time`), and run `scripts/preflight.sh`.

## Notes

- Patch the orchestrator module's `time`, not the global `time.sleep`. The fixture is scoped to `TestRetryLogic` only.
- The "Transition exceeded 1s" debug branch in `orchestrator.py` loses its test on purpose: it is log output, not behaviour (ADR-001).
