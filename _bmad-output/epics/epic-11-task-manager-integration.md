# Epic 11: Task Manager Integration

**Goal:** Enable runs to be initiated from external task management systems (Linear, Jira, GitHub Issues) with automatic task fetching and bidirectional status synchronization.

**Priority:** Post-MVP
**Dependencies:** Epic 6 (Run Management)

---

## Story 11.1: TaskManager Protocol and Configuration

As a developer,
I want a pluggable TaskManager abstraction,
So that different task management systems can be supported.

**Acceptance Criteria:**

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

---

## Story 11.2: Linear Task Manager Implementation

As a user,
I want to run `adw run RULE-123` to fetch my Linear task,
So that I don't have to copy-paste task descriptions.

**Acceptance Criteria:**

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

---

## Story 11.3: Status Synchronization at Phase Transitions

As a user,
I want Linear status updated automatically as my run progresses,
So that my team sees real-time progress.

**Acceptance Criteria:**

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

---

## Story 11.4: Task ID Pattern Detection

As a user,
I want adw to auto-detect when I provide a task ID vs a feature string,
So that I don't need special flags.

**Acceptance Criteria:**

**Given** input "RULE-123"
**When** Linear configured with team_key: RULE
**Then** recognized as Linear task ID

**Given** input "Add user authentication"
**When** any task manager configured
**Then** treated as literal feature string

**Given** input "PROJECT-456"
**When** Linear configured with team_key: RULE
**Then** not recognized, treated as feature string

**Given** ambiguous input
**When** could be task ID or feature
**Then** explicit flag `--task-id` available for override

**Given** `--no-task-manager` flag
**When** provided with any input
**Then** input treated as literal feature string, no task manager used

---

## Story 11.5: Task Context in Prompts

As a developer,
I want task metadata available in prompt templates,
So that I can customize prompts based on task properties.

**Acceptance Criteria:**

**Given** a Linear task with labels ["bug", "urgent"]
**When** prompt template uses `{{task.labels}}`
**Then** labels are included in rendered prompt

**Given** a Linear task with assignee
**When** prompt template uses `{{task.assignee}}`
**Then** assignee name is available

**Given** a Linear task with priority
**When** prompt template uses `{{task.priority}}`
**Then** priority value is available (1-4 or label)

**Given** no task manager used
**When** prompt references `{{task.*}}`
**Then** variables resolve to empty string (graceful degradation)

**Given** task has custom fields
**When** fetched
**Then** custom fields available via `{{task.custom.<field_name>}}`

---

## Dependency Analysis

| Story | Depends On | Blocks |
|-------|------------|--------|
| 11.1 | Epic 6 complete | 11.2, 11.3, 11.4, 11.5 |
| 11.2 | 11.1 | 11.3, 11.5 |
| 11.3 | 11.1, 11.2 | None |
| 11.4 | 11.1 | None |
| 11.5 | 11.2 | None |

### Execution Waves

```
Wave 1: [11.1] TaskManager Protocol + Config
           │
           ▼
Wave 2: [11.2] Linear Implementation
           │
     ┌─────┴─────┬──────────┐
     ▼           ▼          ▼
Wave 3: [11.3]  [11.4]   [11.5]
        Status   Pattern   Context
        Sync     Detect    in Prompts
```

### Parallelization Flowchart

```
                    ┌─────────────────────────────────────┐
                    │              [11.1]                 │
                    │    TaskManager Protocol and        │
                    │         Configuration              │
                    │     (Foundation - Abstraction)     │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │              [11.2]                 │
                    │    Linear Task Manager             │
                    │       Implementation               │
                    │   (First concrete adapter)         │
                    └─────────────────┬───────────────────┘
                                      │
                         ┌────────────┼────────────┐
                         │            │            │
                         ▼            ▼            ▼
        ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
        │       [11.3]       │ │       [11.4]       │ │       [11.5]       │
        │  Status Sync at    │ │   Task ID Pattern  │ │  Task Context in   │
        │ Phase Transitions  │ │     Detection      │ │      Prompts       │
        └────────────────────┘ └────────────────────┘ └────────────────────┘
```

### Critical Path

**Minimum Sequential Path:** 11.1 → 11.2 → (11.3 | 11.4 | 11.5)

**Parallelizable:** Stories 11.3, 11.4, and 11.5 can be developed in parallel after 11.2

### Estimated Story Points

| Story | Complexity | Notes |
|-------|------------|-------|
| 11.1 | Small | Protocol definition, config loading |
| 11.2 | Medium | Linear API integration, error handling |
| 11.3 | Medium | Orchestrator hooks, state mapping |
| 11.4 | Small | Regex pattern matching |
| 11.5 | Small | Template variable extension |

---

## Future Stories (Other Task Managers)

- 11.6: Jira Task Manager Implementation
- 11.7: GitHub Issues Task Manager Implementation
- 11.8: Custom Task Manager via Webhook/HTTP

---

## Technical Notes

### Linear API Integration

```python
# Linear GraphQL query for task fetch
FETCH_ISSUE_QUERY = """
query($id: String!) {
  issue(id: $id) {
    id
    identifier
    title
    description
    state { name }
    priority
    labels { nodes { name } }
    assignee { name email }
    project { name }
    parent { identifier title }
  }
}
"""
```

### Configuration Schema

```yaml
# Full task_manager_config schema
task_manager_config:
  api_key_env: LINEAR_API_KEY      # Env var for API key
  team_key: RULE                    # Team prefix for ID detection
  state_mapping:                    # ADW state → Linear state
    pending: "Todo"
    running: "In Progress"
    completed: "Done"
    failed: "In Progress"
  sync_comments: true               # Add comments on phase transitions
  include_labels: true              # Include labels in task context
  include_parent: true              # Include parent issue context
```

### Error Handling

| Error | ADW Exception | User Message |
|-------|---------------|--------------|
| API key missing | ConfigError | "LINEAR_API_KEY environment variable not set" |
| Task not found | TaskError | "Task not found: RULE-123" |
| API rate limit | TaskError (recoverable) | "Linear API rate limited, retrying..." |
| Network error | TaskError (recoverable) | "Failed to connect to Linear, retrying..." |
| Invalid task ID | TaskError | "Invalid task ID format: xyz" |

---
