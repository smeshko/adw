# Issue: Feature description shows generic text instead of user input

**ID:** ISS-005
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-04
**Reporter:** Ivo

## Related

- **Epic:** 6
- **Story:** 6-1
- **Component:** Run Initialization / Feature Description

## Description

When starting a new run with a specific feature description (e.g., "add hello world"), the `adw list` command displays a generic "Add feature" text instead of the actual user-provided description.

## Reproduction Steps

1. Run `adw start "add hello world"`
2. Run `adw list` to view recent runs
3. Observe the Feature column

## Expected Behavior

The Feature column should display the exact text provided by the user: "add hello world"

## Actual Behavior

The Feature column displays generic text "Add feature" regardless of what was actually entered.

## Impact

- Users cannot identify runs by their actual feature description
- Makes it impossible to distinguish between multiple runs
- Reduces utility of the list command for run management

## User Impact Score

- **Users Affected:** All CLI users
- **Frequency:** Every run start

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

- **Fix Story:** bugfix-ISS-005-feature-description-not-captured.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This could be:
1. Feature description not being saved to run context during initialization
2. Feature description not being loaded/displayed by the list command
3. Default/placeholder value overwriting user input
