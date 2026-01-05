# Story 12.5: Task Context in Prompts

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

---

## Story

As a developer,
I want task metadata available in prompt templates,
So that I can customize prompts based on task properties.

## Acceptance Criteria

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

## Tasks / Subtasks

- [ ] **Task 1**: Add task context to template variables
  - [ ] Add `task` object to template context when task_id present
  - [ ] Include all TaskInfo fields as nested variables
  - [ ] Support dot notation: `{{task.labels}}`, `{{task.assignee}}`

- [ ] **Task 2**: Implement graceful degradation
  - [ ] Return empty string for missing task variables
  - [ ] Don't raise errors when no task manager configured
  - [ ] Log debug message when task variable requested but unavailable

- [ ] **Task 3**: Add priority label mapping
  - [ ] Map Linear priority (0-4) to human-readable labels
  - [ ] `{{task.priority}}` returns number
  - [ ] `{{task.priority_label}}` returns "Urgent", "High", "Medium", "Low", "None"

- [ ] **Task 4**: Add labels formatting helpers
  - [ ] `{{task.labels}}` returns comma-separated string
  - [ ] `{{task.labels_list}}` returns JSON array
  - [ ] `{{task.has_label.bug}}` returns boolean

- [ ] **Task 5**: Document template variables in help
  - [ ] Add `adw template-vars` command to list available variables
  - [ ] Include task.* section when task manager configured
  - [ ] Show example values

- [ ] **Task 6**: Write unit tests
  - [ ] Test variable substitution with task context
  - [ ] Test graceful degradation
  - [ ] Test priority and label formatting

---

## Developer Context

### Technical Requirements

This story extends the template engine to include task metadata from external task managers. Templates can reference task properties to customize prompts based on task type, priority, labels, etc.

**Key Design Decisions:**
- Graceful degradation: missing variables return empty string
- Dot notation: `{{task.field}}` for nested access
- Helper functions: `_list`, `_label` suffixes for formatting

### Architecture Compliance

**Modified Files:**
```
src/adw/commands/
├── template_engine.py   # Add task context support
```

### Library & Framework Requirements

No new dependencies.

### File Structure Requirements

**Modified Files:**
- `src/adw/commands/template_engine.py` - Add task context
- `src/adw/models/context.py` - Add task_info to RunContext (optional)

**New Files:**
- `tests/unit/commands/test_template_task_context.py`

### Testing Requirements

```python
# tests/unit/commands/test_template_task_context.py
def test_task_labels_substitution():
    """{{task.labels}} renders as comma-separated labels."""
    task = TaskInfo(labels=["bug", "urgent", "p1"])
    context = {"task": task}

    result = render_template("Labels: {{task.labels}}", context)
    assert result == "Labels: bug, urgent, p1"

def test_task_priority_label():
    """{{task.priority_label}} renders human-readable priority."""
    task = TaskInfo(priority=1)  # 1 = Urgent
    context = {"task": task}

    result = render_template("Priority: {{task.priority_label}}", context)
    assert result == "Priority: Urgent"

def test_graceful_degradation_no_task():
    """Task variables resolve to empty when no task context."""
    context = {}  # No task

    result = render_template("Labels: {{task.labels}}", context)
    assert result == "Labels: "

def test_custom_fields():
    """{{task.custom.field_name}} accesses custom fields."""
    task = TaskInfo(custom_fields={"estimated_hours": "8"})
    context = {"task": task}

    result = render_template("Hours: {{task.custom.estimated_hours}}", context)
    assert result == "Hours: 8"
```

---

## Previous Story Intelligence

**From Story 12.1:**
- TaskInfo model contains: labels, assignee, priority, custom_fields

**From Story 12.2:**
- LinearTaskManager fetches all task metadata including labels and assignee

---

## Latest Technical Information

### Template Variable Structure

```python
# Template context when task is available
context = {
    "feature_request": "...",
    "project_name": "...",
    "task": {
        "id": "uuid",
        "identifier": "RULE-123",
        "title": "Fix login bug",
        "description": "Users cannot log in...",
        "status": "In Progress",
        "priority": 2,
        "priority_label": "High",
        "labels": "bug, urgent",
        "labels_list": ["bug", "urgent"],
        "assignee": "John Doe",
        "parent": "RULE-100",
        "custom": {
            "story_points": "5",
            "sprint": "Sprint 23"
        }
    }
}
```

### Priority Mapping

```python
PRIORITY_LABELS = {
    0: "None",
    1: "Urgent",
    2: "High",
    3: "Medium",
    4: "Low"
}
```

### Template Engine Extension

```python
def _resolve_task_variable(self, path: str, task: TaskInfo | None) -> str:
    """Resolve task.* variable path."""
    if not task:
        return ""

    parts = path.split(".")
    if len(parts) < 2:
        return ""

    field = parts[1]

    if field == "labels":
        return ", ".join(task.labels)
    elif field == "labels_list":
        return json.dumps(task.labels)
    elif field == "priority_label":
        return PRIORITY_LABELS.get(task.priority, "None")
    elif field == "custom" and len(parts) == 3:
        return task.custom_fields.get(parts[2], "")
    else:
        return getattr(task, field, "")
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Template engine uses simple regex substitution
- Graceful degradation for missing variables

---

## Dev Notes

### Example Usage in Prompts

```markdown
# Plan Phase Prompt

You are implementing: {{feature_request}}

## Task Context
- **Task ID:** {{task.identifier}}
- **Priority:** {{task.priority_label}}
- **Labels:** {{task.labels}}
- **Parent Issue:** {{task.parent}}

{% if task.has_label.bug %}
This is a bug fix. Focus on identifying the root cause first.
{% endif %}
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.5]
- [Source: src/adw/commands/template_engine.py]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### File List

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.2
- **Blocks:** None
- **Can Parallel With:** Story 12.3, Story 12.4

### Dependency Rationale
- Story 12.1: Requires TaskInfo model for template context
- Story 12.2: Requires fetched task data from Linear
