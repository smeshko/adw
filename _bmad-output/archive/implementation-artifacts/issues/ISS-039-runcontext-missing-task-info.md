# Issue: RunContext missing task_id and task_info - Linear comments never posted

**ID:** ISS-039
**Severity:** Critical
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-22
**Reporter:** Ivo

## Related

- **Epic:** 12 (Task Manager Integration)
- **Story:** 12-3, 12-6
- **Component:** Task Manager Integration / Run Lifecycle

## Description

When a run is initiated with a Linear task manager configured, the `StatusSyncService` and `LabelManager` are created correctly in `bootstrap.py`, but the `RunContext` created by `RunLifecycle.create_run_context()` never populates `task_id` or `task_info` fields.

This causes all `StatusSyncService` methods to return early without posting comments because they check:
```python
if not context.task_id or not context.task_info:
    return
```

The root cause is a design gap:
1. `app.py` fetches `task_info` and passes it to `create_orchestrator()`
2. `create_orchestrator()` uses `task_info` to create `LabelManager` and `StatusSyncService`
3. But `RunLifecycle.create_run_context()` creates `RunContext` WITHOUT populating `task_id` or `task_info`
4. The `task_info` is never stored or passed through to context creation

## Reproduction Steps

1. Configure Linear task manager in project.yaml:
   ```yaml
   task_manager:
     type: linear
     sync_comments: true
     labels:
       enabled: true
   ```
2. Ensure LINEAR_API_KEY and LINEAR_TEAM_ID are set in `.adw/.env`
3. Run `adw run RULE-123` where RULE-123 is a valid Linear task
4. Observe that no comments are posted to Linear despite successful phase completions
5. Check logs - no errors, but comments silently not posted

## Expected Behavior

- Phase completion comments should be posted to the Linear issue
- Phase labels (e.g., `adw:phase:plan`, `adw:phase:build`) should be added/removed
- Run completion comment should be posted
- All `StatusSyncService` methods should execute their API calls

## Actual Behavior

- No comments are posted to Linear
- `StatusSyncService.post_phase_comment()` returns early at line 223-224
- `StatusSyncService.post_completion_comment()` returns early at line 305-306
- All sync methods silently skip because `context.task_id` is `None`
- Note: `LabelManager` MAY still work because it uses its own `_task_id` from construction

## Impact

- Linear integration for status comments is completely broken
- Users cannot track ADW progress via Linear comments
- The feature appears to work (no errors) but silently does nothing
- This is a critical regression in the Task Manager Integration feature

## User Impact Score

- **Users Affected:** All users with Linear integration configured
- **Frequency:** Every run with task manager enabled

## Workaround

None - the context fields are not populated, so there's no way to enable comments without code changes.

## Environment

- **OS:** macOS (Darwin 25.0.0)
- **App Version:** Current staging branch
- **DPI Scaling:** N/A (CLI)

## Evidence

### Code Analysis

**sync.py:223-224** - Returns early because context.task_id is None:
```python
def post_phase_comment(self, context, phase, result):
    if not context.task_id or not context.task_info:
        return  # <-- Always returns here
```

**run_lifecycle.py:188-197** - Context created without task fields:
```python
context = RunContext(
    run_id=run_id,
    feature_description=feature_description,
    current_phase=starting_phase,
    started_at=datetime.now(UTC),
    status="running",
    worktree_path=worktree_path,
    use_worktree=should_use_worktree,
    branch_name=branch_name,
    # task_id and task_info are NOT set!
)
```

### Screenshots

N/A

### Logs

N/A - no errors logged, feature silently fails

### Screen Recording

N/A

## Resolution

- **Fix Story:** bugfix-ISS-039-runcontext-missing-task-info.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Proposed Fix

### Design Issue: Inconsistent Task ID Access Patterns

**Current inconsistency:**
- `LabelManager`: Stateful - stores `task_id` at construction, methods take no context
- `StatusSyncService`: Stateless - reads `context.task_id` each call, but context is never populated

**Recommended fix (make both consistent):**

1. **Immediate fix - StatusSyncService stores task_info (like LabelManager):**
   - Pass `task_info` to `StatusSyncService` constructor
   - Store as `self._task_info`
   - Use `self._task_info.id` instead of `context.task_info.id`
   - Remove dependency on context fields for task ID

2. **Also populate RunContext (for consistency and future use):**
   - Store `task_info` on `Orchestrator` or `RunLifecycle` during construction
   - Pass `task_info` through to `create_run_context()` method
   - Populate `task_id=task_info.identifier` and `task_info=task_info` in `RunContext`

3. **Add integration tests** to verify:
   - Comments are posted to Linear on phase completion
   - Labels are added/removed correctly
   - Both services use consistent task ID

### Implementation Details

**bootstrap.py changes:**
```python
# StatusSyncService now takes task_info like LabelManager
status_sync_service = StatusSyncService(task_manager, config.task_manager, task_info)
```

**sync.py changes:**
```python
def __init__(self, task_manager, config, task_info=None):
    self._task_manager = task_manager
    self._config = config
    self._task_info = task_info  # Store for use in methods

def post_phase_comment(self, context, phase, result):
    task_info = self._task_info or context.task_info
    if not task_info:
        return
    # Use task_info.id instead of context.task_info.id
```

## Notes

This issue was discovered while investigating why Linear comments weren't appearing despite correct configuration. The issue is subtle because:
- No errors are logged
- The check `if not context.task_id` silently returns
- LabelManager might still work (uses different path)
- Everything appears to work from the CLI perspective
