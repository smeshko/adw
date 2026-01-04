# Story 9.2: Stage and Commit Changes via Post-Hook

Status: Ready for Review
Epic: 9 - Git Integration & Documentation
Created: 2026-01-04

---

## Story

As a user,
I want changes automatically staged and committed after each phase,
so that my work is preserved incrementally.

## Acceptance Criteria

**Given** Build phase completes successfully
**When** post-hook runs
**Then** changed files are staged and committed with message "[adw] Build: <feature>"

**Given** commit message template
**When** generating
**Then** it includes: phase name, feature description, run_id reference

**Given** no changes to commit
**When** post-hook runs
**Then** commit is skipped silently (not an error)

**Given** commit fails (e.g., pre-commit hook rejects)
**When** post-hook runs
**Then** HookError is raised with the failure details

**Given** auto-commit disabled in project.yaml
**When** phase completes
**Then** no commit is made

## Tasks / Subtasks

- [x] Create `src/adw/hooks/git_commit.py` module
- [x] Implement `stage_changes() -> list[str]`
  - Use `git add -A`
  - Return list of staged files
- [x] Implement `has_staged_changes() -> bool`
  - Use `git diff --cached --quiet`
- [x] Implement `create_commit(phase: str, feature: str, run_id: str) -> str | None`
  - Format message: `[adw] {Phase}: {feature}\n\nRun: {run_id}`
  - Return commit SHA or None if no changes
- [x] Add commit config to project.yaml schema
  - `git.auto_commit: bool` (default: true)
  - `git.commit_template: str` (optional override)
- [x] Create bundled post-hook script `defaults/commands/build/post.sh`
- [x] Handle pre-commit hook failures gracefully
- [x] Write unit tests for commit message formatting
- [x] Write integration tests with git repo fixture

---

## Developer Context

### Technical Requirements

- Commit messages must be UTF-8 encoded
- Handle special characters in feature descriptions
- Pre-commit hooks may modify files - re-stage if needed
- Use `--no-verify` only if explicitly configured

### Architecture Compliance

- Hooks module: `src/adw/hooks/`
- Use `HookError` from exception hierarchy
- Commit info stored in RunContext for audit

### Library & Framework Requirements

| Library | Usage |
|---------|-------|
| subprocess | Git command execution |

### File Structure Requirements

```
src/adw/hooks/
├── __init__.py
├── executor.py      # Existing
├── git_branch.py    # From 9.1
└── git_commit.py    # NEW

defaults/commands/build/
└── post.sh          # NEW - bundled commit hook
```

### Testing Requirements

- Unit tests: `tests/unit/hooks/test_git_commit.py`
- Integration tests: `tests/integration/test_git_hooks.py`
- Test with mock pre-commit hooks that reject/modify
- Test empty commit scenario

---

## Dependencies

- **Depends On:** 9.1 (Create Feature Branch)
- **Blocks:** 9.4 (Generate PR Description)
- **Can Parallel With:** None

### Dependency Rationale
- 9.1: Commits must go to the feature branch created by 9.1
- 9.4: PR description needs commit history from this story

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Use Rich for CLI output
- Full type annotations required
- Exception hierarchy for errors

---

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Completion Notes List
- Created git_commit.py module with stage_changes(), has_staged_changes(), create_commit(), format_commit_message() functions
- All functions use subprocess.run() following existing git_branch.py patterns
- Implemented HookError handling for all git command failures
- Supports custom commit message templates via optional template parameter
- Unit tests cover all functions including edge cases

### File List
- src/adw/hooks/git_commit.py (NEW)
- src/adw/hooks/__init__.py (MODIFIED - added exports)
- src/adw/models/config.py (MODIFIED - added auto_commit, commit_template to GitConfig)
- src/adw/defaults/commands/build/post.sh (NEW)
- tests/unit/hooks/test_git_commit.py (NEW)
- tests/unit/models/test_config.py (MODIFIED - added GitConfig commit tests)
- tests/integration/test_git_hooks.py (MODIFIED - added git commit integration tests)

