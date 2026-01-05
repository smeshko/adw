# Story: Bugfix ISS-009 - Git Diff Capture Fails / Auto-Commit Not Working

Status: ready-for-dev
Linear Issue: not-configured
Epic: 9 - Git Integration & Documentation
Created: 2026-01-05

---

## Story

As a **CLI user**,
I want **my code changes to be automatically committed after each phase**,
so that **git diff capture works and I have incremental commits for PR history**.

## Acceptance Criteria

- [ ] After BUILD phase completes, all created/modified files are staged (`git add -A`)
- [ ] A commit is created with message `[adw] Build: <feature-description>`
- [ ] After subsequent phases (VERIFY, VALIDATE, DOCUMENT), commits are also created
- [ ] Git diff capture (`git diff HEAD~1`) succeeds and captures the phase changes
- [ ] Untracked files (new files created by LLM) are included in staging
- [ ] PR description includes actual diff information

## Tasks / Subtasks

### Task 1: Investigate Current Auto-Commit Flow
- [ ] Check if post-phase hooks are being triggered
- [ ] Examine `src/adw/hooks/` for commit-related hooks
- [ ] Verify hook execution in orchestrator after phase completion
- [ ] Trace why `git add -A` is not staging untracked files

### Task 2: Fix Post-Phase Commit Hook
- [ ] Ensure hook stages ALL changes including untracked: `git add -A`
- [ ] Create commit with proper message format: `[adw] {phase}: {feature}`
- [ ] Handle case where no changes to commit (empty diff)
- [ ] Run in worktree context (correct git directory)

### Task 3: Fix Git Diff Capture
- [ ] Ensure diff capture runs AFTER commit is created
- [ ] Use `git diff HEAD~1` to capture changes from latest commit
- [ ] Handle case where no previous commit exists (initial commit scenario)
- [ ] Store diff as artifact for Document phase

### Task 4: Add Structured Logging
- [ ] Log when files are staged: `logger.info("Staged changes", file_count=N)`
- [ ] Log when commit is created: `logger.info("Committed changes", sha=abc123)`
- [ ] Log when diff is captured: `logger.info("Captured diff", lines=N)`

### Task 5: Write Tests
- [ ] Unit test: Post-hook stages all file types (modified, untracked, deleted)
- [ ] Unit test: Commit message format is correct
- [ ] Unit test: Diff capture returns correct content
- [ ] Integration test: End-to-end BUILD → commit → diff capture flow

---

## Developer Context

### Issue Report Reference

**ISS-009:** Git diff capture fails - auto-commit not working
- **Reported:** 2026-01-05
- **Severity:** Major
- **Type:** Bug
- **File:** `_bmad-output/implementation-artifacts/issues/ISS-009-git-diff-capture-fails-no-commits.md`

**Symptoms:**
- "Git diff command failed" / "Could not capture git diff" shown during BUILD
- `git log` in worktree shows no new commits after LLM creates files
- `git status` shows untracked files (not staged, not committed)

**Root Cause:**
Story 9.2 acceptance criteria states auto-commit should happen, but the post-hook either:
1. Isn't being triggered
2. Only stages modified files, not untracked files
3. Has a bug preventing commits

### Technical Requirements

**Expected Flow:**
```
BUILD phase completes
  → Post-hook triggered
    → git add -A (stage ALL changes including untracked)
    → git commit -m "[adw] Build: <feature>"
      → Commit created successfully
        → git diff HEAD~1 captures changes
          → Diff stored as artifact
```

**Actual Flow:**
```
BUILD phase completes
  → Post-hook triggered (maybe?)
    → git add (only modified files? or not running?)
    → No commit created
      → git diff HEAD~1 fails (nothing to diff)
        → "Git diff command failed" error
```

**Fix Implementation:**
```python
# In post-phase hook (src/adw/hooks/git_hooks.py or similar)
def post_build_commit(context: RunContext) -> None:
    """Commit all changes after BUILD phase."""
    worktree_path = context.worktree_path

    # Stage ALL changes including untracked files
    subprocess.run(["git", "add", "-A"], cwd=worktree_path, check=True)

    # Check if there are changes to commit
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=worktree_path,
        capture_output=True
    )
    if result.returncode == 0:
        logger.info("No changes to commit")
        return

    # Create commit
    message = f"[adw] Build: {context.feature_description}"
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=worktree_path,
        check=True
    )
    logger.info("Committed build changes", sha=get_head_sha())
```

### Architecture Compliance

**File Location:** `src/adw/hooks/` or `src/adw/git/`

**Hook Integration Points:**
- Orchestrator calls hooks after phase completion
- Hooks execute in worktree context
- Hook failures should be logged but not fail the run

**Pydantic Models:** No new models required

**Exception Handling:** Use `HookError` from exceptions hierarchy

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| subprocess | stdlib | Git command execution |
| asyncio | stdlib | Async subprocess if needed |

**Git Commands:**
- `git add -A` - Stage all changes (modified, deleted, untracked)
- `git diff --cached --quiet` - Check if staged changes exist (exit 1 = changes)
- `git commit -m "<msg>"` - Create commit
- `git diff HEAD~1` - Diff against previous commit
- `git rev-parse HEAD` - Get current commit SHA

### File Structure Requirements

**Files to investigate/modify:**
- `src/adw/hooks/` - Post-phase hooks
- `src/adw/core/orchestrator.py` - Hook invocation points
- `src/adw/git/` - Git operations (if exists)

**Files to create (if needed):**
- `src/adw/hooks/git_hooks.py` - Git-specific hooks
- `tests/unit/hooks/test_git_hooks.py`
- `tests/integration/test_git_commit_flow.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/hooks/test_git_hooks.py
class TestGitHooks:
    def test_post_build_stages_untracked_files(self, worktree):
        """New files created by LLM are staged."""

    def test_post_build_creates_commit(self, worktree):
        """Commit is created with correct message format."""

    def test_post_build_no_changes_skips_commit(self, worktree):
        """No commit created when no changes exist."""

    def test_diff_capture_after_commit(self, worktree):
        """Diff captures changes from the new commit."""
```

**Integration Tests:**
```python
# tests/integration/test_git_commit_flow.py
def test_build_phase_creates_commit_with_new_files():
    """End-to-end: BUILD creates files → commit created → diff captured."""
    # 1. Initialize run in worktree
    # 2. Run BUILD phase that creates new files
    # 3. Verify commit exists with correct message
    # 4. Verify diff artifact contains the new files
```

---

## Previous Story Intelligence

**Story 9-2 (Stage and Commit Changes):** Original implementation
- Acceptance criteria: "changed files are staged and committed with message '[adw] Build: <feature>'"
- Implementation may have bug or may not be triggered

**Story 9-3 (Capture Git Diff):** Depends on 9-2
- Calls `git diff HEAD~1` which fails without commits
- Should work correctly once 9-2 is fixed

**Related Issue ISS-008:** Worktree cleanup fails with untracked files
- Symptom of same root cause - files not being committed
- Fixing ISS-009 reduces severity of ISS-008

---

## Git Intelligence

**Recent commits related to git integration:**
- Story 9-1 through 9-5 implemented git integration
- Hooks may have been added in 9-2

**Key Investigation Points:**
- When was `git add -A` last used vs `git add .`?
- Are hooks registered in orchestrator?
- Is worktree context passed to hooks correctly?

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Use `HookError` from exception hierarchy
- Structured logging: `logger.info("Committed changes", sha=sha, phase="build")`
- Run git commands with `subprocess.run()` and `check=True`
- Always use `cwd=worktree_path` for git commands in worktree

---

## Dev Notes

### Investigation Priority

1. **First:** Check if post-build hook is registered and triggered
2. **Second:** Verify git commands are using `-A` flag (not just `-a` or `.`)
3. **Third:** Confirm hook runs in correct directory (worktree, not main repo)
4. **Fourth:** Check if commit is attempted but failing silently

### Key Difference: `git add -A` vs `git add .`
- `git add -A` - Stages all changes (new, modified, deleted) in entire tree
- `git add .` - Stages changes in current directory only
- `git add -a` (with commit) - Only stages modified/deleted, NOT untracked

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-009-git-diff-capture-fails-no-commits.md]
- [Source: _bmad-output/implementation-artifacts/stories/9-2-stage-and-commit-changes-via-post-hook.md]
- [Source: _bmad-output/implementation-artifacts/stories/9-3-capture-git-diff-as-artifact.md]

---

## Dev Agent Record

### Context Reference

- Issue: ISS-009-git-diff-capture-fails-no-commits.md
- Related: Story 9-2, Story 9-3
- Related: ISS-008 (worktree cleanup - same root cause)

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

### File List

- `src/adw/hooks/` (investigate existing)
- `src/adw/core/orchestrator.py`
- `src/adw/git/` (if exists)
- `tests/unit/hooks/test_git_hooks.py`
- `tests/integration/test_git_commit_flow.py`
