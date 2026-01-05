# Story 12.2: Linear Task Manager Implementation

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

---

## Story

As a user,
I want to run `adw run RULE-123` to fetch my Linear task,
So that I don't have to copy-paste task descriptions.

## Acceptance Criteria

**Given** `adw run RULE-123` with Linear configured
**When** executed
**Then** task title and description are fetched via Linear API
**And** used as the feature_request in RunContext

**Given** LINEAR_API_KEY not set
**When** Linear task manager is configured
**Then** ConfigError raised with suggestion to set env var

**Given** task ID doesn't exist in Linear
**When** fetch attempted
**Then** TaskError raised with "Task not found: RULE-123"

**Given** task has labels in Linear
**When** fetched
**Then** labels are available as context (e.g., for prompt templates)

**Given** task has parent issue or project
**When** fetched
**Then** parent context is available for richer prompts

## Tasks / Subtasks

- [ ] **Task 1**: Create `LinearTaskManager` class in `src/adw/task_managers/linear.py`
  - [ ] Implement `TaskManagerProtocol` interface
  - [ ] Initialize with LinearClient (from ~/.claude/skills/linear pattern)
  - [ ] Handle API key detection: project `.linear` file → config → env var

- [ ] **Task 2**: Implement `fetch_task(task_id: str) -> TaskInfo | None`
  - [ ] Use Linear GraphQL API to fetch issue by identifier
  - [ ] Map Linear issue fields to TaskInfo model
  - [ ] Include labels, assignee, priority, parent issue
  - [ ] Handle "not found" errors gracefully

- [ ] **Task 3**: Implement `resolve_task_id(input: str) -> str | None`
  - [ ] Check if input matches team_key pattern (e.g., "RULE-123")
  - [ ] Return issue identifier if pattern matches
  - [ ] Return None if input is not a Linear task ID

- [ ] **Task 4**: Implement `update_status(task_id: str, status: TaskStatus) -> None`
  - [ ] Map TaskStatus to Linear workflow state via state_mapping config
  - [ ] Use Linear GraphQL mutation to update issue state
  - [ ] Log warning if update fails (non-blocking)

- [ ] **Task 5**: Implement error handling
  - [ ] Raise TaskError for API failures with helpful messages
  - [ ] Raise ConfigError for missing/invalid configuration
  - [ ] Handle rate limiting with exponential backoff

- [ ] **Task 6**: Register LinearTaskManager in factory
  - [ ] Update `get_task_manager()` to return LinearTaskManager for `task_manager: linear`
  - [ ] Lazy-load to avoid import errors when `requests` not installed

- [ ] **Task 7**: Write unit tests with mocked Linear API
  - [ ] Test fetch_task returns TaskInfo with all fields
  - [ ] Test resolve_task_id pattern matching
  - [ ] Test update_status maps to correct Linear state
  - [ ] Test error handling for API failures

---

## Developer Context

### Technical Requirements

This story implements the first concrete TaskManager provider using Linear's GraphQL API. The implementation should leverage the existing Linear skill patterns from `~/.claude/skills/linear/`.

**Key Design Decisions:**
- Use `requests` library for HTTP (same as Linear skill scripts)
- GraphQL endpoint: `https://api.linear.app/graphql`
- Authorization header: `lin_api_YOUR_KEY`
- Support project-specific `.linear` config file for API key detection

### Architecture Compliance

**File Locations:**
```
src/adw/task_managers/
├── __init__.py
├── protocol.py     # From story 12.1
├── null.py         # From story 12.1
├── factory.py      # Updated in this story
└── linear.py       # NEW - LinearTaskManager implementation
```

**Import Pattern:**
```python
from adw.task_managers import get_task_manager
from adw.task_managers.linear import LinearTaskManager
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| requests | 2.31+ | HTTP client for GraphQL API |
| pydantic | 2.12+ | TaskInfo model from story 12.1 |

**New Dependency:**
```bash
uv add requests
```

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/linear.py`
- `tests/unit/task_managers/test_linear.py`

**Modified Files:**
- `src/adw/task_managers/factory.py` - Add linear provider
- `pyproject.toml` - Add requests dependency

### Testing Requirements

```python
# tests/unit/task_managers/test_linear.py
import pytest
from unittest.mock import Mock, patch

def test_fetch_task_returns_task_info(mock_linear_api):
    """LinearTaskManager.fetch_task() returns TaskInfo with all fields."""
    manager = LinearTaskManager(api_key="test_key", team_key="RULE")
    task = manager.fetch_task("RULE-123")

    assert task.identifier == "RULE-123"
    assert task.title == "Test task"
    assert task.labels == ["bug", "urgent"]

def test_fetch_task_not_found(mock_linear_api):
    """LinearTaskManager.fetch_task() returns None for non-existent task."""
    mock_linear_api.return_value = {"issue": None}
    manager = LinearTaskManager(api_key="test_key", team_key="RULE")

    task = manager.fetch_task("RULE-999")
    assert task is None

def test_resolve_task_id_matches_team_key():
    """resolve_task_id returns identifier when pattern matches team_key."""
    manager = LinearTaskManager(api_key="test_key", team_key="RULE")

    assert manager.resolve_task_id("RULE-123") == "RULE-123"
    assert manager.resolve_task_id("OTHER-123") is None
    assert manager.resolve_task_id("Add user auth") is None

def test_update_status_maps_to_linear_state(mock_linear_api):
    """update_status maps TaskStatus to Linear workflow state."""
    manager = LinearTaskManager(
        api_key="test_key",
        team_key="RULE",
        state_mapping={"running": "In Progress"}
    )

    manager.update_status("RULE-123", TaskStatus.running)

    # Verify mutation was called with correct state
    mock_linear_api.assert_called()
```

**Coverage Target:** 90% (some error paths may be hard to test)

---

## Previous Story Intelligence

**From Story 12.1:**
- TaskManagerProtocol defines interface: `fetch_task`, `update_status`, `resolve_task_id`
- TaskInfo model contains: id, identifier, title, description, status, priority, labels, assignee, parent, custom_fields
- TaskStatus enum: pending, running, completed, failed
- Factory pattern with lazy loading in `get_task_manager()`

---

## Git Intelligence

**Recent commit patterns:**
- Use `feat(task_managers):` prefix
- Include tests in same commit

**Existing Linear scripts reference:**
- `~/.claude/skills/linear/scripts/linear_client.py` - GraphQL client pattern
- `~/.claude/skills/linear/scripts/get_issue.py` - Issue fetching
- `~/.claude/skills/linear/scripts/update_issue.py` - Issue updating

---

## Latest Technical Information

### Linear GraphQL API Reference

**Endpoint:** `https://api.linear.app/graphql`

**Authentication:**
```python
headers = {
    'Authorization': 'lin_api_YOUR_KEY',
    'Content-Type': 'application/json'
}
```

**Fetch Issue Query:**
```graphql
query GetIssue($id: String!) {
  issue(id: $id) {
    id
    identifier
    title
    description
    priority
    state {
      id
      name
      type
    }
    assignee {
      id
      name
      email
    }
    labels {
      nodes {
        id
        name
      }
    }
    parent {
      id
      identifier
      title
    }
    project {
      id
      name
    }
  }
}
```

**Update Issue Mutation:**
```graphql
mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue {
      id
      identifier
      state {
        name
      }
    }
  }
}
```

**Priority Values:** 0=None, 1=Urgent, 2=High, 3=Medium, 4=Low

### API Key Detection Priority

1. Project `.linear` file (JSON with `api_key` field)
2. `task_manager_config.api_key_env` environment variable
3. `LINEAR_API_KEY` environment variable (fallback)

```python
def _detect_api_key(self) -> str:
    # 1. Check project .linear file
    linear_file = Path.cwd() / ".linear"
    if linear_file.exists():
        config = json.loads(linear_file.read_text())
        if "api_key" in config:
            return config["api_key"]

    # 2. Check configured env var
    if self.config.api_key_env:
        key = os.getenv(self.config.api_key_env)
        if key:
            return key

    # 3. Fallback to LINEAR_API_KEY
    key = os.getenv("LINEAR_API_KEY")
    if key:
        return key

    raise ConfigError(
        code="MISSING_API_KEY",
        message="No Linear API key found",
        suggestion="Set LINEAR_API_KEY or create .linear file"
    )
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models MUST be in `src/adw/models/`
- Use custom exception hierarchy (TaskError, ConfigError)
- Full type annotations required
- Protocol-based design for TaskManagerProtocol

---

## Dev Notes

### Key Implementation Details

1. **GraphQL Client Pattern**: Follow `~/.claude/skills/linear/scripts/linear_client.py` structure
2. **Error Handling**: Non-blocking updates - log warnings, don't crash runs
3. **State Mapping**: Config maps ADW status to Linear workflow state names
4. **Team Key**: Required to validate task ID format (e.g., "RULE-123")

### Configuration Schema

```yaml
task_manager: linear
task_manager_config:
  api_key_env: LINEAR_API_KEY     # Env var name (not the key itself!)
  team_key: RULE                  # Team prefix for ID pattern matching
  state_mapping:
    pending: "Todo"
    running: "In Progress"
    completed: "Done"
    failed: "In Progress"         # Failed tasks stay in progress for human review
```

### Implementation Reference

```python
# src/adw/task_managers/linear.py
class LinearTaskManager:
    """Linear task manager implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        team_key: str = "",
        state_mapping: dict[str, str] | None = None,
    ):
        self.api_key = api_key or self._detect_api_key()
        self.team_key = team_key
        self.state_mapping = state_mapping or {}
        self.endpoint = "https://api.linear.app/graphql"

    def fetch_task(self, task_id: str) -> TaskInfo | None:
        """Fetch task from Linear API."""
        query = FETCH_ISSUE_QUERY
        variables = {"id": task_id}

        result = self._query(query, variables)
        issue = result.get("issue")

        if not issue:
            return None

        return TaskInfo(
            id=issue["id"],
            identifier=issue["identifier"],
            title=issue["title"],
            description=issue.get("description", ""),
            status=self._map_state_to_status(issue.get("state", {}).get("type")),
            priority=issue.get("priority", 0),
            labels=[l["name"] for l in issue.get("labels", {}).get("nodes", [])],
            assignee=issue.get("assignee", {}).get("name"),
            parent=issue.get("parent", {}).get("identifier"),
        )
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.2]
- [Source: ~/.claude/skills/linear/SKILL.md]
- [Source: ~/.claude/skills/linear/scripts/linear_client.py]
- [Source: ~/.claude/skills/linear/references/graphql_reference.md]

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

- **Depends On:** Story 12.1
- **Blocks:** Story 12.3, Story 12.5, Story 12.6, Story 12.7, Story 12.8, Story 12.9
- **Can Parallel With:** Story 12.4, Story 12.10

### Dependency Rationale
- Story 12.1: Requires TaskManagerProtocol and TaskInfo model definitions
