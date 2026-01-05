# Story 12.6: Post Status Update Comments

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

---

## Story

As a user,
I want ADW to post comments to my task when significant events occur,
So that my team can follow progress without checking CLI output.

## Acceptance Criteria

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

## Tasks / Subtasks

- [ ] **Task 1**: Add `add_comment` method to TaskManagerProtocol
  - [ ] Define `add_comment(task_id: str, comment: str) -> None` signature
  - [ ] Mark as optional (not all providers may support)
  - [ ] Add to NullTaskManager as no-op

- [ ] **Task 2**: Implement `add_comment` in LinearTaskManager
  - [ ] Use Linear GraphQL `commentCreate` mutation
  - [ ] Include markdown formatting for rich display
  - [ ] Handle API errors gracefully

- [ ] **Task 3**: Create comment templates
  - [ ] Phase completion: "✓ **{phase}** completed\n- Duration: {duration}\n- Artifacts: {count}"
  - [ ] Phase failure: "❌ **{phase}** failed\n- Error: {message}\n- Run ID: {run_id}"
  - [ ] Run completion: "✅ **Run Complete**\n- PR: {pr_url}\n- Files changed: {count}"

- [ ] **Task 4**: Integrate with Orchestrator lifecycle
  - [ ] Add `_post_phase_comment()` method
  - [ ] Call after each phase if `sync_comments: true`
  - [ ] Add `_post_completion_comment()` for run completion

- [ ] **Task 5**: Add `comment_on_failure_only` config option
  - [ ] If true, only post comments when phases/runs fail
  - [ ] Reduces noise for successful runs
  - [ ] Default: false (post all comments)

- [ ] **Task 6**: Write unit tests
  - [ ] Test comment formatting
  - [ ] Test sync_comments config toggle
  - [ ] Test comment_on_failure_only behavior
  - [ ] Test non-blocking on API error

---

## Developer Context

### Technical Requirements

This story extends task manager integration to post progress comments to the source task. Comments provide visibility for team members without CLI access.

**Key Design Decisions:**
- Optional capability: Check `hasattr(task_manager, 'add_comment')`
- Non-blocking: Comment failures don't crash runs
- Configurable: `sync_comments` and `comment_on_failure_only` options

### Architecture Compliance

**Modified Files:**
```
src/adw/task_managers/
├── protocol.py    # Add add_comment method
├── null.py        # Add no-op add_comment
├── linear.py      # Implement add_comment
src/adw/core/
├── orchestrator.py # Add comment posting hooks
```

### Library & Framework Requirements

No new dependencies.

### File Structure Requirements

**Modified Files:**
- `src/adw/task_managers/protocol.py` - Add add_comment
- `src/adw/task_managers/linear.py` - Implement add_comment
- `src/adw/core/orchestrator.py` - Add comment hooks
- `src/adw/models/config.py` - Add sync_comments, comment_on_failure_only

**New Files:**
- `tests/unit/task_managers/test_comments.py`

### Testing Requirements

```python
def test_phase_completion_comment(mock_task_manager):
    """Comment posted when phase completes."""
    orchestrator = Orchestrator(
        task_manager=mock_task_manager,
        config=TaskManagerConfig(sync_comments=True)
    )
    orchestrator.on_phase_complete("plan", duration=120)

    mock_task_manager.add_comment.assert_called_once()
    comment = mock_task_manager.add_comment.call_args[0][1]
    assert "✓ **plan** completed" in comment

def test_no_comment_when_disabled(mock_task_manager):
    """No comment when sync_comments is false."""
    orchestrator = Orchestrator(
        task_manager=mock_task_manager,
        config=TaskManagerConfig(sync_comments=False)
    )
    orchestrator.on_phase_complete("plan", duration=120)

    mock_task_manager.add_comment.assert_not_called()

def test_comment_on_failure_only(mock_task_manager):
    """Only failure comments when comment_on_failure_only is true."""
    config = TaskManagerConfig(
        sync_comments=True,
        comment_on_failure_only=True
    )
    orchestrator = Orchestrator(task_manager=mock_task_manager, config=config)

    # Success - no comment
    orchestrator.on_phase_complete("plan", duration=120)
    mock_task_manager.add_comment.assert_not_called()

    # Failure - comment posted
    orchestrator.on_phase_fail("build", error="Syntax error")
    mock_task_manager.add_comment.assert_called_once()
```

---

## Previous Story Intelligence

**From Story 12.3:**
- Orchestrator has lifecycle hooks for phase transitions
- Non-blocking pattern established for task manager calls

---

## Latest Technical Information

### Linear Comment GraphQL

```graphql
mutation CommentCreate($input: CommentCreateInput!) {
  commentCreate(input: $input) {
    success
    comment {
      id
      body
      createdAt
    }
  }
}
```

Variables:
```json
{
  "input": {
    "issueId": "issue-uuid",
    "body": "✓ **plan** completed\n- Duration: 2m 30s"
  }
}
```

### Comment Templates

```python
COMMENT_TEMPLATES = {
    "phase_complete": """✓ **{phase}** completed

- Duration: {duration}
- Artifacts: {artifact_count}

Run ID: `{run_id}`""",

    "phase_failed": """❌ **{phase}** failed

- Error: {error_message}
- Run ID: `{run_id}`

Resume with: `adw resume {run_id}`""",

    "run_complete": """✅ **Run Complete**

- PR: [{pr_title}]({pr_url})
- Files changed: {files_changed}
- Commits: {commit_count}

Run ID: `{run_id}`"""
}
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Non-blocking external calls
- Markdown formatting for rich output

---

## Dev Notes

### Configuration Example

```yaml
task_manager_config:
  sync_comments: true            # Enable comment posting
  comment_on_failure_only: false # Post on success too
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.6]
- [Source: ~/.claude/skills/linear/references/graphql_reference.md]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### File List

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.2, Story 12.3
- **Blocks:** None
- **Can Parallel With:** Story 12.7, Story 12.8, Story 12.9

### Dependency Rationale
- Story 12.1: Requires TaskManagerProtocol with add_comment method
- Story 12.2: Requires LinearTaskManager to implement comment API
- Story 12.3: Builds on status sync lifecycle hooks

