# Issue: Feature description shows generic text instead of user input

**ID:** ISS-005
**Severity:** Major
**Type:** Bug
**Status:** resolved (not-a-bug)
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
- **Fixed In:** N/A - Not a bug
- **Verified By:** Investigation
- **Verified Date:** 2026-01-04

## Root Cause Analysis

**Investigation confirmed this is NOT a bug.** The system works correctly:
1. Feature descriptions ARE being stored correctly in `~/.adw/index.jsonl`
2. Example: `"feature_description":"Add heelo world cli command"` stored and displayed correctly
3. The "Add feature" entries in the index are from pytest test runs polluting the user's index
4. Tests use "Add feature" as placeholder text
5. User error: Issue report mentioned `adw start` but command is `adw run`

## Preventive Measures Implemented

1. Added `ADW_TEST_INDEX_PATH` environment variable support to IndexManager
2. Created `isolated_global_index` autouse fixture to prevent test pollution
3. Added comprehensive integration tests for feature description preservation
