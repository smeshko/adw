# Story 12.7: Label Management

Status: done
Linear Issue: not-configured
Epic: 12 - Task Manager Integration
Created: 2026-01-08

---

## Story

As a user,
I want ADW to manage task labels based on run state,
So that my task board reflects current progress.

## Acceptance Criteria

**Given** a run starts
**When** orchestrator initializes
**Then** label `adw:running` is added to the task

**Given** a phase starts
**When** phase runner begins
**Then** label `adw:phase:{phase_name}` is added (e.g., `adw:phase:build`)

**Given** a phase completes
**When** moving to next phase
**Then** previous phase label is removed, new phase label is added

**Given** a run completes successfully
**When** all phases done
**Then** `adw:running` removed, `adw:completed` added

**Given** a run fails
**When** error occurs
**Then** `adw:running` removed, `adw:failed` added, phase label remains

**Given** label configuration
**When** `labels.enabled: false` in config
**Then** no label operations are performed

## Tasks / Subtasks

### Task 1: Extend TaskManager Protocol
- [x] Add `add_label(task_id: str, label: str) -> None` to Protocol
- [x] Add `remove_label(task_id: str, label: str) -> None` to Protocol
- [x] Implement in `NullTaskManager` (no-op)
- [x] Implement in `LinearTaskManager`

### Task 2: Implement Linear Label Operations
- [x] Add label query to get label ID by name
- [x] Create label if it doesn't exist (with prefix color)
- [x] Implement `issueAddLabel` mutation
- [x] Implement `issueRemoveLabel` mutation
- [x] Cache label IDs to reduce API calls

### Task 3: Create LabelManager Service
- [x] Create `src/adw/task_managers/labels.py` with `LabelManager`
- [x] Initialize with `TaskManager` and `TaskManagerLabelsConfig`
- [x] Implement `set_running(task_id)` - add running label
- [x] Implement `set_phase(task_id, phase)` - swap phase labels
- [x] Implement `set_completed(task_id)` - remove running, add completed
- [x] Implement `set_failed(task_id)` - remove running, add failed

### Task 4: Handle Label Prefix
- [x] Use `labels.prefix` from config (default: `adw:`)
- [x] Construct full label names: `{prefix}running`, `{prefix}phase:{phase}`
- [x] Support custom prefixes for multi-project boards

### Task 5: Integrate with Orchestrator
- [x] Inject `LabelManager` into Orchestrator
- [x] Call `set_running` on run start
- [x] Call `set_phase` on phase transitions
- [x] Call `set_completed` or `set_failed` on run end
- [x] Check `labels.enabled` config before operations

### Task 6: Handle Non-Blocking Failures
- [x] Wrap all label operations in try/except
- [x] Log warnings on failure, don't raise
- [x] Continue run execution regardless of label status
- [x] Track label operation failures for debugging

### Task 7: Write Tests
- [x] Unit tests for `LabelManager` (6 tests) - 19 tests written (exceeds requirement)
- [x] Unit tests for `LinearTaskManager` label operations (4 tests) - 15 tests written
- [x] Unit tests for label prefix handling (3 tests) - included in LabelManager tests
- [x] Unit tests for config checking (3 tests) - included in LabelManager tests
- [x] Integration test for full label lifecycle (2 tests) - TestLabelManagerLifecycle

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.2
- **Blocks:** None
- **Can Parallel With:** Story 12.3, 12.5, 12.8

### Dependency Rationale
- Requires TaskManager protocol (12.1) and Linear implementation (12.2)
- Independent of status sync, comments, and closing
- Works at label layer, parallel execution possible

---

## Developer Context

### Technical Requirements

1. **Label Lifecycle**
   ```
   Run Start: +adw:running, +adw:phase:plan
   Phase Transition: -adw:phase:plan, +adw:phase:build
   Run Success: -adw:running, -adw:phase:*, +adw:completed
   Run Failure: -adw:running, +adw:failed (keep phase label)
   ```

2. **Label Creation**
   - Auto-create labels if they don't exist
   - Use consistent color for adw: labels
   - Cache label IDs for efficiency

3. **Non-Blocking**
   - Label operations should not fail the run
   - Log warnings on API errors
   - Continue execution regardless

### Architecture Compliance

**File Location:** `src/adw/task_managers/`

**New Files:**
```
src/adw/task_managers/
└── labels.py         # LabelManager
```

**Implementation Pattern:**
```python
# src/adw/task_managers/labels.py
import logging
from adw.task_managers.base import TaskManager
from adw.models.config import TaskManagerLabelsConfig

logger = logging.getLogger(__name__)

class LabelManager:
    """Manages task labels for ADW run lifecycle."""

    def __init__(
        self,
        task_manager: TaskManager,
        config: TaskManagerLabelsConfig,
    ) -> None:
        self._task_manager = task_manager
        self._config = config
        self._current_phase_label: str | None = None

    @property
    def _prefix(self) -> str:
        return self._config.prefix

    def _label(self, name: str) -> str:
        """Construct full label with prefix."""
        return f"{self._prefix}{name}"

    def set_running(self, task_id: str) -> None:
        """Add running label when run starts."""
        if not self._config.enabled:
            return
        self._safe_add_label(task_id, self._label("running"))

    def set_phase(self, task_id: str, phase: str) -> None:
        """Swap phase label during phase transitions."""
        if not self._config.enabled:
            return
        # Remove previous phase label
        if self._current_phase_label:
            self._safe_remove_label(task_id, self._current_phase_label)
        # Add new phase label
        new_label = self._label(f"phase:{phase}")
        self._safe_add_label(task_id, new_label)
        self._current_phase_label = new_label

    def set_completed(self, task_id: str) -> None:
        """Set labels for successful completion."""
        if not self._config.enabled:
            return
        self._safe_remove_label(task_id, self._label("running"))
        if self._current_phase_label:
            self._safe_remove_label(task_id, self._current_phase_label)
        self._safe_add_label(task_id, self._label("completed"))

    def set_failed(self, task_id: str) -> None:
        """Set labels for failed run."""
        if not self._config.enabled:
            return
        self._safe_remove_label(task_id, self._label("running"))
        self._safe_add_label(task_id, self._label("failed"))
        # Keep phase label to show where it failed

    def _safe_add_label(self, task_id: str, label: str) -> None:
        """Add label with error handling."""
        try:
            self._task_manager.add_label(task_id, label)
        except Exception as e:
            logger.warning("Failed to add label", task_id=task_id, label=label, error=str(e))

    def _safe_remove_label(self, task_id: str, label: str) -> None:
        """Remove label with error handling."""
        try:
            self._task_manager.remove_label(task_id, label)
        except Exception as e:
            logger.warning("Failed to remove label", task_id=task_id, label=label, error=str(e))
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| No new dependencies | - | Uses existing infrastructure |

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/labels.py`

**Modified Files:**
- `src/adw/task_managers/base.py` - Add add_label/remove_label to Protocol
- `src/adw/task_managers/null.py` - Implement no-op label methods
- `src/adw/task_managers/linear.py` - Implement label operations
- `src/adw/task_managers/linear_client.py` - Add label mutations

**Test Files:**
- `tests/unit/task_managers/test_labels.py`
- `tests/unit/task_managers/test_linear_labels.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/task_managers/test_labels.py
class TestLabelManager:
    def test_set_running_adds_label(self, mock_task_manager):
        """Adds adw:running label on run start."""

    def test_set_phase_swaps_labels(self, mock_task_manager):
        """Removes previous phase label, adds new one."""

    def test_set_completed_removes_running(self, mock_task_manager):
        """Removes running and phase labels, adds completed."""

    def test_set_failed_keeps_phase_label(self, mock_task_manager):
        """Removes running, adds failed, keeps phase label."""

    def test_respects_config_enabled(self, mock_task_manager):
        """Does nothing when labels.enabled=false."""

    def test_uses_configured_prefix(self, mock_task_manager):
        """Uses prefix from config."""

class TestLabelManagerErrorHandling:
    def test_add_label_failure_non_blocking(self, failing_task_manager):
        """Logs warning but doesn't raise on add failure."""

    def test_remove_label_failure_non_blocking(self, failing_task_manager):
        """Logs warning but doesn't raise on remove failure."""

    def test_continues_on_partial_failure(self, partially_failing_task_manager):
        """Continues operations even if some fail."""
```

---

## Previous Story Intelligence

**From Story 12.2:**
- LinearTaskManager foundation
- API client patterns

**From Story 12.3:**
- Non-blocking pattern established
- Orchestrator integration points

**Patterns to Follow:**
- Wrap API calls in try/except
- Use structured logging
- Check config before operations

---

## Git Intelligence

**Recent Relevant Commits:**
- Story 12.2: Linear API client
- Story 12.3: Non-blocking sync pattern

**Established Patterns:**
- Service classes encapsulate domain logic
- Config-driven behavior
- Non-blocking external operations

---

## Latest Technical Information

**Linear Label API (2025):**

```graphql
# Get or create label
query Labels($teamId: String!) {
  team(id: $teamId) {
    labels { nodes { id name color } }
  }
}

mutation CreateLabel($teamId: String!, $name: String!, $color: String!) {
  labelCreate(input: {teamId: $teamId, name: $name, color: $color}) {
    success
    label { id name }
  }
}

# Add label to issue
mutation AddLabel($issueId: String!, $labelId: String!) {
  issueAddLabel(id: $issueId, labelId: $labelId) {
    success
  }
}

# Remove label from issue
mutation RemoveLabel($issueId: String!, $labelId: String!) {
  issueRemoveLabel(id: $issueId, labelId: $labelId) {
    success
  }
}
```

**Label Best Practices:**
- Use consistent prefix for automated labels
- Auto-create labels with recognizable color
- Cache label IDs to reduce API calls
- Non-blocking operations for reliability

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Non-blocking external calls**: Wrap in try/except, log and continue
- **Configuration-driven**: Check config.labels.enabled
- **Structured logging**: Log label operations

---

## Dev Notes

### Implementation Approach

1. Add label methods to Protocol
2. Implement Linear label operations with caching
3. Create LabelManager service
4. Integrate with Orchestrator
5. Test non-blocking behavior
6. Handle label creation

### Key Design Decisions

1. **Service Pattern**: LabelManager encapsulates label lifecycle
2. **Label Caching**: Cache label IDs to reduce API calls
3. **Auto-Create**: Create labels if they don't exist
4. **Phase Label Tracking**: Track current phase label for proper swap

### Label State Machine

```
START
  └─> +adw:running, +adw:phase:plan
        │
        ├─> -adw:phase:plan, +adw:phase:build
        │     │
        │     ├─> -adw:phase:build, +adw:phase:verify
        │     │     │
        │     │     └─> ... continue phases ...
        │     │
        │     └─> FAILURE: -adw:running, +adw:failed (keep adw:phase:build)
        │
        └─> SUCCESS: -adw:running, -adw:phase:*, +adw:completed
```

### Linear Color for ADW Labels

```python
ADW_LABEL_COLOR = "#9333EA"  # Purple - distinguishes automation labels
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.7]
- [Source: _bmad-output/architecture.md#Task Manager Integration]
- [Linear API Docs: Label operations]

---

## Dev Agent Record

### Context Reference

Epic 12: Task Manager Integration - Story 12.7

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

- Task 1: Extended TaskManager Protocol with add_label/remove_label methods. Added to base.py Protocol, implemented no-op in null.py, added stub implementations in linear.py that delegate to linear_client.py (stub methods added for Task 2).
- Task 2: Implemented full Linear label operations in linear_client.py. Added GraphQL queries/mutations for labels (GET_TEAM_LABELS_QUERY, CREATE_LABEL_MUTATION, ADD_LABEL_MUTATION, REMOVE_LABEL_MUTATION). Implemented get_team_labels, create_label, add_label_to_issue, remove_label_from_issue methods. Added label caching (_label_cache) to reduce API calls. Full add_label/remove_label now use get-or-create pattern.
- Task 3+4+6: Created LabelManager service in labels.py with set_running(), set_phase(), set_completed(), set_failed() methods. Uses config.prefix for label names (default "adw:"). All operations are non-blocking with try/except and logging. 17 unit tests added.
- Task 5: Integrated LabelManager with Orchestrator. Added label_manager parameter to Orchestrator.__init__. Added set_running() call at run start, set_phase() at phase transitions, set_completed()/set_failed() at run end. Updated bootstrap.py to create LabelManager when task_manager and task_id are provided.
- Task 7: Comprehensive test coverage added. 19 LabelManager tests, 15 LinearClient label tests, plus 2 lifecycle integration tests. Total: 97 passing tests in task_managers module.

### File List

- `src/adw/task_managers/base.py` - Added add_label/remove_label to Protocol
- `src/adw/task_managers/null.py` - Added no-op implementations
- `src/adw/task_managers/linear.py` - Added implementations delegating to client
- `src/adw/task_managers/linear_client.py` - Full label operations with GraphQL, caching
- `src/adw/task_managers/labels.py` - New LabelManager service
- `src/adw/core/orchestrator.py` - Added label_manager parameter and label calls
- `src/adw/cli/bootstrap.py` - Added LabelManager creation in create_orchestrator
- `tests/unit/task_managers/test_base.py` - Added tests for new Protocol methods
- `tests/unit/task_managers/test_null.py` - Added tests for no-op implementations
- `tests/unit/task_managers/test_linear_client.py` - Added tests for label operations (15 tests)
- `tests/unit/task_managers/test_labels.py` - LabelManager tests (19 tests)
