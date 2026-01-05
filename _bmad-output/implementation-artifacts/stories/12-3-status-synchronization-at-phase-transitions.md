# Story 12.3: Status Synchronization at Phase Transitions

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

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

- [ ] **Task 1**: Create status sync integration point in Orchestrator
  - [ ] Add `_sync_task_status(status: TaskStatus)` method to Orchestrator
  - [ ] Call sync on run start (pending → running)
  - [ ] Call sync on run complete (running → completed)
  - [ ] Call sync on run failure (running → failed)

- [ ] **Task 2**: Create phase transition hooks
  - [ ] Add `on_phase_complete` callback to PhaseRunner
  - [ ] Orchestrator registers callback to sync status
  - [ ] Include phase name and summary in sync metadata

- [ ] **Task 3**: Implement state mapping resolution
  - [ ] Read state_mapping from TaskManagerConfig
  - [ ] Map ADW TaskStatus to Linear workflow state name
  - [ ] Query Linear team states to get state ID from name
  - [ ] Cache state ID lookups to avoid repeated API calls

- [ ] **Task 4**: Implement non-blocking status updates
  - [ ] Wrap `task_manager.update_status()` in try/except
  - [ ] Log warning on failure, don't raise
  - [ ] Include task_id and target_status in warning log

- [ ] **Task 5**: Add task_manager to RunContext
  - [ ] Store task_id in RunContext when run initiated from task
  - [ ] Store task_manager instance (or None) for status updates
  - [ ] Persist task_id across run resume

- [ ] **Task 6**: Write integration tests
  - [ ] Test status updates at run lifecycle points
  - [ ] Test state mapping resolution
  - [ ] Test non-blocking behavior on API failure
  - [ ] Test no sync when task_manager is None

---

## Developer Context

### Technical Requirements

This story integrates the TaskManager with the Orchestrator to provide automatic status synchronization during run execution. Updates must be non-blocking to prevent task manager failures from crashing runs.

**Key Design Decisions:**
- Non-blocking: All task manager calls wrapped in try/except
- State caching: Cache Linear state IDs after first lookup
- Optional comments: Controlled by `sync_comments` config
- Lifecycle hooks: Orchestrator notifies task manager at key points

### Architecture Compliance

**Modified Files:**
```
src/adw/core/
├── orchestrator.py    # Add task manager integration
├── phase_runner.py    # Add on_phase_complete callback
```

**File Locations:**
- Status sync logic in `src/adw/core/orchestrator.py`
- State mapping cache in `src/adw/task_managers/linear.py`

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| structlog | existing | Structured warning logs |
| pydantic | 2.12+ | RunContext update with task_id |

No new dependencies required.

### File Structure Requirements

**Modified Files:**
- `src/adw/core/orchestrator.py` - Add task manager hooks
- `src/adw/core/phase_runner.py` - Add completion callback
- `src/adw/models/context.py` - Add task_id field to RunContext
- `src/adw/task_managers/linear.py` - Add state caching

**New Files:**
- `tests/integration/test_task_manager_sync.py`

### Testing Requirements

```python
# tests/integration/test_task_manager_sync.py
def test_status_sync_on_run_start(mock_task_manager):
    """Task status updated to 'running' when run starts."""
    orchestrator = Orchestrator(task_manager=mock_task_manager)
    orchestrator.start_run(task_id="RULE-123", feature="Test")

    mock_task_manager.update_status.assert_called_with(
        "RULE-123", TaskStatus.running
    )

def test_status_sync_on_run_complete(mock_task_manager):
    """Task status updated to 'completed' when run completes."""
    orchestrator = Orchestrator(task_manager=mock_task_manager)
    orchestrator.complete_run()

    mock_task_manager.update_status.assert_called_with(
        ANY, TaskStatus.completed
    )

def test_status_sync_non_blocking_on_error(mock_task_manager, caplog):
    """Run continues when status sync fails."""
    mock_task_manager.update_status.side_effect = Exception("API error")

    orchestrator = Orchestrator(task_manager=mock_task_manager)
    orchestrator.start_run(task_id="RULE-123", feature="Test")

    # Run should continue despite error
    assert "Failed to update task status" in caplog.text

def test_no_sync_without_task_manager():
    """No sync attempted when task_manager is None."""
    orchestrator = Orchestrator(task_manager=None)
    orchestrator.start_run(feature="Test")  # Should not raise
```

**Coverage Target:** 85% (integration tests may miss some edge cases)

---

## Previous Story Intelligence

**From Story 12.1:**
- TaskManagerProtocol defines `update_status(task_id: str, status: TaskStatus)`
- TaskStatus enum: pending, running, completed, failed

**From Story 12.2:**
- LinearTaskManager implements `update_status` via GraphQL mutation
- State mapping configured in `task_manager_config.state_mapping`

---

## Git Intelligence

**Recent commit patterns:**
- Use `feat(core):` prefix for orchestrator changes
- Use `feat(task_managers):` for task manager changes

**Existing patterns:**
- PhaseRunner uses callbacks for progress reporting
- Orchestrator handles lifecycle events

---

## Latest Technical Information

### State Mapping Configuration

```yaml
task_manager_config:
  state_mapping:
    pending: "Todo"           # Before run starts
    running: "In Progress"    # Run is executing
    completed: "Done"         # Run finished successfully
    failed: "In Progress"     # Run failed - needs human attention
```

### Linear State Resolution

Linear uses workflow states with types: `backlog`, `unstarted`, `started`, `completed`, `canceled`.

```python
def _resolve_state_id(self, state_name: str) -> str:
    """Resolve Linear state name to state ID."""
    if state_name in self._state_cache:
        return self._state_cache[state_name]

    # Query team states
    query = """
        query TeamStates($teamId: String!) {
            team(id: $teamId) {
                states {
                    nodes { id, name }
                }
            }
        }
    """
    result = self._query(query, {"teamId": self.team_id})
    states = result["team"]["states"]["nodes"]

    for state in states:
        self._state_cache[state["name"]] = state["id"]

    return self._state_cache.get(state_name)
```

### Non-Blocking Pattern

```python
def _sync_task_status(self, status: TaskStatus) -> None:
    """Sync task status to external task manager (non-blocking)."""
    if not self.task_manager or not self.context.task_id:
        return

    try:
        self.task_manager.update_status(
            self.context.task_id,
            status
        )
        logger.info(
            "Task status synced",
            task_id=self.context.task_id,
            status=status.value
        )
    except Exception as e:
        logger.warning(
            "Failed to update task status",
            task_id=self.context.task_id,
            status=status.value,
            error=str(e)
        )
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- Structured logging: `logger.info("message", key=value)`
- Non-blocking external calls: wrap in try/except, log warnings
- Immutable state updates: use `context.model_copy(update={})`

---

## Dev Notes

### Key Implementation Details

1. **Lifecycle Points:**
   - `start_run()` → sync `running`
   - `complete_run()` → sync `completed`
   - `fail_run()` → sync `failed`

2. **RunContext Changes:**
   ```python
   class RunContext(BaseModel):
       # ... existing fields ...
       task_id: str | None = None  # Linear task identifier if initiated from task
   ```

3. **State Caching:** Cache Linear state IDs per team to avoid repeated lookups

4. **Error Isolation:** Task manager failures must NEVER crash runs

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.3]
- [Source: src/adw/core/orchestrator.py] - Existing orchestrator pattern
- [Source: src/adw/core/phase_runner.py] - Callback pattern

---

## Dev Agent Record

### Context Reference

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.2
- **Blocks:** Story 12.6
- **Can Parallel With:** Story 12.4, Story 12.5

### Dependency Rationale
- Story 12.1: Requires TaskManagerProtocol with update_status method
- Story 12.2: Requires LinearTaskManager implementation for status updates

