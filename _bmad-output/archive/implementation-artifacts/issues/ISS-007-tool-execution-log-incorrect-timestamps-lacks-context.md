# Issue: Tool execution log shows incorrect timestamps and lacks context

**ID:** ISS-007
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-05
**Reporter:** Ivo

## Related

- **Epic:** 7
- **Story:** 7-4
- **Component:** Logging/Observability

## Description

The `adw logs tools` command displays tool execution history with incorrect data - all timestamps show the same value (05:32:26), all durations show the same value (3694ms), and the output lacks context about what each tool call actually did.

## Reproduction Steps

1. Run any ADW workflow that executes multiple tool calls
2. Execute `adw logs tools <run_id>`
3. Observe that all timestamps are identical
4. Observe that all durations are identical
5. Note the lack of context about tool call purposes

## Expected Behavior

Each tool call should show its actual timestamp, actual duration, and some context (e.g., file path for Read, command snippet for Bash, pattern for Glob).

## Actual Behavior

All entries show the same timestamp and duration, making the log useless for understanding execution flow or debugging timing issues.

## Impact

Cannot effectively debug tool execution order, identify slow operations, or understand what the LLM was doing at each step.

## User Impact Score

- **Users Affected:** All developers using ADW
- **Frequency:** Every time logs tools command is used

## Workaround

None - must inspect raw log files manually.

## Environment

- **OS:** macOS
- **App Version:** 0.1.0
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-007-tool-execution-log-incorrect-timestamps-lacks-context.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

Sample output showing the issue:
```
┃ Timestamp ┃ Tool  ┃ Duration ┃ Status    ┃
│ 05:32:26  │ Task  │   3694ms │ ✓ Success │
│ 05:32:26  │ Bash  │   3694ms │ ✓ Success │
│ 05:32:26  │ Glob  │   3694ms │ ✓ Success │
```
All 40 tool calls show identical timestamp and duration values.
