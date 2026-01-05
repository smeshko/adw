# Story 10.6: Worktree Branch Management

Status: ready-for-dev
Linear Issue: not-configured
Epic: 10 - Worktree Isolation
Created: 2026-01-05

---

## Story

As a developer,
I want worktree branches managed automatically,
so that my git history stays clean.

## Acceptance Criteria

**Given** worktree creation
**When** branch is created
**Then** it's named `adw/<run_id>` (e.g., `adw/01HQXK5P3Z7V8R2M4N6T9W1Y3C`)

**Given** run completes with PR created
**When** cleanup runs
**Then** branch is preserved (needed for PR)

**Given** run fails or is aborted
**When** cleanup runs with `--delete-branch`
**Then** worktree AND branch are removed

**Given** run aborted
**When** cleanup runs without flag
**Then** worktree removed, branch preserved for debugging

## Tasks / Subtasks

### Task 1: Create WorktreeBranchManager Class
- [ ] Create `src/adw/worktree/branch.py` with `WorktreeBranchManager` class
- [ ] Implement `get_branch_name(run_id: str) -> str` returning `adw/<run_id>`
- [ ] Implement `branch_exists(branch_name: str) -> bool`
- [ ] Implement `create_branch(run_id: str, base_ref: str) -> str`

### Task 2: Implement Branch Deletion Logic
- [ ] Implement `delete_branch(run_id: str, force: bool = False) -> bool`
- [ ] Check for unpushed commits before deletion
- [ ] Warn user if branch has work that would be lost
- [ ] Return True if deleted, False if preserved

### Task 3: Integrate with Worktree Creation
- [ ] Modify `WorktreeManager.create_worktree()` to use branch manager
- [ ] Create `adw/<run_id>` branch from base ref before worktree add
- [ ] Store branch_name in RunContext

### Task 4: Implement Cleanup Integration
- [ ] Add `delete_branch` parameter to `WorktreeManager.remove_worktree()`
- [ ] Delete branch only when explicitly requested
- [ ] Check for PR before allowing branch deletion (optional via gh CLI)

### Task 5: Add --delete-branch CLI Flag
- [ ] Add `--delete-branch` flag to `adw cleanup` command
- [ ] Add flag to abort/failure cleanup operations
- [ ] Warn user about data loss before branch deletion

### Task 6: Track Branch State in Context
- [ ] Add `branch_name: str | None` to RunContext model
- [ ] Add `branch_deleted: bool = False` for tracking

### Task 7: Write Tests
- [ ] Test branch name generation
- [ ] Test branch creation from different base refs
- [ ] Test deletion with unpushed commits handling
- [ ] Test integration with worktree lifecycle

---

## Dependencies

**Depends On:**
- 10-1: Worktree Creation and Lifecycle (needs base worktree mechanism)

**Blocks:**
- 10-4: Concurrent Run Management (needs branch tracking)

**Can Parallel With:**
- 10-2: Worktree Directory Structure
- 10-3: Port Allocation System

---

## Developer Context

### Technical Requirements

1. **Git Command Execution**
   - Use `subprocess.run()` with `capture_output=True, text=True`
   - Parse command output for success/failure detection
   - Handle git errors with typed exceptions

2. **Branch Safety Checks**
   - Check for unpushed commits: `git log @{u}..HEAD` (if upstream exists)
   - Check for uncommitted changes in worktree
   - Never delete branch with unpushed work without `force=True`

3. **PR Detection (Optional)**
   - Use `gh pr view <branch>` to check for PR
   - Gracefully handle case where gh CLI not available
   - Default to preserving branch if unsure

### Architecture Compliance

**New Files:**
```
src/adw/
├── worktree/
│   └── branch.py   # NEW: WorktreeBranchManager class
```

**WorktreeBranchManager Implementation:**
```python
# src/adw/worktree/branch.py
import subprocess
from pathlib import Path

from adw.exceptions import WorktreeError


class WorktreeBranchManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def get_branch_name(self, run_id: str) -> str:
        """Generate branch name for a run."""
        return f"adw/{run_id}"

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists locally."""
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())

    def create_branch(self, run_id: str, base_ref: str | None = None) -> str:
        """Create a worktree branch from base ref."""
        branch_name = self.get_branch_name(run_id)
        base = base_ref or "HEAD"

        if self.branch_exists(branch_name):
            raise WorktreeError(
                code="BRANCH_EXISTS",
                message=f"Branch {branch_name} already exists",
                suggestion=f"Delete the branch with: git branch -D {branch_name}",
                recoverable=False,
            )

        result = subprocess.run(
            ["git", "branch", branch_name, base],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise WorktreeError(
                code="BRANCH_CREATE_FAILED",
                message=f"Failed to create branch: {result.stderr}",
                suggestion="Check that base ref exists and git is available",
                recoverable=False,
            )

        return branch_name

    def has_unpushed_commits(self, branch_name: str) -> bool:
        """Check if branch has commits not pushed to upstream."""
        result = subprocess.run(
            ["git", "log", f"{branch_name}@{{u}}..{branch_name}", "--oneline"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        # If command fails (no upstream), assume no unpushed
        if result.returncode != 0:
            return False
        return bool(result.stdout.strip())

    def delete_branch(self, run_id: str, force: bool = False) -> bool:
        """Delete a worktree branch.

        Returns True if deleted, False if preserved.
        """
        branch_name = self.get_branch_name(run_id)

        if not self.branch_exists(branch_name):
            return True  # Already gone

        if not force and self.has_unpushed_commits(branch_name):
            return False  # Preserve by default

        delete_flag = "-D" if force else "-d"
        result = subprocess.run(
            ["git", "branch", delete_flag, branch_name],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        return result.returncode == 0

    def check_pr_exists(self, branch_name: str) -> bool | None:
        """Check if a PR exists for the branch using gh CLI.

        Returns None if gh CLI not available.
        """
        result = subprocess.run(
            ["gh", "pr", "view", branch_name, "--json", "state"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # Could be: gh not installed, not authenticated, no PR
            return None

        return "OPEN" in result.stdout or "MERGED" in result.stdout
```

**Model Changes:**
```python
# src/adw/models/context.py - Extend RunContext
class RunContext(BaseModel):
    # ... existing fields ...
    branch_name: str | None = None
    branch_deleted: bool = False
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| subprocess | stdlib | Git command execution |
| pathlib | stdlib | Path operations |

### File Structure Requirements

**New Files:**
- `src/adw/worktree/branch.py`

**Modified Files:**
- `src/adw/worktree/manager.py` - Integrate branch manager
- `src/adw/models/context.py` - Add branch_name field
- `src/adw/cli/cleanup.py` - Add --delete-branch flag

**Test Files:**
- `tests/unit/worktree/test_branch.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/worktree/test_branch.py
class TestBranchNaming:
    def test_get_branch_name_format(self):
        """Branch name follows adw/<run_id> format."""
        manager = WorktreeBranchManager(tmp_path)
        name = manager.get_branch_name("01HQTEST")
        assert name == "adw/01HQTEST"


class TestBranchExists:
    def test_existing_branch_returns_true(self, git_repo_with_branch):
        """Returns True for existing branch."""

    def test_missing_branch_returns_false(self, git_repo):
        """Returns False for non-existent branch."""


class TestBranchCreation:
    def test_creates_branch_from_head(self, git_repo):
        """Creates branch from HEAD when no base specified."""

    def test_creates_branch_from_ref(self, git_repo):
        """Creates branch from specified base ref."""

    def test_raises_if_branch_exists(self, git_repo_with_branch):
        """Raises WorktreeError if branch already exists."""


class TestBranchDeletion:
    def test_deletes_branch(self, git_repo_with_branch):
        """Successfully deletes branch."""

    def test_preserves_with_unpushed_commits(self, git_repo_with_unpushed):
        """Returns False when unpushed commits exist."""

    def test_force_deletes_with_unpushed(self, git_repo_with_unpushed):
        """Force=True deletes despite unpushed commits."""
```

**Test Fixtures:**
```python
@pytest.fixture
def git_repo_with_branch(git_repo):
    """Git repo with an adw/ branch created."""
    subprocess.run(
        ["git", "branch", "adw/01HQTEST"],
        cwd=git_repo,
        check=True,
    )
    return git_repo

@pytest.fixture
def git_repo_with_unpushed(git_repo_with_branch):
    """Git repo with branch containing unpushed commits."""
    # Create remote to simulate unpushed state
    # ... setup code
    return git_repo_with_branch
```

---

## Previous Story Intelligence

**From Story 10-1:**
- WorktreeManager handles worktree lifecycle
- Branch creation happens as part of worktree creation

**From Story 9-1:**
- Feature branch naming uses `feature/<name>` pattern
- Separate from worktree's internal `adw/<run_id>` branches

---

## Git Intelligence

**Relevant Patterns:**
- Git subprocess patterns from `utils/git.py`
- Branch naming patterns from Epic 9 stories

---

## Latest Technical Information

**Git Branch Commands:**
```bash
# Create branch from ref
git branch adw/<run_id> <base_ref>

# Check if branch exists
git branch --list <branch_name>

# Check for unpushed commits (if upstream exists)
git log @{u}..HEAD --oneline

# Delete branch (safe)
git branch -d <branch_name>

# Force delete branch
git branch -D <branch_name>
```

**gh CLI for PR Detection:**
```bash
# Check if PR exists for branch
gh pr view <branch_name> --json state
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- **Exception hierarchy**: Use `WorktreeError` for branch failures
- **Subprocess execution**: Consistent patterns with other git commands
- **Structured logging**: Log branch operations

---

## Dev Notes

### Branch Naming Convention

| Component | Format | Example |
|-----------|--------|---------|
| Prefix | `adw/` | `adw/` |
| Run ID | ULID | `01HQXK5P3Z7V8R2M4N6T9W1Y3C` |
| Full Name | `adw/<run_id>` | `adw/01HQXK5P3Z7V8R2M4N6T9W1Y3C` |

**Note:** `adw/` branches are internal worktree branches, separate from user-facing `feature/` branches created by Epic 9.

### Cleanup Decision Matrix

| Run Status | PR Exists | --delete-branch | Branch Action |
|------------|-----------|-----------------|---------------|
| Success | Yes | N/A | Preserve |
| Success | No | No | Preserve |
| Success | No | Yes | Delete |
| Failed | N/A | No | Preserve |
| Failed | N/A | Yes | Delete |
| Aborted | N/A | No | Preserve |
| Aborted | N/A | Yes | Delete |

### References

- [Source: _bmad-output/epics/epic-10-worktree-isolation.md#Story 10.6]
- [Source: _bmad-output/architecture.md#Git Integration]

---

## Dev Agent Record

### Context Reference

Epic 10: Worktree Isolation - Story 10.6

### Agent Model Used

<!-- To be filled by dev agent -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
