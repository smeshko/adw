# Story 12.2: Linear Task Manager Implementation

Status: ready-for-dev
Linear Issue: not-configured
Epic: 12 - Task Manager Integration
Created: 2026-01-08

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

**Given** LINEAR_API_KEY or LINEAR_TEAM_ID not set in .env
**When** Linear task manager is configured
**Then** ConfigError raised with instruction to add credentials to .env file

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

### Task 1: Create LinearTaskManager Class
- [x] Create `src/adw/task_managers/linear.py` with `LinearTaskManager`
- [x] Implement `TaskManager` Protocol
- [x] Initialize with `TaskManagerConfig` and environment variables
- [x] Validate required env vars on instantiation: `LINEAR_API_KEY` and `LINEAR_TEAM_ID`

### Task 2: Implement Linear API Client
- [ ] Create `src/adw/task_managers/linear_client.py` with `LinearClient`
- [ ] Use `httpx` or `requests` for GraphQL requests
- [ ] Implement `fetch_issue(identifier: str) -> dict`
- [ ] Implement `update_issue(id: str, input: dict) -> dict`
- [ ] Handle authentication via `LINEAR_API_KEY` header
- [ ] Base URL: `https://api.linear.app/graphql`

### Task 3: Implement fetch_task Method
- [ ] Build GraphQL query for issue fetch (see Technical Notes)
- [ ] Map Linear response to `TaskInfo` model:
  - `id` <- `issue.id`
  - `identifier` <- `issue.identifier`
  - `title` <- `issue.title`
  - `description` <- `issue.description`
  - `status` <- `issue.state.name`
  - `priority` <- `issue.priority`
  - `labels` <- `issue.labels.nodes[].name`
  - `assignee` <- `issue.assignee.name`
  - `parent_id` <- `issue.parent.identifier`
  - `parent_title` <- `issue.parent.title`
- [ ] Handle not found error (issue returns null)
- [ ] Handle API errors with proper error wrapping

### Task 4: Implement update_status Method
- [ ] Accept ADW status and map to Linear state using `state_mapping`
- [ ] Fetch workflow states for the team to get state ID
- [ ] Build mutation for status update: `issueUpdate(id: $id, input: {stateId: $stateId})`
- [ ] Cache team workflow states to avoid repeated lookups
- [ ] Handle state not found (log warning, don't fail run)

### Task 5: Implement resolve_task_id Method
- [ ] Use regex pattern based on `team_key` config
- [ ] Pattern: `^{team_key}-\d+$` (case insensitive)
- [ ] Return matched task ID or None
- [ ] Support common variations: "RULE-123", "rule-123", "RULE123"

### Task 6: Add Error Handling
- [ ] Handle network errors with retry logic (3 attempts, exponential backoff)
- [ ] Handle rate limiting (429) with appropriate wait
- [ ] Handle authentication errors (401) with clear message
- [ ] Handle API errors (400, 500) with context
- [ ] All errors wrapped as `TaskError` with appropriate code

### Task 7: Register in Factory
- [ ] Add `"linear"` -> `LinearTaskManager` to factory registry
- [ ] Ensure lazy import to avoid httpx dependency if not using Linear

### Task 8: Write Tests
- [ ] Unit tests for `LinearTaskManager.fetch_task` (5 tests)
- [ ] Unit tests for `LinearTaskManager.update_status` (4 tests)
- [ ] Unit tests for `LinearTaskManager.resolve_task_id` (4 tests)
- [ ] Unit tests for `LinearClient` (5 tests)
- [ ] Unit tests for error handling (4 tests)
- [ ] Integration test with mock server (2 tests)

---

## Dependencies

- **Depends On:** Story 12.1 (TaskManager Protocol)
- **Blocks:** 12.3, 12.5, 12.6, 12.7, 12.8
- **Can Parallel With:** Story 12.4

### Dependency Rationale
- Requires TaskManager Protocol from 12.1
- Status sync (12.3) needs update_status implementation
- All features using Linear API depend on this implementation

---

## Developer Context

### Technical Requirements

1. **Linear API Integration**
   - GraphQL API at `https://api.linear.app/graphql`
   - Authentication via `Authorization: Bearer {LINEAR_API_KEY}` header
   - Rate limits: 1500 requests per hour per user

2. **Environment Variables**
   - `LINEAR_API_KEY` - Required, API key from Linear settings
   - `LINEAR_TEAM_ID` - Required, team UUID

3. **State Mapping**
   - Linear uses workflow states (e.g., "Todo", "In Progress", "Done")
   - Each team can have custom workflow states
   - Must fetch team's workflow states and map by name

### Architecture Compliance

**File Location:** `src/adw/task_managers/`

**New Files:**
```
src/adw/task_managers/
├── linear.py          # LinearTaskManager implementation
└── linear_client.py   # Linear GraphQL client
```

**Implementation Pattern:**
```python
# src/adw/task_managers/linear.py
from typing import Any
from adw.task_managers.base import TaskManager
from adw.models.task import TaskInfo
from adw.models.config import TaskManagerConfig
from adw.exceptions import TaskError, ConfigError

class LinearTaskManager(TaskManager):
    def __init__(self, config: TaskManagerConfig) -> None:
        self._config = config
        self._client = LinearClient(api_key=self._get_api_key())
        self._state_cache: dict[str, str] = {}  # state_name -> state_id

    @property
    def name(self) -> str:
        return "linear"

    def fetch_task(self, task_id: str) -> TaskInfo:
        """Fetch task from Linear by identifier (e.g., RULE-123)."""
        ...

    def update_status(self, task_id: str, status: str, metadata: dict[str, Any]) -> None:
        """Update task status in Linear."""
        ...

    def resolve_task_id(self, input_str: str) -> str | None:
        """Check if input matches Linear task ID pattern."""
        ...
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| httpx | 0.28+ | HTTP client for GraphQL requests |
| re | stdlib | Pattern matching for task IDs |

**New Dependency:**
```bash
uv add httpx
```

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/linear.py`
- `src/adw/task_managers/linear_client.py`

**Modified Files:**
- `src/adw/task_managers/factory.py` - Register LinearTaskManager
- `pyproject.toml` - Add httpx dependency

**Test Files:**
- `tests/unit/task_managers/test_linear.py`
- `tests/unit/task_managers/test_linear_client.py`
- `tests/fixtures/linear/` - Mock responses

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/task_managers/test_linear.py
class TestLinearTaskManager:
    def test_fetch_task_success(self, mock_client):
        """Fetches task and maps to TaskInfo correctly."""

    def test_fetch_task_not_found(self, mock_client):
        """Raises TaskError when task doesn't exist."""

    def test_fetch_task_with_labels(self, mock_client):
        """Includes labels in TaskInfo."""

    def test_fetch_task_with_parent(self, mock_client):
        """Includes parent info in TaskInfo."""

    def test_fetch_task_api_error(self, mock_client):
        """Wraps API errors as TaskError."""

class TestLinearTaskManagerUpdateStatus:
    def test_update_status_success(self, mock_client):
        """Updates status in Linear."""

    def test_update_status_state_mapping(self, mock_client):
        """Maps ADW status to Linear state."""

    def test_update_status_unknown_state(self, mock_client):
        """Logs warning for unknown state, doesn't fail."""

    def test_update_status_api_error(self, mock_client):
        """Logs error but doesn't fail run (non-blocking)."""

class TestLinearTaskManagerResolveTaskId:
    def test_resolve_valid_task_id(self):
        """Returns task ID for valid pattern."""

    def test_resolve_lowercase_task_id(self):
        """Handles lowercase team key."""

    def test_resolve_no_dash(self):
        """Handles RULE123 format."""

    def test_resolve_not_matching(self):
        """Returns None for non-matching input."""
```

**Mock Responses:**
```json
// tests/fixtures/linear/issue_response.json
{
  "data": {
    "issue": {
      "id": "abc123",
      "identifier": "RULE-123",
      "title": "Add user authentication",
      "description": "Implement OAuth2 login flow",
      "state": { "name": "Todo" },
      "priority": 2,
      "labels": { "nodes": [{ "name": "feature" }, { "name": "auth" }] },
      "assignee": { "name": "Alex Dev" },
      "parent": { "identifier": "RULE-100", "title": "Epic: Auth System" }
    }
  }
}
```

---

## Previous Story Intelligence

**From Story 12.1:**
- TaskManager Protocol defines fetch_task, update_status, resolve_task_id
- TaskInfo model with all required fields
- TaskManagerConfig with state_mapping and other options
- TaskError exception with proper codes

**Patterns to Follow:**
- Use config values from TaskManagerConfig
- Wrap all errors in TaskError
- Non-blocking status updates (log and continue on failure)

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 12.1: TaskManager Protocol and configuration
- Epic 8: HTTP client patterns for evidence gathering

**Established Patterns:**
- HTTP clients use httpx for async support
- Error handling wraps external errors in typed exceptions
- Configuration via environment variables for secrets

---

## Latest Technical Information

**Linear GraphQL API (2025):**

```graphql
# Fetch Issue Query
query FetchIssue($identifier: String!) {
  issue(id: $identifier) {
    id
    identifier
    title
    description
    state { id name }
    priority
    labels { nodes { name } }
    assignee { name email }
    project { name }
    parent { identifier title }
  }
}

# Update Issue Mutation
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue { id state { name } }
  }
}

# Get Team Workflow States
query TeamWorkflowStates($teamId: String!) {
  team(id: $teamId) {
    states { nodes { id name type } }
  }
}
```

**Authentication:**
- Header: `Authorization: Bearer lin_api_xxxxx`
- Create at: Linear Settings > API > Personal API Keys

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **HTTP Client**: Use httpx for HTTP requests
- **Exception hierarchy**: TaskError extends ADWError
- **Environment variables**: Use os.environ.get() with clear error messages
- **Type annotations required**: All functions fully typed

---

## Dev Notes

### Implementation Approach

1. Start with LinearClient (API wrapper)
2. Implement fetch_task with full field mapping
3. Implement update_status with state caching
4. Implement resolve_task_id with regex
5. Register in factory
6. Add comprehensive error handling
7. Write tests with mock responses

### Key Design Decisions

1. **Separate Client Class**: Keep API details separate from TaskManager logic
2. **State Caching**: Cache workflow states to reduce API calls
3. **Non-Blocking Updates**: Status updates should not fail the run
4. **Flexible Pattern Matching**: Handle variations in task ID format

### GraphQL Queries

```python
FETCH_ISSUE_QUERY = """
query FetchIssue($identifier: String!) {
  issue(id: $identifier) {
    id
    identifier
    title
    description
    state { id name }
    priority
    labels { nodes { name } }
    assignee { name email }
    project { name }
    parent { identifier title }
  }
}
"""

UPDATE_ISSUE_MUTATION = """
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue { id state { name } }
  }
}
"""
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.2]
- [Source: _bmad-output/architecture.md#Task Manager Integration]
- [Linear API Docs: https://developers.linear.app/docs/graphql/working-with-the-graphql-api]
- [Linear API implementation reference: ~/.claude/skills/linear]
- [Linear local API Docs: ~/.claude/docs/external/linear]

---

## Dev Agent Record

### Context Reference

Epic 12: Task Manager Integration - Story 12.2

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- **Task 1**: Created LinearTaskManager class in `src/adw/task_managers/linear.py`. Implements TaskManager Protocol with name property, validates LINEAR_API_KEY and LINEAR_TEAM_ID environment variables on initialization. Raises ConfigError with clear messages if env vars missing. Added 4 unit tests for init and env var validation.

### File List

**New Files:**
- `src/adw/task_managers/linear.py` - LinearTaskManager class implementation
- `tests/unit/task_managers/test_linear.py` - Unit tests for LinearTaskManager
