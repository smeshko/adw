# TASK-004: Delete LLMResult success, error and attempt_count

Depends on: TASK-002
Suggested commit: `refactor(models): drop unread LLMResult status fields`

## Goal

`LLMResult` carries only what callers read. A failure is an `LLMError`, never a result object, and unknown constructor fields are rejected.

## Files

- `src/adw/models/llm.py`:
  - delete the `success`, `error` and `attempt_count` fields
  - add `model_config = ConfigDict(extra="forbid")`
  - drop `success=True` from the class docstring example
  - update the docstring, which says `content` is required
- `src/adw/executors/claude_code.py`: `_build_result`'s zero-exit path returns `LLMResult(**common)`.
- `src/adw/executors/mock.py`: drop `success=True` from the `configure_responses` construction and from the default-response construction.
- `tests/unit/models/test_llm.py`:
  - `test_result_required_fields` asserts that `content` is the only required field
  - `test_acceptance_criteria_fields` drops `success` and `error`
  - add `test_unknown_field_rejected`: `LLMResult(content="x", success=True)` raises `pydantic.ValidationError`
- `tests/unit/core/test_phase_runner.py`: remove `success=...` from all 18 `LLMResult(...)` constructions.
- `tests/unit/executors/test_protocol.py`: `MinimalExecutor` returns `LLMResult(content="test")`.
- `tests/unit/executors/test_claude_code.py`:
  - delete `test_execute_returns_success_on_zero_exit`, which only asserted `success is True`, now meaningless
  - drop the other `assert result.success is True` lines (≈ line 452)
- `tests/integration/test_claude_code_executor.py`: drop `assert result.success is True` from `test_simple_prompt_execution`. The module is skipped in mock mode, so edit it by hand.

## Acceptance

- [ ] `test_unknown_field_rejected` passes.
- [ ] `grep -rn "\.success\b\|attempt_count\|success=" src/adw/models/llm.py src/adw/executors tests/unit/executors tests/unit/models/test_llm.py tests/unit/core/test_phase_runner.py tests/integration/test_claude_code_executor.py` returns nothing.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%. With `extra="forbid"`, a missed `success=` anywhere in the suite fails here.

Evidence: `test_unknown_field_rejected`, RED then GREEN; the empty grep; the pytest summary line.

## Steps

### RED
- [ ] Add `test_unknown_field_rejected`, run it, and see it fail. Pydantic's default `extra="ignore"` accepts `success=True` silently.

### GREEN
- [ ] Delete the three fields, and add `model_config = ConfigDict(extra="forbid")` (import `ConfigDict` from `pydantic`).
- [ ] Update `ClaudeCodeExecutor._build_result` and both `MockExecutor` constructions.
- [ ] Run `uv run pytest -o addopts="" -q -x`, and fix each `ValidationError` that `extra="forbid"` surfaces in tests, until the run is green.

### REFACTOR
- [ ] Update the `LLMResult` and `MockExecutor.configure_responses` docstrings.
- [ ] Run `scripts/preflight.sh` and the full `uv run pytest`.

## Notes

- `LLMResult` is only ever constructed in-process, by the executors and by tests, and is never loaded from JSON. So `extra="forbid"` cannot break reading older runs.
- Leave `webhook/runner.py`, `dashboard/mutations.py`, `cli/pr.py` and `cli/progress.py` alone. Their `.success` belongs to other result types (`RunTriggerResult`, `AutoPRResult`, `_PRResultFromContext`), not `LLMResult`.
- Extension `on_complete(..., llm_result)` hooks (`core/extensions/*.py`) don't read `success` or `error`. mypy confirms it.
