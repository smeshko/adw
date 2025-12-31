# Story 1.3: Implement Custom Exception Hierarchy

Status: ready-for-dev
Linear Issue: not-configured
Epic: 1 - Project Scaffolding & Test Infrastructure
Created: 2025-12-31

---

## Story

As a developer,
I want a structured exception hierarchy with typed errors,
so that error handling is consistent and errors are actionable.

## Acceptance Criteria

**Given** the exceptions module at `src/adw/exceptions.py`
**When** I import ADWError
**Then** it is the base class with: code (str), message (str), suggestion (str|None), recoverable (bool)

**Given** the exception hierarchy
**When** I inspect available exceptions
**Then** these typed subclasses exist:
  - ConfigError (for configuration issues)
  - HookError (for shell hook failures, includes phase field)
  - LLMError (for Claude Code issues, includes subclasses: LLMTimeoutError, LLMRateLimitError)
  - StateError (for state persistence issues)
  - ValidationError (for schema validation failures)

**Given** any ADWError subclass
**When** I raise it with required fields
**Then** it formats to a user-friendly message suitable for Rich Panel display

**Given** a HookError instance
**When** I access its attributes
**Then** it includes the phase field indicating which phase failed

## Tasks / Subtasks

### Task 1: Create ADWError Base Class
- [ ] Define ADWError with code, message, suggestion, recoverable attributes
- [ ] Implement __str__ for user-friendly formatting
- [ ] Implement to_dict() for structured logging
- [ ] Add type hints for all attributes

### Task 2: Implement ConfigError
- [ ] Create ConfigError subclass for configuration issues
- [ ] Set default recoverable=False
- [ ] Add common error codes: CONFIG_NOT_FOUND, INVALID_CONFIG, COMMAND_NOT_FOUND

### Task 3: Implement HookError
- [ ] Create HookError subclass with phase field
- [ ] Add exit_code field for hook exit status
- [ ] Add stdout/stderr fields for debugging
- [ ] Add common error codes: HOOK_FAILED, HOOK_TIMEOUT

### Task 4: Implement LLMError Hierarchy
- [ ] Create LLMError base class for Claude Code issues
- [ ] Create LLMTimeoutError subclass (recoverable=True)
- [ ] Create LLMRateLimitError subclass (recoverable=True)
- [ ] Add retry_after field for rate limit errors

### Task 5: Implement StateError
- [ ] Create StateError for state persistence issues
- [ ] Add common error codes: CONTEXT_CORRUPTED, SNAPSHOT_FAILED, RUN_NOT_FOUND

### Task 6: Implement ValidationError
- [ ] Create ValidationError for schema validation failures
- [ ] Add field_errors list for field-level messages
- [ ] Add schema_path for reference to failed schema

### Task 7: Write Unit Tests
- [ ] Test ADWError formatting
- [ ] Test all subclass creation with required fields
- [ ] Test error code uniqueness
- [ ] Test recoverable flag inheritance
- [ ] Test phase field on HookError

---

## Developer Context

### Technical Requirements

**From Architecture Document (ARCH-4):**
- Custom exception hierarchy with ADWError base
- All errors must have: code, message, suggestion, recoverable
- Use typed exceptions for different failure categories
- Errors must be displayable in Rich Panels

**Error Handling Pattern:**
```python
# CORRECT - use exception hierarchy
raise HookError(
    code="HOOK_FAILED",
    message="Pre-hook exited with code 1",
    suggestion="Check hook script for errors",
    recoverable=False,
    phase="build"
)

# WRONG
raise Exception("Hook failed")  # NO - use hierarchy
```

### Architecture Compliance

**Exception Hierarchy from Architecture:**
```
ADWError (base)
├── ConfigError
├── CommandError
├── HookError
├── LLMError
│   ├── LLMTimeoutError
│   └── LLMRateLimitError
├── PhaseError
├── ValidationError
└── StateError
```

**Required Attributes:**
| Attribute | Type | Description |
|-----------|------|-------------|
| code | str | Error code like "HOOK_FAILED" |
| message | str | Human-readable message |
| suggestion | str \| None | Actionable next step |
| recoverable | bool | Can this be retried? |

**Additional Attributes by Type:**
- HookError: `phase: str`, `exit_code: int`, `stdout: str`, `stderr: str`
- LLMError: (base for LLM issues)
- LLMTimeoutError: `timeout_seconds: int`, `elapsed_seconds: int`
- LLMRateLimitError: `retry_after: int | None`
- ValidationError: `field_errors: list[dict]`

### Library & Framework Requirements

**Exception Implementation Pattern:**
```python
from dataclasses import dataclass
from typing import Any

class ADWError(Exception):
    """Base exception for all ADW errors."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        self.code = code
        self.message = message
        self.suggestion = suggestion
        self.recoverable = recoverable
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
            "recoverable": self.recoverable,
        }


class HookError(ADWError):
    """Error from hook script execution."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        phase: str,
        exit_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        super().__init__(code, message, suggestion=suggestion, recoverable=recoverable)
        self.phase = phase
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
```

### File Structure Requirements

**File to Create:**
```
src/adw/exceptions.py
```

**Exception Classes to Define:**
1. `ADWError` - Base class
2. `ConfigError` - Configuration issues
3. `CommandError` - Command resolution failures
4. `HookError` - Pre/post hook failures
5. `LLMError` - Base for LLM issues
6. `LLMTimeoutError` - Timeout during LLM call
7. `LLMRateLimitError` - Rate limited by API
8. `PhaseError` - Phase execution failures
9. `ValidationError` - Schema validation failures
10. `StateError` - State persistence/loading failures

### Testing Requirements

**Test File:** `tests/unit/test_exceptions.py`

**Tests to Write:**

```python
import pytest
from adw.exceptions import (
    ADWError, ConfigError, HookError, LLMError,
    LLMTimeoutError, LLMRateLimitError, StateError, ValidationError
)

def test_adw_error_base():
    """ADWError has required attributes."""
    error = ADWError(
        code="TEST_ERROR",
        message="Test message",
        suggestion="Try again",
        recoverable=True,
    )
    assert error.code == "TEST_ERROR"
    assert error.message == "Test message"
    assert error.suggestion == "Try again"
    assert error.recoverable is True

def test_adw_error_str_format():
    """ADWError formats nicely for display."""
    error = ADWError(
        code="TEST_ERROR",
        message="Something failed",
        suggestion="Check logs",
    )
    formatted = str(error)
    assert "[TEST_ERROR]" in formatted
    assert "Something failed" in formatted
    assert "Suggestion: Check logs" in formatted

def test_hook_error_with_phase():
    """HookError includes phase field."""
    error = HookError(
        code="HOOK_FAILED",
        message="Pre-hook failed",
        phase="build",
        exit_code=1,
    )
    assert error.phase == "build"
    assert error.exit_code == 1

def test_llm_timeout_error_recoverable():
    """LLMTimeoutError is recoverable by default."""
    error = LLMTimeoutError(
        code="LLM_TIMEOUT",
        message="Timeout after 300s",
        timeout_seconds=300,
        elapsed_seconds=300,
    )
    assert error.recoverable is True

def test_config_error_not_recoverable():
    """ConfigError is not recoverable by default."""
    error = ConfigError(
        code="CONFIG_NOT_FOUND",
        message="Config file not found",
    )
    assert error.recoverable is False

def test_to_dict():
    """Errors serialize to dict for logging."""
    error = ADWError(
        code="TEST",
        message="Test",
        suggestion="Fix it",
        recoverable=True,
    )
    d = error.to_dict()
    assert d["code"] == "TEST"
    assert d["recoverable"] is True
```

---

## Previous Story Intelligence

**Depends on Story 1.1:**
- Project structure must exist
- `src/adw/exceptions.py` location defined

**Can Run in Parallel with Story 1.2:**
- No dependency on models
- Models (1.2) and exceptions (1.3) are independent

**Required By:**
- Story 1.4 (MockExecutor) - needs LLMError hierarchy
- Story 1.5 (Test fixtures) - needs exception types

---

## Git Intelligence

**Expected Prior Commits:**
- Story 1.1: Project scaffolding

**Recommended Commit Pattern:**
```
feat(exceptions): implement ADWError exception hierarchy

- Add ADWError base class with code, message, suggestion
- Add ConfigError for configuration issues
- Add HookError with phase and exit_code fields
- Add LLMError hierarchy (Timeout, RateLimit)
- Add StateError and ValidationError
- Add unit tests for all exception types
```

---

## Latest Technical Information

**Python Exception Best Practices:**
- Inherit from Exception (or subclass of Exception)
- Call super().__init__() in __init__
- Override __str__ for custom formatting
- Keep exception classes focused and specific

**Rich Panel Display:**
```python
from rich.console import Console
from rich.panel import Panel

console = Console()

def display_error(error: ADWError) -> None:
    title = f"Error [{error.code}]"
    body = error.message
    if error.suggestion:
        body += f"\n\n[bold]Suggestion:[/bold] {error.suggestion}"
    console.print(Panel(body, title=title, border_style="red"))
```

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Never raise bare `Exception` - use ADWError hierarchy
- All errors must have code, message, suggestion fields
- Use Rich for error display in CLI

---

## Dev Notes

### Error Codes Convention

**Format:** `CATEGORY_SPECIFIC_ISSUE`

**Examples:**
- `CONFIG_NOT_FOUND` - Configuration file not found
- `CONFIG_INVALID` - Configuration file has invalid content
- `HOOK_FAILED` - Hook script exited with non-zero
- `HOOK_TIMEOUT` - Hook script exceeded timeout
- `LLM_TIMEOUT` - LLM call timed out
- `LLM_RATE_LIMIT` - LLM API rate limited
- `STATE_CORRUPTED` - State file is corrupted
- `RUN_NOT_FOUND` - Run ID doesn't exist
- `VALIDATION_FAILED` - Schema validation failed

### Recoverable vs Non-Recoverable

**Recoverable (retry makes sense):**
- LLMTimeoutError
- LLMRateLimitError
- Transient network errors

**Non-Recoverable (retry won't help):**
- ConfigError
- ValidationError
- StateError (usually)
- HookError (usually)

### References

- [Source: _bmad-output/architecture.md#Error-Handling]
- [Source: _bmad-output/architecture.md#Implementation-Patterns-&-Consistency-Rules]
- [Source: _bmad-output/project-context.md#Exception-Hierarchy]

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

- **Depends On:** Story 1.1
- **Blocks:** Story 1.4, Story 1.5
- **Can Parallel With:** Story 1.2

### Dependency Rationale
- Story 1.1: Requires project structure with src/adw/exceptions.py location defined
- Story 1.4: LLMError and subclasses needed by executor for failure injection
- Story 1.5: Exception types needed for test error handling scenarios
