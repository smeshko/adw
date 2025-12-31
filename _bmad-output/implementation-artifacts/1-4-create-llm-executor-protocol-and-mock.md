# Story 1.4: Create LLM Executor Protocol and MockExecutor

Status: ready-for-dev
Linear Issue: not-configured
Epic: 1 - Project Scaffolding & Test Infrastructure
Created: 2025-12-31

---

## Story

As a developer,
I want a Protocol-based LLM executor interface with a MockExecutor implementation,
so that I can write deterministic tests without calling Claude Code.

## Acceptance Criteria

**Given** the executors module at `src/adw/executors/`
**When** I import LLMExecutor
**Then** it is a Protocol with method: `execute(prompt: str, *, timeout: int | None = None) -> LLMResult`

**Given** an LLMResult model
**When** I inspect its fields
**Then** it includes: success (bool), content (str), tool_calls (list), tokens_used (int), duration_ms (int), error (LLMError | None)

**Given** a MockExecutor instance
**When** I call `configure_responses([{"content": "response1"}, {"content": "response2"}])`
**Then** subsequent execute() calls return those responses in order

**Given** a MockExecutor with configured failures
**When** I call `configure_failures([LLMTimeoutError("timeout"), None])`
**Then** the first execute() raises LLMTimeoutError
**And** the second execute() succeeds

**Given** a MockExecutor instance
**When** I inspect after multiple calls
**Then** I can access: call_count, last_prompt, all_prompts list for assertions

## Tasks / Subtasks

### Task 1: Create Executors Package Structure
- [x] Create `src/adw/executors/__init__.py` with exports
- [x] Create `src/adw/executors/base.py` for Protocol and models
- [x] Create `src/adw/executors/mock.py` for MockExecutor

### Task 2: Define LLMExecutor Protocol
- [x] Define LLMExecutor as typing.Protocol
- [x] Define execute() method signature
- [x] Add type hints for all parameters and return type

### Task 3: Create LLMResult Model
- [x] Add LLMResult to `src/adw/models/` (or executors/result.py)
- [x] Define all required fields with types
- [x] Add ToolCall model for tool call tracking

### Task 4: Implement MockExecutor
- [ ] Create MockExecutor class implementing LLMExecutor
- [ ] Implement configure_responses() method
- [ ] Implement configure_failures() method
- [ ] Implement execute() method with queue handling
- [ ] Track call_count, last_prompt, all_prompts

### Task 5: Add Assertion Helpers
- [ ] Add assert_called_once() method
- [ ] Add assert_called_with(prompt) method
- [ ] Add reset() method to clear state

### Task 6: Write Unit Tests
- [ ] Test MockExecutor response queuing
- [ ] Test MockExecutor failure injection
- [ ] Test call tracking (count, prompts)
- [ ] Test Protocol compliance
- [ ] Test edge cases (empty queue, mixed success/failure)

---

## Developer Context

### Technical Requirements

**From Architecture Document:**
- Protocol-based abstraction for LLM executors
- MockExecutor for deterministic testing
- LLMResult captures success, content, tool_calls, tokens, duration

**From NFR22 (Test Coverage):**
- >80% test coverage for core logic
- MockExecutor enables testing without Claude Code

**Async Model (ARCH-3):**
- Executor's execute() is synchronous externally
- May use asyncio internally (for real Claude Code executor)
- MockExecutor is fully synchronous

### Architecture Compliance

**Executor Protocol Pattern:**
```python
from typing import Protocol

class LLMExecutor(Protocol):
    def execute(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
    ) -> LLMResult:
        """Execute prompt and return result."""
        ...
```

**Project Structure:**
```
src/adw/executors/
├── __init__.py        # Exports LLMExecutor, MockExecutor, LLMResult
├── base.py            # LLMExecutor Protocol
├── result.py          # LLMResult, ToolCall models
└── mock.py            # MockExecutor implementation
```

### Library & Framework Requirements

**Protocol Definition:**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMExecutor(Protocol):
    """Protocol for LLM execution backends."""

    def execute(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
    ) -> "LLMResult":
        """Execute a prompt and return the result.

        Args:
            prompt: The prompt to send to the LLM
            timeout: Optional timeout in seconds

        Returns:
            LLMResult with success status and content

        Raises:
            LLMTimeoutError: If execution times out
            LLMRateLimitError: If rate limited
            LLMError: For other LLM errors
        """
        ...
```

**LLMResult Model:**
```python
from pydantic import BaseModel
from datetime import datetime

class ToolCall(BaseModel):
    """A tool call made by the LLM."""
    tool_name: str
    arguments: dict[str, Any]
    result_summary: str | None = None

class LLMResult(BaseModel):
    """Result from an LLM execution."""
    success: bool
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tokens_used: int = 0
    duration_ms: int = 0
    error: str | None = None
```

**MockExecutor Implementation:**
```python
from collections import deque
from adw.exceptions import LLMError

class MockExecutor:
    """Mock LLM executor for testing."""

    def __init__(self) -> None:
        self._responses: deque[LLMResult] = deque()
        self._failures: deque[LLMError | None] = deque()
        self._all_prompts: list[str] = []

    def configure_responses(self, responses: list[dict]) -> None:
        """Queue responses for subsequent execute() calls."""
        self._responses.clear()
        for r in responses:
            self._responses.append(LLMResult(
                success=True,
                content=r.get("content", ""),
                tool_calls=r.get("tool_calls", []),
                tokens_used=r.get("tokens_used", 100),
                duration_ms=r.get("duration_ms", 1000),
            ))

    def configure_failures(self, failures: list[LLMError | None]) -> None:
        """Queue failures for subsequent execute() calls.

        None means success, LLMError subclass means failure.
        """
        self._failures.clear()
        self._failures.extend(failures)

    def execute(self, prompt: str, *, timeout: int | None = None) -> LLMResult:
        """Execute mock prompt."""
        self._all_prompts.append(prompt)

        # Check for configured failure
        if self._failures:
            failure = self._failures.popleft()
            if failure is not None:
                raise failure

        # Return configured response
        if self._responses:
            return self._responses.popleft()

        # Default response
        return LLMResult(
            success=True,
            content="Mock response",
            tokens_used=50,
            duration_ms=100,
        )

    @property
    def call_count(self) -> int:
        return len(self._all_prompts)

    @property
    def last_prompt(self) -> str | None:
        return self._all_prompts[-1] if self._all_prompts else None

    @property
    def all_prompts(self) -> list[str]:
        return self._all_prompts.copy()

    def reset(self) -> None:
        """Reset all state."""
        self._responses.clear()
        self._failures.clear()
        self._all_prompts.clear()
```

### File Structure Requirements

**Files to Create:**

```
src/adw/executors/
├── __init__.py        # Re-exports
├── base.py            # LLMExecutor Protocol
├── result.py          # LLMResult, ToolCall models (OR in models/)
└── mock.py            # MockExecutor

src/adw/models/
└── llm.py             # Alternative: LLMResult, ToolCall here
```

**Note:** LLMResult and ToolCall could be in either:
- `src/adw/executors/result.py` (close to executor)
- `src/adw/models/llm.py` (centralized with other models)

Per architecture (ARCH-11), models should be in models/, so prefer:
```python
# src/adw/models/llm.py
from pydantic import BaseModel

class ToolCall(BaseModel):
    ...

class LLMResult(BaseModel):
    ...
```

### Testing Requirements

**Test File:** `tests/unit/executors/test_mock.py`

**Tests to Write:**

```python
import pytest
from adw.executors import MockExecutor, LLMExecutor
from adw.models import LLMResult
from adw.exceptions import LLMTimeoutError, LLMRateLimitError

def test_mock_executor_protocol_compliance():
    """MockExecutor implements LLMExecutor protocol."""
    executor = MockExecutor()
    assert isinstance(executor, LLMExecutor)

def test_mock_executor_default_response():
    """MockExecutor returns default response."""
    executor = MockExecutor()
    result = executor.execute("test prompt")
    assert result.success is True
    assert "Mock" in result.content

def test_mock_executor_configured_responses():
    """MockExecutor returns configured responses in order."""
    executor = MockExecutor()
    executor.configure_responses([
        {"content": "first"},
        {"content": "second"},
    ])

    r1 = executor.execute("prompt 1")
    r2 = executor.execute("prompt 2")

    assert r1.content == "first"
    assert r2.content == "second"

def test_mock_executor_configured_failures():
    """MockExecutor raises configured failures."""
    executor = MockExecutor()
    executor.configure_failures([
        LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=300,
        ),
        None,  # Success
    ])

    with pytest.raises(LLMTimeoutError):
        executor.execute("prompt 1")

    result = executor.execute("prompt 2")
    assert result.success is True

def test_mock_executor_call_tracking():
    """MockExecutor tracks all calls."""
    executor = MockExecutor()
    executor.execute("first prompt")
    executor.execute("second prompt")

    assert executor.call_count == 2
    assert executor.last_prompt == "second prompt"
    assert executor.all_prompts == ["first prompt", "second prompt"]

def test_mock_executor_reset():
    """MockExecutor reset clears all state."""
    executor = MockExecutor()
    executor.configure_responses([{"content": "test"}])
    executor.execute("prompt")

    executor.reset()

    assert executor.call_count == 0
    assert executor.last_prompt is None
```

---

## Previous Story Intelligence

**Depends on Story 1.2:**
- LLMResult is a Pydantic model (goes in models/)
- ToolCall is a Pydantic model

**Depends on Story 1.3:**
- LLMError, LLMTimeoutError, LLMRateLimitError needed for failures
- Exception hierarchy must exist

**Can Run After:**
- Story 1.2 (models)
- Story 1.3 (exceptions)

**Required By:**
- Story 1.5 (mock_executor fixture)
- All subsequent stories that test LLM interaction

---

## Git Intelligence

**Expected Prior Commits:**
- Story 1.1: Project scaffolding
- Story 1.2: Pydantic models
- Story 1.3: Exception hierarchy

**Recommended Commit Pattern:**
```
feat(executors): add LLMExecutor protocol and MockExecutor

- Define LLMExecutor protocol for LLM abstraction
- Add LLMResult and ToolCall models
- Implement MockExecutor for testing
- Add response/failure configuration
- Add call tracking (count, prompts)
- Add unit tests for MockExecutor
```

---

## Latest Technical Information

**Python Protocol (PEP 544):**
- Use `typing.Protocol` for structural subtyping
- Use `@runtime_checkable` for isinstance() checks
- Protocol methods don't need implementation

**Testing Best Practices:**
- MockExecutor enables testing without external dependencies
- Configurable responses for different scenarios
- Failure injection for error handling tests
- Call tracking for assertion helpers

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Protocol-based abstractions for testability
- Models in src/adw/models/
- Exception hierarchy for errors

---

## Dev Notes

### MockExecutor Design Principles

1. **Configurable Responses:** Queue responses for deterministic tests
2. **Failure Injection:** Test error handling paths
3. **Call Tracking:** Verify prompts were sent correctly
4. **Reset Capability:** Clean state between tests

### Usage in Tests

```python
@pytest.fixture
def mock_executor():
    """Provides a fresh MockExecutor for each test."""
    return MockExecutor()

def test_phase_runner_success(mock_executor):
    mock_executor.configure_responses([
        {"content": "Generated code here..."}
    ])

    runner = PhaseRunner(executor=mock_executor)
    result = runner.run("build", context)

    assert result.status == PhaseStatus.COMPLETED
    assert mock_executor.call_count == 1

def test_phase_runner_retry_on_timeout(mock_executor):
    mock_executor.configure_failures([
        LLMTimeoutError(...),  # First fails
        None,  # Second succeeds
    ])
    mock_executor.configure_responses([
        {"content": "Success after retry"}
    ])

    runner = PhaseRunner(executor=mock_executor)
    result = runner.run("build", context)

    assert result.status == PhaseStatus.COMPLETED
    assert mock_executor.call_count == 2
```

### References

- [Source: _bmad-output/architecture.md#LLM-Execution]
- [Source: _bmad-output/architecture.md#Async-Model]
- [Source: _bmad-output/prd.md#LLM-Execution]

---

## Dev Agent Record

### Context Reference

Story context created by create-epic workflow

### Agent Model Used

Claude Opus 4.5 (create-epic autonomous orchestrator)

### Completion Notes List

(To be filled by dev agent after implementation)

### File List

(To be filled by dev agent after implementation)

---

## Dependencies

- **Depends On:** Story 1.1, Story 1.2, Story 1.3
- **Blocks:** Story 1.5
- **Can Parallel With:** None

### Dependency Rationale
- Story 1.1: Requires project structure with src/adw/executors/ directory
- Story 1.2: LLMResult is a Pydantic model in models/
- Story 1.3: LLMError, LLMTimeoutError, LLMRateLimitError needed for failure injection
- Story 1.5: MockExecutor needed for mock_executor fixture in test infrastructure
