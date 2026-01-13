# Story: Tests Not Cleaning Up Worktrees (ISS-024)

Status: ready-for-dev
Linear Issue: pending
Epic: 13 - Webhook Infrastructure (Tech Debt)
Created: 2026-01-10

---

## Story

As a developer running the test suite,
I want all worktrees created during test execution to be automatically cleaned up,
so that I don't have disk space accumulation, git clutter, or confusing development experience.

## Acceptance Criteria

**Given** the test suite runs with worktree-creating tests
**When** tests complete (pass or fail)
**Then** all worktrees created during the test session are removed

**Given** a test creates a worktree using WorktreeManager
**When** the test fixture is torn down
**Then** the worktree directory is removed from `trees/`
**And** the associated git branch `adw/<run_id>` is deleted

**Given** a test fails unexpectedly
**When** pytest cleanup runs
**Then** worktrees are still cleaned up via `finally` block

**Given** multiple test modules create worktrees
**When** the test session ends
**Then** a session-scoped finalizer verifies no orphaned worktrees remain

## Tasks / Subtasks

- [x] **Task 1:** Create shared `git_repo` fixture with yield-based cleanup in `tests/conftest.py`
  - [ ] Move from class-local `git_repo` fixtures to shared fixture (see Task 3)
  - [x] Add cleanup logic after `yield` using `try/finally` pattern
  - [x] Cleanup includes: remove worktree directories, delete `adw/*` branches

- [x] **Task 2:** Add session-scoped worktree cleanup finalizer
  - [x] Create autouse session-scoped fixture `cleanup_orphaned_worktrees`
  - [x] On session end, scan for any ULID-named directories in `trees/`
  - [x] Force-remove any remaining worktrees

- [ ] **Task 3:** Update worktree test fixtures to use shared fixture
  - [ ] Update `TestWorktreeManagerCreation` in `test_manager.py`
  - [ ] Update `TestWorktreeManagerRemoval` in `test_manager.py`
  - [ ] Update `TestWorktreeManagerBranchIntegration` in `test_manager.py`
  - [ ] Update `TestWorktreeForceCleanup` in `test_manager.py`
  - [ ] Update `TestWorktreeCleanupIntegration` in `test_worktree_cleanup_integration.py`
  - [ ] Update `TestConcurrentRunManager` in `test_concurrent.py`

- [ ] **Task 4:** Add verification assertions to tests
  - [ ] After worktree removal, assert directory doesn't exist
  - [ ] Assert git branch is deleted after cleanup

- [ ] **Task 5:** Verify fix with manual testing
  - [ ] Run full test suite: `pytest`
  - [ ] Check for leftover worktrees: `git worktree list`
  - [ ] Verify no orphaned branches: `git branch | grep adw/`

---

## Relevant Feature Documentation

### Test Reduction Strategy (ADR-001)

The ADW test suite follows specific guidelines for test quality:

**Tests Worth KEEPING (Never Delete):**
- Validation tests - `test_*_required_fields`, `test_invalid_*`
- Behavior tests - `test_context_merge()`, `test_to_markdown()`
- Error path tests - `test_raises_*_error`, `test_*_failure_*`
- Integration tests - Real shell execution, file I/O, signal handling
- Concurrency tests - `test_concurrent_*`, lock tests

**Test Naming Convention:**
```
test_<unit>_<behavior>_<condition>
```

[Source: docs/architecture/adrs/ADR-001-test-reduction-strategy.md]

---

## Developer Context

### Technical Requirements

1. **Fixture Pattern:** Use pytest `yield` fixtures with `try/finally` for cleanup
2. **Scope Strategy:**
   - Function-scoped `git_repo` fixture for individual tests
   - Session-scoped cleanup finalizer for orphan detection
3. **Git Commands Required:**
   - `git worktree remove <path> --force` for worktree cleanup
   - `git branch -D adw/<run_id>` for branch cleanup
4. **Error Handling:** Cleanup must succeed even if worktree is in inconsistent state

### Architecture Compliance

**From project-context.md:**

1. **Exception Hierarchy:** If cleanup fails, use `WorktreeError` from `adw.exceptions`
2. **Logging:** Use structured logging: `logger.info("Cleanup completed", worktree_count=3)`
3. **Context Managers:** Always use context managers for file operations
4. **Type Annotations:** Full annotations required on all fixture functions

**From conftest.py patterns:**
- Existing `isolated_global_index` fixture demonstrates `autouse=True, scope="function"` pattern
- Fixtures use docstrings explaining purpose and usage
- Environment variables used for test isolation (e.g., `ADW_TEST_INDEX_PATH`)

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| pytest | latest | Test framework, fixtures |
| ulid | latest | ULID pattern detection |
| subprocess | stdlib | Git command execution |

**Pytest Fixture Best Practices (2025):**
- Use `yield` for teardown (preferred over `addfinalizer`)
- Wrap setup/teardown in `try/finally` for safety
- Keep fixtures limited to one state-changing action
- Use appropriate scopes (function/session) based on resource lifecycle

[Source: pytest documentation - https://docs.pytest.org/en/stable/how-to/fixtures.html]

### File Structure Requirements

**Files to Modify:**

| File | Action | Purpose |
|------|--------|---------|
| `tests/conftest.py` | ADD | Shared `git_repo` fixture with cleanup |
| `tests/conftest.py` | ADD | Session-scoped `cleanup_orphaned_worktrees` |
| `tests/unit/worktree/test_manager.py` | MODIFY | Use shared fixture, remove local fixtures |
| `tests/integration/worktree/test_worktree_cleanup_integration.py` | MODIFY | Use shared fixture |
| `tests/unit/worktree/test_concurrent.py` | MODIFY | Use shared fixture |

**File Naming:** Follow existing convention - fixtures in `conftest.py`

### Testing Requirements

1. **Test the fix:** Create a test that verifies cleanup happens
2. **Failure mode testing:** Ensure cleanup works even when tests fail
3. **No mocking:** This is infrastructure code - test with real git operations
4. **Run full suite:** `pytest tests/` must leave no orphaned worktrees

**Coverage expectation:** >80% for new fixture code

---

## Previous Story Intelligence

Not applicable - this is a bug fix issue, not part of an epic sequence.

---

## Git Intelligence

**Recent Commits:**
- `c861e78` - refactor(template): consolidate template logic (ISS-017)
- `6149275` - fix(ISS-023): Save only last LLM message as output artifact
- `302d1b4` - refactor(epic-16): Remove evidence gathering subsystem (ISS-021)

**Pattern Observed:**
- Commit format: `type(scope): description (issue-ref) (#PR)`
- Types used: `refactor`, `fix`, `docs`
- For this story: `fix(tests): ensure worktree cleanup in test fixtures (ISS-024)`

---

## Latest Technical Information

**Pytest Yield Fixtures (2025 Best Practice):**

```python
@pytest.fixture
def git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create isolated git repository for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, check=True)

    created_worktrees: list[str] = []

    # Inject tracking into tests
    repo._worktrees = created_worktrees  # type: ignore

    try:
        yield repo
    finally:
        # Cleanup all tracked worktrees
        for run_id in created_worktrees:
            worktree_path = repo / "trees" / run_id
            if worktree_path.exists():
                subprocess.run(
                    ["git", "worktree", "remove", str(worktree_path), "--force"],
                    cwd=repo,
                    capture_output=True,
                )
            # Delete branch
            subprocess.run(
                ["git", "branch", "-D", f"adw/{run_id}"],
                cwd=repo,
                capture_output=True,
            )
```

**Session Cleanup Pattern:**

```python
@pytest.fixture(autouse=True, scope="session")
def cleanup_orphaned_worktrees(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Cleanup any orphaned worktrees at session end."""
    yield

    # Scan project root for trees/ directory
    project_root = Path.cwd()
    trees_dir = project_root / "trees"

    if trees_dir.exists():
        for item in trees_dir.iterdir():
            if item.is_dir() and len(item.name) == 26:  # ULID length
                subprocess.run(
                    ["git", "worktree", "remove", str(item), "--force"],
                    capture_output=True,
                )
```

---

## Project Context Reference

See: `/Users/A1E6E98/Developer/Projects/adw/adw-final/_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **Python 3.13+** - Use modern syntax (`X | None`, not `Optional[X]`)
2. **Type annotations required** on all functions
3. **Structured logging** - `logger.info("msg", key=value)` not f-strings
4. **PEP 8 strict** - Functions: `snake_case`, Classes: `PascalCase`
5. **Use uv** for package management (not pip)
6. **Rich for CLI output** - but not needed for test fixtures
7. **Context managers** for resource cleanup - aligns with yield fixtures

---

## Dev Notes

### Root Cause Analysis

The issue stems from test fixtures that create worktrees without systematic cleanup:

1. **Local `git_repo` fixtures** (lines 343-368 in test_manager.py) create git repos but have NO teardown
2. Tests call `manager.create_worktree(run_id)` but only remove if testing the removal function
3. Git branches (`adw/<run_id>`) persist even after tmp_path deletion
4. No session-level hook to catch orphaned worktrees

### Solution Architecture

```
tests/conftest.py
├── git_repo (function-scoped)     # Creates repo, tracks worktrees, cleans on teardown
└── cleanup_orphaned_worktrees     # Session finalizer for safety net
        (session-scoped, autouse)

tests/unit/worktree/test_manager.py
├── TestWorktreeManagerCreation    # Uses shared git_repo
├── TestWorktreeManagerRemoval     # Uses shared git_repo
├── TestWorktreeManagerBranch...   # Uses shared git_repo
└── TestWorktreeForceCleanup       # Uses shared git_repo
```

### Project Structure Notes

- Worktree tests are in `tests/unit/worktree/` and `tests/integration/worktree/`
- Main conftest is at `tests/conftest.py`
- No existing worktree-specific fixtures in conftest
- WorktreeManager lives in `src/adw/worktree/manager.py`

### References

- [Source: tests/conftest.py] - Existing fixture patterns
- [Source: tests/unit/worktree/test_manager.py] - Current local fixtures
- [Source: src/adw/worktree/manager.py] - WorktreeManager implementation
- [Source: docs/architecture/adrs/ADR-001-test-reduction-strategy.md] - Test guidelines
- [Source: _bmad-output/project-context.md] - Project coding standards

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

### File List
