# Story 3.4: Implement Timeout Configuration and Enforcement

Status: done
Linear Issue: not-configured
Epic: 3 - Hook & Phase Execution
Created: 2025-12-31

---

## Story

As a developer,
I want timeouts enforced on LLM execution,
so that hung processes don't block the pipeline indefinitely.

## Acceptance Criteria

**Given** a timeout of 300 seconds in project config
**When** Claude Code execution exceeds 300 seconds
**Then** the process is killed and LLMTimeoutError is raised

**Given** no timeout configured
**When** execution proceeds
**Then** a default timeout of 600 seconds is used

**Given** timeout occurs
**When** error is raised
**Then** it includes elapsed time and configured timeout in the message

**Given** execution completes before timeout
**When** result is returned
**Then** duration_ms is included in the result

## Tasks / Subtasks

### Task 1: Define Timeout Constants
- [x] Add `DEFAULT_LLM_TIMEOUT = 600` constant to `src/adw/executors/claude_code.py`
- [x] Add `DEFAULT_HOOK_TIMEOUT = 60` constant to `src/adw/hooks/runner.py`
- [x] Document timeout hierarchy: parameter → config → default

### Task 2: Implement Timeout in ClaudeCodeExecutor
- [x] Update `_stream_subprocess()` to use `asyncio.wait_for()` with timeout
- [x] Handle `asyncio.TimeoutError` by killing process
- [x] Raise `LLMTimeoutError` with elapsed time and configured timeout
- [x] Track execution start time with `time.monotonic()`

### Task 3: Implement Timeout Resolution
- [x] If `timeout` parameter provided → use it
- [x] Else if `config.timeout_seconds` set → use it
- [x] Else → use `DEFAULT_LLM_TIMEOUT`
- [x] Add `_resolve_timeout(timeout: int | None) -> int` helper

### Task 4: Process Cleanup on Timeout
- [x] On timeout, call `process.kill()` to terminate subprocess
- [x] Await `process.wait()` to clean up zombie process
- [x] Capture any partial output before killing
- [x] Log timeout event with context

### Task 5: Update HookRunner for Timeout Support
- [x] Apply same timeout pattern to hook execution
- [x] Use `HookConfig.timeout_seconds` or `DEFAULT_HOOK_TIMEOUT`
- [x] Raise `HookError` with code `HOOK_TIMEOUT` on timeout

### Task 6: Track Duration in Results
- [x] Calculate `duration_ms = int((end - start) * 1000)`
- [x] Set `LLMResult.duration_ms` from actual execution time
- [x] Set `HookResult.duration_ms` from actual execution time
- [x] Duration should be set even on failure (for debugging)

### Task 7: Write Unit Tests
- [x] Create/update `tests/unit/executors/test_claude_code.py`
- [x] Test timeout is enforced correctly
- [x] Test default timeout used when none configured
- [x] Test timeout from config is respected
- [x] Test timeout parameter overrides config
- [x] Test process is killed on timeout
- [x] Test LLMTimeoutError includes elapsed time
- [x] Test duration_ms is set on success
- [x] Target: >90% coverage for timeout-related code (achieved: 91%)

### Task 8: Integration Tests
- [x] Test with slow subprocess (mock or real)
- [x] Verify process doesn't become zombie
- [x] Test partial output captured on timeout

---

## Developer Context

### Technical Requirements

- **Timeout Enforcement**: Use `asyncio.wait_for()` for async timeout
- **Process Termination**: Call `process.kill()` then `process.wait()`
- **Time Tracking**: Use `time.monotonic()` for accurate duration
- **Error Details**: Include both elapsed and configured timeout in error

### Architecture Compliance

**From architecture.md - LLMConfig:**
```python
class LLMConfig(BaseModel):
    path: str = Field(default="/usr/bin/claude")
    timeout_seconds: int = Field(default=300)
    max_retries: int = Field(default=3)
    model: str | None = Field(default=None)
```

**Timeout Pattern:**
```python
import asyncio
import time

async def _stream_subprocess(
    self,
    prompt: str,
    timeout: int,
) -> LLMResult:
    start_time = time.monotonic()

    process = await asyncio.create_subprocess_exec(...)

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        elapsed = int(time.monotonic() - start_time)
        process.kill()
        await process.wait()
        raise LLMTimeoutError(
            code="LLM_TIMEOUT",
            message=f"LLM execution timed out after {elapsed}s (limit: {timeout}s)",
            timeout_seconds=timeout,
            elapsed_seconds=elapsed,
            suggestion="Consider increasing timeout or simplifying prompt",
        )

    duration_ms = int((time.monotonic() - start_time) * 1000)
    return LLMResult(..., duration_ms=duration_ms)
```

**LLMTimeoutError already exists at `src/adw/exceptions.py`:**
```python
class LLMTimeoutError(LLMError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        timeout_seconds: int,
        elapsed_seconds: int,
        suggestion: str | None = None,
        recoverable: bool = True,
    ) -> None:
```

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Python | 3.13+ | `asyncio.wait_for()`, `asyncio.TimeoutError` |
| time | stdlib | `time.monotonic()` for accurate timing |

**Key APIs:**
```python
# Timeout enforcement
try:
    result = await asyncio.wait_for(coro, timeout=timeout)
except asyncio.TimeoutError:
    # Handle timeout

# Process termination
process.kill()      # Send SIGKILL
await process.wait()  # Wait for cleanup

# Duration tracking
start = time.monotonic()
# ... do work ...
duration_ms = int((time.monotonic() - start) * 1000)
```

### File Structure Requirements

**Files to modify:**
```
src/adw/
├── executors/
│   └── claude_code.py     # Update with timeout enforcement
├── hooks/
│   └── runner.py          # Update with timeout enforcement
```

**Constants to add:**
```python
# src/adw/executors/claude_code.py
DEFAULT_LLM_TIMEOUT = 600  # 10 minutes

# src/adw/hooks/runner.py
DEFAULT_HOOK_TIMEOUT = 60  # 1 minute
```

### Testing Requirements

**Test Framework:** pytest with pytest-asyncio

**Mocking slow processes:**
```python
@pytest.fixture
def slow_process_mock():
    """Mock that simulates a slow subprocess."""
    async def slow_communicate():
        await asyncio.sleep(10)  # Slow!
        return b"output", b""

    with patch("asyncio.create_subprocess_exec") as mock:
        process = AsyncMock()
        process.communicate = slow_communicate
        process.kill = MagicMock()
        process.wait = AsyncMock()
        mock.return_value = process
        yield mock, process
```

**Test timeout behavior:**
```python
@pytest.mark.asyncio
async def test_timeout_kills_process(slow_process_mock):
    mock, process = slow_process_mock
    executor = ClaudeCodeExecutor(LLMConfig(timeout_seconds=1))

    with pytest.raises(LLMTimeoutError) as exc_info:
        executor.execute("test prompt")

    assert exc_info.value.timeout_seconds == 1
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()
```

**Coverage Target:** >80% overall, >90% for timeout-related code

---

## Previous Story Intelligence

**From Story 3.1 (Shell Hooks):**
- Same timeout pattern applies to hook execution
- Use `asyncio.wait_for()` for async timeout enforcement

**From Story 3.2 (Claude Code Executor):**
- ClaudeCodeExecutor uses async subprocess
- Timeout needs to integrate with streaming logic

**Dependencies:**
- Story 3.4 depends on Story 3.2 (ClaudeCodeExecutor must exist)
- Story 3.4 can run in parallel with Story 3.3 and 3.5 (Wave 2)

---

## Git Intelligence

**Existing timeout configuration at `src/adw/models/config.py`:**
```python
class LLMConfig(BaseModel):
    timeout_seconds: int = Field(
        default=300,
        description="Maximum time for LLM calls in seconds",
    )

class HookConfig(BaseModel):
    timeout_seconds: int = Field(
        default=60, description="Maximum time for hook execution"
    )
```

Configuration already supports timeouts - just need to enforce them.

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:

1. **Async Model**: Use `asyncio.wait_for()` for timeout enforcement
2. **Exception Hierarchy**: Use `LLMTimeoutError` with `timeout_seconds` and `elapsed_seconds`
3. **Structured Logging**: Log timeout events with context
4. **Resource Cleanup**: Always kill and wait for processes

---

## Dev Notes

### Key Implementation Points

1. **Timeout Resolution** - Three-tier priority:
   ```python
   def _resolve_timeout(self, timeout: int | None) -> int:
       if timeout is not None:
           return timeout
       if self.config.timeout_seconds:
           return self.config.timeout_seconds
       return DEFAULT_LLM_TIMEOUT
   ```

2. **Process Cleanup** - Must await cleanup:
   ```python
   except asyncio.TimeoutError:
       process.kill()  # SIGKILL
       await process.wait()  # Wait for cleanup, prevent zombie
       raise LLMTimeoutError(...)
   ```

3. **Duration Always Set** - Even on partial completion:
   ```python
   finally:
       duration_ms = int((time.monotonic() - start_time) * 1000)
   ```

4. **Streaming Consideration** - If streaming, timeout applies to whole operation, not individual lines

### Project Structure Notes

- Alignment with unified project structure ✓
- Timeout logic integrates into existing executor and hook modules
- No new files needed, just modifications

### References

- [Source: _bmad-output/architecture.md#LLMConfig]
- [Source: src/adw/exceptions.py:272-330] - LLMTimeoutError
- [Source: src/adw/models/config.py:14-39] - LLMConfig with timeout_seconds
- [Source: src/adw/models/config.py:64-75] - HookConfig with timeout_seconds

---

## Dev Agent Record

### Context Reference

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

### Code Review (2025-12-31)

**Reviewer:** claude-opus-4-5-20251101

**Findings Fixed:**
1. **[HIGH] H1** - Empty File List → Added complete file list with changes
2. **[HIGH] H2** - Uncovered exception cleanup paths → Added `TestExceptionCleanup` tests
3. **[MEDIUM] M1** - Inconsistent time functions → Standardized on `time.monotonic()` in runner.py
4. **[MEDIUM] M2** - No test for duration_ms on failure → Added `TestDurationOnFailure` test
5. **[LOW] L2** - Missing logging in HookRunner → Added structured logging for timeout events

**Post-Review Coverage:**
- `claude_code.py`: 95%
- `hooks/runner.py`: 100%

### File List

| File | Changes |
|------|---------|
| `src/adw/executors/claude_code.py` | Added `DEFAULT_LLM_TIMEOUT=600`, `_resolve_timeout()` helper, timeout enforcement with `asyncio.wait_for()`, `LLMTimeoutError` handling, partial output capture |
| `src/adw/hooks/runner.py` | Added `DEFAULT_HOOK_TIMEOUT=60`, `_resolve_timeout()` helper, timeout enforcement with `asyncio.wait_for()`, `HookError` with `HOOK_TIMEOUT` code |
| `src/adw/exceptions.py` | Added `duration_ms` parameter to `HookError` for timeout debugging |
| `tests/unit/executors/test_claude_code.py` | Added `TestTimeoutEnforcement`, `TestTimeoutResolution`, `TestHookRunnerTimeoutResolution` test classes |
| `tests/integration/test_claude_code_executor.py` | Added `TestTimeoutIntegration` with slow subprocess, zombie prevention, and hook timeout tests |

---

## Dependencies

- **Depends On:** Story 3.2
- **Blocks:** None
- **Can Parallel With:** Story 3.3, Story 3.5

### Dependency Rationale
- Story 3.2: Timeout enforcement integrates into ClaudeCodeExecutor's subprocess handling
- Can run in parallel with 3.3 and 3.5 since they all depend only on 3.2
