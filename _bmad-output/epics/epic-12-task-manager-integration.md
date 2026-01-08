# Epic 12: Task Manager Integration

**Goal:** Enable runs to be initiated from external task management systems (Linear, Jira, GitHub Issues) with automatic task fetching and bidirectional status synchronization.

**Priority:** Post-MVP
**Dependencies:** Epic 6 (Run Management)

---

## Story 12.1: TaskManager Protocol and Configuration

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

## Story 12.2: Linear Task Manager Implementation

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

## Story 12.3: Status Synchronization at Phase Transitions

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

## Story 12.4: Task ID Pattern Detection

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

## Story 12.5: Task Context in Prompts

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

## Story 12.6: Post Status Update Comments (Course Correction 2026-01-03)

As a user,
I want ADW to post comments to my task when significant events occur,
So that my team can follow progress without checking CLI output.

**Acceptance Criteria:**

**Given** a phase completes successfully
**When** `sync_comments: true` in config
**Then** a comment is posted: "✓ [PHASE] completed - [summary]"

**Given** a phase fails
**When** `sync_comments: true` in config
**Then** a comment is posted: "❌ [PHASE] failed - [error summary]. Run ID: [id]"

**Given** a run completes with PR created
**When** `sync_comments: true` in config
**Then** a comment is posted with PR link and artifact summary

**Given** `sync_comments: false` or not specified
**When** phases transition
**Then** no comments are posted (status-only sync)

**Given** comment posting fails (API error)
**When** the failure occurs
**Then** warning is logged, run continues (non-blocking)

---

## Story 12.7: Label Management (Course Correction 2026-01-03)

As a user,
I want ADW to manage task labels based on run state,
So that my task board reflects current progress.

**Acceptance Criteria:**

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

---

## Story 12.8: Issue Closing (Course Correction 2026-01-03)

As a user,
I want ADW to close my task when the PR is merged,
So that completed work is automatically tracked.

**Acceptance Criteria:**

**Given** Ship phase completes with PR merged
**When** `auto_close: true` in config
**Then** the source task is moved to "Done" state and closed

**Given** Ship phase completes but PR not merged (manual approval pending)
**When** `auto_close: true` in config
**Then** task remains open with `adw:pr-ready` label

**Given** task closing fails
**When** API error occurs
**Then** warning logged with manual close instructions

**Given** `auto_close: false` or not specified
**When** run completes
**Then** task status updated but not closed

---

## Story 12.9: Issue Assignment (Course Correction 2026-01-03)

As a user,
I want ADW to assign the task to me when a run starts,
So that ownership is clear during automated work.

**Acceptance Criteria:**

**Given** a run starts from a task
**When** `auto_assign: true` in config
**Then** task is assigned to the configured user (from API key owner or explicit config)

**Given** task is already assigned
**When** run starts
**Then** assignment is not changed

**Given** `auto_assign: false` or not specified
**When** run starts
**Then** no assignment change occurs

---

## Story 12.10: GitHub Issues Provider (Course Correction 2026-01-03)

As a user,
I want to run `adw run #123` to fetch my GitHub issue,
So that I can use ADW with GitHub Issues as my task manager.

**Acceptance Criteria:**

**Given** `task_manager: github_issues` in config
**When** `adw run #123` is executed
**Then** issue title and body are fetched via `gh` CLI

**Given** GitHub issue with labels
**When** fetched
**Then** labels are available as `{{task.labels}}` in prompts

**Given** `GITHUB_TOKEN` not set and `gh` not authenticated
**When** GitHub task manager is configured
**Then** ConfigError raised with authentication instructions

**Given** issue doesn't exist
**When** fetch attempted
**Then** TaskError raised: "Issue #123 not found"

**Given** status sync
**When** phase transitions
**Then** issue labels are updated (using Story 12.7 patterns)

---

## Updated Configuration Schema (Course Correction 2026-01-03)

```yaml
# Full task_manager_config schema (updated)
task_manager: linear  # or: github_issues, jira, none
task_manager_config:
  api_key_env: LINEAR_API_KEY
  team_key: RULE

  # Status mapping
  state_mapping:
    pending: "Todo"
    running: "In Progress"
    completed: "Done"
    failed: "In Progress"

  # Comment sync
  sync_comments: true           # Post comments on phase transitions
  comment_on_failure_only: false # Only comment when things fail

  # Label management
  labels:
    enabled: true
    prefix: "adw:"              # Label prefix

  # Issue lifecycle
  auto_assign: true             # Assign task on run start
  auto_close: true              # Close task when PR merged

  # Existing
  include_labels: true
  include_parent: true
```

---

## Dependency Analysis

| Story | Depends On | Blocks |
|-------|------------|--------|
| 12.1 | Epic 6 complete | 12.2, 12.3, 12.4, 12.5, 12.7, 12.8, 12.9, 12.10 |
| 12.2 | 12.1 | 12.3, 12.5, 12.6, 12.7, 12.8, 12.9 |
| 12.3 | 12.1, 12.2 | 12.6 |
| 12.4 | 12.1 | None |
| 12.5 | 12.1, 12.2 | None |
| 12.6 | 12.3 | None |
| 12.7 | 12.1, 12.2 | None |
| 12.8 | 12.1, 12.2 | None |
| 12.9 | 12.1, 12.2 | None |
| 12.10 | 12.1 | 12.3, 12.5, 12.7, 12.8, 12.9 |

### Estimated Story Points

| Story | Complexity | Notes |
|-------|------------|-------|
| 12.1 | Small | Protocol definition, config loading |
| 12.2 | Medium | Linear API integration, error handling |
| 12.3 | Medium | Orchestrator hooks, state mapping |
| 12.4 | Small | Regex pattern matching |
| 12.5 | Small | Template variable extension |
| 12.6 | Small | Extends 12.3 with comment posting |
| 12.7 | Medium | Label lifecycle management |
| 12.8 | Small | Issue closing logic |
| 12.9 | Small | Assignment logic |
| 12.10 | Medium | GitHub API integration via gh CLI |

---

## Epic 12: Dependency Flowchart (Updated 2026-01-05)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [12.1] TaskManager Protocol and Configuration                                ║
║         Foundation: Protocol, Models, NullManager, Factory                    ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 12.1 (PARALLEL x3)                                             ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [12.2] Linear Task Manager  ║  [12.4] Task ID Pattern  ║  [12.10] GitHub    ║
║         Implementation       ║         Detection        ║          Issues    ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                    │                       │                      │
                    ▼                       │                      │
╔═══════════════════════════════════════════╗                      │
║  WAVE 3: After 12.2 (PARALLEL x6)         ║◄─────────────────────┘
╠═══════════════════════════════════════════╣
║                                           ║
║  [12.3] Status Sync    [12.5] Task Context║
║  [12.7] Label Mgmt     [12.8] Issue Close ║
║  [12.9] Issue Assign                      ║
║                                           ║
╚═══════════════════════════════════════════╝
                    │
                    ▼
╔═══════════════════════════════════════════╗
║  WAVE 4: After 12.3                       ║
╠═══════════════════════════════════════════╣
║                                           ║
║  [12.6] Post Status Update Comments       ║
║         (Extends status sync with comment ║
║          posting at phase transitions)    ║
║                                           ║
╚═══════════════════════════════════════════╝
```

### Execution Summary

| Wave | Stories | Description | Parallelizable |
|------|---------|-------------|----------------|
| 1 | 12.1 | Protocol + Models | No (foundation) |
| 2 | 12.2, 12.4, 12.10 | Providers + Pattern Detection | Yes (3 parallel) |
| 3 | 12.3, 12.5, 12.7, 12.8, 12.9 | Features | Yes (5 parallel) |
| 4 | 12.6 | Comments | No (depends on 12.3) |

**Critical Path:** 12.1 → 12.2 → 12.3 → 12.6

**Maximum Parallelization:** Up to 5 stories can be worked simultaneously in Wave 3

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

### Error Handling

| Error | ADW Exception | User Message |
|-------|---------------|--------------|
| API key missing | ConfigError | "LINEAR_API_KEY environment variable not set" |
| Task not found | TaskError | "Task not found: RULE-123" |
| API rate limit | TaskError (recoverable) | "Linear API rate limited, retrying..." |
| Network error | TaskError (recoverable) | "Failed to connect to Linear, retrying..." |
| Invalid task ID | TaskError | "Invalid task ID format: xyz" |

---
