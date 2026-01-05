# Story 12.9: Issue Assignment

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

---

## Story

As a user,
I want ADW to assign the task to me when a run starts,
So that ownership is clear during automated work.

## Acceptance Criteria

**Given** a run starts from a task
**When** `auto_assign: true` in config
**Then** task is assigned to the configured user (from API key owner or explicit config)

**Given** task is already assigned
**When** run starts
**Then** assignment is not changed

**Given** `auto_assign: false` or not specified
**When** run starts
**Then** no assignment change occurs

## Tasks / Subtasks

- [ ] **Task 1**: Add `assign_task` method to TaskManagerProtocol
  - [ ] Define `assign_task(task_id: str, user_id: str | None = None) -> None`
  - [ ] If user_id is None, assign to API key owner
  - [ ] Mark as optional capability

- [ ] **Task 2**: Implement `assign_task` in LinearTaskManager
  - [ ] Query current viewer (API key owner) if no user_id provided
  - [ ] Check if task already assigned
  - [ ] Use Linear `issueUpdate` mutation to set assignee

- [ ] **Task 3**: Integrate with Orchestrator
  - [ ] Call assign on run start if `auto_assign: true`
  - [ ] Skip if task already has assignee
  - [ ] Non-blocking on failure

- [ ] **Task 4**: Support explicit user configuration
  - [ ] Add `assignee_id` to task_manager_config
  - [ ] Use explicit ID if configured, else API key owner
  - [ ] Support email-based lookup

- [ ] **Task 5**: Cache viewer info
  - [ ] Query viewer once on first use
  - [ ] Store user ID and email
  - [ ] Reuse for subsequent operations

- [ ] **Task 6**: Write unit tests
  - [ ] Test auto-assign to API key owner
  - [ ] Test skip when already assigned
  - [ ] Test explicit assignee config
  - [ ] Test disabled auto_assign

---

## Developer Context

### Technical Requirements

This story ensures task ownership is clear when ADW starts working. Auto-assignment prevents orphaned tasks and clarifies who is responsible.

**Key Design Decisions:**
- Default to API key owner: Most common use case
- Skip if assigned: Don't override existing assignments
- Non-blocking: Assignment failures don't crash runs

### Architecture Compliance

**Modified Files:**
```
src/adw/task_managers/
├── protocol.py    # Add assign_task method
├── linear.py      # Implement assign_task
src/adw/core/
├── orchestrator.py # Add assignment hook
```

### Library & Framework Requirements

No new dependencies.

### File Structure Requirements

**Modified Files:**
- `src/adw/task_managers/protocol.py` - Add assign_task
- `src/adw/task_managers/linear.py` - Implement assign_task
- `src/adw/core/orchestrator.py` - Add assignment hook
- `src/adw/models/config.py` - Add auto_assign, assignee_id config

**New Files:**
- `tests/unit/task_managers/test_issue_assignment.py`

### Testing Requirements

```python
def test_auto_assign_to_viewer(mock_task_manager, mock_viewer):
    """Task assigned to API key owner when auto_assign is true."""
    mock_viewer.return_value = {"id": "user-123", "name": "John"}

    orchestrator = Orchestrator(
        task_manager=mock_task_manager,
        config=TaskManagerConfig(auto_assign=True)
    )
    orchestrator.on_run_start(task_id="RULE-123")

    mock_task_manager.assign_task.assert_called_with("RULE-123", "user-123")

def test_skip_when_already_assigned(mock_task_manager):
    """Assignment skipped when task already has assignee."""
    mock_task_manager.fetch_task.return_value = TaskInfo(
        assignee="existing-user"
    )

    orchestrator = Orchestrator(
        task_manager=mock_task_manager,
        config=TaskManagerConfig(auto_assign=True)
    )
    orchestrator.on_run_start(task_id="RULE-123")

    mock_task_manager.assign_task.assert_not_called()

def test_no_assign_when_disabled(mock_task_manager):
    """No assignment when auto_assign is false."""
    orchestrator = Orchestrator(
        task_manager=mock_task_manager,
        config=TaskManagerConfig(auto_assign=False)
    )
    orchestrator.on_run_start(task_id="RULE-123")

    mock_task_manager.assign_task.assert_not_called()
```

---

## Previous Story Intelligence

**From Story 12.2:**
- LinearTaskManager already fetches assignee info
- TaskInfo has assignee field

**From Story 12.3:**
- Orchestrator has run start hooks

---

## Latest Technical Information

### Linear Viewer Query

```graphql
query {
  viewer {
    id
    name
    email
  }
}
```

### Linear Assignment Update

```graphql
mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue {
      assignee { id, name }
    }
  }
}
```

Variables:
```json
{
  "id": "issue-uuid",
  "input": {
    "assigneeId": "user-uuid"
  }
}
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

---

## Dev Notes

### Configuration Example

```yaml
task_manager_config:
  auto_assign: true          # Assign task on run start
  assignee_id: "user-uuid"   # Optional explicit assignee (else API key owner)
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.9]
- [Source: ~/.claude/skills/linear/references/graphql_reference.md]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### File List

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.2
- **Blocks:** None
- **Can Parallel With:** Story 12.3, Story 12.5, Story 12.6, Story 12.7, Story 12.8

### Dependency Rationale
- Story 12.1: Requires TaskManagerProtocol with assign_task method
- Story 12.2: Requires LinearTaskManager to query viewer and update assignee

