# Story 9.1: Create Feature Branch via Pre-Hook

Status: drafted
Epic: 9 - Git Integration & Documentation
Created: 2026-01-04

---

## Story

As a user,
I want a feature branch created automatically when a run starts,
so that my work is isolated from the main branch.

## Acceptance Criteria

**Given** git integration enabled in project.yaml
**When** run starts
**Then** the bundled pre-hook creates branch `feature/<sanitized-feature-name>`

**Given** feature name "Add user authentication"
**When** branch name is generated
**Then** it becomes `feature/add-user-authentication`

**Given** the branch already exists
**When** pre-hook runs
**Then** it switches to the existing branch instead of failing

**Given** uncommitted changes exist
**When** branch creation is attempted
**Then** HookError is raised with suggestion to commit or stash

**Given** git integration disabled
**When** run starts
**Then** no branch operations occur

## Tasks / Subtasks

- [ ] Create `src/adw/hooks/git_branch.py` module
- [ ] Implement `sanitize_branch_name(feature: str) -> str` function
  - Lowercase, replace spaces with hyphens, remove special chars
  - Max length 50 chars
- [ ] Implement `create_or_switch_branch(branch_name: str) -> None`
  - Check if branch exists: `git branch --list`
  - Create: `git checkout -b <branch>`
  - Switch: `git checkout <branch>`
- [ ] Implement `check_uncommitted_changes() -> bool`
  - Use `git status --porcelain`
- [ ] Add git integration config to project.yaml schema
  - `git.enabled: bool`
  - `git.branch_prefix: str` (default: "feature/")
- [ ] Create bundled pre-hook script `defaults/commands/plan/pre.sh`
- [ ] Write unit tests for branch name sanitization
- [ ] Write integration tests with git repo fixture

---

## Developer Context

### Technical Requirements

- Use `subprocess.run()` for git commands, not gitpython library
- Capture stderr for error messages
- All git operations must be idempotent (safe to run multiple times)

### Architecture Compliance

- Hooks module: `src/adw/hooks/`
- Use `HookError` from exception hierarchy for failures
- No direct CLI output - return results for caller to display

### Library & Framework Requirements

| Library | Usage |
|---------|-------|
| subprocess | Git command execution |
| shlex | Command argument escaping |

### File Structure Requirements

```
src/adw/hooks/
├── __init__.py
├── executor.py      # Existing hook execution
└── git_branch.py    # NEW - branch management

defaults/commands/plan/
└── pre.sh           # NEW - bundled git branch hook
```

### Testing Requirements

- Unit tests: `tests/unit/hooks/test_git_branch.py`
- Integration tests: `tests/integration/test_git_hooks.py`
- Use `tmp_path` fixture for isolated git repos
- Mock subprocess for unit tests

---

## Dependencies

- **Depends on:** None (Wave 1 - can start immediately)
- **Blocks:** 9.2 (Stage and Commit Changes)

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Use Rich for CLI output
- Full type annotations required
- Exception hierarchy for errors
- Context managers for resources

---

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List

