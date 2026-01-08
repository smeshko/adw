# Story 12.3: Status Synchronization at Phase Transitions

Status: ready-for-dev
Linear Issue: not-configured
Epic: 12 - Task Manager Integration
Created: 2026-01-08

---

## Story

As a user,
I want Linear status updated automatically as my run progresses,
So that my team sees real-time progress.

## Acceptance Criteria

**Given** a run initiated from Linear task
**When** the run starts
**Then** Linear status updated per state_mapping (e.g., "In Progress")

**Given** a phase completes
**When** transitioning to next phase
**Then** Linear comment added with phase completion info (optional, configurable)

**Given** the run completes successfully
**When** all phases done
**Then** Linear status set to mapped "completed" state (e.g., "Done")

**Given** the run fails
**When** error occurs
**Then** Linear status set to mapped "failed" state
**And** error summary added as comment (configurable)

**Given** status update fails (API error)
**When** updating Linear
**Then** warning logged, run continues (non-blocking)

**Given** `sync_comments: false` in config
**When** phases transition
**Then** only status is updated, no comments added

## Tasks / Subtasks

### Task 1: Add Task Context to RunContext
- [ ] Add `task_id: str | None` field to `RunContext` model
- [ ] Add `task_info: TaskInfo | None` field to `RunContext` model
- [ ] Add `task_manager: str | None` field (e.g., "linear", "none")
- [ ] Populate fields when run is initiated from task ID

### Task 2: Create StatusSyncService
- [ ] Create `src/adw/task_managers/sync.py` with `StatusSyncService`
- [ ] Initialize with `TaskManager` instance and `TaskManagerConfig`
- [ ] Implement `sync_run_start(context: RunContext) -> None`
- [ ] Implement `sync_phase_transition(context: RunContext, from_phase: str, to_phase: str) -> None`
- [ ] Implement `sync_run_complete(context: RunContext, success: bool, error: str | None) -> None`

### Task 3: Integrate with Orchestrator
- [ ] Inject `StatusSyncService` into Orchestrator
- [ ] Call `sync_run_start` when run begins
- [ ] Call `sync_phase_transition` between phases
- [ ] Call `sync_run_complete` on run completion or failure
- [ ] Ensure sync calls are non-blocking (catch and log errors)

### Task 4: Implement Status Mapping
- [ ] Read `state_mapping` from config
- [ ] Map ADW states: `pending`, `running`, `completed`, `failed`
- [ ] Handle missing mapping gracefully (use current state)
- [ ] Support custom mappings per project

### Task 5: Add Phase Transition Metadata
- [ ] Include metadata in update_status calls:
  - `run_id: str`
  - `phase: str`
  - `duration_seconds: float`
  - `artifacts_count: int`
- [ ] Metadata available for comment generation

### Task 6: Handle Non-Blocking Failures
- [ ] Wrap all sync calls in try/except
- [ ] Log warnings on failure, don't raise
- [ ] Continue run execution regardless of sync status
- [ ] Track sync failures in run context for debugging

### Task 7: Write Tests
- [ ] Unit tests for `StatusSyncService` (6 tests)
- [ ] Unit tests for status mapping (4 tests)
- [ ] Unit tests for orchestrator integration (4 tests)
- [ ] Unit tests for error handling (3 tests)
- [ ] Integration test for full run with sync (2 tests)

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.2
- **Blocks:** Story 12.6
- **Can Parallel With:** Story 12.5, 12.7, 12.8

### Dependency Rationale
- Requires TaskManager protocol (12.1) and Linear implementation (12.2)
- Story 12.6 (comments) extends this infrastructure
- Other stories (12.5, 12.7, 12.8) work at different layers

---

## Developer Context

### Technical Requirements

1. **Orchestrator Integration**
   - StatusSyncService injected via constructor or context
   - Sync calls happen at specific lifecycle points
   - All sync calls must be non-blocking

2. **Status State Machine**
   ```
   Run Start -> "running"
   Phase Complete -> "running" (no change)
   Run Complete (success) -> "completed"
   Run Complete (failure) -> "failed"
   ```

3. **Error Handling**
   - API failures logged but don't stop run
   - Track failures in context for debugging
   - Retry logic handled by TaskManager

### Architecture Compliance

**File Location:** `src/adw/task_managers/`

**New File:**
```
src/adw/task_managers/
└── sync.py           # StatusSyncService
```

**Implementation Pattern:**
```python
# src/adw/task_managers/sync.py
from typing import Any
import logging
from adw.task_managers.base import TaskManager
from adw.models.config import TaskManagerConfig
from adw.models.context import RunContext

logger = logging.getLogger(__name__)

class StatusSyncService:
    def __init__(
        self,
        task_manager: TaskManager,
        config: TaskManagerConfig,
    ) -> None:
        self._task_manager = task_manager
        self._config = config

    def sync_run_start(self, context: RunContext) -> None:
        """Sync status when run starts."""
        if not context.task_id:
            return
        self._safe_update_status(context.task_id, "running", {
            "run_id": context.run_id,
            "phase": "start",
        })

    def sync_phase_transition(
        self,
        context: RunContext,
        from_phase: str,
        to_phase: str,
    ) -> None:
        """Sync status on phase transition (optional comment)."""
        ...

    def sync_run_complete(
        self,
        context: RunContext,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Sync final status when run completes."""
        ...

    def _safe_update_status(
        self,
        task_id: str,
        status: str,
        metadata: dict[str, Any],
    ) -> None:
        """Update status, catching and logging any errors."""
        try:
            mapped_status = self._config.state_mapping.get(status, status)
            self._task_manager.update_status(task_id, mapped_status, metadata)
        except Exception as e:
            logger.warning(
                "Failed to sync status to task manager",
                task_id=task_id,
                status=status,
                error=str(e),
            )
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| logging | stdlib | Error logging |

**No New Dependencies:** Uses existing TaskManager infrastructure.

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/sync.py`

**Modified Files:**
- `src/adw/models/context.py` - Add task_id, task_info fields
- `src/adw/core/orchestrator.py` - Integrate StatusSyncService

**Test Files:**
- `tests/unit/task_managers/test_sync.py`
- `tests/integration/test_task_manager_sync.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/task_managers/test_sync.py
class TestStatusSyncService:
    def test_sync_run_start_updates_status(self, mock_task_manager):
        """Calls update_status with 'running' on run start."""

    def test_sync_run_start_skipped_without_task_id(self, mock_task_manager):
        """Does nothing when context has no task_id."""

    def test_sync_phase_transition(self, mock_task_manager):
        """Calls update_status with phase metadata."""

    def test_sync_run_complete_success(self, mock_task_manager):
        """Updates to 'completed' state on success."""

    def test_sync_run_complete_failure(self, mock_task_manager):
        """Updates to 'failed' state on failure."""

    def test_sync_uses_state_mapping(self, mock_task_manager, config):
        """Maps ADW status to external system status."""

class TestStatusSyncServiceErrorHandling:
    def test_sync_continues_on_api_error(self, failing_task_manager):
        """Logs warning but doesn't raise on API failure."""

    def test_sync_logs_error_details(self, failing_task_manager, caplog):
        """Logs task_id, status, and error message."""

    def test_sync_doesnt_block_run(self, slow_task_manager):
        """Sync operations don't block main execution."""
```

---

## Previous Story Intelligence

**From Story 12.2:**
- LinearTaskManager.update_status() available
- State mapping in TaskManagerConfig
- Non-blocking error handling pattern

**Patterns to Follow:**
- Wrap external calls in try/except
- Use structured logging for errors
- Include context in error messages

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 12.1: TaskManager Protocol
- Epic 12.2: LinearTaskManager implementation
- Epic 5: Orchestrator phase execution patterns

**Established Patterns:**
- Orchestrator uses dependency injection
- Lifecycle hooks at phase boundaries
- Non-blocking external integrations

---

## Latest Technical Information

**Status Sync Best Practices (2025):**
- Non-blocking: External sync should never block main workflow
- Idempotent: Status updates should be safe to retry
- Audit trail: Log all sync attempts for debugging
- Graceful degradation: Run continues if sync fails

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Structured logging**: Use `logger.info("Status synced", task_id=..., status=...)`
- **Non-blocking external calls**: Wrap in try/except, log and continue
- **Dependency injection**: Pass services via constructor

---

## Dev Notes

### Implementation Approach

1. Add task fields to RunContext model
2. Create StatusSyncService with sync methods
3. Integrate into Orchestrator lifecycle
4. Add status mapping logic
5. Implement non-blocking error handling
6. Write comprehensive tests

### Key Design Decisions

1. **Service Pattern**: StatusSyncService encapsulates sync logic
2. **Non-Blocking**: All sync calls wrapped in try/except
3. **Configurable**: State mapping from config allows customization
4. **Observable**: All sync operations logged for debugging

### Orchestrator Integration Points

```python
# In Orchestrator.run()
def run(self, feature_request: str, task_id: str | None = None) -> RunResult:
    context = self._create_context(feature_request, task_id)

    # Sync run start
    self._sync_service.sync_run_start(context)

    try:
        for phase in self._phase_sequence:
            result = self._run_phase(phase, context)

            # Sync phase transition
            next_phase = self._get_next_phase(phase)
            if next_phase:
                self._sync_service.sync_phase_transition(context, phase, next_phase)

        # Sync run complete (success)
        self._sync_service.sync_run_complete(context, success=True)

    except Exception as e:
        # Sync run complete (failure)
        self._sync_service.sync_run_complete(context, success=False, error=str(e))
        raise
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.3]
- [Source: _bmad-output/architecture.md#Task Manager Integration]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 12: Task Manager Integration - Story 12.3

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
