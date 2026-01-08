# Story 12.8: Issue Closing

Status: ready-for-dev
Linear Issue: not-configured
Epic: 12 - Task Manager Integration
Created: 2026-01-08

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

### Task 1: Extend TaskManager Protocol
- [ ] Add `close_task(task_id: str) -> None` to Protocol
- [ ] Add `is_pr_merged(pr_url: str) -> bool` to Protocol (optional, can return False)
- [ ] Implement in `NullTaskManager` (no-op)
- [ ] Implement in `LinearTaskManager`

### Task 2: Implement Linear Task Closing
- [ ] Find "Done" or "Completed" state ID in team workflow
- [ ] Update issue to Done state
- [ ] Set `completedAt` timestamp
- [ ] Handle custom done states via state_mapping

### Task 3: Implement PR Merge Detection
- [ ] Parse PR URL to extract owner/repo/number
- [ ] Query GitHub API for PR merged status
- [ ] Handle missing GitHub token gracefully (assume not merged)
- [ ] Cache PR status during run to avoid repeated calls

### Task 4: Create IssueCloser Service
- [ ] Create `src/adw/task_managers/closer.py` with `IssueCloser`
- [ ] Initialize with `TaskManager`, `LabelManager`, and config
- [ ] Implement `maybe_close(task_id, pr_url) -> bool`
- [ ] Check `auto_close` config before closing
- [ ] Add `adw:pr-ready` label if PR not merged

### Task 5: Integrate with Orchestrator
- [ ] Call `maybe_close` after successful run completion
- [ ] Pass PR URL from Ship phase artifacts
- [ ] Handle missing PR URL gracefully

### Task 6: Handle Non-Blocking Failures
- [ ] Wrap closing operations in try/except
- [ ] Log warnings on failure with manual instructions
- [ ] Continue execution regardless
- [ ] Provide command for manual close: `adw task close <task_id>`

### Task 7: Write Tests
- [ ] Unit tests for `IssueCloser` (5 tests)
- [ ] Unit tests for `LinearTaskManager.close_task` (3 tests)
- [ ] Unit tests for PR merge detection (4 tests)
- [ ] Unit tests for config checking (3 tests)
- [ ] Integration test for full closing flow (2 tests)

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.2
- **Blocks:** None
- **Can Parallel With:** Story 12.3, 12.5, 12.7

### Dependency Rationale
- Requires TaskManager protocol (12.1) and Linear implementation (12.2)
- Uses LabelManager from 12.7 for pr-ready label
- Independent of status sync and comments

---

## Developer Context

### Technical Requirements

1. **Close Criteria**
   - Run completed successfully
   - auto_close config is true
   - PR is merged (if PR URL available)
   - OR user explicitly requests close

2. **PR Merge Detection**
   - Parse GitHub PR URL
   - Query GitHub API for merged status
   - Graceful degradation if no GitHub token

3. **Non-Blocking**
   - Closing failures don't affect run status
   - Log warnings with manual instructions
   - Provide manual close command

### Architecture Compliance

**File Location:** `src/adw/task_managers/`

**New Files:**
```
src/adw/task_managers/
└── closer.py         # IssueCloser
```

**Implementation Pattern:**
```python
# src/adw/task_managers/closer.py
import logging
import os
import re
from adw.task_managers.base import TaskManager
from adw.task_managers.labels import LabelManager
from adw.models.config import TaskManagerConfig

logger = logging.getLogger(__name__)

class IssueCloser:
    """Manages issue closing based on PR merge status."""

    def __init__(
        self,
        task_manager: TaskManager,
        label_manager: LabelManager,
        config: TaskManagerConfig,
    ) -> None:
        self._task_manager = task_manager
        self._label_manager = label_manager
        self._config = config

    def maybe_close(self, task_id: str, pr_url: str | None) -> bool:
        """
        Close task if conditions are met.

        Returns True if task was closed, False otherwise.
        """
        if not self._config.auto_close:
            logger.debug("Auto-close disabled", task_id=task_id)
            return False

        if pr_url and not self._is_pr_merged(pr_url):
            logger.info("PR not merged, adding pr-ready label", task_id=task_id, pr_url=pr_url)
            self._safe_add_pr_ready_label(task_id)
            return False

        return self._safe_close_task(task_id)

    def _is_pr_merged(self, pr_url: str) -> bool:
        """Check if PR is merged using GitHub API."""
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            logger.debug("No GITHUB_TOKEN, assuming PR not merged")
            return False

        # Parse PR URL: https://github.com/owner/repo/pull/123
        match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
        if not match:
            logger.warning("Could not parse PR URL", pr_url=pr_url)
            return False

        owner, repo, number = match.groups()
        # Call GitHub API to check merged status
        # ... implementation ...
        return False  # Default to not merged

    def _safe_close_task(self, task_id: str) -> bool:
        """Close task with error handling."""
        try:
            self._task_manager.close_task(task_id)
            logger.info("Task closed", task_id=task_id)
            return True
        except Exception as e:
            logger.warning(
                "Failed to close task",
                task_id=task_id,
                error=str(e),
                suggestion=f"Close manually with: adw task close {task_id}",
            )
            return False

    def _safe_add_pr_ready_label(self, task_id: str) -> None:
        """Add pr-ready label with error handling."""
        try:
            prefix = self._config.labels.prefix
            self._task_manager.add_label(task_id, f"{prefix}pr-ready")
        except Exception as e:
            logger.warning("Failed to add pr-ready label", task_id=task_id, error=str(e))


# In LinearTaskManager
def close_task(self, task_id: str) -> None:
    """Close a task by moving to Done state."""
    # Get done state ID
    done_state_id = self._get_done_state_id()

    # Update issue with done state and completedAt
    mutation = """
    mutation CloseIssue($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) {
        success
        issue { id state { name } completedAt }
      }
    }
    """
    self._client.execute(mutation, {
        "id": task_id,
        "input": {
            "stateId": done_state_id,
            "completedAt": datetime.now(UTC).isoformat(),
        }
    })
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| httpx | 0.28+ | GitHub API calls (existing) |
| re | stdlib | PR URL parsing |

**No New Dependencies** (uses existing httpx for GitHub API).

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/closer.py`

**Modified Files:**
- `src/adw/task_managers/base.py` - Add close_task to Protocol
- `src/adw/task_managers/null.py` - Implement no-op close_task
- `src/adw/task_managers/linear.py` - Implement close_task
- `src/adw/core/orchestrator.py` - Call IssueCloser on completion

**Test Files:**
- `tests/unit/task_managers/test_closer.py`
- `tests/unit/task_managers/test_linear_close.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/task_managers/test_closer.py
class TestIssueCloser:
    def test_maybe_close_when_enabled(self, mock_task_manager):
        """Closes task when auto_close=true and PR merged."""

    def test_maybe_close_disabled(self, mock_task_manager):
        """Does nothing when auto_close=false."""

    def test_maybe_close_pr_not_merged(self, mock_task_manager):
        """Adds pr-ready label when PR not merged."""

    def test_maybe_close_no_pr_url(self, mock_task_manager):
        """Closes task when no PR URL (direct completion)."""

    def test_maybe_close_failure_non_blocking(self, failing_task_manager):
        """Logs warning but doesn't raise on close failure."""

class TestPRMergeDetection:
    def test_is_pr_merged_without_token(self):
        """Returns False when no GITHUB_TOKEN."""

    def test_is_pr_merged_parses_url(self, mock_github_api):
        """Correctly parses GitHub PR URL."""

    def test_is_pr_merged_returns_true(self, mock_github_api):
        """Returns True when PR is merged."""

    def test_is_pr_merged_returns_false(self, mock_github_api):
        """Returns False when PR is not merged."""
```

---

## Previous Story Intelligence

**From Story 12.2:**
- LinearTaskManager state update
- API client patterns

**From Story 12.7:**
- LabelManager for adding labels
- Non-blocking pattern

**Patterns to Follow:**
- Wrap API calls in try/except
- Use structured logging with suggestions
- Check config before operations

---

## Git Intelligence

**Recent Relevant Commits:**
- Story 12.2: Linear state updates
- Story 12.7: Label management

**Established Patterns:**
- Service classes for domain logic
- Non-blocking external operations
- Config-driven behavior

---

## Latest Technical Information

**Linear Close Task (2025):**

```graphql
mutation CloseIssue($id: String!, $stateId: String!) {
  issueUpdate(id: $id, input: {
    stateId: $stateId,
    completedAt: "2025-01-08T00:00:00Z"
  }) {
    success
    issue { id state { name } completedAt }
  }
}
```

**GitHub PR Merge Check:**

```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/{owner}/{repo}/pulls/{number} \
  | jq '.merged'
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Non-blocking external calls**: Wrap in try/except, log and continue
- **Configuration-driven**: Check auto_close config
- **Actionable errors**: Include manual close instructions

---

## Dev Notes

### Implementation Approach

1. Add close_task to Protocol
2. Implement Linear close_task
3. Implement PR merge detection
4. Create IssueCloser service
5. Integrate with Orchestrator
6. Test non-blocking behavior

### Key Design Decisions

1. **Service Pattern**: IssueCloser encapsulates closing logic
2. **PR Check First**: Only close if PR merged (or no PR)
3. **pr-ready Label**: Visual indicator when waiting for merge
4. **Manual Fallback**: Provide command for manual close

### Close Flow

```
Run Complete
    │
    ├─> auto_close: false
    │     └─> Do nothing (status already updated)
    │
    └─> auto_close: true
          │
          ├─> No PR URL
          │     └─> Close task
          │
          └─> Has PR URL
                │
                ├─> PR merged: true
                │     └─> Close task
                │
                └─> PR merged: false
                      └─> Add adw:pr-ready label, keep open
```

### Manual Close Command

```bash
# Manually close a task
adw task close RULE-123

# Force close even if PR not merged
adw task close RULE-123 --force
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.8]
- [Source: _bmad-output/architecture.md#Task Manager Integration]
- [Linear API Docs: Issue updates]
- [GitHub API Docs: Pull requests]

---

## Dev Agent Record

### Context Reference

Epic 12: Task Manager Integration - Story 12.8

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
