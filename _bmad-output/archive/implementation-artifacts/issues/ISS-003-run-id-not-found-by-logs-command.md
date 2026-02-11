# Issue: Run ID not found by logs command while run is active

**ID:** ISS-003
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-04
**Reporter:** Ivo

## Related

- **Epic:** 6/7
- **Story:** N/A
- **Component:** Run Management / Logs

## Description

When starting a run with `adw run`, the run displays progress in the terminal (showing phase execution, tokens, etc.) but `adw logs show <run_id>` returns "Run not found" error immediately after.

## Reproduction Steps

1. Run `adw run "Add heelo world cli command"`
2. Note the Run ID displayed in the output (e.g., 01KE596NV69MAP2RNJ1CKRVRE1)
3. While the run is still active and showing progress, execute `adw logs show 01KE596NV69MAP2RNJ1CKRVRE1`
4. Observe the error message

## Expected Behavior

The logs command should find the active run and display its logs, allowing users to monitor the run in real-time or review what has happened so far.

## Actual Behavior

Error displayed:
```
Error: Run not found: 01KE596NV69MAP2RNJ1CKRVRE1
Suggestion: Use 'adw list' to see available runs
```

## Impact

Users cannot view logs for active runs, making it impossible to debug issues or monitor run progress from a separate terminal. This significantly impacts the ability to troubleshoot failed or stuck runs.

## User Impact Score

- **Users Affected:** All users trying to monitor runs
- **Frequency:** Every time logs are accessed for active runs

## Workaround

None known - users must wait for run to complete (if it completes) to potentially access logs.

## Environment

- **OS:** macOS (Darwin 25.0.0)
- **App Version:** Current development build
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-003-run-id-not-found-by-logs-command.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

The run ID format appears to be ULID (01KE596NV69MAP2RNJ1CKRVRE1). Possible causes:
- Run directory not being created before the run starts executing
- Race condition between run creation and file system persistence
- Logs command looking in wrong location for run data
