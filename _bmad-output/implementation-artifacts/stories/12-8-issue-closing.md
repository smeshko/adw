# Story 12.8: Issue Closing

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

---

## Story

As a user,
I want ADW to close my task when the PR is merged,
So that completed work is automatically tracked.

## Acceptance Criteria

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

## Tasks / Subtasks

- [ ] **Task 1**: Add `close_task` method to TaskManagerProtocol
  - [ ] Define `close_task(task_id: str) -> None` signature
  - [ ] Mark as optional capability
  - [ ] Add no-op to NullTaskManager

- [ ] **Task 2**: Implement `close_task` in LinearTaskManager
  - [ ] Move issue to "Done" or configured completed state
  - [ ] Optionally archive the issue
  - [ ] Handle already-closed tasks gracefully

- [ ] **Task 3**: Integrate with Ship phase completion
  - [ ] Check if PR was merged (from Ship phase output)
  - [ ] If merged + auto_close: close task
  - [ ] If not merged: add `adw:pr-ready` label

- [ ] **Task 4**: Add PR detection logic
  - [ ] Parse Ship phase artifacts for PR URL and merge status
  - [ ] Use `gh pr view` or API to check merge status
  - [ ] Cache PR status to avoid repeated lookups

- [ ] **Task 5**: Provide manual close instructions on failure
  - [ ] Log warning with task ID and target state
  - [ ] Suggest CLI command: `adw task close RULE-123`
  - [ ] Include Linear web URL for manual action

- [ ] **Task 6**: Write unit tests
  - [ ] Test auto-close on merged PR
  - [ ] Test pr-ready label on unmerged PR
  - [ ] Test disabled auto_close
  - [ ] Test error handling

---

## Developer Context

### Technical Requirements

This story completes the task lifecycle by automatically closing tasks when work is done. Closing is triggered by PR merge detection in the Ship phase.

**Key Design Decisions:**
- PR merge detection: Check PR status before closing
- Label fallback: Add `adw:pr-ready` if PR not merged
- Non-blocking: Closing failures don't crash runs

### Architecture Compliance

**Modified Files:**
```
src/adw/task_managers/
├── protocol.py    # Add close_task method
├── linear.py      # Implement close_task
src/adw/core/
├── orchestrator.py # Add close logic at Ship completion
```

### Library & Framework Requirements

No new dependencies.

### File Structure Requirements

**Modified Files:**
- `src/adw/task_managers/protocol.py` - Add close_task
- `src/adw/task_managers/linear.py` - Implement close_task
- `src/adw/core/orchestrator.py` - Add close hook
- `src/adw/models/config.py` - Add auto_close config

**New Files:**
- `tests/unit/task_managers/test_issue_closing.py`

### Testing Requirements

```python
def test_auto_close_on_merged_pr(mock_task_manager, mock_pr_status):
    """Task closed when PR is merged and auto_close is true."""
    mock_pr_status.return_value = {"merged": True}

    orchestrator = Orchestrator(
        task_manager=mock_task_manager,
        config=TaskManagerConfig(auto_close=True)
    )
    orchestrator.on_ship_complete(pr_url="https://github.com/org/repo/pull/123")

    mock_task_manager.close_task.assert_called_once()

def test_pr_ready_label_on_unmerged(mock_task_manager, mock_pr_status):
    """adw:pr-ready label added when PR not merged."""
    mock_pr_status.return_value = {"merged": False}

    orchestrator = Orchestrator(
        task_manager=mock_task_manager,
        config=TaskManagerConfig(auto_close=True)
    )
    orchestrator.on_ship_complete(pr_url="https://github.com/org/repo/pull/123")

    mock_task_manager.update_labels.assert_called_with(
        ANY,
        add=["adw:pr-ready"],
        remove=[]
    )
    mock_task_manager.close_task.assert_not_called()

def test_no_close_when_disabled(mock_task_manager):
    """Task not closed when auto_close is false."""
    orchestrator = Orchestrator(
        task_manager=mock_task_manager,
        config=TaskManagerConfig(auto_close=False)
    )
    orchestrator.on_ship_complete(pr_url="...")

    mock_task_manager.close_task.assert_not_called()
```

---

## Previous Story Intelligence

**From Story 12.3:**
- Status sync happens at run lifecycle points
- Orchestrator has lifecycle hooks

**From Story 12.7:**
- Label management for `adw:pr-ready`

---

## Latest Technical Information

### Linear Issue Closing

In Linear, "closing" an issue means moving it to a completed state (type: `completed`).

```graphql
mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue {
      state { name, type }
    }
  }
}
```

Variables:
```json
{
  "id": "issue-uuid",
  "input": {
    "stateId": "done-state-uuid"
  }
}
```

### PR Merge Status Check

Using GitHub CLI:
```bash
gh pr view 123 --json merged,state
# {"merged": true, "state": "MERGED"}
```

Or via GitHub API:
```python
def check_pr_merged(pr_url: str) -> bool:
    # Parse PR number from URL
    # Use subprocess to call `gh pr view` or requests to GitHub API
    pass
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

---

## Dev Notes

### Configuration Example

```yaml
task_manager_config:
  auto_close: true  # Close task when PR merged
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.8]
- [Source: src/adw/phases/ship.py] - Ship phase output

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### File List

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.2
- **Blocks:** None
- **Can Parallel With:** Story 12.3, Story 12.5, Story 12.6, Story 12.7, Story 12.9

### Dependency Rationale
- Story 12.1: Requires TaskManagerProtocol with close_task method
- Story 12.2: Requires LinearTaskManager implementation

