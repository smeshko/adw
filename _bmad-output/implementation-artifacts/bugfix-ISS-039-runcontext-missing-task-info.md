# Story: Bugfix ISS-039 - RunContext Missing task_id and task_info

Status: ready-for-dev
Linear Issue: not-configured
Epic: 12 - Task Manager Integration
Created: 2026-01-22

---

## Story

As a user with Linear integration configured,
I want StatusSyncService methods to execute reliably,
So that phase completion comments and status updates are posted to my Linear issues.

## Acceptance Criteria

**Given** a project with Linear task manager configured and `sync_comments: true`
**When** an ADW run executes with a task ID (e.g., `adw run RULE-151`)
**Then** phase completion comments MUST be posted to the Linear issue
**And** StatusSyncService methods MUST NOT silently return early

**Given** StatusSyncService methods check `context.task_id` and `context.task_info`
**When** these methods are called during phase execution
**Then** the context MUST contain valid task_id and task_info values

**Given** LabelManager uses constructor-injected task_id (stateful pattern)
**When** StatusSyncService is refactored for consistency
**Then** StatusSyncService MUST also use constructor-injected task_info (stateful pattern)
**And** both services MUST have consistent task ID access patterns

**Given** RunContext model has `task_id` and `task_info` fields
**When** RunLifecycle.create_run_context() is called
**Then** these fields SHOULD be populated for future use and consistency

## Tasks / Subtasks

### Task 1: Make StatusSyncService Consistent with LabelManager (Primary Fix)
- [x] Add `task_info` parameter to StatusSyncService constructor
- [x] Store as `self._task_info` instance variable
- [x] Update all methods to use `self._task_info` instead of `context.task_info`
- [x] Fallback to context for backwards compatibility: `task_info = self._task_info or context.task_info`
- [x] Update bootstrap.py to pass task_info to StatusSyncService constructor

### Task 2: Populate RunContext Fields (Consistency Fix)
- [x] Add `task_info` parameter to RunLifecycle constructor
- [x] Store `task_info` as instance variable on RunLifecycle
- [x] Update `create_run_context()` to populate `task_id` and `task_info` fields
- [x] Ensure RunContext fields are set: `task_id=task_info.identifier`, `task_info=task_info`

### Task 3: Wire task_info Through Lifecycle Creation
- [ ] Update bootstrap.py `create_orchestrator()` to pass task_info to RunLifecycle
- [ ] Verify task_info flows from app.py → bootstrap.py → RunLifecycle → RunContext

### Task 4: Write Tests
- [ ] Add test: StatusSyncService stores task_info from constructor
- [ ] Add test: StatusSyncService.post_phase_comment() uses stored task_info
- [ ] Add test: RunContext created with task_id and task_info populated
- [ ] Add test: StatusSyncService methods don't return early when task_info provided

---

## Relevant Feature Documentation

From ISS-033 story (completed):
- StatusSyncService is now instantiated in bootstrap.py (PR #143)
- LabelManager now receives task_info.id (UUID) correctly
- The wiring is correct, but StatusSyncService still depends on context fields

---

## Developer Context

### Technical Requirements

**Design Issue: Inconsistent Task ID Access Patterns**

| Service | Current Pattern | Issue |
|---------|----------------|-------|
| `LabelManager` | Stateful - stores `task_id` at construction | Works correctly |
| `StatusSyncService` | Stateless - reads `context.task_id` each call | Fails - context fields never populated |

**Root Cause (from ISS-039 investigation):**

1. `app.py` fetches `task_info` and passes it to `create_orchestrator()` ✓
2. `create_orchestrator()` creates `StatusSyncService` ✓ (fixed in ISS-033)
3. `create_orchestrator()` creates `LabelManager` with `task_info.id` ✓ (fixed in ISS-033)
4. BUT: `RunLifecycle.create_run_context()` creates `RunContext` WITHOUT `task_id` or `task_info` ✗
5. `StatusSyncService` methods check `context.task_id` and return early when None ✗

### Architecture Compliance

**File Locations:**
- `src/adw/task_managers/sync.py` - StatusSyncService (primary fix)
- `src/adw/cli/bootstrap.py` - Wiring updates
- `src/adw/core/run_lifecycle.py` - Context population (secondary fix)

**sync.py Current Code (PROBLEMATIC):**
```python
class StatusSyncService:
    def __init__(self, task_manager: TaskManager, config: TaskManagerConfig):
        self._task_manager = task_manager
        self._config = config
        # Missing: self._task_info storage

    def post_phase_comment(self, context: RunContext, phase: str, result: PhaseResult) -> None:
        if not context.task_id or not context.task_info:
            return  # BUG: Always returns here because context fields are None
        # ... rest of method never executes
```

**sync.py Required Fix:**
```python
class StatusSyncService:
    def __init__(
        self,
        task_manager: TaskManager,
        config: TaskManagerConfig,
        task_info: TaskInfo | None = None,  # ADD: Optional for backwards compat
    ):
        self._task_manager = task_manager
        self._config = config
        self._task_info = task_info  # ADD: Store for method use

    def post_phase_comment(self, context: RunContext, phase: str, result: PhaseResult) -> None:
        # FIX: Use stored task_info, fallback to context
        task_info = self._task_info or context.task_info
        if not task_info:
            return

        task_id = task_info.id  # Use internal UUID for API calls
        # ... rest of method now executes
```

**bootstrap.py Required Change:**
```python
# Current (after ISS-033 fix):
status_sync_service = StatusSyncService(task_manager, config.task_manager)

# After ISS-039 fix:
status_sync_service = StatusSyncService(task_manager, config.task_manager, task_info)
```

**run_lifecycle.py Required Change:**
```python
# In create_run_context():
context = RunContext(
    run_id=run_id,
    feature_description=feature_description,
    # ... existing fields ...
    task_id=self._task_info.identifier if self._task_info else None,  # ADD
    task_info=self._task_info,  # ADD
)
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| None | N/A | Uses existing project dependencies only |

**No New Dependencies:** This fix uses existing models and services.

### File Structure Requirements

**Modified Files:**
- `src/adw/task_managers/sync.py` - Add task_info to constructor and methods
- `src/adw/cli/bootstrap.py` - Pass task_info to StatusSyncService
- `src/adw/core/run_lifecycle.py` - Store task_info and populate in context
- `src/adw/core/orchestrator.py` - Pass task_info to RunLifecycle (if needed)

**Test Files:**
- `tests/unit/task_managers/test_sync.py` - StatusSyncService task_info tests
- `tests/unit/core/test_run_lifecycle.py` - RunContext population tests

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/task_managers/test_sync.py

class TestStatusSyncServiceTaskInfo:
    def test_stores_task_info_from_constructor(self, mock_task_manager, mock_config):
        """StatusSyncService stores task_info from constructor."""
        task_info = TaskInfo(id="uuid-123", identifier="RULE-151", title="Test")
        service = StatusSyncService(mock_task_manager, mock_config, task_info)
        assert service._task_info == task_info

    def test_post_phase_comment_uses_stored_task_info(
        self, mock_task_manager, mock_config, mock_context
    ):
        """post_phase_comment uses stored task_info, not context."""
        task_info = TaskInfo(id="uuid-123", identifier="RULE-151", title="Test")
        service = StatusSyncService(mock_task_manager, mock_config, task_info)

        # Context has None for task_info
        mock_context.task_info = None

        # Should still work because service has stored task_info
        result = PhaseResult(phase="plan", status="success", ...)
        service.post_phase_comment(mock_context, "plan", result)

        # Verify comment was posted
        mock_task_manager.post_comment.assert_called_once()

    def test_post_phase_comment_falls_back_to_context(
        self, mock_task_manager, mock_config, mock_context
    ):
        """post_phase_comment falls back to context.task_info if not stored."""
        service = StatusSyncService(mock_task_manager, mock_config, task_info=None)

        # Context has task_info
        mock_context.task_info = TaskInfo(id="uuid-456", identifier="RULE-152", title="Test")

        result = PhaseResult(phase="plan", status="success", ...)
        service.post_phase_comment(mock_context, "plan", result)

        # Verify comment was posted using context task_info
        mock_task_manager.post_comment.assert_called_once()
```

**Integration Test Verification:**
```python
# tests/integration/test_task_manager_integration.py

def test_run_with_linear_posts_comments(mock_linear_client, project_with_linear):
    """Full ADW run with Linear posts phase completion comments."""
    # This verifies the complete wiring from app.py through to Linear API
```

---

## Previous Story Intelligence

**From ISS-033 (Task Manager Wiring):**
- StatusSyncService is now instantiated in bootstrap.py ✓
- LabelManager receives task_info.id (UUID) correctly ✓
- The wiring is correct at bootstrap level
- BUT: StatusSyncService still reads from context, which is never populated

**Key Learning:**
ISS-033 fixed the service creation but didn't fix the context population. Both services need task_info available, but LabelManager gets it via constructor (works) while StatusSyncService gets it via context (fails).

**Pattern to Follow:**
LabelManager's stateful pattern is the correct design:
```python
# LabelManager (correct pattern)
def __init__(self, task_manager, config, task_id):  # Receives at construction
    self._task_id = task_id  # Stores for later use

def set_running(self):  # Methods don't need context
    self._task_manager.add_label(self._task_id, label)
```

---

## Git Intelligence

**Recent Relevant Commits:**
- `6ff17e8` fix(ISS-033): Wire task manager services in bootstrap (#143)
- `3db0ad1` feat(epic-12): Post status update comments (Story 12.6) (#97)
- `7fbb4dc` feat(epic-12): Story 12.8 - Issue Closing (#92)

**Established Patterns:**
- Services receive dependencies via constructor (dependency injection)
- Non-blocking external integrations (catch and log errors)
- Optional parameters with None defaults for backwards compatibility

---

## Latest Technical Information

**StatusSyncService Methods Affected:**
All methods in sync.py that check `context.task_id` or `context.task_info`:

| Method | Line | Check |
|--------|------|-------|
| `sync_phase_start` | 72-73 | `if not context.task_id or not context.task_info` |
| `sync_phase_transition` | 100-101 | `if not context.task_id or not context.task_info` |
| `sync_run_failed` | 129-130 | `if not context.task_id or not context.task_info` |
| `post_phase_comment` | 223-224 | `if not context.task_id or not context.task_info` |
| `post_failure_comment` | 271-272 | `if not context.task_id or not context.task_info` |
| `post_completion_comment` | 305-306 | `if not context.task_id or not context.task_info` |

**All 6 methods need the same fix pattern.**

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Type annotations required**: Full type hints for all function signatures
- **Dependency injection**: Pass services via constructor
- **Non-blocking external calls**: Wrap in try/except, log and continue
- **Backwards compatibility**: Use optional parameters with None defaults

---

## Dev Notes

### Implementation Order

1. **Fix StatusSyncService first** (Task 1) - This is the primary fix
   - Add task_info to constructor
   - Update all 6 methods to use stored task_info
   - This alone will fix the bug

2. **Update bootstrap.py** (Task 3 partial) - Wire the fix
   - Pass task_info to StatusSyncService constructor
   - Verify with manual test

3. **Populate RunContext** (Task 2) - Optional but recommended
   - For consistency and future use
   - May help other code that expects context to have task_info

### Design Decision

**Why make StatusSyncService stateful like LabelManager:**
1. Consistent design pattern across task manager services
2. No dependency on context being properly populated
3. Task info is known at construction time and doesn't change during run
4. Simpler method signatures (context is still passed but not relied upon for task_id)

### Verification Checklist

After implementation:
- [ ] `adw run RULE-XXX` with Linear configured posts phase comments
- [ ] Comments appear on Linear issue after each phase
- [ ] No Python errors or stack traces related to StatusSyncService
- [ ] Existing tests pass
- [ ] New tests verify task_info storage and usage

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-039-runcontext-missing-task-info.md]
- [Source: src/adw/task_managers/sync.py:223-224]
- [Source: src/adw/core/run_lifecycle.py:188-197]
- [Source: _bmad-output/implementation-artifacts/bugfix-ISS-033-task-manager-wiring-broken.md]

---

## Dev Agent Record

### Context Reference

Bugfix for ISS-039: RunContext Missing task_id and task_info

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

