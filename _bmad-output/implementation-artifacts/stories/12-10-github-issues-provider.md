# Story 12.10: GitHub Issues Provider

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

---

## Story

As a user,
I want to run `adw run #123` to fetch my GitHub issue,
So that I can use ADW with GitHub Issues as my task manager.

## Acceptance Criteria

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

## Tasks / Subtasks

- [ ] **Task 1**: Create `GitHubTaskManager` class in `src/adw/task_managers/github.py`
  - [ ] Implement `TaskManagerProtocol` interface
  - [ ] Use `gh` CLI for all GitHub operations
  - [ ] Support `GITHUB_TOKEN` or `gh auth login`

- [ ] **Task 2**: Implement `fetch_task(task_id: str) -> TaskInfo | None`
  - [ ] Parse issue number from input (e.g., "#123" or "123")
  - [ ] Use `gh issue view 123 --json title,body,labels,assignees,state`
  - [ ] Map GitHub fields to TaskInfo model

- [ ] **Task 3**: Implement `resolve_task_id(input: str) -> str | None`
  - [ ] Pattern: `#\d+` or just `\d+` (for GitHub issue numbers)
  - [ ] Return issue number if pattern matches
  - [ ] Return None for non-numeric input

- [ ] **Task 4**: Implement `update_status` via labels
  - [ ] GitHub Issues don't have workflow states like Linear
  - [ ] Use labels for status: `adw:running`, `adw:completed`, `adw:failed`
  - [ ] Add/remove labels via `gh issue edit`

- [ ] **Task 5**: Implement `add_comment` for progress tracking
  - [ ] Use `gh issue comment 123 --body "message"`
  - [ ] Support markdown formatting
  - [ ] Non-blocking on failure

- [ ] **Task 6**: Register GitHubTaskManager in factory
  - [ ] Update `get_task_manager()` for `task_manager: github_issues`
  - [ ] Check `gh` CLI availability on init
  - [ ] Provide helpful error if `gh` not installed

- [ ] **Task 7**: Write unit tests with mocked `gh` CLI
  - [ ] Test fetch_task parsing and mapping
  - [ ] Test resolve_task_id patterns
  - [ ] Test label-based status updates
  - [ ] Test authentication error handling

---

## Developer Context

### Technical Requirements

This story adds GitHub Issues as an alternative task manager. Implementation uses the `gh` CLI for all operations, avoiding direct API complexity.

**Key Design Decisions:**
- Use `gh` CLI: Simpler than direct API, handles auth
- Label-based status: GitHub Issues lack workflow states
- Pattern: `#123` or `123` for issue numbers

### Architecture Compliance

**File Locations:**
```
src/adw/task_managers/
├── github.py      # NEW - GitHubTaskManager implementation
```

### Library & Framework Requirements

| Dependency | Type | Purpose |
|------------|------|---------|
| `gh` CLI | External | GitHub operations |
| subprocess | stdlib | Execute gh commands |

**No Python dependencies** - uses `gh` CLI.

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/github.py`
- `tests/unit/task_managers/test_github.py`

**Modified Files:**
- `src/adw/task_managers/factory.py` - Add github_issues provider

### Testing Requirements

```python
# tests/unit/task_managers/test_github.py
from unittest.mock import patch

def test_fetch_task_parses_gh_output(mock_subprocess):
    """fetch_task parses gh issue view JSON output."""
    mock_subprocess.return_value = json.dumps({
        "title": "Fix login bug",
        "body": "Users cannot log in",
        "labels": [{"name": "bug"}, {"name": "urgent"}],
        "assignees": [{"login": "johndoe"}],
        "state": "OPEN"
    })

    manager = GitHubTaskManager()
    task = manager.fetch_task("123")

    assert task.title == "Fix login bug"
    assert task.description == "Users cannot log in"
    assert task.labels == ["bug", "urgent"]
    assert task.assignee == "johndoe"

def test_resolve_task_id_patterns():
    """resolve_task_id handles various input formats."""
    manager = GitHubTaskManager()

    assert manager.resolve_task_id("#123") == "123"
    assert manager.resolve_task_id("123") == "123"
    assert manager.resolve_task_id("Add feature") is None

def test_update_status_via_labels(mock_subprocess):
    """update_status adds/removes labels via gh CLI."""
    manager = GitHubTaskManager()
    manager.update_status("123", TaskStatus.running)

    mock_subprocess.assert_called_with(
        ["gh", "issue", "edit", "123", "--add-label", "adw:running"],
        capture_output=True
    )
```

---

## Previous Story Intelligence

**From Story 12.1:**
- TaskManagerProtocol defines the interface
- Factory pattern for provider selection

**From Story 12.7:**
- Label-based status tracking pattern
- ADW label prefix convention

---

## Latest Technical Information

### GitHub CLI Commands

```bash
# Fetch issue
gh issue view 123 --json title,body,labels,assignees,state,milestone

# Add label
gh issue edit 123 --add-label "adw:running"

# Remove label
gh issue edit 123 --remove-label "adw:running"

# Add comment
gh issue comment 123 --body "✓ **plan** completed"

# Close issue
gh issue close 123
```

### TaskInfo Mapping

| GitHub Field | TaskInfo Field |
|--------------|----------------|
| title | title |
| body | description |
| labels[].name | labels |
| assignees[0].login | assignee |
| state | status (OPEN→running, CLOSED→completed) |
| milestone.title | parent |

### Authentication Check

```python
def _check_gh_auth(self) -> None:
    """Verify gh CLI is authenticated."""
    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise ConfigError(
            code="GH_NOT_AUTHENTICATED",
            message="GitHub CLI is not authenticated",
            suggestion="Run 'gh auth login' or set GITHUB_TOKEN"
        )
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

---

## Dev Notes

### Configuration Example

```yaml
task_manager: github_issues
task_manager_config:
  # No additional config needed - uses gh CLI auth
  # Optional:
  repo: "owner/repo"  # If not in a git repo context
```

### GitHub Issues vs Linear

| Feature | Linear | GitHub Issues |
|---------|--------|---------------|
| Workflow states | Yes (via state_mapping) | No (label-based) |
| API auth | API key | gh CLI / GITHUB_TOKEN |
| Task ID pattern | TEAM-123 | #123 or 123 |
| Priority | 0-4 numeric | Labels |

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.10]
- [Source: https://cli.github.com/manual/gh_issue]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### File List

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.7
- **Blocks:** None
- **Can Parallel With:** Story 12.2

### Dependency Rationale
- Story 12.1: Requires TaskManagerProtocol interface definition
- Story 12.7: Uses label-based status patterns for GitHub Issues
