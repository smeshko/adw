# Template Variables Reference

This document describes the template variables available in ADW prompt templates.

## Task Variables (Story 12.5)

When a run is initiated from a task ID (e.g., `adw run RULE-123`), task information is fetched from the configured task manager and made available in templates via `{{task.*}}` variables.

### Available Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{task.id}}` | Internal task ID from the task manager | `abc123-uuid` |
| `{{task.identifier}}` | Human-readable task identifier | `RULE-123` |
| `{{task.title}}` | Task title/summary | `Fix login bug` |
| `{{task.description}}` | Full task description | `Users cannot log in...` |
| `{{task.status}}` | Current status in task manager | `In Progress` |
| `{{task.priority}}` | Priority number (1-4) | `2` |
| `{{task.priority_label}}` | Priority label | `High` |
| `{{task.labels}}` | Comma-separated labels | `bug, urgent` |
| `{{task.assignee}}` | Assigned user | `john.doe` |
| `{{task.parent_id}}` | Parent issue ID (if exists) | `RULE-100` |
| `{{task.parent_title}}` | Parent issue title | `Epic: Authentication` |

### Priority Labels

| Priority | Label |
|----------|-------|
| 1 | Urgent |
| 2 | High |
| 3 | Medium |
| 4 | Low |

### Custom Fields

Access custom fields from the task manager using dot notation:

```
{{task.custom.my_field}}
{{task.custom.nested.deep.value}}
```

### Graceful Degradation

When no task manager is configured or the run is started with a feature description instead of a task ID, all `{{task.*}}` variables resolve to empty strings. This allows templates to reference task variables without errors when task context is unavailable.

**Example:**
```markdown
# Implementation Plan

Task: {{task.identifier}} - {{task.title}}
Priority: {{task.priority_label}}

## Description
{{task.description}}
```

When run with `adw run RULE-123`:
```markdown
# Implementation Plan

Task: RULE-123 - Fix login bug
Priority: High

## Description
Users cannot log in when using special characters in password.
```

When run with `adw run "Add user authentication"`:
```markdown
# Implementation Plan

Task:  -
Priority:

## Description

```
