# Tech-Spec: Live Log Streaming Improvements

**Created:** 2026-01-22
**Status:** Completed

## Overview

### Problem Statement

The `adw logs follow` command has two issues that degrade the real-time logging experience:

1. **Tool calls appear at the end instead of streaming in real-time** - All tool calls are written with the same timestamp after the subprocess completes, rather than as they happen during execution. This is because `_extract_display_text()` only handles text content and ignores `tool_use` events in the stream.

2. **Output is raw and hard to read** - The current output lacks visual hierarchy. LLM text content is mixed with log lines, making it difficult to distinguish between different event types.

### Solution

1. **Real-time tool call streaming**: Modify `_extract_display_text()` to also detect and return tool call events from the stream-json output, then write them to `live_stream` immediately during streaming.

2. **Visual boxes for LLM output**: Enhance `LiveStreamTransport` to wrap LLM token streams in visual box drawing characters, providing clear separation between LLM output and log events.

3. **Tool result display**: Track in-progress tool calls and display their results (output/exit code) in boxed format when the tool completes.

### Scope

**In Scope:**
- Real-time tool call detection during streaming
- Tool result capture and display (boxed output format)
- Visual box formatting for LLM output sections
- Color coding improvements (already partially implemented)

**Out of Scope:**
- Collapsing/grouping repetitive tool calls
- `--format` flag for output modes
- Changes to the `follow` command itself

## Context for Development

### Codebase Patterns

**Streaming Pattern** (`claude_code.py`):
```python
async def read_stdout() -> None:
    while True:
        line = await stdout.readline()
        if not line:
            break
        decoded = line.decode()
        content_lines.append(decoded)

        if self.live_stream:
            display_text = self._extract_display_text(decoded)
            if display_text:
                self.live_stream.write_llm_token(display_text)
```

**Stream-JSON Message Types**:
- `content_block_delta` with `delta.type == "text_delta"` - streaming text tokens
- `content_block_start` with `content_block.type == "tool_use"` - tool call initiation
- `content_block_delta` with `delta.type == "input_json_delta"` - tool input arguments (streaming)
- `content_block_stop` - tool call input complete
- `tool_result` - tool execution result with output content
- `assistant` - full message with content blocks
- `result` - completion with token counts

**Tool Result Message Format**:
```json
{"type":"tool_result","tool_use_id":"toolu_01...","content":[{"type":"text","text":"file contents here..."}],"is_error":false}
```

**ANSI Colors** (already defined in `live_stream.py`):
```python
COLORS = {
    "reset": "\033[0m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "bold_red": "\033[1;31m",
    "magenta": "\033[35m",
    "bold": "\033[1m",
}
```

### Files to Reference

1. `src/adw/executors/claude_code.py` (lines 331-352, 420-423, 656-692)
2. `src/adw/logging/live_stream.py` (full file)
3. `tests/unit/executors/test_claude_code.py` (for test patterns)
4. `tests/unit/logging/test_live_stream.py` (for test patterns)

### Technical Decisions

1. **Structured event parsing**: Create `StreamEvent` dataclass to represent different event types (text, tool_start, tool_result) with a unified interface for the streaming loop.

2. **Tool ID correlation**: Track `tool_use_id` from `content_block_start` to correlate with `tool_result` messages. This ensures results are associated with the correct tool call.

3. **Box drawing characters**: Use Unicode box drawing for visual separation:
   - `┌─` top left corner with label (e.g., `┌─ output ─────`)
   - `│ ` vertical line prefix for content lines
   - `└─` bottom left corner with optional status (e.g., `└─ exit 0 ─────`)

4. **Output truncation strategy**: For tool results > 10 lines:
   - Show first 5 lines
   - Show "... (N lines truncated) ..."
   - Show last 5 lines
   - This keeps output manageable while showing context

5. **Tool call format in stream**: Tool calls appear as `content_block_start` with:
   ```json
   {"type": "content_block_start", "content_block": {"type": "tool_use", "name": "Read", "id": "toolu_01..."}}
   ```

6. **Tool result format in stream**: Results appear as:
   ```json
   {"type": "tool_result", "tool_use_id": "toolu_01...", "content": [{"type": "text", "text": "..."}], "is_error": false}
   ```

## Implementation Plan

### Tasks

- [x] **Task 1: Create StreamEvent dataclass for structured event parsing**
  - Define `StreamEvent` with variants: `text`, `tool_start`, `tool_result`
  - Include fields: `event_type`, `content`, `tool_name`, `tool_id`, `is_error`, `exit_code`
  - Use this as return type for stream parsing

- [x] **Task 2: Add `_extract_stream_event()` method to ClaudeCodeExecutor**
  - Create new method that returns `StreamEvent | None`
  - Parse `content_block_start` with `tool_use` type → `tool_start` event
  - Parse `content_block_delta` with `text_delta` → `text` event
  - Parse `tool_result` message → `tool_result` event with output content
  - Track tool_use_id to correlate starts with results

- [x] **Task 3: Update `read_stdout()` to handle all event types**
  - Call `_extract_stream_event()` for each line
  - `text` event → `live_stream.write_llm_token()`
  - `tool_start` event → `live_stream.write_tool_call()` (shows tool name + context)
  - `tool_result` event → `live_stream.write_tool_result()` (shows boxed output)
  - Remove duplicate tool call logging from `_build_result()`

- [x] **Task 4: Add `write_tool_result()` method to LiveStreamTransport**
  - Accept: tool_name, output content, is_error flag, exit_code (optional)
  - Format with boxed output:
    ```
    ┌─ output ────────────────────────
    │ file contents or command output
    │ (truncated if > 10 lines)
    └─ exit 0 ────────────────────────
    ```
  - Red box border for errors, dim for success
  - Truncate long output (show first 5 + last 5 lines with "..." in middle)

- [x] **Task 5: Add visual box formatting to LiveStreamTransport for LLM output**
  - Update `write_llm_start()` to output top border: `┌─ LLM ─────────────────`
  - Update `write_llm_token()` to prefix content with `│ `
  - Update `write_llm_end()` to output bottom border: `└──────────────────────`
  - Cyan color for LLM boxes

- [x] **Task 6: Improve tool call header formatting**
  - Format: `[timestamp] [TOOL] ToolName: context`
  - Dim timestamp, yellow [TOOL], bold tool name
  - Truncate long file paths: `/very/long/.../file.swift`

- [x] **Task 7: Update tests**
  - Add tests for `StreamEvent` dataclass
  - Add tests for `_extract_stream_event()` with all message types
  - Add tests for `write_tool_result()` formatting
  - Add tests for LLM box formatting
  - Verify real-time streaming (no batching)
  - Verify no duplicate tool calls

### Acceptance Criteria

- [ ] **AC1: Real-time tool calls** - Given a running `adw` execution, when a tool is invoked, then the tool call appears in `live.log` immediately with a current timestamp (not batched at end)

- [ ] **AC2: Tool results displayed** - Given a tool call completion, when the result is received, then the output is displayed in a boxed format below the tool call header

- [ ] **AC3: No duplicate tool calls** - Given a completed execution, when viewing `live.log`, then each tool call appears exactly once (not both during streaming AND at the end)

- [ ] **AC4: Visual LLM sections** - Given LLM output in `live.log`, when viewing with `adw logs follow`, then LLM content is wrapped in box drawing characters with `│ ` prefix

- [ ] **AC5: Color coding** - Given different event types, when viewing `live.log`, then:
  - Tool call headers are yellow with bold tool name
  - Tool result boxes are dim (success) or red (error)
  - LLM boxes are cyan
  - Phase events are magenta
  - Errors are red
  - Timestamps are dim

- [ ] **AC6: Timestamps accurate** - Given tool call events in stream, when written to `live.log`, then each has the actual time it occurred (different timestamps for different calls)

- [ ] **AC7: Long output truncated** - Given a tool result with > 10 lines of output, when displayed, then show first 5 lines + "..." + last 5 lines

## Additional Context

### Dependencies

- No new dependencies required
- Uses existing `filelock` for write safety
- Uses existing ANSI color infrastructure

### Testing Strategy

1. **Unit tests**: Mock the stream-json input and verify correct event extraction
2. **Integration tests**: Run actual Claude Code subprocess and verify `live.log` output
3. **Manual testing**: Use `adw logs follow` on a real execution to verify visual appearance

### Notes

**Stream-JSON tool_use example** (to verify during implementation):
```json
{"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_01...","name":"Read","input":{}}}
{"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"file_path\":\"/path/to/file\"}"}}
{"type":"content_block_stop","index":1}
```

**Target Output - Complete Example:**
```
[2026-01-22 00:01:10] [LLM] ▶ Token stream begins (build)
┌─ LLM ───────────────────────────────────────────────────
│ I'll implement the Remote Config feature according to
│ the story plan. Let me start by reading the config...
└─────────────────────────────────────────────────────────
[2026-01-22 00:01:12] [TOOL] Read: /path/to/config.swift
┌─ output ────────────────────────────────────────────────
│ import Foundation
│
│ struct Config {
│     let apiKey: String
│     let baseURL: URL
│ }
└─────────────────────────────────────────────────────────
[2026-01-22 00:01:13] [TOOL] Bash: swift build
┌─ output ────────────────────────────────────────────────
│ Building for debugging...
│ [1/1] Compiling App main.swift
│ Build complete! (2.34s)
└─ exit 0 ────────────────────────────────────────────────
[2026-01-22 00:01:18] [TOOL] Write: /path/to/new-file.swift
┌─ output ────────────────────────────────────────────────
│ ✓ 1,234 bytes written
└─────────────────────────────────────────────────────────
[2026-01-22 00:01:19] [LLM] ▶ Token stream begins
┌─ LLM ───────────────────────────────────────────────────
│ The module has been created successfully. Now let me
│ run the tests to verify everything works...
└─────────────────────────────────────────────────────────
```

**Error Example:**
```
[2026-01-22 00:01:25] [TOOL] Bash: swift test
┌─ output ────────────────────────────────────────────────
│ Testing...
│ Test Suite 'ConfigTests' failed
│   ✗ testAPIKey: XCTAssertEqual failed
│     Expected: "sk-xxx"
│     Actual: nil
└─ exit 1 ─────────────────────────────────────── ERROR ──
```

**Truncated Output Example (> 10 lines):**
```
[2026-01-22 00:01:30] [TOOL] Read: /path/to/large-file.swift
┌─ output ────────────────────────────────────────────────
│ import Foundation
│ import Vapor
│ import Fluent
│ import Redis
│
│ ... (42 lines truncated) ...
│
│     return response
│   }
│ }
└─────────────────────────────────────────────────────────
```
