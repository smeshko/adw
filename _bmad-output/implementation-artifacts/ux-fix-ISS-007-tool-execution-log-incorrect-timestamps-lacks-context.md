# Story: UX Fix - Tool Execution Log Incorrect Timestamps & Lacks Context

Status: ready-for-dev
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-05

---

## Story

As a developer using ADW,
I want the `adw logs tools` command to show correct timestamps, durations, and contextual information for each tool call,
so that I can effectively debug tool execution order, identify slow operations, and understand what the LLM was doing at each step.

## Acceptance Criteria

**Given** command `adw logs tools <run_id>`
**When** executed
**Then** each tool call displays its actual individual timestamp (not a shared timestamp)

**Given** command `adw logs tools <run_id>`
**When** executed
**Then** each tool call displays meaningful duration information (or "N/A" if not available)

**Given** command `adw logs tools <run_id>`
**When** executed
**Then** each tool call displays contextual information:
- Read: file path being read
- Bash: command being executed (truncated)
- Glob: pattern being searched
- Write: file path being written
- Grep: pattern and path
- Task: agent type or description

**Given** command `adw logs tools <run_id> --verbose`
**When** executed
**Then** full arguments are shown for each tool call

## Tasks / Subtasks

### Task 1: Fix Timestamp Capture in Tool Logging (claude_code.py)
- [ ] Modify `_log_tool_calls()` to generate individual timestamps per tool call
- [ ] Modify `_check_and_log_tool_calls()` similarly
- [ ] Ensure timestamps reflect actual logging time, not batch time

### Task 2: Improve Duration Handling
- [ ] Since individual tool durations aren't available from Claude Code CLI, change approach:
  - Option A: Show "N/A" or "-" for individual durations, show total only in summary
  - Option B: Keep approximation but clearly label as "~{duration}ms (est.)"
- [ ] Update display to communicate duration limitations clearly
- [ ] Consider capturing elapsed time between tool calls for rough timing

### Task 3: Add Context Column to Tool Display (logs.py)
- [ ] Add new "Context" column to the tools table
- [ ] Extract meaningful context from tool arguments:
  - `Read`: Show `file_path` (truncated to ~40 chars)
  - `Write`: Show `file_path` (truncated)
  - `Bash`: Show `command` (truncated to ~40 chars)
  - `Glob`: Show `pattern`
  - `Grep`: Show `pattern` + `path` if present
  - `Task`: Show `subagent_type` or `description`
  - `Edit`: Show `file_path`
  - Default: Show first argument key/value or "-"
- [ ] Create helper function `_extract_tool_context(tool_name: str, arguments: dict) -> str`

### Task 4: Update Table Layout
- [ ] Adjust column widths to accommodate new Context column
- [ ] Ensure table is readable at standard terminal widths (80-120 chars)
- [ ] Consider making Context column optional with `--context` flag or default on

### Task 5: Update Unit Tests
- [ ] Update existing tests for new timestamp behavior
- [ ] Add tests for context extraction for each tool type
- [ ] Verify duration display changes

---

## Developer Context

### Technical Requirements

**Root Cause Analysis:**

The bug occurs in `src/adw/executors/claude_code.py` in two methods:

1. **`_log_tool_calls()` (lines 581-626):**
   ```python
   timestamp = datetime.now(UTC).isoformat()  # Single timestamp for ALL tools

   for tool_call in tool_calls:
       log_entry = ToolCallLog(
           timestamp=timestamp,  # Same timestamp reused
           ...
       )
   ```

2. **`_check_and_log_tool_calls()` (lines 709-803):**
   ```python
   timestamp = datetime.now(UTC).isoformat()  # Single timestamp for ALL tools
   per_tool_duration = total_duration_ms // len(tool_calls)  # Evenly distributed
   ```

**The Fix:**
- Move `timestamp = datetime.now(UTC).isoformat()` INSIDE the loop so each tool gets its own timestamp
- For duration, either show estimated values with clear labeling OR show "N/A" and only display total in summary

### Architecture Compliance

**Files to Modify:**
```
src/adw/executors/claude_code.py    # Fix timestamp generation per tool
src/adw/cli/logs.py                 # Add context column, improve display
```

**No New Files Required** - this is a bug fix in existing code.

### Library & Framework Requirements

**Context Extraction Pattern:**
```python
def _extract_tool_context(tool_name: str, arguments: dict[str, Any]) -> str:
    """Extract meaningful context from tool arguments for display."""
    max_len = 40

    if tool_name == "Read":
        path = arguments.get("file_path", "")
        return _truncate(path, max_len)

    elif tool_name == "Write":
        path = arguments.get("file_path", "")
        return _truncate(path, max_len)

    elif tool_name == "Bash":
        cmd = arguments.get("command", "")
        return _truncate(cmd, max_len)

    elif tool_name == "Glob":
        return arguments.get("pattern", "-")

    elif tool_name == "Grep":
        pattern = arguments.get("pattern", "")
        path = arguments.get("path", "")
        if path:
            return f"{_truncate(pattern, 20)} in {_truncate(path, 18)}"
        return _truncate(pattern, max_len)

    elif tool_name == "Task":
        return arguments.get("subagent_type", arguments.get("description", "-"))[:max_len]

    elif tool_name == "Edit":
        return _truncate(arguments.get("file_path", ""), max_len)

    else:
        # Generic: show first argument value
        if arguments:
            first_key = next(iter(arguments))
            return _truncate(str(arguments[first_key]), max_len)
        return "-"

def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."
```

### File Structure Requirements

**Existing File Locations:**
- `src/adw/executors/claude_code.py` - Tool logging happens here
- `src/adw/cli/logs.py` - `logs_tools` command at line 615
- `src/adw/models/security.py` - `ToolCallLog` model at line 92

**Test Locations:**
- `tests/unit/cli/test_logs.py` - CLI command tests
- `tests/unit/security/test_tool_logger.py` - Tool logger tests

### Testing Requirements

**Test Updates Required:**

```python
# tests/unit/cli/test_logs.py

def test_logs_tools_shows_individual_timestamps():
    """Verify each tool call has a unique timestamp."""
    # Create tools.jsonl with multiple entries
    # Each should have different timestamp
    # Run command and verify timestamps differ

def test_logs_tools_shows_context_column():
    """Verify context column shows meaningful info per tool type."""
    # Create entries for Read, Bash, Glob, etc.
    # Verify context extraction works correctly

def test_extract_tool_context_read():
    """Test context extraction for Read tool."""
    args = {"file_path": "/very/long/path/to/some/file.py"}
    ctx = _extract_tool_context("Read", args)
    assert "file.py" in ctx or "..." in ctx

def test_extract_tool_context_bash():
    """Test context extraction for Bash tool."""
    args = {"command": "npm run build && npm test"}
    ctx = _extract_tool_context("Bash", args)
    assert len(ctx) <= 43  # 40 + "..."
```

---

## Previous Story Intelligence

**From Story 7.4 (Log Viewing Commands):**
- `logs_tools` command defined in `src/adw/cli/logs.py:615-696`
- Uses `ToolLogger.get_tool_history()` to load entries
- Displays via Rich `Table` with columns: Timestamp, Tool, Duration, Status
- Summary shows totals at the end

**From Story 3.8 (Tool Execution Logging):**
- `ToolCallLog` model captures tool call data
- JSONL format at `.adw/runs/<run_id>/tools.jsonl`
- Duration is intentionally approximated (documented limitation)

**Key Insight:**
The duration approximation was a known limitation documented in the code:
```python
# Note: Duration Approximation - Individual tool timing is not available
# from Claude Code CLI output, so the total duration is distributed
# evenly across all tools.
```

---

## Git Intelligence

**Recent relevant commits:**
- Story 7.4 implemented the `logs tools` command
- Story 3.8 implemented tool logging infrastructure

**Code patterns observed:**
- Rich Tables for CLI output
- JSONL for structured logging
- Pydantic models for data validation

---

## Latest Technical Information

**Rich Table with Context:**
```python
table = Table(show_header=True, header_style="bold cyan")
table.add_column("Timestamp", style="dim", width=10)
table.add_column("Tool", width=8)
table.add_column("Context", style="dim", width=40)
table.add_column("Duration", justify="right", width=10)
table.add_column("Status", width=12)
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Typer for CLI commands
- Rich for terminal output
- Pydantic models for data structures
- pytest for testing

---

## Dev Notes

### Key Implementation Points:

1. **Timestamp Fix (Easy):** Move timestamp generation inside the loop in both `_log_tool_calls()` and `_check_and_log_tool_calls()`

2. **Duration Display (Decision Needed):**
   - Current: Shows estimated duration spread evenly (misleading)
   - Option A: Show "~Xms" with tilde to indicate estimate
   - Option B: Show "-" for individual, only show total in summary
   - **Recommended:** Option A with clear labeling

3. **Context Column (Main Work):**
   - Add `_extract_tool_context()` helper function
   - Add Context column to table (between Tool and Duration)
   - Keep it concise (40 chars max)

### Project Structure Notes

- All changes in existing files, no new modules needed
- Follow existing patterns in `logs.py` for Rich Table formatting
- Add helper function near the `logs_tools` command

### References

- [Source: src/adw/cli/logs.py:615-696] - logs_tools command
- [Source: src/adw/executors/claude_code.py:581-626] - _log_tool_calls method
- [Source: src/adw/executors/claude_code.py:709-803] - _check_and_log_tool_calls method
- [Source: src/adw/models/security.py:92-136] - ToolCallLog model
- [Source: _bmad-output/implementation-artifacts/issues/ISS-007-*.md] - Issue report

---

## Dev Agent Record

### Context Reference
- ISS-007 issue report
- Story 7.4 implementation details
- claude_code.py tool logging code

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
