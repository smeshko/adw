# Story 3.3: Implement Retry Logic with Exponential Backoff

Status: ready-for-dev
Linear Issue: not-configured
Epic: 3 - Hook & Phase Execution
Created: 2025-12-31

---

## Story

As a developer,
I want transient LLM failures to be retried automatically,
so that temporary issues don't fail the entire run.

## Acceptance Criteria

**Given** LLMTimeoutError occurs during execution
**When** retries are configured (default: 3)
**Then** the request is retried with exponential backoff (1s, 2s, 4s)

**Given** LLMRateLimitError occurs during execution
**When** retries are configured
**Then** the request is retried with backoff respecting rate limit headers if available

**Given** all retry attempts fail
**When** the final attempt fails
**Then** the original error is raised with attempt count in the message

**Given** a non-retryable error (e.g., invalid prompt)
**When** error occurs
**Then** no retries are attempted and error is raised immediately

**Given** MockExecutor with configured failures
**When** first two attempts fail and third succeeds
**Then** execution succeeds with attempt_count=3

## Tasks / Subtasks

### Task 1: Create RetryConfig Model
- [x] Add retry configuration to `src/adw/models/config.py` or create new model
- [x] Fields: `max_retries: int = 3`, `base_delay_seconds: float = 1.0`, `max_delay_seconds: float = 60.0`
- [x] Add `multiplier: float = 2.0` for exponential backoff

### Task 2: Create RetryExecutor Wrapper
- [x] Create `src/adw/executors/retry.py`
- [x] Implement `RetryExecutor` class that wraps any `LLMExecutor`
- [x] Constructor takes `executor: LLMExecutor` and `config: RetryConfig`
- [x] Implement `execute()` that handles retry logic

### Task 3: Implement Exponential Backoff
- [ ] Calculate delay as `base_delay * (multiplier ^ attempt)`
- [ ] Cap delay at `max_delay_seconds`
- [ ] Add jitter (randomness) to prevent thundering herd
- [ ] Use `asyncio.sleep()` for non-blocking delay

### Task 4: Implement Error Classification
- [ ] Create `is_retryable(error: ADWError) -> bool` function
- [ ] `LLMTimeoutError` → retryable
- [ ] `LLMRateLimitError` → retryable (use `retry_after` if available)
- [ ] Other `LLMError` → not retryable by default
- [ ] `HookError`, `ConfigError` → not retryable

### Task 5: Handle Rate Limit Headers
- [ ] Check `LLMRateLimitError.retry_after` for server-suggested delay
- [ ] Use larger of: calculated backoff OR `retry_after`
- [ ] Log when using rate limit delay

### Task 6: Update LLMResult for Attempt Tracking
- [ ] Add `attempt_count: int = 1` field to `LLMResult`
- [ ] Set to number of attempts made (including final successful one)
- [ ] Log each retry attempt with attempt number

### Task 7: Enhance Error Messages
- [ ] On final failure, include attempt count in error message
- [ ] Example: "LLM execution failed after 3 attempts"
- [ ] Preserve original error as `__cause__`

### Task 8: Write Unit Tests
- [ ] Create `tests/unit/executors/test_retry.py`
- [ ] Test successful execution (no retry needed)
- [ ] Test retry on LLMTimeoutError
- [ ] Test retry on LLMRateLimitError
- [ ] Test non-retryable errors fail immediately
- [ ] Test max retries exceeded raises error
- [ ] Test exponential backoff delays (mock sleep)
- [ ] Test rate limit retry_after is respected
- [ ] Target: >90% coverage for retry module

---

## Developer Context

### Technical Requirements

- **Decorator Pattern**: RetryExecutor wraps any LLMExecutor
- **Exponential Backoff**: `delay = base * (multiplier ^ attempt)` with jitter
- **Async Sleep**: Use `asyncio.sleep()` for non-blocking waits
- **Error Classification**: Only retry transient errors (timeout, rate limit)
- **Cause Chain**: Preserve original exception with `from` clause

### Architecture Compliance

**From architecture.md - Error Handling Decision:**

```python
# Exception Hierarchy:
# - ADWError (base)
#   - LLMError - Claude Code execution failures
#     - LLMTimeoutError (recoverable=True)
#     - LLMRateLimitError (recoverable=True)
```

**Retry Pattern:**
```python
class RetryExecutor:
    def __init__(
        self,
        executor: LLMExecutor,
        max_retries: int = 3,
        base_delay: float = 1.0,
        multiplier: float = 2.0,
    ) -> None:
        self.executor = executor
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.multiplier = multiplier

    def execute(self, prompt: str, *, timeout: int | None = None) -> LLMResult:
        return asyncio.run(self._execute_with_retry(prompt, timeout))

    async def _execute_with_retry(
        self,
        prompt: str,
        timeout: int | None,
    ) -> LLMResult:
        last_error: LLMError | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = self.executor.execute(prompt, timeout=timeout)
                result.attempt_count = attempt
                return result
            except LLMError as e:
                last_error = e
                if not self._is_retryable(e) or attempt == self.max_retries:
                    raise LLMError(
                        code=e.code,
                        message=f"{e.message} (after {attempt} attempts)",
                        suggestion=e.suggestion,
                        recoverable=False,
                    ) from e

                delay = self._calculate_delay(attempt, e)
                logger.info(
                    "Retrying LLM call",
                    attempt=attempt,
                    delay_seconds=delay,
                    error_code=e.code,
                )
                await asyncio.sleep(delay)

        raise last_error  # Should never reach here
```

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Python | 3.13+ | `asyncio.sleep()` for non-blocking delay |
| random | stdlib | Jitter for backoff |

**Backoff with jitter:**
```python
import random

def _calculate_delay(self, attempt: int, error: LLMError) -> float:
    base_delay = self.base_delay * (self.multiplier ** (attempt - 1))

    # Respect rate limit retry_after if available
    if isinstance(error, LLMRateLimitError) and error.retry_after:
        base_delay = max(base_delay, error.retry_after)

    # Add jitter (±25%)
    jitter = base_delay * 0.25 * (random.random() * 2 - 1)
    delay = base_delay + jitter

    # Cap at max delay
    return min(delay, self.max_delay)
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── executors/
│   ├── __init__.py        # Update exports
│   ├── base.py            # Already exists
│   ├── mock.py            # Already exists
│   ├── claude_code.py     # From Story 3.2
│   └── retry.py           # NEW: RetryExecutor

tests/
├── unit/
│   └── executors/
│       ├── test_mock.py   # Already exists
│       ├── test_claude_code.py # From Story 3.2
│       └── test_retry.py  # NEW
```

**Models to update:**
```python
# src/adw/models/llm.py - Add to LLMResult:
attempt_count: int = 1
"""Number of attempts made (including final successful one)."""
```

### Testing Requirements

**Test Framework:** pytest with pytest-asyncio

**Key Test Fixtures:**
```python
@pytest.fixture
def mock_executor() -> MockExecutor:
    return MockExecutor()

@pytest.fixture
def retry_executor(mock_executor: MockExecutor) -> RetryExecutor:
    return RetryExecutor(
        executor=mock_executor,
        max_retries=3,
        base_delay=0.01,  # Fast for tests
    )
```

**Test Patterns:**
```python
def test_retry_on_timeout(
    retry_executor: RetryExecutor,
    mock_executor: MockExecutor,
):
    # First two calls timeout, third succeeds
    mock_executor.configure_failures([
        LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=300,
        ),
        LLMTimeoutError(...),
        None,  # Success
    ])
    mock_executor.configure_responses([{"content": "Success!"}])

    result = retry_executor.execute("test prompt")

    assert result.success
    assert result.attempt_count == 3
    assert mock_executor.call_count == 3
```

**Coverage Target:** >80% overall, >90% for retry module

---

## Previous Story Intelligence

**From Story 3.2 (Claude Code Executor):**
- `LLMExecutor` Protocol is established
- `LLMResult` model is defined
- Async pattern: sync wrapper around async internals

**Dependencies:**
- Story 3.3 depends on Story 3.2 (needs ClaudeCodeExecutor to wrap)
- Story 3.3 can run in parallel with Story 3.4 and 3.5 (Wave 2)

---

## Git Intelligence

**Exception classes already defined at `src/adw/exceptions.py`:**
- `LLMTimeoutError` - has `timeout_seconds`, `elapsed_seconds`, `recoverable=True`
- `LLMRateLimitError` - has `retry_after`, `recoverable=True`

Use the `recoverable` field to determine if retry is appropriate.

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:

1. **Exception Hierarchy**: Use `recoverable` field to determine retry eligibility
2. **Structured Logging**: Log each retry attempt with context
3. **Async Model**: Use `asyncio.sleep()` for backoff, not `time.sleep()`
4. **Type Annotations**: Full annotations on all functions

---

## Dev Notes

### Key Implementation Points

1. **Wrapper Pattern** - RetryExecutor wraps any executor:
   ```python
   claude_executor = ClaudeCodeExecutor(config)
   retry_executor = RetryExecutor(claude_executor, max_retries=3)
   result = retry_executor.execute(prompt)
   ```

2. **Error Classification** - Use `recoverable` field:
   ```python
   def _is_retryable(self, error: ADWError) -> bool:
       return isinstance(error, LLMError) and error.recoverable
   ```

3. **Logging Pattern**:
   ```python
   logger.info(
       "Retrying LLM call",
       attempt=attempt,
       max_attempts=self.max_retries,
       delay_seconds=delay,
       error_code=error.code,
   )
   ```

4. **Jitter Formula** - Full jitter is recommended:
   ```python
   delay = random.uniform(0, base_delay * (multiplier ** attempt))
   ```

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming) ✓
- RetryExecutor goes in `executors/` module alongside other executors
- Consider making this a decorator pattern for flexibility

### References

- [Source: _bmad-output/architecture.md#Error-Handling]
- [Source: src/adw/exceptions.py:272-386] - LLMTimeoutError, LLMRateLimitError
- [Source: src/adw/executors/base.py] - LLMExecutor Protocol
- [Source: src/adw/models/llm.py] - LLMResult model

---

## Dev Agent Record

### Context Reference

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Task 1: Created RetryConfig Pydantic model with max_retries, base_delay_seconds, max_delay_seconds, multiplier fields. Added validation for positive values and max_delay >= base_delay constraint.
- Task 2: Created RetryExecutor class that wraps any LLMExecutor and implements retry logic with exponential backoff and jitter.

### File List

- src/adw/models/config.py (modified) - Added RetryConfig model
- src/adw/models/__init__.py (modified) - Export RetryConfig
- src/adw/models/llm.py (modified) - Added attempt_count field to LLMResult
- src/adw/executors/retry.py (created) - RetryExecutor wrapper
- src/adw/executors/__init__.py (modified) - Export RetryExecutor
- tests/unit/models/__init__.py (created) - Test package init
- tests/unit/models/test_retry_config.py (created) - RetryConfig unit tests
- tests/unit/executors/test_retry.py (created) - RetryExecutor unit tests

---

## Dependencies

- **Depends On:** Story 3.2
- **Blocks:** None
- **Can Parallel With:** Story 3.4, Story 3.5

### Dependency Rationale
- Story 3.2: Retry logic wraps ClaudeCodeExecutor; needs base executor implementation first
- Can run in parallel with 3.4 and 3.5 since they all depend only on 3.2
