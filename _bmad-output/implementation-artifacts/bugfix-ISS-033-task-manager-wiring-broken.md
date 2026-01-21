# Story: Bugfix ISS-033 - Task Manager Services Not Wired in Bootstrap

Status: ready-for-dev
Linear Issue: not-configured
Epic: 12 - Task Manager Integration
Created: 2026-01-21

---

## Story

As a user with Linear integration configured,
I want status sync and label management to work correctly,
So that my team can see ADW progress on Linear issues and labels are applied correctly.

## Acceptance Criteria

**Given** a project with Linear task manager configured and `sync_comments: true`
**When** an ADW run executes with a task ID (e.g., `adw run RULE-151`)
**Then** phase completion comments MUST be posted to the Linear issue

**Given** a project with label management enabled (`labels.enabled: true`)
**When** an ADW run starts with a task ID
**Then** the `adw:running` label MUST be added to the Linear issue
**And** phase labels like `adw:phase:plan` MUST be added/updated during execution
**And** the `adw:completed` or `adw:failed` label MUST be applied on completion

**Given** the Linear API requires internal UUID for label operations
**When** LabelManager is created
**Then** it MUST receive `task_info.id` (the Linear UUID), NOT the identifier (like "RULE-151")

**Given** StatusSyncService exists in the codebase
**When** bootstrap.py creates the orchestrator
**Then** StatusSyncService MUST be instantiated and passed to the Orchestrator

## Tasks / Subtasks

### Task 1: Create StatusSyncService in bootstrap.py
- [x] Import StatusSyncService from `adw.task_managers.sync`
- [x] Create StatusSyncService after TaskManager is created
- [x] Pass task_manager and task_manager_config to StatusSyncService constructor
- [x] Pass status_sync_service to Orchestrator constructor

### Task 2: Fix LabelManager to receive internal UUID
- [x] Locate LabelManager creation at bootstrap.py:278
- [x] Change `task_id` parameter to `task_info.id` (requires task_info to be available)
- [x] Ensure task_info is fetched before LabelManager creation
- [x] Add guard to only create LabelManager when task_info is available

### Task 3: Wire task_info through the bootstrap chain
- [x] Ensure fetch_task() result (task_info) is available in bootstrap.py
- [x] Pass task_info.id to LabelManager constructor
- [x] Verify task_info contains the correct internal UUID from Linear

### Task 4: Write Tests
- [ ] Add test: StatusSyncService instantiated when task_manager is configured
- [ ] Add test: LabelManager receives internal UUID, not identifier
- [ ] Add test: Labels are applied correctly during a mock run
- [ ] Add test: Comments are posted when sync_comments is true

---

## Relevant Feature Documentation

- **Story 12.3** (Status Synchronization): Defines StatusSyncService integration patterns
- **Story 12.7** (Label Management): Defines LabelManager requirements
- **Epic 12** (Task Manager Integration): Overall architecture for task manager services

---

## Developer Context

### Technical Requirements

1. **Bug 1: StatusSyncService Not Instantiated**
   - Location: `src/adw/cli/bootstrap.py`
   - Issue: The orchestrator accepts `status_sync_service` parameter but bootstrap.py never creates it
   - StatusSyncService exists at `src/adw/task_managers/sync.py` and is fully implemented
   - Constructor signature: `StatusSyncService(task_manager: TaskManager, config: TaskManagerConfig)`

2. **Bug 2: LabelManager Receives Wrong ID**
   - Location: `src/adw/cli/bootstrap.py:278`
   - Issue: `LabelManager(task_manager, labels_config, task_id)` uses identifier (e.g., "RULE-151")
   - Linear API requires internal UUID (e.g., "550e8400-e29b-41d4-a716-446655440000")
   - The UUID is available from `task_info.id` after calling `task_manager.fetch_task()`

### Architecture Compliance

**File Location:** `src/adw/cli/bootstrap.py`

**Current Code (BROKEN):**
```python
# Line 273-278 - LabelManager uses wrong ID
label_manager: LabelManager | None = None
if task_manager is not None and task_id is not None and config is not None:
    labels_config = config.task_manager.labels if config.task_manager else None
    if labels_config and labels_config.enabled:
        label_manager = LabelManager(task_manager, labels_config, task_id)  # BUG: task_id is identifier

# StatusSyncService is NEVER created - no code exists for it
```

**Required Fix:**
```python
# Import at top of file
from adw.task_managers.sync import StatusSyncService

# In create_orchestrator() function - after task_manager is created:

# Create StatusSyncService if task manager is configured
status_sync_service: StatusSyncService | None = None
if task_manager is not None and config is not None and config.task_manager:
    status_sync_service = StatusSyncService(task_manager, config.task_manager)

# Create LabelManager with internal UUID (requires task_info)
label_manager: LabelManager | None = None
if task_manager is not None and task_info is not None and config is not None:
    labels_config = config.task_manager.labels if config.task_manager else None
    if labels_config and labels_config.enabled:
        label_manager = LabelManager(task_manager, labels_config, task_info.id)  # FIX: Use internal UUID

# Pass both to orchestrator
orchestrator = Orchestrator(
    ...
    label_manager=label_manager,
    status_sync_service=status_sync_service,  # ADD THIS
)
```

**Challenge: task_info Availability**

The current `create_orchestrator()` function signature is:
```python
def create_orchestrator(
    console: Console | None = None,
    *,
    with_progress: bool = True,
    allow_dangerous: bool = False,
    run_id: str | None = None,
    show_llm_output: bool = False,
    task_manager: TaskManager | None = None,
    task_id: str | None = None,  # This is the identifier, e.g., "RULE-151"
) -> Orchestrator:
```

**Option A (Recommended):** Add `task_info` parameter to `create_orchestrator()`:
```python
def create_orchestrator(
    ...
    task_manager: TaskManager | None = None,
    task_id: str | None = None,  # Keep for backwards compatibility
    task_info: TaskInfo | None = None,  # Add this
) -> Orchestrator:
```

**Option B:** Fetch task_info inside create_orchestrator() if task_manager and task_id are provided:
```python
# Inside create_orchestrator():
task_info: TaskInfo | None = None
if task_manager is not None and task_id is not None:
    try:
        task_info = task_manager.fetch_task(task_id)
    except TaskError:
        pass  # Non-blocking - allow run without task_info
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| None | N/A | Uses existing project dependencies only |

**No New Dependencies:** This fix uses existing services that are already implemented.

### File Structure Requirements

**Modified Files:**
- `src/adw/cli/bootstrap.py` - Main fix location

**Potentially Modified Files (depending on approach):**
- `src/adw/cli/commands/run.py` - If task_info needs to be fetched and passed earlier
- `src/adw/cli/commands/resume.py` - Same consideration

**Test Files:**
- `tests/unit/cli/test_bootstrap.py` - Add tests for service wiring

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/cli/test_bootstrap.py

class TestBootstrapTaskManagerWiring:
    def test_status_sync_service_created_when_task_manager_configured(
        self, mock_task_manager, mock_config
    ):
        """StatusSyncService is instantiated when task_manager is provided."""
        orchestrator = create_orchestrator(
            task_manager=mock_task_manager,
            task_id="RULE-123",
            task_info=mock_task_info,
        )
        assert orchestrator._status_sync_service is not None

    def test_status_sync_service_none_without_task_manager(self):
        """StatusSyncService is None when no task_manager is configured."""
        orchestrator = create_orchestrator()
        assert orchestrator._status_sync_service is None

    def test_label_manager_receives_internal_uuid(
        self, mock_task_manager, mock_config, mock_task_info
    ):
        """LabelManager is created with task_info.id (UUID), not identifier."""
        mock_task_info.id = "internal-uuid-123"
        mock_task_info.identifier = "RULE-151"

        orchestrator = create_orchestrator(
            task_manager=mock_task_manager,
            task_id="RULE-151",
            task_info=mock_task_info,
        )

        # Verify LabelManager was created with the UUID, not identifier
        assert orchestrator._label_manager._task_id == "internal-uuid-123"

    def test_label_manager_not_created_without_task_info(
        self, mock_task_manager, mock_config
    ):
        """LabelManager is None when task_info is not available."""
        orchestrator = create_orchestrator(
            task_manager=mock_task_manager,
            task_id="RULE-151",
            task_info=None,  # No task_info
        )
        assert orchestrator._label_manager is None
```

**Integration Tests (verify end-to-end flow):**
```python
# tests/integration/test_task_manager_integration.py

class TestTaskManagerIntegration:
    def test_run_with_task_manager_posts_comments(
        self, mock_linear_client, project_with_linear
    ):
        """ADW run with Linear configured posts phase comments."""
        # This test verifies the full wiring works end-to-end

    def test_run_with_task_manager_applies_labels(
        self, mock_linear_client, project_with_linear
    ):
        """ADW run with Linear configured applies correct labels."""
```

---

## Previous Story Intelligence

**From Story 12.3 (Status Synchronization):**
- StatusSyncService is fully implemented at `src/adw/task_managers/sync.py`
- Accepts TaskManager and TaskManagerConfig in constructor
- Has methods: `sync_phase_start()`, `sync_phase_transition()`, `sync_run_failed()`, `post_phase_comment()`, etc.
- All methods are non-blocking (catch exceptions and log warnings)
- Orchestrator already has `_status_sync_service` attribute and uses it in `_execute_phase_with_transitions()`

**From Story 12.7 (Label Management):**
- LabelManager is fully implemented at `src/adw/task_managers/labels.py`
- Constructor: `LabelManager(task_manager, config, task_id)` - but task_id should be internal UUID
- Orchestrator already has `_label_manager` attribute and calls `set_running()`, `set_phase()`, etc.

**Key Insight:**
The services are implemented and the Orchestrator uses them correctly. The ONLY bug is in bootstrap.py which:
1. Never creates StatusSyncService
2. Passes identifier instead of UUID to LabelManager

---

## Git Intelligence

**Recent Relevant Commits:**
- `589a051` fix(ISS-031): Move PR creation to after document phase, before ship
- `6caa73e` fix(ISS-030): Honor project config.yaml without prompt.md
- `251b6c1` fix(ISS-029): Honor phase configuration from command configs

**Established Patterns:**
- Bootstrap.py uses dependency injection pattern
- Services are created in bootstrap and passed to Orchestrator
- Non-blocking external integrations (catch and log errors)

---

## Latest Technical Information

**Linear API Requirements (2026):**
- All issue mutations require internal UUID, not public identifier
- Label operations: `IssueAddLabel` and `IssueRemoveLabel` mutations use `issueId: ID!`
- Comment operations: `CommentCreate` mutation uses `issueId: ID!`

**TaskInfo Model:**
```python
class TaskInfo(BaseModel):
    id: str           # Internal UUID (use this for API calls)
    identifier: str   # Public identifier like "RULE-151" (display only)
    title: str
    description: str | None
    ...
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Structured logging**: Use `logger.info("message", extra={"key": "value"})`
- **Non-blocking external calls**: Wrap in try/except, log and continue
- **Dependency injection**: Pass services via constructor
- **Type annotations required**: Full type hints for all function signatures

---

## Dev Notes

### Implementation Approach

1. **Start with the simplest fix**: Add StatusSyncService creation and fix LabelManager task_id
2. **Handle task_info availability**: Either add parameter or fetch inside bootstrap
3. **Verify with existing tests**: The orchestrator tests should still pass
4. **Add specific wiring tests**: Test that services are correctly instantiated

### Key Design Decisions

1. **Option A (Recommended)**: Add `task_info` parameter to `create_orchestrator()`
   - Pros: Cleaner, explicit, caller controls when fetch happens
   - Cons: Requires updating callers in run.py and resume.py

2. **Option B**: Fetch task_info inside `create_orchestrator()`
   - Pros: No signature changes, backwards compatible
   - Cons: Duplicates fetch logic, may fetch twice if caller already has it

### Callers of create_orchestrator()

Search the codebase for callers that need updating if Option A:
- `src/adw/cli/commands/run.py`
- `src/adw/cli/commands/resume.py`
- Any tests that call `create_orchestrator()`

### Verification Checklist

After implementation:
- [ ] `adw run RULE-XXX` with Linear configured posts comments
- [ ] Labels appear on Linear issue during run
- [ ] `adw:running` added at start
- [ ] `adw:phase:plan`, `adw:phase:build`, etc. cycle correctly
- [ ] `adw:completed` or `adw:failed` applied at end
- [ ] No Python errors or stack traces related to task manager

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-033-task-manager-wiring-broken.md]
- [Source: src/adw/cli/bootstrap.py:273-278]
- [Source: src/adw/task_managers/sync.py]
- [Source: src/adw/task_managers/labels.py]
- [Source: src/adw/core/orchestrator.py:141-142]

---

## Dev Agent Record

### Context Reference

Bugfix for ISS-033: Task Manager Services Not Wired in Bootstrap

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

