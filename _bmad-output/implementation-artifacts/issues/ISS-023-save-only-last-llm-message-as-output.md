# Issue: SDK Should Save Only LLM's Last Message as Output File

**ID:** ISS-023
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-09
**Reporter:** Ivo

## Related

- **Epic:** 16
- **Story:** N/A
- **Component:** Phase Runner / LLM Response Handling

## Description

Currently the SDK saves the full LLM conversation/response to the output files in `.adw/runs/{run_id}/llm/`. This includes all the intermediate reasoning, tool calls, and verbose output.

The SDK should only save the LLM's **last message** (final output) as the phase artifact, not the entire conversation history. The last message typically contains the structured result or summary that downstream phases need.

## Reproduction Steps

1. Run `adw run "Create hello world cli command"`
2. Examine `.adw/runs/{run_id}/llm/003_validate_response.json`
3. Observe the `content` field contains the full conversation including:
   - Workflow initialization steps
   - Intermediate reasoning
   - Tool call descriptions
   - Final output mixed with everything else

## Expected Behavior

The response file should contain only the LLM's final message - the actual output/result of the phase, not the full conversation trace.

Alternatively, structure should be:
```json
{
  "final_output": "...",  // Just the last message
  "full_conversation": "...",  // Optional, for debugging
  "tool_calls": [...],
  "stats": {...}
}
```

## Actual Behavior

The entire conversation content is saved as a single blob, making it difficult to:
1. Extract just the phase result
2. Pass clean output to downstream phases
3. Parse structured results from the phase

## Impact

- Downstream phases receive noisy input if they consume previous phase output
- Difficult to extract structured results (like JSON) from verbose output
- Larger file sizes than necessary
- Harder to debug what the actual output was vs intermediate steps

## User Impact Score

- **Users Affected:** All users / developers inspecting runs
- **Frequency:** Every phase of every run

## Workaround

Manually extract the last message from the response files.

## Environment

- **OS:** macOS/Linux
- **App Version:** 0.1.6
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

Example from `003_validate_response.json` - content field contains ~5800 tokens of conversation instead of just the final result.

### Screen Recording

N/A

## Resolution

- **Fix Story:** Pending
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Suggested Implementation

1. In `phase_runner.py` or wherever LLM responses are processed:
   - Extract only the final assistant message (after all tool calls complete)
   - Save that as the primary output artifact
   - Optionally save full conversation to a separate debug file

2. Update the response JSON structure:
```json
{
  "timestamp": "...",
  "phase": "validate",
  "final_output": "The actual result text",
  "tool_calls": [...],
  "stats": {...}
}
```

3. Full conversation can go to a separate file like `003_validate_full.json` for debugging.

## Notes

This is especially important for phases that produce structured output (like JSON results from code review) - extracting that output from a verbose conversation blob is error-prone.
