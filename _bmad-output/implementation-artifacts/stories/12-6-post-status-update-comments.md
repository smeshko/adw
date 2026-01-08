# Story 12.6: Post Status Update Comments

Status: ready-for-dev
Linear Issue: not-configured
Epic: 12 - Task Manager Integration
Created: 2026-01-08

---

## Story

As a user,
I want ADW to post comments to my task when significant events occur,
So that my team can follow progress without checking CLI output.

## Acceptance Criteria

**Given** a phase completes successfully
**When** `sync_comments: true` in config
**Then** a comment is posted: "[PHASE] completed - [summary]"

**Given** a phase fails
**When** `sync_comments: true` in config
**Then** a comment is posted: "[PHASE] failed - [error summary]. Run ID: [id]"

**Given** a run completes with PR created
**When** `sync_comments: true` in config
**Then** a comment is posted with PR link and artifact summary

**Given** `sync_comments: false` or not specified
**When** phases transition
**Then** no comments are posted (status-only sync)

**Given** comment posting fails (API error)
**When** the failure occurs
**Then** warning is logged, run continues (non-blocking)

### PR-Task Linking

**Given** a task manager is configured with a task ID
**When** a PR is created during the document phase
**Then** PR title follows format: `TASK-ID: description` (e.g., "RULE-123: Add user authentication")

**Given** a PR is created with task ID
**When** PR body is generated
**Then** PR body includes link to Linear task (e.g., "Linear: https://linear.app/team/issue/RULE-123")

**Given** a PR is created and `sync_comments: true`
**When** PR creation completes
**Then** Linear task receives comment with PR URL for bidirectional linking

## Tasks / Subtasks

### Task 1: Extend TaskManager Protocol
- [ ] Add `post_comment(task_id: str, body: str) -> None` to Protocol
- [ ] Implement in `NullTaskManager` (no-op)
- [ ] Implement in `LinearTaskManager` (GraphQL mutation)

### Task 2: Implement Linear Comment Posting
- [ ] Add `commentCreate` mutation to LinearClient
- [ ] Format comment with markdown
- [ ] Include run context (run_id, phase, duration)
- [ ] Handle API errors gracefully

### Task 3: Create CommentFormatter
- [ ] Create `src/adw/task_managers/comments.py` with `CommentFormatter`
- [ ] Implement `format_phase_complete(phase: str, duration: float, artifacts: int) -> str`
- [ ] Implement `format_phase_failed(phase: str, error: str, run_id: str) -> str`
- [ ] Implement `format_run_complete(run_id: str, pr_url: str | None, summary: str) -> str`

### Task 4: Extend StatusSyncService
- [ ] Add `post_phase_comment(context, phase, result)` method
- [ ] Add `post_completion_comment(context, pr_url)` method
- [ ] Check `sync_comments` config before posting
- [ ] Check `comment_on_failure_only` config
- [ ] Wrap in non-blocking try/except

### Task 5: Integrate with Orchestrator
- [ ] Call `post_phase_comment` after phase completes
- [ ] Call `post_completion_comment` after run completes
- [ ] Pass PR URL if available from Ship phase

### Task 6: Add Comment Templates
- [ ] Create configurable comment templates
- [ ] Support template variables for run context
- [ ] Default templates with good formatting

### Task 7: Implement PR-Task Linking
- [ ] Create `PRTitleFormatter` to generate PR titles with task ID
- [ ] Format: `TASK-ID: description` (e.g., "RULE-123: Add user authentication")
- [ ] Add task link to PR body when task_id is present
- [ ] Include Linear URL format: `https://linear.app/{team}/issue/{task_id}`
- [ ] Post PR URL as comment to Linear task after PR creation
- [ ] Make PR title format configurable (default: `{task_id}: {description}`)

### Task 8: Write Tests
- [ ] Unit tests for `CommentFormatter` (5 tests)
- [ ] Unit tests for `LinearTaskManager.post_comment` (3 tests)
- [ ] Unit tests for `StatusSyncService` comment methods (4 tests)
- [ ] Unit tests for config checking (3 tests)
- [ ] Unit tests for `PRTitleFormatter` (4 tests)
- [ ] Unit tests for PR body with task link (2 tests)
- [ ] Integration test for full comment flow (2 tests)
- [ ] Integration test for PR-task linking (2 tests)

---

## Dependencies

- **Depends On:** Story 12.3 (Status Synchronization)
- **Blocks:** None
- **Can Parallel With:** None

### Dependency Rationale
- Extends StatusSyncService from 12.3
- Uses same non-blocking patterns
- Depends on orchestrator integration from 12.3

---

## Developer Context

### Technical Requirements

1. **Comment Format**
   - Use markdown for formatting
   - Include structured information (run ID, phase, duration)
   - Keep comments concise but informative

2. **Configuration**
   - `sync_comments: true/false` controls all comments
   - `comment_on_failure_only: true` limits to failures only
   - Both defaults to false (opt-in)

3. **Non-Blocking**
   - Comment failures don't stop the run
   - Log warnings on failure
   - Continue execution regardless

4. **PR-Task Linking**
   - PR title format: `{task_id}: {description}` (e.g., "RULE-123: Add user authentication")
   - PR body includes Linear task URL for traceability
   - Linear task receives PR URL comment for bidirectional linking
   - Configurable via `pr_title_format` in task_manager_config

### Architecture Compliance

**File Location:** `src/adw/task_managers/`

**New Files:**
```
src/adw/task_managers/
└── comments.py       # CommentFormatter
```

**Implementation Pattern:**
```python
# src/adw/task_managers/comments.py
class CommentFormatter:
    """Formats comments for task manager updates."""

    def format_phase_complete(
        self,
        phase: str,
        duration_seconds: float,
        artifacts_count: int,
    ) -> str:
        """Format comment for successful phase completion."""
        return f"""**{phase.title()} Phase Completed**

Duration: {duration_seconds:.1f}s
Artifacts: {artifacts_count}
"""

    def format_phase_failed(
        self,
        phase: str,
        error: str,
        run_id: str,
    ) -> str:
        """Format comment for phase failure."""
        return f"""**{phase.title()} Phase Failed**

Error: {error}
Run ID: `{run_id}`

Check logs with: `adw logs show {run_id}`
"""

    def format_run_complete(
        self,
        run_id: str,
        pr_url: str | None,
        summary: str,
    ) -> str:
        """Format comment for run completion."""
        pr_section = f"\n**PR:** {pr_url}" if pr_url else ""
        return f"""**Run Completed** ✓

Run ID: `{run_id}`{pr_section}

{summary}
"""

# In LinearTaskManager
def post_comment(self, task_id: str, body: str) -> None:
    """Post a comment to a Linear issue."""
    mutation = """
    mutation CreateComment($issueId: String!, $body: String!) {
      commentCreate(input: {issueId: $issueId, body: $body}) {
        success
        comment { id }
      }
    }
    """
    self._client.execute(mutation, {"issueId": task_id, "body": body})


# src/adw/task_managers/pr_linking.py
class PRTitleFormatter:
    """Formats PR titles with task ID."""

    def __init__(self, config: TaskManagerConfig) -> None:
        self._config = config

    def format_title(self, task_id: str | None, description: str) -> str:
        """Format PR title with task ID prefix if available."""
        if not task_id:
            return description
        # Default format: "RULE-123: description"
        format_template = self._config.pr_title_format or "{task_id}: {description}"
        return format_template.format(task_id=task_id, description=description)

    def format_body_with_task_link(
        self,
        body: str,
        task_id: str,
        team_key: str,
    ) -> str:
        """Add Linear task link to PR body."""
        task_url = f"https://linear.app/{team_key.lower()}/issue/{task_id}"
        return f"{body}\n\n---\nLinear: {task_url}"
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| No new dependencies | - | Uses existing infrastructure |

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/comments.py`
- `src/adw/task_managers/pr_linking.py`

**Modified Files:**
- `src/adw/task_managers/base.py` - Add post_comment to Protocol
- `src/adw/task_managers/null.py` - Implement no-op post_comment
- `src/adw/task_managers/linear.py` - Implement post_comment
- `src/adw/task_managers/sync.py` - Add comment posting methods
- `src/adw/models/config.py` - Add pr_title_format to TaskManagerConfig

**Test Files:**
- `tests/unit/task_managers/test_comments.py`
- `tests/unit/task_managers/test_linear_comments.py`
- `tests/unit/task_managers/test_pr_linking.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/task_managers/test_comments.py
class TestCommentFormatter:
    def test_format_phase_complete(self):
        """Formats phase completion with duration and artifacts."""

    def test_format_phase_failed(self):
        """Formats phase failure with error and run ID."""

    def test_format_run_complete_with_pr(self):
        """Formats run completion with PR URL."""

    def test_format_run_complete_without_pr(self):
        """Formats run completion without PR URL."""

    def test_format_uses_markdown(self):
        """Output includes markdown formatting."""

class TestStatusSyncServiceComments:
    def test_post_phase_comment_when_enabled(self, mock_task_manager, config):
        """Posts comment when sync_comments=true."""

    def test_skip_comment_when_disabled(self, mock_task_manager, config):
        """Skips comment when sync_comments=false."""

    def test_comment_on_failure_only(self, mock_task_manager, config):
        """Only posts on failure when comment_on_failure_only=true."""

    def test_comment_failure_non_blocking(self, failing_task_manager):
        """Logs warning but doesn't raise on comment failure."""

# tests/unit/task_managers/test_pr_linking.py
class TestPRTitleFormatter:
    def test_format_title_with_task_id(self):
        """Formats title as 'RULE-123: description'."""

    def test_format_title_without_task_id(self):
        """Returns plain description when no task_id."""

    def test_format_title_custom_format(self):
        """Uses custom pr_title_format from config."""

    def test_format_body_adds_linear_link(self):
        """Adds Linear task URL to PR body."""

class TestPRTaskLinkingIntegration:
    def test_pr_created_with_task_link(self, mock_task_manager):
        """PR includes task link when task_id present."""

    def test_linear_receives_pr_comment(self, mock_task_manager):
        """Linear task receives comment with PR URL."""
```

---

## Previous Story Intelligence

**From Story 12.3:**
- StatusSyncService with non-blocking pattern
- sync_comments config option exists
- Orchestrator integration points

**Patterns to Follow:**
- Wrap external calls in try/except
- Use structured logging
- Non-blocking failures

---

## Git Intelligence

**Recent Relevant Commits:**
- Story 12.3: Status sync infrastructure
- StatusSyncService implementation

**Established Patterns:**
- Non-blocking external calls
- Configuration-driven behavior
- Markdown formatting for external systems

---

## Latest Technical Information

**Linear Comment API (2025):**

```graphql
mutation CreateComment($issueId: String!, $body: String!) {
  commentCreate(input: {issueId: $issueId, body: $body}) {
    success
    comment {
      id
      body
      createdAt
    }
  }
}
```

**Comment Best Practices:**
- Use markdown for formatting
- Keep comments concise
- Include actionable information (run ID, error details)
- Provide commands for further investigation

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Non-blocking external calls**: Wrap in try/except, log and continue
- **Structured logging**: Log comment posting attempts
- **Configuration-driven**: Check config before posting

---

## Dev Notes

### Implementation Approach

1. Add post_comment to Protocol and implementations
2. Create CommentFormatter with format methods
3. Extend StatusSyncService with comment methods
4. Add config checks for sync_comments
5. Integrate with orchestrator
6. Test non-blocking behavior

### Key Design Decisions

1. **Separate Formatter**: CommentFormatter isolates formatting logic
2. **Protocol Extension**: post_comment added to TaskManager Protocol
3. **Config-Driven**: Comments only posted when explicitly enabled
4. **Non-Blocking**: Failures logged but don't stop run

### Comment Examples

**Phase Complete:**
```markdown
**Build Phase Completed** ✓

Duration: 45.2s
Artifacts: 3
```

**Phase Failed:**
```markdown
**Build Phase Failed** ❌

Error: Test failures in auth module
Run ID: `01HQX...`

Check logs with: `adw logs show 01HQX...`
```

**Run Complete:**
```markdown
**Run Completed** ✓

Run ID: `01HQX...`
**PR:** https://github.com/org/repo/pull/123

All 5 phases completed successfully.
- Plan: 12.3s
- Build: 45.2s
- Verify: 23.1s
- Validate: 18.7s
- Document: 8.9s
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.6]
- [Source: _bmad-output/architecture.md#Task Manager Integration]
- [Linear API Docs: commentCreate mutation]

---

## Dev Agent Record

### Context Reference

Epic 12: Task Manager Integration - Story 12.6

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
