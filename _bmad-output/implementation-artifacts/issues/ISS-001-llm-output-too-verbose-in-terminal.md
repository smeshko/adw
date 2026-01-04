# Issue: LLM output too verbose in terminal during phase execution

**ID:** ISS-001
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-04
**Reporter:** Ivo

## Related

- **Epic:** Epic 7
- **Story:** N/A
- **Component:** Phase Output

## Description

The LLM output is printed directly to the terminal during phase execution, making it extremely verbose and hard to follow.

## Reproduction Steps

1. Run a phase execution with `adw run`
2. Observe the terminal output
3. LLM responses are printed in full to stdout

## Expected Behavior

LLM output should be hidden from main terminal output during execution. It should be available live via a separate logs command (e.g., `adw logs --follow`).

## Actual Behavior

Full LLM output is printed to the terminal, cluttering the display and making it difficult to follow execution progress.

## Impact

Users cannot easily track execution progress; terminal becomes cluttered with verbose LLM responses, reducing usability.

## User Impact Score

- **Users Affected:** All users running phase executions
- **Frequency:** Every execution

## Workaround

None

## Environment

- **OS:** Windows 10/11
- **App Version:** 0.1.0-dev
- **DPI Scaling:** 100%

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-001-llm-output-too-verbose-in-terminal.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

_Add any additional context here._
