# Issue: Task Manager Services Not Wired in Bootstrap

**ID:** ISS-033
**Severity:** Critical
**Type:** Bug
**Status:** done
**Reported:** 2026-01-21
**Reporter:** Ivo

## Related

- **Epic:** Epic 12 (Task Manager Integration)
- **Story:** N/A
- **Component:** Bootstrap, Task Manager Integration (bootstrap.py, sync.py, labels.py)

## Description

Two critical bugs prevent task manager integration from functioning correctly:

### Bug 1: StatusSyncService Not Instantiated
The `StatusSyncService` is never created in `bootstrap.py`, so no phase completion comments are posted to Linear despite `sync_comments: true` in the project config.

**Location:** `src/adw/cli/bootstrap.py` (missing service instantiation)

### Bug 2: LabelManager Receives Wrong Task ID
The `LabelManager` is created with `task_id` (the identifier like "RULE-151") instead of `task_info.id` (the internal Linear UUID). The Linear API requires the internal UUID for label operations.

**Location:** `src/adw/cli/bootstrap.py:278`

## Reproduction Steps

1. Configure a project with Linear integration:
   ```yaml
   task_manager:
     type: linear
     team_key: RULE
     sync_comments: true
   ```
2. Run `adw run "RULE-151"` or similar task ID
3. Observe no comments are posted to the Linear issue
4. Observe no labels (adw:running, adw:plan, etc.) are added to the issue

**Evidence from project-rulebook-be run 01KFEG36NZMB5E39YCM0A36CBX:**
- Config has `sync_comments: true`
- No comments posted to RULE-151 on Linear
- No labels added to the issue

## Expected Behavior

1. `StatusSyncService` should be instantiated and passed to the orchestrator
2. Phase completion comments should be posted to Linear
3. `LabelManager` should receive `task_info.id` (UUID) for label operations
4. Labels like `adw:running`, `adw:plan`, etc. should be added/managed on the issue

## Actual Behavior

1. `StatusSyncService` is never created
2. No comments are posted despite config enabling them
3. `LabelManager` receives identifier string which Linear API rejects
4. No labels are applied to issues

## Impact

- **Core functionality broken**: Task manager sync is advertised but doesn't work
- **User confusion**: Config appears correct but has no effect
- **Lost visibility**: Teams don't see ADW progress on their Linear issues

## Workaround

None. The services are simply not wired.

## Environment

- **OS:** macOS / Any
- **App Version:** adw-sdk (current staging)
- **DPI Scaling:** N/A

## Evidence

### Code Analysis

**bootstrap.py:273-278** - LabelManager wiring:
```python
# Create LabelManager if task manager and task ID are provided (Story 12.7)
label_manager: LabelManager | None = None
if task_manager is not None and task_id is not None and config is not None:
    labels_config = config.task_manager.labels if config.task_manager else None
    if labels_config and labels_config.enabled:
        label_manager = LabelManager(task_manager, labels_config, task_id)  # ← Wrong! Uses identifier, not UUID
```

**Missing StatusSyncService creation:**
```python
# There is NO code creating StatusSyncService anywhere in bootstrap.py
# The orchestrator receives None for _status_sync_service
```

### Logs

From `logs.jsonl` - No sync/comment logs present despite config:
```json
{"level":"info","category":"phase","message":"Phase completed"}
// No "Comment posted to task manager" log entries
// No "Status synced to task manager" log entries
```

## Proposed Fix

### 1. Create StatusSyncService in bootstrap.py
**File:** `src/adw/cli/bootstrap.py`
```python
# After creating task_manager, before creating orchestrator
status_sync_service = None
if task_manager is not None and config is not None and config.task_manager:
    from adw.task_managers.sync import StatusSyncService
    status_sync_service = StatusSyncService(task_manager, config.task_manager)

# Pass to orchestrator
orchestrator = Orchestrator(
    ...
    status_sync_service=status_sync_service,
)
```

### 2. Fix LabelManager to use internal UUID
**File:** `src/adw/cli/bootstrap.py:278`
```python
if labels_config and labels_config.enabled and task_info:
    label_manager = LabelManager(task_manager, labels_config, task_info.id)  # Use internal ID
```

## Files Affected

| File | Change |
|------|--------|
| `src/adw/cli/bootstrap.py` | Create StatusSyncService, fix LabelManager task_id |
| `src/adw/core/orchestrator.py` | Ensure _status_sync_service parameter is used |

## Resolution

- **Fix Story:** [bugfix-ISS-033-task-manager-wiring-broken.md](../bugfix-ISS-033-task-manager-wiring-broken.md)
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This issue was discovered during analysis of a failed ADW run in project-rulebook-be (01KFEG36NZMB5E39YCM0A36CBX) where:
- Linear integration was configured with `sync_comments: true`
- No comments or labels appeared on the Linear issue despite successful phases
- The code paths exist but the services are never instantiated
