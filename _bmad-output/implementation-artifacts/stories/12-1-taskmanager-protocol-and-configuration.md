# Story 12.1: TaskManager Protocol and Configuration

Status: ready-for-dev
Linear Issue: not-configured
Epic: 12 - Task Manager Integration
Created: 2026-01-08

---

## Story

As a developer,
I want a pluggable TaskManager abstraction,
So that different task management systems can be supported.

## Acceptance Criteria

**Given** `task_manager: linear` in project.yaml
**When** adw initializes
**Then** LinearTaskManager is instantiated

**Given** `task_manager: none` or not specified
**When** adw runs
**Then** no task manager is used (current behavior)

**Given** TaskManager protocol
**When** implementing a new task manager
**Then** only `fetch_task`, `update_status`, `resolve_task_id` need implementation

**Given** invalid task_manager value
**When** config is loaded
**Then** ConfigError raised with available options

## Tasks / Subtasks

### Task 1: Create TaskManager Protocol
- [x] Create `src/adw/task_managers/__init__.py` package
- [x] Create `src/adw/task_managers/base.py` with `TaskManager` Protocol
- [x] Define Protocol methods:
  - `fetch_task(task_id: str) -> TaskInfo`
  - `update_status(task_id: str, status: str, metadata: dict[str, Any]) -> None`
  - `resolve_task_id(input_str: str) -> str | None`
- [x] Add `@property name: str` to Protocol for identification

### Task 2: Create TaskInfo Model
- [ ] Create `src/adw/models/task.py` with `TaskInfo` model
- [ ] Define fields:
  - `id: str` - Task ID (e.g., "RULE-123")
  - `identifier: str` - Full identifier from system
  - `title: str` - Task title/summary
  - `description: str | None` - Task description/body
  - `status: str | None` - Current status in external system
  - `priority: int | None` - Priority (1-4 or system-specific)
  - `labels: list[str]` - Task labels/tags
  - `assignee: str | None` - Assignee name
  - `parent_id: str | None` - Parent issue ID if exists
  - `parent_title: str | None` - Parent issue title
  - `custom_fields: dict[str, Any]` - Custom fields from system
- [ ] Export from `src/adw/models/__init__.py`

### Task 3: Implement NullTaskManager
- [ ] Create `src/adw/task_managers/null.py` with `NullTaskManager`
- [ ] Implement as no-op for all methods
- [ ] `fetch_task` raises `TaskError("No task manager configured")`
- [ ] `update_status` does nothing (no-op)
- [ ] `resolve_task_id` returns `None`
- [ ] Used when `task_manager: none` or not configured

### Task 4: Create TaskManager Factory
- [ ] Create `src/adw/task_managers/factory.py` with `TaskManagerFactory`
- [ ] Implement `create(config: TaskManagerConfig) -> TaskManager`
- [ ] Registry pattern for available task managers:
  - `"none"` -> `NullTaskManager`
  - `"linear"` -> `LinearTaskManager` (stub for now, implemented in 12.2)
- [ ] Raise `ConfigError` for unknown task_manager values with available options

### Task 5: Add TaskManager Configuration
- [ ] Add `TaskManagerConfig` model to `src/adw/models/config.py`
- [ ] Configuration fields:
  - `type: str = "none"` - Task manager type (none, linear)
  - `team_key: str | None` - Team prefix for ID detection
  - `state_mapping: dict[str, str]` - ADW state to external state mapping
  - `sync_comments: bool = False` - Post comments on transitions
  - `comment_on_failure_only: bool = False` - Only comment on failures
  - `labels: TaskManagerLabelsConfig` - Label management config
  - `auto_close: bool = False` - Close task when PR merged
  - `include_labels: bool = True` - Include labels in context
  - `include_parent: bool = True` - Include parent context
- [ ] Add `task_manager` field to `ProjectConfig`
- [ ] Default state_mapping: `{"pending": "Todo", "running": "In Progress", "completed": "Done", "failed": "In Progress"}`

### Task 6: Add TaskError Exception
- [ ] Add `TaskError` to `src/adw/exceptions.py`
- [ ] Include fields: `code`, `message`, `suggestion`, `recoverable`, `task_id`
- [ ] Error codes: `TASK_NOT_FOUND`, `TASK_FETCH_FAILED`, `TASK_UPDATE_FAILED`, `NO_TASK_MANAGER`

### Task 7: Write Tests
- [ ] Unit tests for `TaskManager` Protocol compliance (3 tests)
- [ ] Unit tests for `TaskInfo` model (4 tests)
- [ ] Unit tests for `NullTaskManager` (4 tests)
- [ ] Unit tests for `TaskManagerFactory` (5 tests)
- [ ] Unit tests for `TaskManagerConfig` validation (4 tests)
- [ ] Integration test for factory creation flow (2 tests)

---

## Dependencies

- **Depends On:** Epic 6 complete (Run Management)
- **Blocks:** 12.2, 12.3, 12.4, 12.5, 12.7, 12.8
- **Can Parallel With:** None

### Dependency Rationale
- All other stories in Epic 12 depend on the TaskManager protocol being defined
- Story 12.2 needs the protocol to implement LinearTaskManager
- Stories 12.3-12.8 need the protocol methods and models

---

## Developer Context

### Technical Requirements

1. **Protocol Design**
   - Use `typing.Protocol` for structural subtyping
   - All methods should be synchronous (API calls are blocking)
   - Methods should raise typed exceptions on failure
   - Protocol should be minimal - only essential methods

2. **Factory Pattern**
   - Lazy import of implementations to avoid import cycles
   - Registry-based lookup for extensibility
   - Clear error messages for invalid configurations

3. **Configuration Design**
   - Use Pydantic for validation
   - Sensible defaults for all optional fields
   - State mapping should be flexible for different systems

### Architecture Compliance

**File Location:** `src/adw/task_managers/`

**New Package Structure:**
```
src/adw/
├── task_managers/
│   ├── __init__.py           # Re-exports TaskManager, TaskManagerFactory
│   ├── base.py               # TaskManager Protocol
│   ├── null.py               # NullTaskManager (no-op implementation)
│   └── factory.py            # TaskManagerFactory
```

**Model Additions:**
```python
# src/adw/models/task.py
class TaskInfo(BaseModel):
    id: str
    identifier: str
    title: str
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    labels: list[str] = Field(default_factory=list)
    assignee: str | None = None
    parent_id: str | None = None
    parent_title: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)

# src/adw/models/config.py
class TaskManagerLabelsConfig(BaseModel):
    enabled: bool = True
    prefix: str = "adw:"

class TaskManagerConfig(BaseModel):
    type: str = "none"
    team_key: str | None = None
    state_mapping: dict[str, str] = Field(default_factory=lambda: {
        "pending": "Todo",
        "running": "In Progress",
        "completed": "Done",
        "failed": "In Progress"
    })
    sync_comments: bool = False
    comment_on_failure_only: bool = False
    labels: TaskManagerLabelsConfig = Field(default_factory=TaskManagerLabelsConfig)
    auto_close: bool = False
    include_labels: bool = True
    include_parent: bool = True
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| typing | stdlib | Protocol definition |
| Pydantic | 2.12+ | Model validation |

**No External Dependencies:** This story only defines protocols and configuration.

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/__init__.py`
- `src/adw/task_managers/base.py`
- `src/adw/task_managers/null.py`
- `src/adw/task_managers/factory.py`
- `src/adw/models/task.py`

**Modified Files:**
- `src/adw/models/config.py` - Add TaskManagerConfig, TaskManagerLabelsConfig
- `src/adw/models/__init__.py` - Export TaskInfo, TaskManagerConfig
- `src/adw/exceptions.py` - Add TaskError

**Test Files:**
- `tests/unit/task_managers/__init__.py`
- `tests/unit/task_managers/test_base.py`
- `tests/unit/task_managers/test_null.py`
- `tests/unit/task_managers/test_factory.py`
- `tests/unit/models/test_task.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/task_managers/test_base.py
class TestTaskManagerProtocol:
    def test_null_task_manager_implements_protocol(self):
        """NullTaskManager satisfies TaskManager protocol."""

    def test_protocol_defines_required_methods(self):
        """Protocol requires fetch_task, update_status, resolve_task_id."""

    def test_protocol_defines_name_property(self):
        """Protocol requires name property."""

# tests/unit/task_managers/test_null.py
class TestNullTaskManager:
    def test_fetch_task_raises_error(self):
        """fetch_task raises TaskError with NO_TASK_MANAGER code."""

    def test_update_status_no_op(self):
        """update_status does nothing and doesn't raise."""

    def test_resolve_task_id_returns_none(self):
        """resolve_task_id always returns None."""

    def test_name_returns_none(self):
        """name property returns 'none'."""

# tests/unit/task_managers/test_factory.py
class TestTaskManagerFactory:
    def test_create_none_returns_null_manager(self):
        """Creating with type='none' returns NullTaskManager."""

    def test_create_unknown_raises_config_error(self):
        """Unknown task_manager type raises ConfigError."""

    def test_create_linear_returns_linear_manager(self):
        """Creating with type='linear' returns LinearTaskManager."""

    def test_error_includes_available_options(self):
        """ConfigError message includes available task manager types."""

    def test_factory_uses_config_values(self):
        """Factory passes config to created task manager."""
```

---

## Previous Story Intelligence

This is the first story in Epic 12 (Task Manager Integration). No previous story learnings available.

**Relevant Patterns from Other Epics:**
- Epic 11 established the Validator Protocol pattern (structural subtyping)
- Epic 5 established the LLM Executor Protocol pattern
- Factory pattern used in Epic 5 for executor creation

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 11 stories: Validation system with Protocol pattern
- Epic 5 stories: LLM executor abstraction

**Established Patterns:**
- Protocols defined in `base.py` within each package
- Factory classes create implementations based on config
- Configuration models use Pydantic with sensible defaults
- Typed exceptions with code, message, suggestion fields

---

## Latest Technical Information

**Python Protocol Best Practices (2025):**
- Use `typing.Protocol` for structural subtyping
- Define minimal interfaces - only essential methods
- Use `runtime_checkable` decorator if isinstance checks needed
- Document expected behavior in docstrings

**Task Manager API Patterns:**
- Linear API uses GraphQL
- Jira uses REST
- GitHub Issues uses REST via octokit
- All support similar CRUD operations

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **All models in models/**: TaskInfo, TaskManagerConfig go in `models/`
- **Exception hierarchy**: TaskError extends ADWError
- **Type annotations required**: All functions fully typed
- **Protocol pattern**: Similar to LLMExecutor Protocol in executors/base.py

---

## Dev Notes

### Implementation Approach

1. Start with TaskManager Protocol definition (most important)
2. Add TaskInfo model and configuration models
3. Implement NullTaskManager as reference implementation
4. Create factory with registry pattern
5. Add TaskError to exceptions
6. Write comprehensive tests

### Key Design Decisions

1. **Protocol over ABC**: Use Protocol for structural subtyping flexibility
2. **NullTaskManager**: Default implementation when no task manager configured
3. **Factory Pattern**: Centralized creation with lazy imports
4. **Synchronous API**: Task manager calls are blocking (simpler model)

### Configuration Example

```yaml
# project.yaml
task_manager:
  type: linear
  team_key: RULE
  state_mapping:
    pending: "Todo"
    running: "In Progress"
    completed: "Done"
    failed: "In Progress"
  sync_comments: true
  labels:
    enabled: true
    prefix: "adw:"
  auto_close: true
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.1]
- [Source: _bmad-output/architecture.md#Task Manager Integration]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 12: Task Manager Integration - Story 12.1

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created TaskManager Protocol with runtime_checkable decorator, fetch_task, update_status, resolve_task_id methods, and name property. Created TaskInfo model (needed by Protocol) and tests.

### File List

**New Files:**
- `src/adw/task_managers/__init__.py` - Package init with TaskManager export
- `src/adw/task_managers/base.py` - TaskManager Protocol definition
- `src/adw/models/task.py` - TaskInfo model
- `tests/unit/task_managers/__init__.py` - Test package init
- `tests/unit/task_managers/test_base.py` - Protocol tests (3 tests)

**Modified Files:**
- `src/adw/models/__init__.py` - Added TaskInfo export
- `tests/unit/cli/test_progress.py` - Fixed pre-existing ISS-019 test bug (VERIFY -> VALIDATE)
