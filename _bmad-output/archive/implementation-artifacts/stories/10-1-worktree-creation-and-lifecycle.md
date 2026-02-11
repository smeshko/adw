# Story 10.1: Worktree Creation and Lifecycle

Status: done
Linear Issue: not-configured
Epic: 10 - Worktree Isolation
Created: 2026-01-05

---

## Story

As a developer,
I want each ADW run to execute in an isolated git worktree,
so that concurrent runs don't interfere with each other or my working directory.

## Acceptance Criteria

**Given** a new run starts
**When** orchestrator initializes
**Then** a worktree is created at `trees/<run_id>/` from current branch

**Given** worktree creation
**When** `git worktree add` executes
**Then** a new branch `adw/<run_id>` is created for the worktree

**Given** run completes successfully
**When** cleanup runs
**Then** worktree is removed via `git worktree remove`

**Given** run fails
**When** cleanup runs
**Then** worktree is preserved for debugging (configurable)

**Given** `--no-worktree` flag
**When** run starts
**Then** execution happens in current directory (legacy mode)

## Tasks / Subtasks

### Task 1: Create WorktreeManager Class
- [x] Create `src/adw/worktree/manager.py` with `WorktreeManager` class
- [x] Implement `create_worktree(run_id: str, source_branch: str | None) -> Path` method
- [x] Use `git worktree add trees/<run_id> -b adw/<run_id>` subprocess call
- [x] Handle errors: branch already exists, worktree already exists, git not available
- [x] Return the absolute path to the created worktree

### Task 2: Implement Worktree Cleanup
- [x] Implement `remove_worktree(run_id: str, force: bool = False) -> bool` method
- [x] Use `git worktree remove trees/<run_id>` subprocess call
- [x] Handle case where worktree has uncommitted changes (require force or preserve)
- [x] Clean up the `adw/<run_id>` branch after worktree removal (optional via config)

### Task 3: Add Worktree Configuration
- [x] Add `worktree` section to `ProjectConfig` model in `src/adw/models/config.py`
- [x] Configuration fields:
  - `enabled: bool = True` - Enable worktree isolation
  - `base_dir: str = "trees"` - Relative to project root
  - `preserve_on_failure: bool = True` - Keep worktree on failure for debugging
  - `cleanup_branch_on_remove: bool = False` - Delete branch when removing worktree

### Task 4: Integrate with Orchestrator
- [x] Modify `Orchestrator.run()` to create worktree when enabled
- [x] Store worktree path in `RunContext.worktree_path: Path | None`
- [x] Add `use_worktree` flag to `RunContext`
- [x] Modify `Orchestrator.run()` completion to cleanup worktree based on config
- [x] Modify `Orchestrator.abort()` to preserve worktree for debugging
- [x] Add `worktree_config` parameter to Orchestrator.__init__()
- [x] Add `_create_worktree_for_run()` and `_cleanup_worktree()` helper methods

### Task 5: Add --no-worktree CLI Flag
- [x] Add `--no-worktree` option to `adw run` command in `src/adw/cli/app.py`
- [x] When flag is set, skip worktree creation and run in current directory
- [x] Pass `use_worktree=not no_worktree` to orchestrator.run()

### Task 6: Write Tests
- [x] Unit tests for `WorktreeManager.create_worktree()` (8 tests)
- [x] Unit tests for `WorktreeManager.remove_worktree()` (6 tests)
- [x] Integration test for full worktree lifecycle (3 orchestrator tests)
- [x] Test error handling: git not available, permission denied, branch conflicts
- [x] Unit tests for WorktreeConfig model (6 tests)
- [x] Unit tests for RunContext worktree fields (5 tests)

---

## Dependencies

**Depends On:** None (Wave 1 - can start immediately)

**Blocks:**
- 10-2: Worktree Directory Structure (needs base creation logic)
- 10-3: Port Allocation System (needs worktree lifecycle hooks)
- 10-6: Worktree Branch Management (needs branch creation mechanism)

**Can Parallel With:** None (this is the foundation story)

---

## Developer Context

### Technical Requirements

1. **Git Subprocess Execution**
   - Use `subprocess.run()` with `capture_output=True, text=True, check=False`
   - Parse git command output for success/failure detection
   - Handle git not installed gracefully with `ConfigError`

2. **Path Handling**
   - All worktree paths must be absolute
   - Use `pathlib.Path` for all path operations
   - Ensure worktree base directory is created if it doesn't exist

3. **Error Recovery**
   - If worktree creation fails mid-way, attempt cleanup
   - Log all git command outputs for debugging
   - Provide actionable suggestions in error messages

### Architecture Compliance

**File Location:** `src/adw/worktree/manager.py`

**New Package Structure:**
```
src/adw/
├── worktree/
│   ├── __init__.py       # Re-exports WorktreeManager
│   └── manager.py        # WorktreeManager class
```

**Model Changes:**
```python
# src/adw/models/config.py - Add WorktreeConfig
class WorktreeConfig(BaseModel):
    enabled: bool = True
    base_dir: str = "trees"
    preserve_on_failure: bool = True
    cleanup_branch_on_remove: bool = False

class ProjectConfig(BaseModel):
    # ... existing fields ...
    worktree: WorktreeConfig = Field(default_factory=WorktreeConfig)
```

```python
# src/adw/models/context.py - Add worktree_path to RunContext
class RunContext(BaseModel):
    # ... existing fields ...
    worktree_path: Path | None = None
    use_worktree: bool = True
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| subprocess | stdlib | Git command execution |
| pathlib | stdlib | Path manipulation |
| Pydantic | 2.12+ | Config/model validation |

**Git Commands Used:**
```bash
# Create worktree with new branch
git worktree add <path> -b <branch_name>

# Remove worktree
git worktree remove <path>

# Force remove worktree (uncommitted changes)
git worktree remove --force <path>

# Delete branch
git branch -D <branch_name>

# List worktrees (for cleanup/verification)
git worktree list --porcelain
```

### File Structure Requirements

**New Files:**
- `src/adw/worktree/__init__.py`
- `src/adw/worktree/manager.py`

**Modified Files:**
- `src/adw/models/config.py` - Add WorktreeConfig
- `src/adw/models/context.py` - Add worktree_path field
- `src/adw/core/orchestrator.py` - Integrate worktree creation/cleanup
- `src/adw/cli/run.py` - Add --no-worktree flag

**Test Files:**
- `tests/unit/worktree/test_manager.py`
- `tests/integration/test_worktree_lifecycle.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/worktree/test_manager.py
class TestWorktreeManager:
    def test_create_worktree_success(self, tmp_path, git_repo):
        """Worktree is created at expected path with correct branch."""

    def test_create_worktree_branch_exists(self, tmp_path, git_repo):
        """Raises WorktreeError when branch already exists."""

    def test_create_worktree_git_not_available(self, tmp_path, monkeypatch):
        """Raises ConfigError when git is not installed."""

    def test_remove_worktree_success(self, tmp_path, git_repo):
        """Worktree is removed successfully."""

    def test_remove_worktree_uncommitted_changes(self, tmp_path, git_repo):
        """Preserves worktree with uncommitted changes unless force=True."""

    def test_remove_worktree_cleanup_branch(self, tmp_path, git_repo):
        """Deletes branch when cleanup_branch_on_remove=True."""
```

**Integration Tests:**
```python
# tests/integration/test_worktree_lifecycle.py
class TestWorktreeLifecycle:
    def test_full_run_with_worktree(self, project_with_git):
        """Run creates worktree, executes, and cleans up on success."""

    def test_run_preserves_worktree_on_failure(self, project_with_git):
        """Run preserves worktree when preserve_on_failure=True and run fails."""

    def test_no_worktree_flag_skips_creation(self, project_with_git):
        """--no-worktree runs in current directory."""
```

**Test Fixtures Needed:**
```python
@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    # Create initial commit
    (tmp_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)
    return tmp_path
```

---

## Previous Story Intelligence

This is the first story in Epic 10 (Worktree Isolation). No previous story learnings available.

**Relevant Patterns from Other Epics:**
- Epic 4 established state persistence patterns in `.adw/runs/`
- Epic 6 established orchestrator lifecycle patterns
- Hook execution (Epic 3) provides subprocess execution patterns

---

## Git Intelligence

**Recent Relevant Commits:**
- Story 9-5: PR creation command - shows git subprocess patterns
- Story 9-3: Git diff capture - shows git command output parsing
- Story 9-1: Feature branch creation - shows branch naming patterns

**Established Patterns:**
- Git operations use subprocess with captured output
- Errors wrapped in typed exceptions with suggestions
- Git state changes logged at INFO level

---

## Latest Technical Information

**Git Worktree Best Practices (2025):**
- Worktrees share `.git` directory, reducing disk usage
- Worktrees can be on different branches simultaneously
- `--detach` creates worktree without a branch (not used here)
- `git worktree prune` cleans up stale worktree references

**Considerations:**
- Worktrees cannot share a branch - enforced by git
- Removing a worktree does NOT delete the branch automatically
- Force removal needed if worktree has uncommitted changes

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **All models in models/**: WorktreeConfig goes in `models/config.py`
- **Exception hierarchy**: Create `WorktreeError` extending `ADWError`
- **Type annotations required**: All functions fully typed
- **Structured logging**: Use `logger.info("Worktree created", path=str(path), branch=branch)`
- **Context managers**: Use for subprocess cleanup if needed

---

## Dev Notes

### Implementation Approach

1. Start with `WorktreeManager` class - standalone, testable
2. Add configuration model support
3. Integrate with orchestrator
4. Add CLI flag
5. Write comprehensive tests

### Exception to Add

```python
# src/adw/exceptions.py
class WorktreeError(ADWError):
    """Raised when worktree operations fail."""
    pass
```

### Project Structure Notes

- New `worktree/` package follows existing package patterns
- Configuration integrates with existing `ProjectConfig`
- RunContext field addition is backward compatible (optional field)

### References

- [Source: _bmad-output/epics/epic-10-worktree-isolation.md#Story 10.1]
- [Source: _bmad-output/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 10: Worktree Isolation - Story 10.1

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- All 8 unit tests for WorktreeManager.create_worktree() pass
- 308 total unit tests pass (no regressions)

### Completion Notes List

- Task 1: Created WorktreeManager class with create_worktree() method
  - Added WorktreeError exception to exceptions.py
  - Created src/adw/worktree/ package with __init__.py and manager.py
  - Implemented create_worktree() with branch/path conflict detection
  - Added cleanup for partial failures during worktree creation
  - All 8 creation tests pass

- Task 2: Implemented remove_worktree() method
  - Added remove_worktree(run_id, force, cleanup_branch) method
  - Added _has_uncommitted_changes() helper for change detection
  - Added _delete_branch() helper for optional branch cleanup
  - All 6 removal tests pass (14 total tests)

- Task 3: Added WorktreeConfig model
  - Created WorktreeConfig class with enabled, base_dir, preserve_on_failure, cleanup_branch_on_remove
  - Added worktree field to ProjectConfig
  - Exported WorktreeConfig from models/__init__.py
  - All 8 new config tests pass (33 total config tests)

- Task 4: Full Orchestrator integration
  - Added worktree_path: Path | None field to RunContext
  - Added use_worktree: bool field to RunContext
  - Added worktree_config parameter to Orchestrator.__init__()
  - Added _create_worktree_for_run() and _cleanup_worktree() helper methods
  - Modified run() to create worktree when enabled and use_worktree=True
  - Added cleanup on successful completion
  - Added preservation on failure (based on preserve_on_failure config)
  - Added preservation on abort for debugging
  - All 61 orchestrator tests pass

- Task 5: Added --no-worktree CLI flag
  - Added --no-worktree option to `adw run` command
  - Updated help text with example usage
  - Passed use_worktree=not no_worktree to orchestrator.run()

- Task 6: Completed all tests
  - 14 unit tests for WorktreeManager (create + remove)
  - 6 unit tests for WorktreeConfig model
  - 5 unit tests for RunContext worktree fields
  - 3 integration tests for orchestrator worktree integration
  - Total: 28 new tests, all passing

### File List

**New Files:**
- src/adw/worktree/__init__.py
- src/adw/worktree/manager.py
- tests/unit/worktree/__init__.py
- tests/unit/worktree/test_manager.py

**Modified Files:**
- src/adw/exceptions.py (added WorktreeError class)
- src/adw/models/config.py (added WorktreeConfig class)
- src/adw/models/context.py (added worktree_path, use_worktree fields)
- src/adw/models/__init__.py (exported WorktreeConfig)
- src/adw/core/orchestrator.py (integrated WorktreeManager)
- src/adw/cli/app.py (added --no-worktree flag)
- tests/unit/models/test_config.py (added WorktreeConfig tests)
- tests/unit/models/test_context.py (added worktree field tests)
- tests/unit/core/test_orchestrator.py (added worktree integration tests)
