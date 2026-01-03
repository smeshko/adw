# Story 7.3: Capture LLM Interactions

Status: ready-for-dev
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-03

---

## Story

As a developer,
I want full LLM request/response captured,
so that I can debug and reproduce issues.

## Acceptance Criteria

**Given** LLM execution
**When** capturing
**Then** full request (prompt, params) is saved to `llm/<seq>_request.json`

**Given** LLM execution
**When** capturing
**Then** full response (content, tool_calls, tokens) is saved to `llm/<seq>_response.json`

**Given** streaming output
**When** capturing
**Then** raw stream is captured to `llm/<seq>_stream.txt`

**Given** captured LLM interactions
**When** replayed with same prompt
**Then** equivalent behavior can be reproduced (NFR12)

**Given** captured interactions
**When** reviewing
**Then** no API keys or secrets are included (NFR14)

## Tasks / Subtasks

### Task 1: Create LLM Capture Models (models/logging.py)
- [ ] Create `LLMRequest` model (prompt, params, timestamp, phase)
- [ ] Create `LLMResponse` model (content, tool_calls, tokens, duration)
- [ ] Create `LLMStreamEvent` model for stream capture
- [ ] Create `LLMToolCall` and `LLMToolResult` models

### Task 2: Implement Stream Logger (logging/stream.py)
- [ ] Create `StreamLogger` class with interface from arch doc
- [ ] Implement `token(content)` method
- [ ] Implement `tool_call(call)` and `tool_result(result)` methods
- [ ] Implement `thinking(content)` for reasoning blocks
- [ ] Implement `end(stats)` and `error(error)` methods

### Task 3: Implement LLM File Capture (logging/llm_capture.py)
- [ ] Create `LLMCaptureManager` class
- [ ] Implement `capture_request(phase, request)` → writes `<seq>_request.json`
- [ ] Implement `capture_response(phase, response)` → writes `<seq>_response.json`
- [ ] Implement `capture_stream(phase, events)` → writes `<seq>_stream.jsonl`
- [ ] Sequence numbering: 001, 002, etc. per run

### Task 4: Integrate with Claude Code Executor
- [ ] Modify `ClaudeCodeExecutor.execute()` to accept StreamLogger
- [ ] Capture all tokens during streaming
- [ ] Capture tool calls and results
- [ ] Save request before execution, response after
- [ ] Handle errors gracefully

### Task 5: Add Secret Filtering (prep for 7.6)
- [ ] Add `redact_secrets(content)` placeholder function
- [ ] Apply to request/response before saving
- [ ] Document integration point for Story 7.6

### Task 6: Write Unit Tests
- [ ] Test LLM model serialization
- [ ] Test StreamLogger event capture
- [ ] Test LLMCaptureManager file creation
- [ ] Test sequence numbering
- [ ] Test integration with mock executor

---

## Relevant Feature Documentation

<!-- LLM Stream Logger defined in docs/arch-logging.md -->

---

## Developer Context

### Technical Requirements

**From PRD:**
- Capture full LLM request/response for debugging (FR49)
- Stream capture for token-by-token replay
- Support reproducibility (NFR12)
- No secrets in captures (NFR14)

**File Naming Convention:**
```
.agent/runs/<run_id>/llm/
├── 001_plan_request.json
├── 001_plan_response.json
├── 001_plan_stream.jsonl
├── 002_build_request.json
├── 002_build_response.json
├── 002_build_stream.jsonl
└── 002_build_tools.jsonl
```

### Architecture Compliance

**Files to Create:**
```
src/adw/logging/
├── stream.py          # StreamLogger class (NEW)
└── llm_capture.py     # LLMCaptureManager class (NEW)

src/adw/models/
└── logging.py         # Add LLM capture models (extend from 7.1)
```

**Files to Modify:**
```
src/adw/executors/claude_code.py  # Integrate stream capture
```

**Integration Points:**
- Executor calls StreamLogger during execution
- LLMCaptureManager writes to run directory
- LogManager coordinates capture lifecycle

### Library & Framework Requirements

**Stream Capture Format (JSONL):**
```jsonl
{"t":0,"type":"token","content":"I'll"}
{"t":12,"type":"token","content":" create"}
{"t":1250,"type":"tool_call_start","id":"call_01","name":"create_file","input":{...}}
{"t":1295,"type":"tool_call_end","id":"call_01","duration_ms":45,"success":true}
{"t":45230,"type":"complete","stats":{"input_tokens":4521,"output_tokens":3892}}
```

**Request/Response JSON:**
```python
# Request
{
    "timestamp": "2026-01-03T10:23:45.123Z",
    "phase": "build",
    "prompt": "...",
    "params": {
        "model": "claude-sonnet-4-20250514",
        "temperature": 0,
        "max_tokens": 16000
    }
}

# Response
{
    "timestamp": "2026-01-03T10:24:32.456Z",
    "phase": "build",
    "content": "...",
    "tool_calls": [...],
    "stats": {
        "input_tokens": 4521,
        "output_tokens": 3892,
        "duration_ms": 47333
    }
}
```

### File Structure Requirements

**Sequence Numbering:**
- Use 3-digit zero-padded sequence: 001, 002, 003
- Sequence is per-run, not per-phase
- Include phase name in filename for clarity

**Directory:** Files go in `.agent/runs/<run_id>/llm/`

### Testing Requirements

**Test Cases:**
```python
def test_stream_logger_captures_tokens():
    logger = StreamLogger()
    logger.token("Hello")
    logger.token(" world")
    assert logger.get_events()[0]["content"] == "Hello"

def test_capture_manager_creates_files(tmp_path):
    manager = LLMCaptureManager(tmp_path)
    manager.capture_request("plan", request)
    assert (tmp_path / "001_plan_request.json").exists()

def test_tool_calls_captured():
    logger = StreamLogger()
    logger.tool_call({"id": "1", "name": "create_file", "input": {}})
    logger.tool_result({"id": "1", "output": "success"})
    # Verify both events captured
```

---

## Previous Story Intelligence

**From Story 7.1:**
- LogManager and transports exist
- LogEvent model for structured logging
- File writing patterns established

**From Story 3.2 (Claude Code Executor):**
- `ClaudeCodeExecutor` class in `executors/claude_code.py`
- Streaming subprocess execution via asyncio
- Token streaming already implemented for display

**From Story 4.1 (Run Directory):**
- `RunDirectory.create()` creates `llm/` subdirectory
- Path: `.agent/runs/<run_id>/llm/`

**Dependency:** Story 7.1 must be completed first.

---

## Git Intelligence

**Existing patterns:**
- `executors/claude_code.py` handles streaming
- `core/run_directory.py` manages run file structure
- Models follow Pydantic patterns in `models/`

---

## Latest Technical Information

**Streaming Subprocess:**
- Use `asyncio.StreamReader` for real-time capture
- Buffer tokens for batch writes to reduce I/O
- Write stream file incrementally during execution

**Token Timing:**
- Use `time.monotonic_ns()` for precise timing
- Convert to milliseconds for JSON output
- Relative to stream start, not absolute time

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Pydantic for all structured data
- Context managers for file resources
- Async for streaming operations

---

## Dev Notes

- Stream capture happens during executor execution
- Request saved before LLM call, response after
- Sequence number tracked in LLMCaptureManager
- Secret redaction placeholder for Story 7.6 integration
- Tool call capture essential for debugging

### Project Structure Notes

- New files: `logging/stream.py`, `logging/llm_capture.py`
- Extend models from Story 7.1
- Modify existing executor

### References

- [Source: docs/arch-logging.md#LLM-Stream-Logger] - Stream capture interface
- [Source: src/adw/executors/claude_code.py] - Existing executor
- [Source: src/adw/core/run_directory.py] - Run directory structure

---

## Dependencies

**Depends On:**
- Story 7.1: Multi-Tier Logging System (provides LogManager foundation)

**Blocks:**
- Story 7.4: Log Viewing Commands (needs LLM captures for `logs llm` command)

**Parallel With:**
- Story 7.2, 7.5, 7.6 can run in parallel

---

## Dev Agent Record

### Context Reference

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

