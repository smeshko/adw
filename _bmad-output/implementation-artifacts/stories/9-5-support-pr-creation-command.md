# Story 9.5: Support PR Creation Command

Status: Ready for Review
Epic: 9 - Git Integration & Documentation
Created: 2026-01-04

---

## Story

As a user,
I want to create a PR directly from the completed run,
so that I can quickly share my work for review.

## Acceptance Criteria

**Given** command `adw pr <run_id>`
**When** run is complete
**Then** it opens PR creation with pre-filled title and description

**Given** GitHub CLI (gh) is available
**When** pr command runs
**Then** it uses `gh pr create` with generated description

**Given** gh is not available
**When** pr command runs
**Then** it outputs the description and instructions for manual PR

**Given** run is not complete
**When** pr command is attempted
**Then** ConfigError is raised with "Run must be complete to create PR"

**Given** pr creation succeeds
**When** complete
**Then** PR URL is displayed and stored in run artifacts

## Tasks / Subtasks

- [x] Create CLI command `adw pr <run_id>` in `src/adw/cli/pr.py`
- [x] Implement `check_gh_available() -> bool`
  - Use `shutil.which("gh")` for detection
- [x] Implement `create_pr_via_gh(title: str, body: str, base: str) -> str`
  - Use `gh pr create --title --body --base`
  - Return PR URL
- [x] Implement `display_manual_instructions(description: str)`
  - Show PR description for copy/paste
  - Show installation instructions for gh CLI
- [x] Add run completion check before PR creation
- [x] Store PR URL in run artifacts when created
- [x] Update run status to include PR link
- [x] Handle authentication errors from gh CLI
- [x] Write unit tests for gh detection
- [x] Write integration tests (with mocked gh)

---

## Developer Context

### Technical Requirements

- Use `shutil.which("gh")` to detect gh CLI
- PR title: feature description from run
- Base branch: from project.yaml or detect default
- Handle gh auth failures with clear message

### Architecture Compliance

- CLI commands in: `src/adw/cli/`
- Use Typer for command definition
- Use Rich for output formatting
- ConfigError for validation failures

### Library & Framework Requirements

| Library | Usage |
|---------|-------|
| Typer | CLI command |
| Rich | Output formatting |
| subprocess | gh CLI execution |
| shutil | which() for gh detection |

### File Structure Requirements

```
src/adw/cli/
├── __init__.py
├── main.py          # Register pr command
└── pr.py            # NEW - PR creation command

.agent/runs/<run_id>/
├── context.json     # Add pr_url field
└── artifacts/document/
    └── pr_description.md  # From 9.4
```

### Testing Requirements

- Unit tests: `tests/unit/cli/test_pr.py`
- Mock subprocess for gh calls
- Test gh not available scenario
- Test run not complete scenario
- Test successful PR creation

---

## Dependencies

- **Depends On:** 9.4 (Generate PR Description)
- **Blocks:** None (final story in epic)
- **Can Parallel With:** None

### Dependency Rationale
- 9.4: Needs the generated PR description artifact for pr create command

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Typer for CLI commands
- Rich for terminal output
- Exception hierarchy for errors

---

## CLI Command Specification

```bash
# Create PR from completed run
adw pr <run_id>

# Options
--base <branch>    # Override base branch (default: main)
--draft            # Create as draft PR
--no-open          # Don't open browser after creation
```

---

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5

### Completion Notes List
- Implemented complete `adw pr` CLI command with Typer
- Added gh CLI detection using `shutil.which("gh")`
- Implemented gh authentication check via `gh auth status`
- Created PR via `gh pr create` with proper error handling
- Added fallback to manual instructions when gh not available
- Stores PR URL in run artifacts under `pr` key
- Comprehensive unit tests (27 tests) covering all functions
- Handles auth errors, timeouts, and no-commits errors gracefully
- Supports `--base`, `--draft`, and `--no-open` options

### File List
- `src/adw/cli/pr.py` (NEW) - PR creation command implementation
- `src/adw/cli/app.py` (MODIFIED) - Registered pr command
- `tests/unit/cli/test_pr.py` (NEW) - Unit and integration tests

