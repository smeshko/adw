# Issue: Run ID truncated in list command output

**ID:** ISS-004
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-04
**Reporter:** Ivo

## Related

- **Epic:** 6
- **Story:** 6-4
- **Component:** CLI Output / Run List

## Description

The `adw list` command truncates the Run ID column with "...", making it impossible to see or copy the full run IDs needed for subsequent commands like `adw logs <run-id>` or `adw status <run-id>`.

## Reproduction Steps

1. Run `adw list` command
2. Observe the Run ID column in the table output

## Expected Behavior

Full Run ID should be visible in the table output without truncation.

## Actual Behavior

Run ID is truncated (e.g., "01KE1MKDYQN7...") hiding the full identifier needed for other commands.

## Impact

Users cannot copy full run IDs to use with other ADW commands (logs, status, resume, abort), blocking workflow continuity.

## User Impact Score

- **Users Affected:** All CLI users
- **Frequency:** Every time `adw list` is used

## Workaround

None

## Environment

- **OS:** macOS
- **App Version:** Current
- **DPI Scaling:** N/A (CLI)

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-004-run-id-truncated-in-list-output.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

The table width should either:
1. Not truncate the Run ID column (it's critical data)
2. Allow horizontal scrolling
3. Use a shorter display format with full ID available via hover/click
4. Show full ID on a separate line if terminal width is insufficient
