# Story 3.8: Tool Execution Logging

Status: ready-for-dev
Linear Issue: not-configured
Epic: 3 - Hook & Phase Execution
Created: 2026-01-03

---

## Story

As a developer,
I want all LLM tool calls logged,
So that I can audit what the AI did during a run.

## Acceptance Criteria

**Given** any tool call during a phase
**When** the tool executes
**Then** entry is written to `.adw/runs/<id>/tools.jsonl`

**Given** tool log entry
**When** written
**Then** includes: timestamp, tool_name, arguments, result_summary, duration_ms

**Given** `adw logs tools <run_id>`
**When** executed
**Then** displays formatted tool execution history

## Tasks / Subtasks

### Task 1: Finalize ToolCallLog Model
- [ ] Ensure `src/adw/models/security.py` has complete `ToolCallLog` model:
  - `timestamp`: ISO 8601 format
  - `tool_name`: Name of the tool (e.g., "Bash", "Read", "Write")
  - `arguments`: Dictionary of tool arguments
  - `result_summary`: Brief summary of result (truncated if long)
  - `duration_ms`: Execution time in milliseconds
  - `blocked`: Boolean indicating if call was blocked
  - `block_reason`: Reason for blocking (if applicable)
  - `phase`: Current phase when tool was called

### Task 2: Implement ToolLogger Class
- [ ] Create/finalize `src/adw/security/tool_logger.py`:
  - `ToolLogger` class with run directory awareness
  - `log_tool_call(entry: ToolCallLog) -> None` - append to JSONL
  - `get_tool_history(run_id: str) -> list[ToolCallLog]` - read all entries
  - Thread-safe file writing (file locking)

### Task 3: Integrate with Claude Code Executor
- [ ] Modify `src/adw/executors/claude_code.py`:
  - Log each tool call as it's captured
  - Include timing for each tool
  - Summarize results (truncate to reasonable length)
  - Log blocked calls with reason

### Task 4: Implement CLI Command: adw logs tools
- [ ] Add to `src/adw/cli/logs.py`:
  - `logs_tools` command with run_id argument
  - Formatted table output using Rich
  - Columns: Timestamp, Tool, Duration, Status
  - Optional `--verbose` for full arguments
  - Optional `--blocked-only` filter

### Task 5: Create Tool History Display
- [ ] Create `src/adw/cli/tool_display.py`:
  - `display_tool_history(entries: list[ToolCallLog])` function
  - Rich Table formatting
  - Color coding: green=success, red=blocked, yellow=warning
  - Truncated argument display with expand option

### Task 6: Add Summary Statistics
- [ ] In logs tools command, show summary:
  - Total tool calls
  - Blocked calls count
  - Total execution time
  - Most used tools

### Task 7: Write Unit Tests
- [ ] Test ToolLogger file operations
- [ ] Test JSONL parsing
- [ ] Test CLI command output formatting
- [ ] Test summary statistics calculation
- [ ] Test thread-safety of logging

---

## Relevant Feature Documentation

**Dependencies**:
- Story 3.6 (Security Hook Infrastructure) - ToolCallLog model
- Story 3.5 (Track Token Usage and Tool Calls) - Tool call capture in executor

---

## Developer Context

### Technical Requirements

- **File Format**: JSONL (newline-delimited JSON)
- **Thread Safety**: Use file locking for concurrent writes
- **Performance**: Append-only writes, no read-modify-write
- **Storage Location**: `.adw/runs/<run_id>/tools.jsonl`

### Architecture Compliance

**From architecture.md:**

1. **CLI Commands**: Follow existing patterns in `cli/logs.py`
2. **Display Components**: Create separate display module like `cli/status_display.py`
3. **Logging Location**: Use run directory structure from Epic 4
4. **Output Format**: Use Rich for all CLI output

### Library & Framework Requirements

- **Typer**: CLI framework (already in use)
- **Rich**: Table, Panel for output formatting
- **filelock**: Thread-safe file operations (already dependency)
- **Pydantic v2**: Model serialization

### File Structure Requirements

**New Files:**
- `src/adw/cli/tool_display.py` - Tool history display formatting

**Modified Files:**
- `src/adw/security/tool_logger.py` - Complete implementation
- `src/adw/cli/logs.py` - Add `tools` subcommand
- `src/adw/executors/claude_code.py` - Integrate tool logging
- `src/adw/models/security.py` - Finalize ToolCallLog

**Test Files:**
- `tests/unit/security/test_tool_logger.py`
- `tests/unit/cli/test_logs_tools.py`
- `tests/unit/cli/test_tool_display.py`

### Testing Requirements

**Unit Tests:**
- ToolLogger JSONL read/write
- File locking behavior
- CLI output formatting
- Summary statistics calculation
- Filter options (--blocked-only)

**Integration Tests:**
- End-to-end tool logging during execution
- CLI command reading from actual log files

**Coverage Target:** >80% for tool logging module

---

## Previous Story Intelligence

**From Story 3.5 (Token & Tool Calls):**
- Tool calls captured in `LLMResult.tool_calls`
- Format: `tool_name`, `arguments`, `result_summary`
- This story adds persistent logging of these calls

**From Story 3.6 (Security Hook Infrastructure):**
- ToolCallLog model defined
- Security interceptor integration point
- tools.jsonl file format established

**From Epic 4 (State Persistence):**
- Run directory structure at `.adw/runs/<id>/`
- File organization patterns established

---

## Git Intelligence

Relevant patterns:
- `cli/logs.py` - Existing log viewing commands
- `cli/status_display.py` - Display formatting patterns
- `logging/file.py` - JSONL writing patterns

---

## Latest Technical Information

**JSONL Best Practices:**
```python
# Writing
with open(log_path, "a") as f:
    f.write(entry.model_dump_json() + "\n")

# Reading
entries = []
with open(log_path) as f:
    for line in f:
        entries.append(ToolCallLog.model_validate_json(line))
```

**File Locking Pattern:**
```python
from filelock import FileLock

lock = FileLock(str(log_path) + ".lock")
with lock:
    with open(log_path, "a") as f:
        f.write(entry.model_dump_json() + "\n")
```

---

## Project Context Reference

See: `docs/project-context.md` (if exists)

Key patterns:
- Follow `cli/logs.py` command structure
- Use Rich Tables like in `cli/list_display.py`
- JSONL format like `logging/file.py`

---

## Dev Notes

### Tool Log Entry Format

```json
{
  "timestamp": "2026-01-03T10:30:00.123Z",
  "tool_name": "Bash",
  "arguments": {
    "command": "npm test",
    "timeout": 30000
  },
  "result_summary": "Exit code: 0, output: 15 tests passed",
  "duration_ms": 2500,
  "blocked": false,
  "block_reason": null,
  "phase": "build"
}
```

### CLI Output Format

```
adw logs tools 01HQXK5P3Z

Tool Execution History for run 01HQXK5P3Z

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Timestamp          ┃ Tool      ┃ Duration  ┃ Status    ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 10:30:00           │ Read      │ 15ms      │ ✓ Success │
│ 10:30:01           │ Bash      │ 2500ms    │ ✓ Success │
│ 10:30:04           │ Write     │ 5ms       │ ✓ Success │
│ 10:30:05           │ Bash      │ 0ms       │ ✗ Blocked │
└────────────────────┴───────────┴───────────┴───────────┘

Summary:
  Total calls: 4
  Successful:  3
  Blocked:     1
  Total time:  2520ms
```

### Implementation Notes

1. **Result Summary Truncation**: Limit to ~200 characters with "..." suffix
2. **Argument Sanitization**: Redact sensitive values before logging
3. **Timestamp Format**: Use ISO 8601 with milliseconds
4. **Phase Tracking**: Include current phase in each entry

### Project Structure Notes

- Builds on Story 3.6 infrastructure
- Follows existing CLI patterns from `logs.py`
- Display module follows `status_display.py` pattern

### References

- [Source: _bmad-output/architecture.md#Observability]
- [Source: _bmad-output/epics/epic-3-hook-phase-execution.md#Story 3.8]
- [Source: src/adw/cli/logs.py - Existing log commands]
- [Source: src/adw/logging/file.py - File logging patterns]

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
- **Can Parallel With:** Story 3.6, Story 3.7