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
**When** the plan phase starts
**Then** Linear status updated per state_mapping (default: "In Progress")

**Given** a phase completes
**When** transitioning to next phase
**Then** Linear status updated per state_mapping for the new phase
**And** Linear comment added with phase completion info (optional, configurable)

**Given** the document phase completes successfully
**When** all phases done
**Then** Linear status remains at mapped "document" state (default: "In Review")
**And** issue is NOT closed (closing is a separate concern handled by 12.8)

**Given** the run fails at any phase
**When** error occurs
**Then** Linear status set to mapped "failed" state (default: "In Progress")
**And** error summary added as comment (configurable)

**Given** status update fails (API error)
**When** updating Linear
**Then** warning logged, run continues (non-blocking)

**Given** `sync_comments: false` in config
**When** phases transition
**Then** only status is updated, no comments added

**Given** custom state_mapping in config
**When** phase transitions occur
**Then** custom mapping is used instead of defaults

## Tasks / Subtasks

### Task 1: Add Task Context to RunContext
- [x] Add `task_id: str | None` field to `RunContext` model
- [x] Add `task_info: TaskInfo | None` field to `RunContext` model
- [x] Add `task_manager: str | None` field (e.g., "linear", "none")
- [x] Populate fields when run is initiated from task ID

### Task 2: Create StatusSyncService
- [x] Create `src/adw/task_managers/sync.py` with `StatusSyncService`
- [x] Initialize with `TaskManager` instance and `TaskManagerConfig`
- [x] Implement `sync_run_start(context: RunContext) -> None`
- [x] Implement `sync_phase_transition(context: RunContext, from_phase: str, to_phase: str) -> None`
- [x] Implement `sync_run_complete(context: RunContext, success: bool, error: str | None) -> None`

### Task 3: Integrate with Orchestrator
- [x] Inject `StatusSyncService` into Orchestrator
- [x] Call `sync_run_start` when run begins
- [x] Call `sync_phase_transition` between phases
- [x] Call `sync_run_complete` on run completion or failure
- [x] Ensure sync calls are non-blocking (catch and log errors)

### Task 4: Implement Phase-Based Status Mapping
- [x] Read `state_mapping` from config
- [x] Map ADW phases: `plan`, `build`, `validate`, `document`
- [x] Map error state: `failed`
- [x] Default mapping for Linear:
  - `plan`: "In Progress"
  - `build`: "In Progress"
  - `validate`: "In Review"
  - `document`: "In Review"
  - `failed`: "In Progress"
- [x] Handle missing mapping gracefully (use phase name as status)
- [x] Support custom mappings per project (config override)

### Task 5: Add Phase Transition Metadata
- [x] Include metadata in update_status calls:
  - `run_id: str`
  - `phase: str`
  - `duration_seconds: float`
  - `artifacts_count: int`
- [x] Metadata available for comment generation

### Task 6: Handle Non-Blocking Failures
- [x] Wrap all sync calls in try/except
- [x] Log warnings on failure, don't raise
- [x] Continue run execution regardless of sync status
- [x] Track sync failures in run context for debugging

### Task 7: Write Tests
- [ ] Unit tests for `StatusSyncService` (6 tests)
- [ ] Unit tests for phase-to-status mapping (4 tests)
- [ ] Unit tests for orchestrator integration (4 tests)
- [ ] Unit tests for error handling (3 tests)
- [ ] Integration test for full run with phase sync (2 tests)

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

2. **Phase-Based Status State Machine**
   ```
   Plan Start     -> state_mapping["plan"]     (default: "In Progress")
   Build Start    -> state_mapping["build"]    (default: "In Progress")
   Validate Start -> state_mapping["validate"] (default: "In Review")
   Document Start -> state_mapping["document"] (default: "In Review")
   Any Failure    -> state_mapping["failed"]   (default: "In Progress")

   Note: Run completion does NOT change status or close issue.
         Issue closing is handled separately by Story 12.8 if auto_close=true.
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

# Default phase-to-status mapping for Linear
DEFAULT_STATE_MAPPING = {
    "plan": "In Progress",
    "build": "In Progress",
    "validate": "In Review",
    "document": "In Review",
    "failed": "In Progress",
}

class StatusSyncService:
    def __init__(
        self,
        task_manager: TaskManager,
        config: TaskManagerConfig,
    ) -> None:
        self._task_manager = task_manager
        self._config = config

    def sync_phase_start(self, context: RunContext, phase: str) -> None:
        """Sync status when a phase starts."""
        if not context.task_id:
            return
        self._safe_update_status(context.task_id, phase, {
            "run_id": context.run_id,
            "phase": phase,
        })

    def sync_phase_transition(
        self,
        context: RunContext,
        from_phase: str,
        to_phase: str,
    ) -> None:
        """Sync status on phase transition."""
        if not context.task_id:
            return
        self._safe_update_status(context.task_id, to_phase, {
            "run_id": context.run_id,
            "from_phase": from_phase,
            "to_phase": to_phase,
        })

    def sync_run_failed(
        self,
        context: RunContext,
        phase: str,
        error: str,
    ) -> None:
        """Sync status when run fails."""
        if not context.task_id:
            return
        self._safe_update_status(context.task_id, "failed", {
            "run_id": context.run_id,
            "failed_phase": phase,
            "error": error,
        })

    def _safe_update_status(
        self,
        task_id: str,
        phase_or_state: str,
        metadata: dict[str, Any],
    ) -> None:
        """Update status, catching and logging any errors."""
        try:
            # Use config mapping, fall back to defaults, then to phase name
            mapping = self._config.state_mapping or DEFAULT_STATE_MAPPING
            mapped_status = mapping.get(phase_or_state, phase_or_state)
            self._task_manager.update_status(task_id, mapped_status, metadata)
        except Exception as e:
            logger.warning(
                "Failed to sync status to task manager",
                task_id=task_id,
                phase=phase_or_state,
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
    def test_sync_phase_start_updates_status(self, mock_task_manager):
        """Calls update_status with mapped phase status on phase start."""

    def test_sync_phase_start_skipped_without_task_id(self, mock_task_manager):
        """Does nothing when context has no task_id."""

    def test_sync_phase_transition(self, mock_task_manager):
        """Calls update_status with next phase mapping on transition."""

    def test_sync_run_failed_updates_to_failed_status(self, mock_task_manager):
        """Updates to 'failed' mapped state on run failure."""

    def test_sync_uses_default_state_mapping(self, mock_task_manager):
        """Uses default mapping (plan->In Progress, validate->In Review, etc.)."""

    def test_sync_uses_custom_state_mapping(self, mock_task_manager, config):
        """Uses custom mapping from config when provided."""

class TestPhaseStatusMapping:
    def test_plan_maps_to_in_progress(self, mock_task_manager):
        """'plan' phase maps to 'In Progress' by default."""

    def test_build_maps_to_in_progress(self, mock_task_manager):
        """'build' phase maps to 'In Progress' by default."""

    def test_validate_maps_to_in_review(self, mock_task_manager):
        """'validate' phase maps to 'In Review' by default."""

    def test_document_maps_to_in_review(self, mock_task_manager):
        """'document' phase maps to 'In Review' by default."""

class TestStatusSyncServiceErrorHandling:
    def test_sync_continues_on_api_error(self, failing_task_manager):
        """Logs warning but doesn't raise on API failure."""

    def test_sync_logs_error_details(self, failing_task_manager, caplog):
        """Logs task_id, phase, and error message."""

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

    try:
        for phase in self._phase_sequence:  # ["plan", "build", "validate", "document"]
            # Sync phase start (updates Linear status)
            self._sync_service.sync_phase_start(context, phase)

            result = self._run_phase(phase, context)

            # Sync phase transition (if there's a next phase)
            next_phase = self._get_next_phase(phase)
            if next_phase:
                self._sync_service.sync_phase_transition(context, phase, next_phase)

        # Run complete - status stays at "document" mapping (e.g., "In Review")
        # Issue is NOT closed here - that's handled by Story 12.8 if auto_close=true

    except Exception as e:
        # Sync failure status
        self._sync_service.sync_run_failed(context, phase=current_phase, error=str(e))
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
