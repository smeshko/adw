# Story 3.2: Implement Claude Code Executor with Streaming

Status: ready-for-dev
Linear Issue: not-configured
Epic: 3 - Hook & Phase Execution
Created: 2025-12-31

---

## Story

As a developer,
I want to invoke Claude Code CLI and stream its output in real-time,
so that users see LLM responses as they're generated.

## Acceptance Criteria

**Given** a rendered prompt
**When** I call the Claude Code executor
**Then** it spawns `claude` (or configured path) as subprocess

**Given** Claude Code is producing output
**When** streaming is enabled
**Then** output appears in the console in real-time via Rich
**And** artifact writes don't block the stream (NFR3)

**Given** the configured Claude Code path doesn't exist
**When** execution is attempted
**Then** LLMError is raised with code "CLAUDE_NOT_FOUND" and suggestion to configure path

**Given** Claude Code execution completes
**When** I inspect the result
**Then** it includes: full content, tool_calls list, tokens_used, duration_ms

**Given** Claude Code respects the `--print` flag
**When** streaming output
**Then** tool calls are captured separately from text content

## Tasks / Subtasks

### Task 1: Create ClaudeCodeExecutor Class
- [ ] Create `src/adw/executors/claude_code.py`
- [ ] Implement `ClaudeCodeExecutor` class implementing `LLMExecutor` Protocol
- [ ] Constructor takes `LLMConfig` for configuration (path, timeout, etc.)
- [ ] Implement `execute(prompt: str, *, timeout: int | None = None) -> LLMResult`

### Task 2: Implement Subprocess Execution
- [ ] Use `asyncio.create_subprocess_exec()` for subprocess spawning
- [ ] Pass `--print` flag to Claude Code for machine-readable output
- [ ] Set up stdout and stderr pipes for capture
- [ ] Handle process execution with `asyncio.run()` wrapper

### Task 3: Implement Real-Time Streaming
- [ ] Read stdout line-by-line as it becomes available
- [ ] Forward output to Rich console in real-time
- [ ] Use `asyncio.create_task()` for concurrent output processing
- [ ] Ensure artifact writes don't block stream (NFR3)

### Task 4: Parse Claude Code Output
- [ ] Parse `--print` flag JSON output format
- [ ] Extract text content from output
- [ ] Extract tool calls from output
- [ ] Extract token usage if available
- [ ] Build `LLMResult` from parsed output

### Task 5: Implement Error Handling
- [ ] Check if Claude path exists before execution
- [ ] Raise `LLMError` with code `CLAUDE_NOT_FOUND` if not found
- [ ] Handle subprocess errors and convert to `LLMError`
- [ ] Include helpful suggestions in error messages

### Task 6: Implement Path Configuration
- [ ] Use `LLMConfig.path` for Claude executable path
- [ ] Default to "claude" (assumes in PATH)
- [ ] Support absolute paths from config
- [ ] Use `shutil.which()` to verify executable exists

### Task 7: Write Unit Tests
- [ ] Create `tests/unit/executors/test_claude_code.py`
- [ ] Mock subprocess execution for deterministic testing
- [ ] Test successful execution returns `LLMResult`
- [ ] Test missing Claude raises `LLMError` with `CLAUDE_NOT_FOUND`
- [ ] Test output parsing extracts content and tool calls
- [ ] Test timeout handling (integration with Story 3.4)
- [ ] Target: >90% coverage for claude_code module

### Task 8: Integration Tests
- [ ] Create `tests/integration/test_claude_code_executor.py`
- [ ] Test with real Claude Code CLI (if available)
- [ ] Skip if Claude not installed

---

## Developer Context

### Technical Requirements

- **Async Pattern**: Use `asyncio.create_subprocess_exec()` for subprocess
- **Streaming**: Read stdout line-by-line using `readline()` for real-time output
- **Console Output**: Use Rich `Console.print()` for real-time display
- **Process Handling**: Properly cleanup subprocess on error or timeout
- **Non-blocking**: Use async tasks for concurrent output processing (NFR3)

### Architecture Compliance

**From architecture.md - Async Model Decision:**
```python
# Executor (async internally)
def execute(self, prompt: str) -> LLMResult:
    return asyncio.run(self._stream_subprocess(prompt))
```

**From architecture.md - Claude Code CLI Invocation:**

**Default:** Invoke `claude` assuming it's in PATH.

**Configuration:** Users can override in config.yaml:
```yaml
llm:
  claude_code:
    path: /custom/path/to/claude
```

**Error Handling:** If `claude` not found, raise `ConfigError` with suggestion to install Claude Code or configure path.

**LLMExecutor Protocol already exists at `src/adw/executors/base.py`:**
```python
@runtime_checkable
class LLMExecutor(Protocol):
    def execute(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
    ) -> LLMResult:
        ...
```

**LLMResult already exists at `src/adw/models/llm.py`:**
```python
class LLMResult(BaseModel):
    success: bool
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tokens_used: int = 0
    duration_ms: int = 0
    error: str | None = None
```

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Python | 3.13+ | `asyncio.create_subprocess_exec()` for subprocess |
| Rich | 14.1.0 | Real-time console output streaming |
| shutil | stdlib | `shutil.which()` for executable discovery |

**Key Claude Code CLI flags:**
- `--print`: Output in machine-readable JSON format
- `--timeout N`: Timeout in seconds
- `--model MODEL`: Model to use (optional)

**Example invocation:**
```bash
claude --print "Your prompt here"
```

**Async subprocess pattern:**
```python
import asyncio
import time

async def _stream_subprocess(
    self,
    prompt: str,
    timeout: int | None,
) -> LLMResult:
    start_time = time.monotonic()

    process = await asyncio.create_subprocess_exec(
        self.config.path,
        "--print",
        prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Stream output in real-time
    content_lines = []
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded = line.decode()
        content_lines.append(decoded)
        self.console.print(decoded, end="")

    await process.wait()
    duration_ms = int((time.monotonic() - start_time) * 1000)

    return LLMResult(
        success=process.returncode == 0,
        content="".join(content_lines),
        duration_ms=duration_ms,
    )
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── executors/
│   ├── __init__.py        # Update exports
│   ├── base.py            # Already exists
│   ├── mock.py            # Already exists
│   └── claude_code.py     # NEW: ClaudeCodeExecutor

tests/
├── unit/
│   └── executors/
│       ├── __init__.py    # May need creation
│       ├── test_mock.py   # Already exists
│       └── test_claude_code.py # NEW
├── integration/
│   └── test_claude_code_executor.py # NEW
```

**Naming conventions (PEP 8):**
- Class: `ClaudeCodeExecutor`
- Functions: `execute()`, `_stream_subprocess()`
- Constants: `DEFAULT_TIMEOUT = 300`

### Testing Requirements

**Test Framework:** pytest with pytest-asyncio for async tests

**Mocking Strategy:**
```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_subprocess():
    """Mock asyncio subprocess for deterministic tests."""
    with patch("asyncio.create_subprocess_exec") as mock:
        process = AsyncMock()
        process.stdout.readline = AsyncMock(side_effect=[
            b"Line 1\n",
            b"Line 2\n",
            b"",  # EOF
        ])
        process.wait = AsyncMock(return_value=None)
        process.returncode = 0
        mock.return_value = process
        yield mock
```

**Coverage Target:** >80% overall, >90% for executors module

---

## Previous Story Intelligence

**From Story 3.1 (Shell Hooks):**
- Async subprocess pattern established
- Use `asyncio.create_subprocess_exec()` with `wait_for()` for timeouts
- Error handling pattern: catch subprocess errors, re-raise as typed exceptions

**Dependencies:**
- Story 3.2 can run in parallel with Story 3.1 (Wave 1)
- Story 3.3 (retry logic) depends on this story
- Story 3.4 (timeout) depends on this story
- Story 3.5 (token tracking) depends on this story

---

## Git Intelligence

Recent commits show:
- Story 2-3 and 2-4 recently completed
- MockExecutor already implemented and tested
- LLMExecutor Protocol established

**Existing code to integrate with:**
- `src/adw/executors/base.py` - Protocol definition
- `src/adw/executors/mock.py` - Reference implementation
- `src/adw/models/llm.py` - LLMResult, ToolCall models
- `src/adw/models/config.py` - LLMConfig model

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **Async Model**: "Sync with Async Islands" - `asyncio.run()` wrapper for async internals
2. **Exception Hierarchy**: Use `LLMError` from `src/adw/exceptions.py`
3. **Rich Output**: Use `Console.print()` for all CLI output
4. **Structured Logging**: Log with structured context fields
5. **Type Annotations**: Full annotations with modern `|` syntax

---

## Dev Notes

### Key Implementation Points

1. **Protocol Compliance** - Must implement `LLMExecutor` Protocol:
   ```python
   class ClaudeCodeExecutor:
       def execute(
           self,
           prompt: str,
           *,
           timeout: int | None = None,
       ) -> LLMResult:
           return asyncio.run(self._stream_subprocess(prompt, timeout))
   ```

2. **Path Verification** - Check executable exists before running:
   ```python
   import shutil

   def _verify_claude_path(self) -> Path:
       if not shutil.which(self.config.path):
           raise LLMError(
               code="CLAUDE_NOT_FOUND",
               message=f"Claude Code CLI not found at '{self.config.path}'",
               suggestion="Install Claude Code or configure llm.claude_code.path in adw.yaml",
               recoverable=False,
           )
       return Path(self.config.path)
   ```

3. **Real-Time Streaming** - Use Rich for live output:
   ```python
   from rich.console import Console
   from rich.live import Live

   async def _stream_with_live(self, process, console: Console):
       with Live(console=console, refresh_per_second=4) as live:
           # Update display as lines arrive
           pass
   ```

4. **Output Parsing** - Parse Claude's `--print` JSON format:
   ```python
   import json

   def _parse_output(self, raw_output: str) -> tuple[str, list[ToolCall]]:
       # Parse JSON output from --print flag
       # Extract content and tool_calls
       pass
   ```

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming) ✓
- `executors/` module already has `base.py` and `mock.py` - add `claude_code.py`
- Follow MockExecutor patterns for consistency

### References

- [Source: _bmad-output/architecture.md#Async-Model]
- [Source: _bmad-output/architecture.md#Claude-Code-CLI-Invocation]
- [Source: src/adw/executors/base.py] - LLMExecutor Protocol
- [Source: src/adw/executors/mock.py] - MockExecutor reference
- [Source: src/adw/models/llm.py] - LLMResult, ToolCall models
- [Source: src/adw/models/config.py:14-39] - LLMConfig model

---

## Dev Agent Record

### Context Reference

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** None
- **Blocks:** Story 3.3, Story 3.4, Story 3.5
- **Can Parallel With:** Story 3.1

### Dependency Rationale
- No dependencies - this story can start immediately in Wave 1
- Story 3.3: Retry logic requires the base ClaudeCodeExecutor to wrap
- Story 3.4: Timeout enforcement requires the base executor implementation
- Story 3.5: Token tracking depends on LLMResult structure from executor output parsing
