# Story 3.6: Security Hook Infrastructure

Status: ready-for-dev
Linear Issue: not-configured
Epic: 3 - Hook & Phase Execution
Created: 2026-01-03

---

## Story

As a developer,
I want ADW to block dangerous LLM tool calls,
So that automated code generation cannot accidentally destroy my project.

## Acceptance Criteria

**Given** LLM attempts to execute `rm -rf` or similar destructive commands
**When** the tool call is intercepted
**Then** the call is blocked and a warning is logged

**Given** LLM attempts to read `.env` or `.adw.env` files
**When** the tool call is intercepted
**Then** the call is blocked (except for `.env.example` or `.env.sample`)

**Given** any tool call is executed
**When** execution completes
**Then** the tool name, arguments, and result are logged to `tools.log`

**Given** security patterns are configurable
**When** `project.yaml` includes `security.blocked_patterns`
**Then** custom patterns are also blocked

## Tasks / Subtasks

### Task 1: Create Security Models
- [ ] Create `src/adw/models/security.py` with:
  - `BlockedPattern` model (pattern, description, severity)
  - `SecurityConfig` model (blocked_patterns, allow_dangerous, blocked_env_files)
  - `ToolCallLog` model (timestamp, tool_name, arguments, result_summary, duration_ms, blocked, block_reason)
- [ ] Add SecurityConfig to project configuration loading

### Task 2: Create SecurityError Exception
- [ ] Add `SecurityError` to `src/adw/exceptions.py`
  - code: e.g., "DANGEROUS_COMMAND_BLOCKED"
  - pattern_matched: The pattern that triggered the block
  - tool_name: The tool that was blocked
  - suggestion: How to override if needed

### Task 3: Implement Security Interceptor
- [ ] Create `src/adw/security/__init__.py`
- [ ] Create `src/adw/security/interceptor.py` with:
  - `SecurityInterceptor` class
  - `check_tool_call(tool_name: str, arguments: dict) -> SecurityCheckResult`
  - `is_blocked(command: str) -> tuple[bool, BlockedPattern | None]`
  - Default blocked patterns (rm -rf, .env access, git push --force)
- [ ] Create `src/adw/security/patterns.py` with:
  - Default security patterns (BLOCKED_SHELL_PATTERNS, BLOCKED_FILE_PATTERNS)
  - Pattern matching utilities

### Task 4: Implement Tool Call Logger
- [ ] Create `src/adw/security/tool_logger.py` with:
  - `ToolLogger` class
  - `log_tool_call(entry: ToolCallLog) -> None`
  - Writes to `.adw/runs/<id>/tools.jsonl`
- [ ] Integrate with run directory structure

### Task 5: Integrate with Claude Code Executor
- [ ] Modify `src/adw/executors/claude_code.py` to:
  - Check tool calls against security interceptor before execution
  - Log all tool calls (blocked and allowed)
  - Raise SecurityError for blocked calls (unless --allow-dangerous)

### Task 6: Add --allow-dangerous Flag
- [ ] Add `--allow-dangerous` flag to CLI run commands
- [ ] When set, log warnings instead of blocking
- [ ] Pass flag through to executor configuration

### Task 7: Write Unit Tests
- [ ] Test SecurityInterceptor with default patterns
- [ ] Test custom pattern configuration
- [ ] Test ToolLogger writes correctly
- [ ] Test SecurityError formatting
- [ ] Test .env exception patterns (.env.example, .env.sample)

---

## Relevant Feature Documentation

None - this is a new security feature.

---

## Developer Context

### Technical Requirements

- **Language**: Python 3.13+
- **Pattern Matching**: Use regex for shell command matching
- **File Format**: JSONL for tool logs (append-only)
- **Configuration**: YAML in project.yaml under `security:` key
- **Error Handling**: Use SecurityError from exception hierarchy

### Architecture Compliance

**From architecture.md:**

1. **Exception Hierarchy**: Create `SecurityError` as subclass of `ADWError`
   - Must include `code`, `message`, `suggestion`, `recoverable`
   - Additional fields: `pattern_matched`, `tool_name`

2. **Model Location**: All Pydantic models go in `src/adw/models/`
   - Create `security.py` for security-related models

3. **Module Location**: Create `src/adw/security/` package
   - Follow existing patterns from `src/adw/hooks/` and `src/adw/logging/`

4. **Logging Pattern**: Use structured logging with context fields
   ```python
   logger.warning("Tool call blocked",
       tool_name=tool_name,
       pattern=pattern.pattern,
       severity=pattern.severity)
   ```

5. **File Structure**:
   ```
   src/adw/security/
   ├── __init__.py
   ├── interceptor.py    # SecurityInterceptor class
   ├── patterns.py       # Default blocked patterns
   └── tool_logger.py    # ToolLogger for tools.jsonl
   ```

### Library & Framework Requirements

- **Pydantic v2**: Use `BaseModel` for all security models
- **re**: Standard library regex for pattern matching
- **pathlib**: Use `Path` for file operations
- **No additional dependencies required**

### File Structure Requirements

**New Files:**
- `src/adw/models/security.py` - Security-related Pydantic models
- `src/adw/security/__init__.py` - Package exports
- `src/adw/security/interceptor.py` - Security checking logic
- `src/adw/security/patterns.py` - Default pattern definitions
- `src/adw/security/tool_logger.py` - Tool call logging

**Modified Files:**
- `src/adw/exceptions.py` - Add SecurityError
- `src/adw/models/__init__.py` - Export security models
- `src/adw/executors/claude_code.py` - Integrate security interceptor
- `src/adw/models/config.py` - Add SecurityConfig to project config
- `src/adw/cli/app.py` or relevant CLI file - Add --allow-dangerous flag

**Test Files:**
- `tests/unit/security/test_interceptor.py`
- `tests/unit/security/test_patterns.py`
- `tests/unit/security/test_tool_logger.py`
- `tests/unit/models/test_security.py`

### Testing Requirements

**Unit Tests:**
- Test pattern matching with various command formats
- Test custom pattern loading from config
- Test .env file exception handling
- Test tool log serialization
- Test SecurityError formatting

**Test Patterns from Existing Code:**
- Follow `tests/unit/hooks/test_runner.py` patterns
- Use pytest fixtures for temp directories
- Mock file system operations where appropriate

**Coverage Target:** >80% for security module

---

## Previous Story Intelligence

**From Story 3.5 (Token & Tool Calls):**
- Tool calls are captured in `LLMResult.tool_calls`
- Each tool call has: `tool_name`, `arguments`, `result_summary`
- This story builds on that foundation by adding security checking

**From Existing Hooks Implementation (Story 3.1):**
- HookRunner pattern for async execution with timeout
- Error handling with typed exceptions
- Environment variable setup for subprocess

---

## Git Intelligence

Recent commits show patterns:
- `feat(story-7-3): Capture LLM Interactions` - Shows logging patterns
- `feat(story-7-6): Implement Secret Redaction` - Shows security-related patterns

Relevant patterns:
- Structured logging with LogEvent model
- JSONL file format for append-only logs
- Redaction patterns from `logging/redactor.py`

---

## Latest Technical Information

**Python Regex Best Practices:**
- Use raw strings for patterns: `r'rm\s+-rf\s+'`
- Compile patterns once for performance: `re.compile(pattern)`
- Use `re.search()` for substring matching

**JSONL Best Practices:**
- One JSON object per line
- Use `model_dump_json()` from Pydantic for serialization
- Open with `"a"` mode for append-only writes

---

## Project Context Reference

See: `docs/project-context.md` (if exists)

Key patterns and rules from project context:
- All models use Pydantic v2 BaseModel
- All exceptions inherit from ADWError
- Use Rich for CLI output
- Follow PEP 8 naming conventions strictly

---

## Dev Notes

### Key Implementation Considerations

1. **Pattern Matching Order**: Check more specific patterns first
2. **Performance**: Compile regex patterns once at initialization
3. **Configurability**: Allow project-level override of default patterns
4. **Graceful Degradation**: --allow-dangerous should log, not crash

### Default Blocked Patterns (Minimum)

```python
BLOCKED_SHELL_PATTERNS = [
    r"rm\s+(-[rRfF]+\s+)*[/~\.]",  # rm -rf / or ~ or .
    r"chmod\s+777",                 # chmod 777 anything
    r"git\s+push\s+.*--force",      # git push --force
    r">\s*\.env\b",                 # redirect to .env
]

BLOCKED_FILE_PATTERNS = [
    r"^\.env$",
    r"^\.adw\.env$",
    # Exceptions handled separately
]

ALLOWED_ENV_PATTERNS = [
    r"\.env\.example$",
    r"\.env\.sample$",
    r"\.env\.template$",
]
```

### Tool Log Format

```json
{
  "timestamp": "2026-01-03T10:30:00Z",
  "tool_name": "Bash",
  "arguments": {"command": "rm -rf /tmp/test"},
  "result_summary": "blocked",
  "duration_ms": 0,
  "blocked": true,
  "block_reason": "Matches dangerous pattern: rm -rf"
}
```

### Project Structure Notes

- Alignment with unified project structure: ✓
- New `security/` package follows pattern of `hooks/`, `logging/`
- Model placement in `models/security.py` follows established pattern

### References

- [Source: _bmad-output/architecture.md#Exception Hierarchy]
- [Source: _bmad-output/architecture.md#Project Structure]
- [Source: _bmad-output/epics/epic-3-hook-phase-execution.md#Story 3.6]
- [Source: src/adw/exceptions.py - Exception patterns]
- [Source: src/adw/hooks/runner.py - Async execution patterns]

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

### File List

## Dependencies

- **Depends On:** None
- **Blocks:** None
- **Can Parallel With:** Story 3.7, Story 3.8
