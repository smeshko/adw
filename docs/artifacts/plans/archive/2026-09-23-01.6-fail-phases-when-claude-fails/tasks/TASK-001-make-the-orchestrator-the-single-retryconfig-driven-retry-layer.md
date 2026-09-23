# TASK-001: Make the orchestrator the single RetryConfig-driven retry layer

Depends on: None
Suggested commit: `refactor(core): make the orchestrator the single retry layer`

## Goal

`Orchestrator._execute_phase_with_retry` is the only retry loop. It reads `llm.retry` from `project.yaml`, and `RetryExecutor` and `LLMRateLimitError` are gone.

## Files

- `src/adw/core/orchestrator.py`:
  - `__init__`: replace `max_retries: int = 3` with `retry_config: RetryConfig | None = None`, stored as `self.retry_config = retry_config or RetryConfig()`. Update the class and `__init__` docstrings.
  - `_execute_phase_with_retry`: loop `for attempt in range(1, retry.max_retries + 1)`. Keep the `on_llm_complete()` call and the non-recoverable re-raise. Before each retry:
    - compute `delay = min(retry.base_delay_seconds * retry.multiplier ** (attempt - 1), retry.max_delay_seconds)`
    - log `"Retrying phase"` with `attempt`, `max_attempts`, `delay` and `error_code`
    - if `progress_display` is set, print `f"[yellow]⚠[/yellow] Phase '{phase}' failed ({e.code}), retrying in {delay:g}s ({attempt + 1}/{retry.max_retries})..."` through `progress_display.console`
    - `time.sleep(delay)`

    Re-raise the last error when attempts run out. Rewrite the "1s, 2s, 4s" docstring.
- `src/adw/cli/bootstrap.py`:
  - drop the `RetryExecutor` import and wrapping, so the production path assigns `ClaudeCodeExecutor(...)` straight to `llm_executor`
  - pass `retry_config=llm_config.retry` to `Orchestrator(...)`
  - reword the "MockExecutor is NOT wrapped" comment
- `src/adw/executors/retry.py`: delete.
- `src/adw/executors/__init__.py`: drop the `RetryExecutor` import and `__all__` entry.
- `src/adw/exceptions.py`: delete `LLMRateLimitError`.
- `src/adw/executors/base.py`: drop the `LLMRateLimitError` line from the `execute` docstring's `Raises:`.
- `src/adw/models/config.py`, `RetryConfig`:
  - the docstring says the orchestrator applies it to recoverable phase errors
  - the `max_retries` description reads "Maximum attempts per phase, including the first"
- `docs/architecture/deep-dive/orchestrator.md`: the "up to 3x" rows (≈ lines 48 and 57) read "up to `llm.retry.max_retries` attempts, `RetryConfig` backoff".
- `tests/unit/executors/test_retry.py`: delete.
- `tests/unit/cli/test_bootstrap.py`: `TestBootstrapRetryExecutorWiring` becomes `TestBootstrapRetryWiring`:
  - the production path gives `PhaseRunner` the bare `ClaudeCodeExecutor` instance
  - `orchestrator.retry_config is llm_config.retry`
  - drop every `patch("adw.cli.bootstrap.RetryExecutor")`
- `tests/unit/core/test_orchestrator.py`:
  - delete `test_init_default_max_retries` and `test_init_custom_max_retries` (trivial attribute tests, ADR-001)
  - in `TestRetryLogic`, `test_retry_with_custom_max_retries` passes `retry_config=RetryConfig(max_retries=5)`
  - `test_retry_uses_exponential_backoff` asserts `[call(1.0), call(2.0)]` under the default config
  - add `test_backoff_reads_retry_config`: `RetryConfig(max_retries=4, base_delay_seconds=0.5, multiplier=3, max_delay_seconds=1.0)` with 4 recoverable failures sleeps `[0.5, 1.0, 1.0]` and then raises
  - add `test_retry_prints_line_per_retry`: a `MagicMock` progress display gets `console.print` called once per retry, and the text contains `(2/3)` and `(3/3)`
- `tests/integration/core/test_phase_failure.py` (new):
  - fixture `retry_project(git_repo, monkeypatch)`:
    - writes `.adw/project.yaml` with `worktree: {enabled: false}` and `llm: {retry: {max_retries: 4, base_delay_seconds: 0.5, multiplier: 3, max_delay_seconds: 1.0}}`
    - writes `.gitignore` with `home/`, `bin/` and `.adw/runs/`, then commits both
    - `monkeypatch.chdir(git_repo)`
    - patches `adw.core.orchestrator.time.sleep`, and yields the sleep mock
  - `test_mock_executor_fails_twice_then_succeeds`:
    - `orchestrator = create_orchestrator(with_progress=False)`
    - configure `orchestrator._phase_runner.executor` (a `MockExecutor`) with `[LLMError(..., recoverable=True), LLMError(..., recoverable=True), None]`
    - `run_single_phase("plan", "noop feature", use_worktree=False)` returns `status == "completed"`
    - `executor.call_count == 3`, and the sleeps were `[call(0.5), call(1.0)]`

## Acceptance

- [ ] `test_mock_executor_fails_twice_then_succeeds` passes: attempt 3 succeeds, and the sleeps are `[0.5, 1.0]`, taken from `project.yaml`.
- [ ] `test_backoff_reads_retry_config` and `test_retry_prints_line_per_retry` pass.
- [ ] `grep -rn "RetryExecutor\|LLMRateLimitError\|executors.retry" src tests` returns nothing.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.

Evidence: the new integration test's output, RED before the change (sleeps `[1, 2]` from the hard-coded `2**attempt`) and GREEN after, plus the empty grep.

## Steps

### RED
- [ ] Add `tests/integration/core/test_phase_failure.py` with the `retry_project` fixture and `test_mock_executor_fails_twice_then_succeeds`, then run it. It must fail on the sleep assertion (`[call(1), call(2)]` ≠ `[call(0.5), call(1.0)]`). Save the output.
- [ ] Add `test_backoff_reads_retry_config` and `test_retry_prints_line_per_retry` to `TestRetryLogic`. They fail, because `retry_config` is not a constructor argument yet.

### GREEN
- [ ] Change `Orchestrator.__init__` and `_execute_phase_with_retry` as described under Files.
- [ ] Wire `retry_config=llm_config.retry` in `create_orchestrator`, and drop the `RetryExecutor` wrapping.
- [ ] Delete `executors/retry.py`, `tests/unit/executors/test_retry.py`, the `RetryExecutor` export and `LLMRateLimitError`.
- [ ] Update `test_bootstrap.py` and the existing `TestRetryLogic` tests, and delete the two `test_init_*_max_retries` tests.
- [ ] Run `uv run pytest tests/unit/core/test_orchestrator.py tests/unit/cli/test_bootstrap.py tests/integration/core/test_phase_failure.py -o addopts="" -q`.

### REFACTOR
- [ ] Update the `RetryConfig` docstring and descriptions, the `executors/base.py` docstring and `orchestrator.md`.
- [ ] Run `scripts/preflight.sh` and the full `uv run pytest`.

## Notes

- Keep `for attempt in range(1, n + 1)` 1-based, so the delay exponent and the printed `(next/max)` counter read straight off `attempt`.
- `MockExecutor` configured with `LLMError` entries raises them in order, then falls back to its default response. No `configure_responses` call is needed for the success attempt.
- The run's `HOME` is `tmp_path/home`, inside the `git_repo`, so without the committed `.gitignore`, `plan/pre.sh` refuses to run ("Uncommitted changes detected").
- `test_retry_config.py` stays untouched. It tests the model's validation, which does not change.
