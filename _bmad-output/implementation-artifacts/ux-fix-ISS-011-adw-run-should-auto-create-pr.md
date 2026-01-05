# Story: UX Fix ISS-011 - ADW Run Should Auto-Create PR

Status: in-progress
Linear Issue: not-configured
Epic: 9 - Git Integration & Documentation
Created: 2026-01-05

---

## Story

As a **CLI user**,
I want **a PR to be automatically created when my run completes successfully**,
so that **I don't need to run a separate command and can immediately see my work in GitHub**.

## Acceptance Criteria

- [ ] After successful run completion, check if git remote exists
- [ ] Check if `gh` CLI is available in PATH
- [ ] If both conditions met: automatically create PR using generated description
- [ ] Display PR URL in completion summary
- [ ] If conditions not met: show current behavior (path to PR description)
- [ ] Add optional hint: "Run 'adw pr <run_id>' to create PR manually"
- [ ] Add config option: `git.auto_create_pr` (default: true if remote exists)

## Tasks / Subtasks

### Task 1: Add Remote and GH CLI Detection
- [x] Create utility function to check if git remote exists: `git remote -v`
- [x] Create utility function to check if `gh` CLI is available: `which gh`
- [x] Cache results to avoid repeated subprocess calls

### Task 2: Implement Auto-PR Creation
- [ ] After document phase completes successfully:
  - Check remote exists
  - Check gh CLI available
  - If both true: call existing `adw pr` logic
  - Capture PR URL from gh output
- [ ] Handle errors gracefully (network issues, auth problems)
- [ ] Don't fail the run if PR creation fails

### Task 3: Update Completion Summary
- [ ] If PR created: display `PR Created: <url>`
- [ ] If PR not created (no remote): display `PR Description: <path>`
- [ ] If PR not created (no gh): display `PR Description: <path>` + hint about `gh` CLI
- [ ] If PR creation failed: display error + fallback to description path

### Task 4: Add Configuration Option
- [ ] Add `git.auto_create_pr: bool` to project config schema
- [ ] Default: `True` (auto-create when possible)
- [ ] Allow users to disable auto-PR creation

### Task 5: Write Tests
- [ ] Unit test: Remote detection works correctly
- [ ] Unit test: GH CLI detection works correctly
- [ ] Unit test: PR is created when conditions met
- [ ] Unit test: Graceful fallback when conditions not met
- [ ] Integration test: End-to-end run → PR creation flow

---

## Developer Context

### Issue Report Reference

**ISS-011:** adw run should automatically create PR when remote exists
- **Reported:** 2026-01-05
- **Severity:** Minor
- **Type:** UX Issue
- **File:** `_bmad-output/implementation-artifacts/issues/ISS-011-adw-run-should-auto-create-pr.md`

**Current Behavior:**
- Run completes successfully
- PR description generated at `.adw/runs/.../artifacts/document/pr_description.md`
- User must run `adw pr <run_id>` separately

**Desired Behavior:**
- Run completes successfully
- PR automatically created if remote + gh CLI exist
- PR URL shown in completion summary

### Technical Requirements

**Detection Logic:**
```python
def can_create_pr() -> tuple[bool, str]:
    """Check if PR can be created automatically."""
    # Check git remote
    result = subprocess.run(
        ["git", "remote", "-v"],
        capture_output=True,
        text=True
    )
    if not result.stdout.strip():
        return False, "No git remote configured"

    # Check gh CLI
    result = subprocess.run(
        ["which", "gh"],
        capture_output=True
    )
    if result.returncode != 0:
        return False, "GitHub CLI (gh) not found"

    return True, "Ready"
```

**PR Creation Flow:**
```python
def auto_create_pr(context: RunContext) -> str | None:
    """Create PR automatically after successful run."""
    can_create, reason = can_create_pr()
    if not can_create:
        logger.info("Skipping auto PR creation", reason=reason)
        return None

    # Use existing PR creation logic from Story 9-5
    pr_url = create_pr(context)
    return pr_url
```

**Config Schema Addition:**
```yaml
# .adw/project.yaml
git:
  auto_create_pr: true  # default: true
```

### Architecture Compliance

**File Location:** `src/adw/git/` or `src/adw/core/`

**Integration Point:**
- After document phase completes in orchestrator
- Before final summary is displayed

**Pydantic Models:**
- Add `auto_create_pr: bool = True` to `GitConfig` model

**Exception Handling:**
- PR creation errors should warn, not fail run
- Use existing `GitError` from hierarchy

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| subprocess | stdlib | Git/gh command execution |
| shutil | stdlib | `which` alternative for gh detection |

**External Dependencies:**
- `gh` CLI must be installed and authenticated
- Git remote must be configured

### File Structure Requirements

**Files to modify:**
- `src/adw/core/orchestrator.py` - Add auto-PR after document phase
- `src/adw/models/config.py` - Add `auto_create_pr` config option
- `src/adw/cli/run.py` or display code - Update completion summary

**Files to potentially create:**
- `src/adw/git/pr.py` - PR creation utilities (if not already centralized)

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/git/test_pr_auto_create.py
class TestPRAutoCreate:
    def test_can_create_pr_with_remote_and_gh(self, mock_subprocess):
        """Returns True when remote exists and gh is available."""

    def test_can_create_pr_without_remote(self, mock_subprocess):
        """Returns False with reason when no remote."""

    def test_can_create_pr_without_gh(self, mock_subprocess):
        """Returns False with reason when gh not available."""

    def test_auto_create_pr_creates_when_possible(self, mock_subprocess):
        """PR is created when conditions are met."""

    def test_auto_create_pr_skips_when_not_possible(self, mock_subprocess):
        """PR creation skipped gracefully when conditions not met."""
```

**Integration Tests:**
```python
# tests/integration/test_auto_pr.py
def test_run_creates_pr_when_remote_exists():
    """End-to-end: successful run → PR created → URL displayed."""
    # Requires actual git remote and gh auth for true integration test
```

---

## Previous Story Intelligence

**Story 9-5 (Support PR Creation Command):** Implemented `adw pr` command
- Creates PR using `gh pr create`
- Reads description from generated file
- Handles errors appropriately

**Story 9-4 (Generate PR Description):** Generates PR description file
- Stored at `.adw/runs/<id>/artifacts/document/pr_description.md`
- Includes summary, changes, testing notes

---

## Git Intelligence

**Recent commits related to PR creation:**
- Story 9-5 implemented PR command
- PR description generation in Story 9-4

**Key Observation:**
The PR creation logic already exists in `adw pr` command. This story is about calling it automatically after successful runs.

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Use Rich console for output formatting
- Structured logging for actions taken
- Config options in Pydantic models with defaults
- Graceful error handling (warn, don't fail)

---

## Dev Notes

### Implementation Approach

1. **Reuse Existing Logic:** Call same code as `adw pr` command
2. **Detection First:** Check conditions before attempting creation
3. **Fail Gracefully:** PR creation failure should not fail the run
4. **Inform User:** Clear messaging about what happened and why

### UX Considerations

**Success Case:**
```
╭─────────────────────────── Pipeline Summary ───────────────────────────╮
│ ✓ plan → ✓ build → ✓ verify → ✓ validate → ✓ document                  │
│                                                                         │
│ Status: completed                                                       │
│ Duration: 390.7s                                                        │
│ Tokens: 10,846                                                          │
│                                                                         │
│ PR Created: https://github.com/org/repo/pull/123                        │
╰─────────────────────────────────────────────────────────────────────────╯
```

**No Remote Case:**
```
│ PR Description: .adw/runs/.../pr_description.md                         │
│ ℹ️ No git remote configured - run 'adw pr <id>' after pushing          │
```

**No GH CLI Case:**
```
│ PR Description: .adw/runs/.../pr_description.md                         │
│ ℹ️ Install GitHub CLI (gh) for automatic PR creation                   │
```

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-011-adw-run-should-auto-create-pr.md]
- [Source: _bmad-output/implementation-artifacts/stories/9-5-support-pr-creation-command.md]
- [Source: _bmad-output/implementation-artifacts/stories/9-4-generate-pr-description.md]

---

## Dev Agent Record

### Context Reference

- Issue: ISS-011-adw-run-should-auto-create-pr.md
- Related: Story 9-4, Story 9-5

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

### File List

- `src/adw/core/orchestrator.py`
- `src/adw/models/config.py`
- `src/adw/git/pr.py` (existing or create)
- `src/adw/cli/run.py` or display code
- `tests/unit/git/test_pr_auto_create.py`
- `tests/integration/test_auto_pr.py`
