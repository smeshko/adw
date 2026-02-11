# Issue: LogManager not connected to Python logging - logs.jsonl never written

**ID:** ISS-006
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

The `LogManager` is created in `app.py:221-222` but immediately discarded by assigning to `_`. The core code throughout orchestrator and other modules uses Python's standard `logging.getLogger(__name__)` which is not connected to ADW's `StructuredFileTransport`. As a result, `logs/logs.jsonl` is never written and `adw logs show` always returns "No log entries found".

## Reproduction Steps

1. Run any ADW pipeline: `adw run "any feature"`
2. Wait for run to complete or fail
3. Run `adw logs show <run_id>`
4. Observe "No log entries found" error

## Expected Behavior

Log entries should be written to `logs/logs.jsonl` and displayed by the `adw logs show` command.

## Actual Behavior

"No log entries found" because `logs.jsonl` is never created - the `LogManager` with its file transports exists but nothing calls its methods to write logs.

## Impact

Users cannot view logs for debugging runs. The entire logging subsystem (Epic 7) is effectively non-functional for file-based logging.

## User Impact Score

- **Users Affected:** All users
- **Frequency:** Every run

## Workaround

Check `tools.jsonl` or `llm/` directory for partial debugging information.

## Environment

- **OS:** macOS/Linux
- **App Version:** Current development
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-006-logmanager-not-connected-to-python-logging.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

Root cause analysis:
- `app.py:221-222`: `log_manager = create_log_manager(...)` then `_ = log_manager`
- `orchestrator.py:68`: Uses `logger = logging.getLogger(__name__)` (Python standard logging)
- The `StructuredFileTransport` is never connected to Python's logging system

Fix options:
1. Wire up LogManager to Python's standard logging as a handler
2. Replace Python logging calls with LogManager calls throughout codebase
