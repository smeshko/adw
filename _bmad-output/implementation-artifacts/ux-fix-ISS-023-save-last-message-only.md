# Story 13.8: UX Fix - Save Only Last LLM Message as Output

<!-- TEMPLATE SECTION: story_header -->
Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure (Tech Debt)
Created: 2026-01-09

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer inspecting run artifacts,
I want the SDK to save only the LLM's final message (not the full conversation),
so that phase output files contain clean, usable results for downstream phases and debugging.

## Acceptance Criteria

**Given** a phase execution completes successfully
**When** the LLM response artifact is saved
**Then** it contains:
- Only the final assistant message content (after all tool calls complete)
- Structured JSON format with clear separation

**Given** a phase execution completes
**When** I examine `.adw/runs/{run_id}/llm/{seq}_{phase}_response.json`
**Then** the file contains:
```json
{
  "content": "The actual final output text only",
  "phase": "validate",
  "stats": {
    "input_tokens": 1500,
    "output_tokens": 3200,
    "duration_ms": 45000
  },
  "tool_calls": [...]
}
```

**Given** I need to debug the full conversation
**When** I look in the run's llm directory
**Then** I can still access the complete stream via `{seq}_{phase}_stream.jsonl`

## Tasks / Subtasks

- [ ] **Task 1: Modify `_parse_output` in ClaudeCodeExecutor**
  - Extract only the FINAL assistant message text block
  - Ignore intermediate reasoning, tool call descriptions, workflow steps
  - Keep tool_calls list separate from content
  - Return only the last text content block from the final assistant message

- [ ] **Task 2: Update LLMResult.content semantics**
  - Document that `content` contains only final output
  - Verify `LLMResult` model doesn't need structural changes
  - Update docstring to clarify "final assistant message"

- [ ] **Task 3: Update LLMCaptureManager.capture_response**
  - Ensure the `content` field in response JSON is the final message only
  - Stream file already captures full conversation (no change needed)
  - Add optional `full_conversation` field for debugging if needed

- [ ] **Task 4: Update artifact storage in PhaseRunner**
  - `{phase}_output.md` should contain clean final output
  - Existing `_capture_artifacts` method may need adjustment
  - Ensure downstream phases get clean input

- [ ] **Task 5: Add tests**
  - Test that multi-turn conversations extract only final message
  - Test that tool calls are preserved separately
  - Test JSON round-trip of response files

- [ ] **Task 6: Manual verification**
  - Run `adw run "Create hello world cli command"`
  - Verify `003_validate_response.json` contains clean output
  - Verify stream.jsonl still has full trace

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->

**From docs/architecture/deep-dive/phase-runner.md:**
- PhaseRunner._capture_artifacts stores LLM output as `{phase}_output.md`
- The artifact is stored via `artifact_manager.store(run_id, phase, output_name, llm_result.content)`
- Content comes directly from `LLMResult.content`

**From CONDITIONAL_DOCS.md:**
- No specific docs match, but architecture docs cover phase execution flow

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->

1. **Final Message Extraction**: Claude Code's `--output-format stream-json` outputs JSONL where multiple `assistant` messages can appear. The final message is the last one with `type: "assistant"` and contains the actual result.

2. **Current Problem Location**: `ClaudeCodeExecutor._parse_output` (src/adw/executors/claude_code.py:506) concatenates ALL text blocks from ALL assistant messages:
   ```python
   for block in data.get("message", {}).get("content", []):
       if block.get("type") == "text":
           content_parts.append(block.get("text", ""))  # Appends ALL text
   ```

3. **Message Types to Handle**:
   - `type: "assistant"` - Contains content blocks (text, tool_use)
   - `type: "result"` - Final summary with token usage
   - `type: "content_block_delta"` - Streaming deltas (intermediate)
   - `type: "message_delta"` - Usage updates

4. **Solution Approach**: Track assistant messages, only return content from the LAST assistant message's text blocks. Intermediate messages (tool results, reasoning) should be excluded from `content`.

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
<!-- Constraints the developer MUST follow from architecture docs -->

**From project-context.md:**
- All models in `src/adw/models/` - `LLMResult` is already there (models/llm.py)
- Full type annotations required
- Use Pydantic BaseModel for data structures
- Structured logging with extra dict

**Naming conventions:**
- `_parse_output` stays (private method, snake_case)
- No new public API changes needed

**Key Files:**
| File | Purpose |
|------|---------|
| `src/adw/executors/claude_code.py` | Primary change - _parse_output |
| `src/adw/models/llm.py` | LLMResult model (likely no change) |
| `src/adw/logging/llm_capture.py` | capture_response (verify correct) |
| `src/adw/core/phase_runner.py` | _capture_artifacts (verify correct) |

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
<!-- Specific versions, APIs, and usage patterns -->

| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | LLMResult, LLMResponse models |
| json | stdlib | Parsing JSONL output |

**No new dependencies required.**

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
<!-- Where files should be created/modified, naming conventions -->

**Files to MODIFY:**
- `src/adw/executors/claude_code.py` - `_parse_output` method (~line 506-589)
  - Track last assistant message
  - Return only final text blocks

**Files to VERIFY (likely no change):**
- `src/adw/models/llm.py` - LLMResult model
- `src/adw/logging/llm_capture.py` - capture_response
- `src/adw/core/phase_runner.py` - _capture_artifacts

**Test Files:**
- `tests/unit/executors/test_claude_code.py` - Add final message extraction tests
- `tests/integration/test_claude_code_executor.py` - Verify with real output

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
<!-- Testing standards, frameworks, coverage expectations -->

1. **Unit test for _parse_output**:
   ```python
   def test_parse_output_extracts_final_message_only():
       """Only the last assistant message content should be returned."""
       raw_output = '''
       {"type": "assistant", "message": {"content": [{"type": "text", "text": "Thinking..."}]}}
       {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "read_file", "input": {"path": "test.py"}}]}}
       {"type": "assistant", "message": {"content": [{"type": "text", "text": "Final result here"}]}}
       {"type": "result", "usage": {"input_tokens": 100, "output_tokens": 200}}
       '''
       executor = ClaudeCodeExecutor(config)
       parsed = executor._parse_output(raw_output)

       assert parsed["content"] == "Final result here"
       assert "Thinking" not in parsed["content"]
   ```

2. **Integration test**:
   - Run actual phase, verify response.json contains clean output
   - Verify stream.jsonl still has full trace

3. **ADR-001 compliance**: This is a targeted fix, minimal test overhead.

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
<!-- Learnings from previous story implementation (if story_num > 1) -->

**From Story 16.4 (Update Phase Result Model):**
- Simplified ValidationResult to 6 fields
- Pattern: Remove complexity, focus on clean output
- Same philosophy applies here: clean final output vs verbose trace

**From Story 16.1 (Remove SDK Validation Loop):**
- Removed complex iteration/triage tracking
- LLM now handles validate->fix cycle internally
- Final output from validate phase should be clean result

**From Story 16.2 (Create Unified Validation Prompt):**
- Created JSON schema for validation output
- LLM produces structured final result
- This story ensures that result is cleanly captured

**Learnings to apply:**
- Keep changes focused and minimal
- Preserve debugging capability (stream.jsonl)
- Follow existing code patterns

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
<!-- Recent commit patterns, files modified, conventions observed -->

**Recent Epic 16 commits:**
```
a369178 refactor(epic-16): Simplify ValidationResult model (Story 16.4) (#93)
2d6432d fix(epic-16): Post-merge review fixes for Story 16.2 (#94)
ba63824 refactor(epic-16): Story 16.1 - Remove SDK Validation Loop (#90)
61ffa59 feat(epic-16): Create unified validation prompt (Story 16.2) (#89)
```

**Commit pattern for this story:**
```
fix(epic-16): Save only final LLM message as output (UX-ISS-023)

- Extract only last assistant message content in _parse_output
- Preserve full conversation trace in stream.jsonl
- Clean output for downstream phases and debugging

Issue: ISS-023
```

**Files touched in recent Epic 16 work:**
- `src/adw/validation/models.py` (16.4)
- `src/adw/defaults/commands/validate/` (16.2)
- `src/adw/core/orchestrator.py` (16.1)

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
<!-- Web research results for current library versions, API changes, best practices -->

**Claude Code CLI output format:**
- `--output-format stream-json` produces JSONL
- Each line is a separate JSON object
- Multiple `type: "assistant"` messages for multi-turn interactions
- Tool results interspersed between assistant messages
- Final message contains the actual response

**JSONL structure example:**
```jsonl
{"type":"assistant","message":{"content":[{"type":"text","text":"Let me analyze..."}]}}
{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"src/main.py"}}]}}
{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"...","content":"file contents..."}]}}
{"type":"assistant","message":{"content":[{"type":"text","text":"Based on my analysis, here is the implementation:\n\n```python\n...\n```"}]}}
{"type":"result","usage":{"input_tokens":5000,"output_tokens":2000}}
```

**Key insight:** Only the LAST `type: "assistant"` message with `type: "text"` content blocks should be captured as the final output.

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: _bmad-output/project-context.md

Key patterns and rules from project context:
- All models in `src/adw/models/`
- Full type annotations required
- Structured logging with extra dict
- Use Pydantic BaseModel
- Context managers for resources

---

## Dev Notes

### Current Flow Analysis

```
ClaudeCodeExecutor.execute()
  → _stream_subprocess() → _read_process_output()
  → _build_result() → _parse_output(raw_output)
     ↓
  LLMResult(content=ALL_TEXT_CONCATENATED, ...)
     ↓
  LLMCaptureManager.capture_response(LLMResponse(content=...))
     ↓
  PhaseRunner._capture_artifacts()
     → artifact_manager.store(run_id, phase, "{phase}_output.md", llm_result.content)
```

**Problem:** `_parse_output` concatenates all text from all assistant messages.

**Fix location:** `_parse_output` method - track messages, return only last.

### Implementation Approach

```python
def _parse_output(self, raw_output: str) -> dict[str, Any]:
    # Track ALL assistant messages, but only keep last text content
    all_messages: list[dict] = []  # Track all assistant messages
    tool_calls: list[ToolCall] = []
    tokens_used = 0

    for line in raw_output.strip().split("\n"):
        # ... parse JSON ...

        if msg_type == "assistant":
            # Store the entire message for later processing
            all_messages.append(data)
            # Still extract tool calls from all messages
            for block in data.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    tool_calls.append(ToolCall(...))

    # Extract text ONLY from the LAST assistant message
    final_content_parts: list[str] = []
    if all_messages:
        last_message = all_messages[-1]
        for block in last_message.get("message", {}).get("content", []):
            if block.get("type") == "text":
                final_content_parts.append(block.get("text", ""))

    return {
        "content": "".join(final_content_parts),
        "tool_calls": tool_calls,
        "tokens_used": tokens_used,
    }
```

### Edge Cases to Handle

1. **Single assistant message** - Works normally (last = only)
2. **No assistant messages** - Return empty content (existing behavior)
3. **Multiple text blocks in final message** - Concatenate all
4. **Final message has only tool_use** - Return empty content (likely error case)
5. **result type with text** - Include if it's the final actual output

### Project Structure Notes

- This is a UX fix in Epic 16 (Validation Phase Simplification)
- Follows pattern of other ISS fixes: targeted, minimal changes
- Does not change public API or break existing functionality

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-023-save-only-last-llm-message-as-output.md]
- [Source: src/adw/executors/claude_code.py:506-589] - _parse_output method
- [Source: src/adw/models/llm.py] - LLMResult model
- [Source: src/adw/logging/llm_capture.py] - LLMCaptureManager

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
