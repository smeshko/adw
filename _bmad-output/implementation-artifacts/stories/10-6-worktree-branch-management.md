# Story 10.6: Worktree Branch Management

Status: Draft
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

- [ ] Create `src/adw/worktree/branch.py` module
- [ ] Implement `WorktreeBranchManager` class:
  - `create_worktree_branch(run_id: str, base_ref: str) -> str`
  - `delete_worktree_branch(run_id: str, force: bool = False) -> None`
  - `branch_exists(run_id: str) -> bool`
  - `get_branch_name(run_id: str) -> str`
- [ ] Define branch naming convention:
  - Pattern: `adw/<run_id>`
  - Example: `adw/01HQXK5P3Z7V8R2M4N6T9W1Y3C`
- [ ] Integrate with worktree creation (Story 10.1):
  - Create branch before worktree add
  - `git branch adw/<run_id> <base_ref>`
  - `git worktree add trees/<run_id> adw/<run_id>`
- [ ] Implement branch cleanup logic:
  - Check if PR exists for branch (optional, via gh CLI)
  - Preserve branch if PR exists
  - Delete branch if `--delete-branch` flag and no PR
  - Default: preserve branch for debugging
- [ ] Add `--delete-branch` flag to cleanup operations:
  - `adw cleanup --delete-branch`
  - Individual run cleanup after failure
- [ ] Track branch status in run context:
  - Add `branch_name: str` to RunContext
  - Add `branch_preserved: bool` after cleanup
- [ ] Handle branch conflict scenarios:
  - Branch already exists: reuse or error?
  - Branch has unpushed commits: warn before delete
- [ ] Write unit tests for branch operations
- [ ] Write integration tests with real git repos

---

## Developer Context

### Technical Requirements

- Use `subprocess.run()` for git commands, consistent with git_branch.py
- Check for unpushed commits before branch deletion
- Handle detached HEAD state gracefully
- Support rebasing worktree branch onto updated base
- Never force-delete branches with unpushed work without explicit flag

### Architecture Compliance

- New file: `src/adw/worktree/branch.py`
- Extend `RunContext` with branch tracking
- Integrate with existing `git_branch.py` utilities if applicable
- Use `GitError` or `WorktreeError` for failures
- Coordinate with Story 9.1 (feature branch) naming

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| subprocess | stdlib | Git command execution |
| re | stdlib | Branch name validation |

### File Structure Requirements

```
src/adw/
├── worktree/
│   ├── __init__.py
│   ├── manager.py          # Worktree lifecycle
│   ├── branch.py           # NEW - branch management
│   ├── ports.py            # Port allocation
│   └── concurrent.py       # Concurrent runs
├── models/
│   └── context.py          # Extend with branch_name
└── hooks/
    └── git_branch.py       # Existing - may share utilities
```

### Testing Requirements

- Unit tests:
  - Branch name generation
  - Branch existence check
  - Cleanup decision logic
- Integration tests:
  - Full worktree + branch lifecycle
  - Branch preservation on PR
  - Force delete with unpushed commits
- Use `tmp_path` fixture for isolated git repos

---

## Dependencies

- **Depends On:** 10.1 (Worktree Creation and Lifecycle)
- **Blocks:** 10.4 (Concurrent Run Management)
- **Can Parallel With:** 10.2 (Directory Structure), 10.3 (Port Allocation)

### Dependency Rationale
- 10.1: Branch management is part of worktree lifecycle
- 10.4: Concurrent management needs branch tracking for run identification

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- subprocess.run() for shell commands
- Full type annotations
- Exception hierarchy for errors
- Structured logging for git operations

---

## Branch Naming Convention

| Component | Format | Example |
|-----------|--------|---------|
| Prefix | `adw/` | `adw/` |
| Run ID | ULID | `01HQXK5P3Z7V8R2M4N6T9W1Y3C` |
| Full Name | `adw/<run_id>` | `adw/01HQXK5P3Z7V8R2M4N6T9W1Y3C` |

**Note:** This is separate from feature branches created by Story 9.1 (`feature/<name>`). The `adw/` branches are internal worktree branches, while `feature/` branches are the user-facing branches for PRs.

---

## Cleanup Decision Matrix

| Run Status | PR Exists | --delete-branch | Branch Action |
|------------|-----------|-----------------|---------------|
| Success | Yes | N/A | Preserve |
| Success | No | No | Preserve |
| Success | No | Yes | Delete |
| Failed | N/A | No | Preserve |
| Failed | N/A | Yes | Delete |
| Aborted | N/A | No | Preserve |
| Aborted | N/A | Yes | Delete |

---

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List
