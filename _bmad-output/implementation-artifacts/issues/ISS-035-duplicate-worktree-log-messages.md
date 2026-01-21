# Issue: Duplicate Worktree Creation Log Messages

**ID:** ISS-035
**Severity:** Minor
**Type:** Bug
**Status:** fixed
**Reported:** 2026-01-21
**Reporter:** Ivo

## Related

- **Epic:** Epic 10 (Worktree Isolation)
- **Story:** N/A
- **Component:** Worktree Management (manager.py, orchestrator.py)

## Description

Two nearly identical log messages appear when a worktree is created:
```
20:03:49 [INFO ] [phase] Worktree created successfully
20:03:49 [INFO ] [phase] Created worktree for run
```

This is redundant and adds noise to the logs.

**Locations:**
- `src/adw/worktree/manager.py:497-504` - "Worktree created successfully"
- Caller (orchestrator or bootstrap) - "Created worktree for run"

## Reproduction Steps

1. Run any ADW workflow with worktrees enabled: `adw run "any feature"`
2. Observe two worktree creation messages in the logs

**Evidence from project-rulebook-be run:**
```
20:03:49 [INFO ] [phase] Worktree created successfully
20:03:49 [INFO ] [phase] Created worktree for run
```

## Expected Behavior

Single log message indicating worktree creation with relevant details.

## Actual Behavior

Two separate log messages for the same event.

## Impact

- **Log noise**: Redundant messages clutter logs
- **Minor confusion**: Appears as if two operations occurred

## Workaround

None needed - purely cosmetic issue.

## Environment

- **OS:** macOS / Any
- **App Version:** adw-sdk (current staging)
- **DPI Scaling:** N/A

## Proposed Fix

Remove one of the redundant log calls. Keep the more detailed one in `worktree/manager.py`:

**File:** `src/adw/worktree/manager.py:497-504`
```python
logger.info(
    "Worktree created successfully",
    extra={
        "run_id": run_id,
        "path": str(worktree_path),
        "branch": branch_name,
    },
)
```

Remove the redundant "Created worktree for run" log from the caller.

## Files Affected

| File | Change |
|------|--------|
| `src/adw/worktree/manager.py` | Keep existing detailed log |
| Caller (orchestrator/bootstrap) | Remove redundant log call |

## Resolution

- **Fix Story:** ux-fix-ISS-035
- **Fixed In:** story/ux-fix-ISS-035 branch (commit 7d401d0)
- **Verified By:** Automated tests (2979 passed)
- **Verified Date:** 2026-01-21

### Implementation Details

Removed the redundant log message from `src/adw/core/orchestrator.py:1902-1909`.
The detailed log in `WorktreeManager.create_worktree()` is retained as the single source of worktree creation logging.

## Notes

This is a minor cosmetic issue. Can be addressed during a polish sprint or when working on related worktree code.
