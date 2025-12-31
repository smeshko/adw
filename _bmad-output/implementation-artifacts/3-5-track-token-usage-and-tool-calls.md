# Story 3.5: Track Token Usage and Tool Calls

Status: ready-for-dev
Linear Issue: not-configured
Epic: 3 - Hook & Phase Execution
Created: 2025-12-31

---

## Story

As a developer,
I want token usage and tool calls captured from each LLM execution,
so that I can monitor costs and understand what actions the LLM took.

## Acceptance Criteria

**Given** Claude Code execution completes
**When** I inspect LLMResult
**Then** tokens_used contains the token count from the execution

**Given** Claude Code makes tool calls during execution
**When** I inspect LLMResult.tool_calls
**Then** each tool call includes: tool_name, arguments, result_summary

**Given** the LLM execution for a phase
**When** phase completes
**Then** token usage is logged in structured format for aggregation

**Given** an entire run completes
**When** I query total tokens
**Then** it's the sum of all phase executions

## Tasks / Subtasks

### Task 1: Parse Claude Code Token Output
- [x] Research Claude Code `--print` output format for token usage
- [x] Extract token count from Claude Code response
- [x] Handle cases where token info is not available
- [x] Default to 0 if not parseable

### Task 2: Parse Tool Call Output
- [x] Research Claude Code output format for tool calls
- [x] Extract tool_name from tool call data
- [x] Extract arguments from tool call data
- [x] Generate result_summary from tool output (truncate if long)

### Task 3: Update Output Parsing in ClaudeCodeExecutor
- [x] Enhance `_parse_output()` to extract tokens_used
- [x] Enhance `_parse_output()` to extract tool_calls
- [x] Build list of `ToolCall` objects from parsed data
- [x] Handle malformed output gracefully (log warning, continue)

### Task 4: Implement Token Aggregation
- [x] Track token usage per phase in RunContext
- [x] Add `phase_tokens: dict[str, int]` field to RunContext or PhaseResult
- [x] Calculate total tokens from sum of all phases
- [x] Add `total_tokens` property or method

### Task 5: Implement Structured Logging for Tokens
- [ ] Log token usage after each LLM call
- [ ] Use structured format: `logger.info("LLM completed", tokens_used=500, phase="plan")`
- [ ] Log tool calls made during execution
- [ ] Enable aggregation through log analysis

### Task 6: Update PhaseResult for Token Tracking
- [ ] Add `tokens_used: int` field to PhaseResult
- [ ] Add `tool_calls: list[ToolCall]` field to PhaseResult
- [ ] Populate from LLMResult when phase completes

### Task 7: Write Unit Tests
- [ ] Create/update `tests/unit/executors/test_claude_code.py`
- [ ] Test token extraction from mock Claude output
- [ ] Test tool call extraction from mock output
- [ ] Test handling of missing token data
- [ ] Test ToolCall model creation
- [ ] Test aggregation across phases
- [ ] Target: >90% coverage for token tracking code

### Task 8: Write Integration Tests
- [ ] Test with actual Claude Code output (if available)
- [ ] Verify token counts are reasonable
- [ ] Verify tool calls are captured correctly

---

## Developer Context

### Technical Requirements

- **Output Parsing**: Parse Claude Code's `--print` JSON format
- **Model Updates**: Ensure `LLMResult` has `tokens_used` and `tool_calls`
- **Structured Logging**: Log token usage for downstream aggregation
- **Error Tolerance**: Handle missing/malformed data gracefully

### Architecture Compliance

**From architecture.md - LLM Execution Result:**
```python
class LLMResult(BaseModel):
    success: bool
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tokens_used: int = 0
    duration_ms: int = 0
```

**ToolCall model already exists at `src/adw/models/llm.py`:**
```python
class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_summary: str | None = None
```

**Logging Pattern:**
```python
logger.info(
    "LLM execution completed",
    phase="plan",
    tokens_used=500,
    tool_count=3,
    duration_ms=2500,
)

for tool_call in result.tool_calls:
    logger.debug(
        "Tool call",
        tool_name=tool_call.tool_name,
        arguments=tool_call.arguments,
    )
```

### Claude Code Output Format

Claude Code with `--print` outputs structured data. Token usage and tool calls need to be extracted from this output.

**Expected output structure (to be verified):**
```json
{
  "content": "...",
  "usage": {
    "input_tokens": 100,
    "output_tokens": 400
  },
  "tool_calls": [
    {
      "name": "read_file",
      "input": {"path": "/src/main.py"},
      "output": "file contents..."
    }
  ]
}
```

**Parsing implementation:**
```python
import json

def _parse_output(self, raw_output: str) -> tuple[str, list[ToolCall], int]:
    """Parse Claude Code --print output.

    Returns:
        Tuple of (content, tool_calls, tokens_used)
    """
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        # Fallback: treat as plain text
        return raw_output, [], 0

    content = data.get("content", raw_output)

    # Extract token usage
    usage = data.get("usage", {})
    tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

    # Extract tool calls
    tool_calls = []
    for tc in data.get("tool_calls", []):
        tool_calls.append(ToolCall(
            tool_name=tc.get("name", "unknown"),
            arguments=tc.get("input", {}),
            result_summary=self._truncate(str(tc.get("output", "")), 200),
        ))

    return content, tool_calls, tokens_used
```

### File Structure Requirements

**Files to modify:**
```
src/adw/
├── executors/
│   └── claude_code.py     # Update parsing to extract tokens/tools
├── models/
│   ├── llm.py             # Already has ToolCall, LLMResult
│   ├── phase.py           # Add tokens_used, tool_calls to PhaseResult
│   └── context.py         # Consider adding phase_tokens for aggregation
```

**PhaseResult enhancement:**
```python
# src/adw/models/phase.py - Add fields:
tokens_used: int = 0
"""Total tokens used during this phase."""

tool_calls: list[ToolCall] = Field(default_factory=list)
"""Tool calls made during this phase."""
```

### Testing Requirements

**Test Framework:** pytest

**Mock Claude Code output:**
```python
@pytest.fixture
def mock_claude_output():
    return json.dumps({
        "content": "Generated code...",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 400,
        },
        "tool_calls": [
            {
                "name": "read_file",
                "input": {"path": "/src/main.py"},
                "output": "def main():\n    pass",
            },
        ],
    })
```

**Test token extraction:**
```python
def test_extracts_token_usage(executor, mock_claude_output):
    # Configure mock to return JSON output
    result = executor.execute("test prompt")

    assert result.tokens_used == 500  # 100 + 400
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "read_file"
```

**Coverage Target:** >80% overall, >90% for token tracking code

---

## Previous Story Intelligence

**From Story 3.2 (Claude Code Executor):**
- ClaudeCodeExecutor captures output from subprocess
- Need to enhance parsing to extract tokens and tool calls

**From Story 3.4 (Timeout):**
- Duration tracking already implemented
- Token tracking follows same pattern

**Dependencies:**
- Story 3.5 depends on Story 3.2 (needs ClaudeCodeExecutor output)
- Story 3.5 can run in parallel with Story 3.3 and 3.4 (Wave 2)

---

## Git Intelligence

**LLMResult already has required fields at `src/adw/models/llm.py`:**
```python
class LLMResult(BaseModel):
    tokens_used: int = 0
    tool_calls: list[ToolCall] = Field(default_factory=list)
```

**ToolCall model is fully defined:**
```python
class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_summary: str | None = None
```

Models are ready - just need to populate them from parsed output.

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:

1. **Structured Logging**: Log token usage with context fields for aggregation
2. **Error Tolerance**: Handle missing data gracefully, log warnings
3. **Type Annotations**: Full annotations on parsing functions
4. **Pydantic Models**: Use existing `ToolCall` model

---

## Dev Notes

### Key Implementation Points

1. **Output Parsing** - JSON from `--print` flag:
   ```python
   def _parse_output(self, raw: str) -> tuple[str, list[ToolCall], int]:
       try:
           data = json.loads(raw)
           return self._extract_from_json(data)
       except json.JSONDecodeError:
           return raw, [], 0
   ```

2. **Graceful Degradation** - Continue even if parsing fails:
   ```python
   try:
       tokens_used = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
   except (KeyError, TypeError):
       logger.warning("Could not extract token usage from Claude output")
       tokens_used = 0
   ```

3. **Result Summary Truncation** - Keep summaries manageable:
   ```python
   def _truncate(self, text: str, max_len: int = 200) -> str:
       if len(text) <= max_len:
           return text
       return text[:max_len - 3] + "..."
   ```

4. **Aggregation Helper** - Sum across phases:
   ```python
   def total_tokens(self, context: RunContext) -> int:
       return sum(
           result.tokens_used
           for result in context.phase_results.values()
       )
   ```

### Project Structure Notes

- Alignment with unified project structure ✓
- Uses existing `ToolCall` and `LLMResult` models
- May need to enhance `PhaseResult` for token storage

### Research Needed

- **Claude Code `--print` output format** - Need to verify exact JSON structure
- **Token counting granularity** - input vs output tokens
- **Tool call output format** - how Claude reports tool usage

### References

- [Source: src/adw/models/llm.py:11-32] - ToolCall model
- [Source: src/adw/models/llm.py:34-67] - LLMResult model
- [Source: _bmad-output/architecture.md#LLM-Execution]

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

- **Depends On:** Story 3.2
- **Blocks:** None
- **Can Parallel With:** Story 3.3, Story 3.4

### Dependency Rationale
- Story 3.2: Token tracking requires ClaudeCodeExecutor output parsing to be implemented
- Can run in parallel with 3.3 and 3.4 since they all depend only on 3.2
