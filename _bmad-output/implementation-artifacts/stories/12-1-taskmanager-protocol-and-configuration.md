# Story 12.1: TaskManager Protocol and Configuration

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

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

- [ ] **Task 1**: Create `TaskManagerProtocol` in `src/adw/task_managers/protocol.py`
  - [ ] Define `fetch_task(task_id: str) -> TaskInfo` method signature
  - [ ] Define `update_status(task_id: str, status: TaskStatus) -> None` method signature
  - [ ] Define `resolve_task_id(input: str) -> str | None` method signature
  - [ ] Define `add_comment(task_id: str, comment: str) -> None` method signature (optional)
  - [ ] Define `update_labels(task_id: str, add: list[str], remove: list[str]) -> None` method signature (optional)

- [ ] **Task 2**: Create Pydantic models in `src/adw/models/task_manager.py`
  - [ ] Create `TaskInfo` model (id, identifier, title, description, status, priority, labels, assignee, parent, custom_fields)
  - [ ] Create `TaskStatus` enum (pending, running, completed, failed)
  - [ ] Create `TaskManagerConfig` model with validation
  - [ ] Create `TaskManagerType` enum (none, linear, github_issues, jira)

- [ ] **Task 3**: Create `NullTaskManager` in `src/adw/task_managers/null.py`
  - [ ] Implement protocol with no-op methods
  - [ ] All methods return None or empty values
  - [ ] Used when no task manager is configured

- [ ] **Task 4**: Update project configuration schema
  - [ ] Add `task_manager: TaskManagerType` field to project config
  - [ ] Add `task_manager_config: TaskManagerConfig` nested config
  - [ ] Add validation for api_key_env, team_key, state_mapping
  - [ ] Ensure backward compatibility (no task_manager = NullTaskManager)

- [ ] **Task 5**: Implement TaskManager factory
  - [ ] Create `get_task_manager(config: ProjectConfig) -> TaskManagerProtocol` factory function
  - [ ] Return NullTaskManager when task_manager is "none" or not specified
  - [ ] Raise ConfigError with available options for invalid values
  - [ ] Lazy-load provider modules to avoid import errors when dependencies missing

- [ ] **Task 6**: Write unit tests
  - [ ] Test protocol method signatures with MockTaskManager
  - [ ] Test factory returns NullTaskManager by default
  - [ ] Test ConfigError for invalid task_manager values
  - [ ] Test TaskInfo model serialization/deserialization
  - [ ] Test TaskManagerConfig validation

---

## Developer Context

### Technical Requirements

This story establishes the foundation for external task manager integration. The protocol pattern allows multiple providers (Linear, GitHub Issues, Jira) to be added without modifying core orchestration code.

**Key Design Decisions:**
- Use Protocol class (PEP 544) for structural subtyping - no inheritance required
- Optional methods (add_comment, update_labels) use `@runtime_checkable` for feature detection
- NullTaskManager provides graceful degradation when no integration configured
- Factory pattern with lazy loading prevents import errors when provider SDKs not installed

### Architecture Compliance

**File Locations:**
```
src/adw/
├── task_managers/
│   ├── __init__.py          # Export protocol, factory, null manager
│   ├── protocol.py          # TaskManagerProtocol definition
│   ├── null.py              # NullTaskManager implementation
│   └── factory.py           # get_task_manager() factory function
├── models/
│   └── task_manager.py      # TaskInfo, TaskStatus, TaskManagerConfig models
```

**Import Pattern:**
```python
from adw.task_managers import TaskManagerProtocol, get_task_manager
from adw.models.task_manager import TaskInfo, TaskStatus
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| pydantic | 2.12+ | Model definitions, validation |
| typing | stdlib | Protocol, runtime_checkable |

**No external dependencies required for this story** - provider SDKs (linear-sdk, etc.) are added in subsequent stories.

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/__init__.py`
- `src/adw/task_managers/protocol.py`
- `src/adw/task_managers/null.py`
- `src/adw/task_managers/factory.py`
- `src/adw/models/task_manager.py`
- `tests/unit/task_managers/test_protocol.py`
- `tests/unit/task_managers/test_null.py`
- `tests/unit/task_managers/test_factory.py`
- `tests/unit/models/test_task_manager.py`

**Modified Files:**
- `src/adw/models/__init__.py` - Export new models
- `src/adw/models/config.py` - Add task_manager fields to ProjectConfig

### Testing Requirements

```python
# tests/unit/task_managers/test_protocol.py
def test_protocol_method_signatures():
    """Verify TaskManagerProtocol defines required methods."""

def test_null_task_manager_returns_none():
    """NullTaskManager.fetch_task() returns None."""

def test_factory_returns_null_by_default():
    """get_task_manager with no config returns NullTaskManager."""

def test_factory_raises_config_error_for_invalid():
    """get_task_manager raises ConfigError for unknown provider."""
```

**Coverage Target:** 100% for protocol and null manager (simple code paths)

---

## Previous Story Intelligence

This is the first story in Epic 12. No previous story learnings apply.

**Relevant patterns from Epic 6 (Run Management):**
- Protocol pattern used successfully for `LLMExecutorProtocol`
- Factory pattern in `get_executor()` provides good reference
- Configuration validation patterns in `ProjectConfig`

---

## Git Intelligence

**Recent commit patterns:**
- Use `feat(task_managers):` prefix for new module
- Keep commits atomic (one task per commit)
- Include tests in same commit as implementation

**Naming conventions observed:**
- Module directories: `snake_case`
- Protocol classes: `{Feature}Protocol`
- Factory functions: `get_{thing}()`

---

## Latest Technical Information

**Python Protocol Pattern (PEP 544):**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class TaskManagerProtocol(Protocol):
    def fetch_task(self, task_id: str) -> TaskInfo | None: ...
    def update_status(self, task_id: str, status: TaskStatus) -> None: ...
    def resolve_task_id(self, input: str) -> str | None: ...
```

**Optional Methods with hasattr:**
```python
# Check if provider supports comments
if hasattr(task_manager, 'add_comment'):
    task_manager.add_comment(task_id, comment)
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models MUST be in `src/adw/models/`
- Use custom exception hierarchy (ConfigError for invalid config)
- Full type annotations required
- Protocol-based design for extensibility (ref: LLMExecutorProtocol)
- Rich console for any CLI output during config loading

---

## Dev Notes

### Key Implementation Details

1. **Protocol vs ABC**: Use `Protocol` (structural subtyping) not `ABC` (nominal subtyping) for flexibility
2. **Optional Methods**: Use `@runtime_checkable` + `hasattr()` for optional capabilities like comments/labels
3. **Lazy Loading**: Import provider modules inside factory to avoid dependency errors
4. **State Mapping**: `TaskManagerConfig.state_mapping` maps ADW phases to provider-specific states

### Configuration Schema

```yaml
# project.yaml
task_manager: linear  # or: github_issues, jira, none (default)
task_manager_config:
  api_key_env: LINEAR_API_KEY
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
  auto_assign: true
  auto_close: true
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.1]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]
- [Source: src/adw/executors/protocol.py] - Reference for Protocol pattern
- [Source: src/adw/models/config.py] - Reference for config model pattern

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** None (Foundation story)
- **Blocks:** Story 12.2, Story 12.3, Story 12.4, Story 12.5, Story 12.6, Story 12.7, Story 12.8, Story 12.9, Story 12.10
- **Can Parallel With:** None

### Dependency Rationale
- All subsequent stories require the TaskManagerProtocol and base models defined here
