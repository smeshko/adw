# Story 14.3: Git Integration Step (Required)

Status: ready-for-dev
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user in the wizard,
I want to configure git integration,
so that ADW can manage branches and PRs automatically.

## Acceptance Criteria

- [ ] Git integration is **always enabled** (not optional)
- [ ] Checks if current directory is a git repository
- [ ] If NOT a git repo, shows error and guidance to initialize git first
- [ ] If IS a git repo, proceeds with configuration:
  - [ ] "Branch prefix: feature/ [Enter or override]"
  - [ ] "Auto-create PR after successful run? [Y/n]"
- [ ] Validates branch prefix format (no spaces, valid git branch chars)
- [ ] All values stored in wizard state for final generation

## Tasks / Subtasks

### Task 1: Create Git Integration Step Module
- [x] Create `src/adw/cli/wizard/git.py`
- [x] Define `run_git_step(state: WizardState) -> WizardState`
- [x] Import and register in flow controller

### Task 2: Implement Git Repository Requirement
- [x] Check if current directory is a git repository
- [x] Use `git rev-parse --is-inside-work-tree` or check for `.git/`
- [x] If NOT a git repo:
  - Show error: "Git repository required. ADW needs git for branch management."
  - Show guidance: "Run 'git init' to initialize a repository, then re-run the wizard."
  - Exit wizard (git is mandatory)
- [x] If IS a git repo, proceed with configuration

### Task 3: Implement Branch Prefix Validation
- [x] Create validation function for branch prefix
- [x] Rules:
  - No spaces allowed
  - Must end with `/` (auto-append if missing)
  - Valid git branch characters only (alphanumeric, `-`, `_`, `/`)
  - Cannot start with `-`
- [x] Show error and re-prompt on invalid input

### Task 4: Implement Interactive Prompts
- [ ] Git is always enabled (no enable/disable prompt)
- [ ] Prompt for branch prefix with default "feature/"
- [ ] Validate branch prefix (re-prompt if invalid)
- [ ] Prompt for auto-PR creation [Y/n]

### Task 5: Store Results in Wizard State
- [ ] Update WizardState with:
  - `git_enabled: bool` (always True)
  - `git_branch_prefix: str`
  - `git_auto_create_pr: bool`
- [ ] Mark git step as completed

### Task 6: Write Unit Tests
- [ ] Test git repo detection (is a repo)
- [ ] Test git repo detection (not a repo - should error/exit)
- [ ] Test branch prefix validation (valid and invalid cases)
- [ ] Test full prompt flow (branch prefix + auto-PR)
- [ ] Test state update after step completion (git_enabled always True)

---

## Dependencies

### Depends On
- 14.1 (Wizard Entry Point & Flow Control) - provides WizardState and flow controller
- 14.2 (Basics Configuration Step) - runs before this step in wizard flow

### Blocks
- 14.10 (Summary) - displays git configuration

### Parallel With
- 14.4 (Port Configuration Step) - no dependencies
- 14.5 (Task Manager Setup) - no dependencies
- 14.6 (Phase Customization) - no dependencies

---

## Developer Context

### Technical Requirements

**Git is Mandatory:**
- ADW requires git for branch management and worktree isolation
- Wizard cannot proceed without a git repository
- User must initialize git before running the wizard

**Git Repository Detection:**
```python
import subprocess
from rich.console import Console
from rich.panel import Panel

console = Console()

def require_git_repo() -> bool:
    """Require current directory to be inside a git repository.

    Returns True if valid git repo, exits wizard if not.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Not a git repo - show error and exit
    console.print(Panel(
        "[red bold]Git repository required[/]\n\n"
        "ADW needs git for branch management and worktree isolation.\n\n"
        "[dim]To fix:[/]\n"
        "  1. Run [cyan]git init[/] to initialize a repository\n"
        "  2. Re-run [cyan]adw init[/]",
        title="Error",
        border_style="red"
    ))
    raise SystemExit(1)
```

**Branch Prefix Validation Rules:**
- Pattern: `^[a-zA-Z][a-zA-Z0-9_-]*/+$`
- Examples valid: `feature/`, `bugfix/`, `feat/task/`
- Examples invalid: `-feature/`, `my feature/`, `feature` (no trailing /)

### Architecture Compliance

**Layer Boundaries:**
- Wizard step in `src/adw/cli/wizard/git.py`
- Validation can be inline (simple rules)
- Subprocess for git detection is acceptable in CLI layer

**Existing Git Integration:**
- Review existing git hooks at `src/adw/hooks/`
- Config models likely exist at `src/adw/models/config.py`
- Ensure consistency with existing `GitConfig` model

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Rich | Interactive prompts | `from rich.prompt import Prompt, Confirm` |
| subprocess | Git detection | `import subprocess` |
| re | Branch prefix validation | `import re` |

**Validation Pattern:**
```python
import re

BRANCH_PREFIX_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_/-]*/$")

def validate_branch_prefix(prefix: str) -> tuple[bool, str]:
    """Validate branch prefix format.

    Returns:
        (is_valid, error_message)
    """
    if not prefix:
        return False, "Branch prefix cannot be empty"

    # Auto-append trailing slash if missing
    if not prefix.endswith("/"):
        prefix = prefix + "/"

    if " " in prefix:
        return False, "Branch prefix cannot contain spaces"

    if not BRANCH_PREFIX_PATTERN.match(prefix):
        return False, "Invalid branch prefix format. Use alphanumeric, hyphens, underscores, and slashes only."

    return True, prefix  # Return normalized prefix
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
└── git.py                # Git integration step
```

**Files to Modify:**
```
src/adw/cli/wizard/flow.py    # Register git step
src/adw/models/wizard.py      # Add git fields to WizardState
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
└── test_git.py           # Git step tests
```

**Test Cases:**
```python
# Branch prefix validation
def test_valid_branch_prefix():
    assert validate_branch_prefix("feature/") == (True, "feature/")
    assert validate_branch_prefix("feat/task/") == (True, "feat/task/")
    assert validate_branch_prefix("feature") == (True, "feature/")  # Auto-append

def test_invalid_branch_prefix():
    valid, _ = validate_branch_prefix("-invalid/")
    assert not valid

    valid, _ = validate_branch_prefix("my feature/")
    assert not valid

# Git repo requirement
def test_git_repo_exists(mocker):
    # Mock subprocess.run to return success
    # Verify function returns True and continues

def test_git_repo_missing_exits(mocker):
    # Mock subprocess.run to return failure
    # Verify SystemExit is raised

# Full step flow (git is always enabled)
def test_git_step_full_flow(mocker):
    # Mock git repo exists
    # Mock prompts for branch prefix and auto-PR
    # Verify state has git_enabled=True, branch_prefix, auto_create_pr
```

**Mock Requirements:**
- Mock `subprocess.run` for git detection
- Mock Rich prompts for automated testing

---

## Previous Story Intelligence

**From Story 14.1:**
- WizardState model structure
- Flow controller step registration

**From Story 14.2:**
- Prompt patterns established
- State update patterns

---

## Git Intelligence

**Existing Git Config:**
- Check `src/adw/models/config.py` for `GitConfig` model
- Ensure wizard produces compatible configuration

**Search Commands:**
```bash
grep -r "GitConfig" src/
grep -r "branch_prefix" src/
grep -r "auto_create_pr" src/
```

---

## Latest Technical Information

**Git Branch Naming:**
- Git allows most characters in branch names
- Avoid: space, ~, ^, :, ?, *, [, \
- Conventions: use `/` as separator for hierarchies

**Rich Validation Pattern:**
```python
from rich.prompt import Prompt

while True:
    prefix = Prompt.ask(
        "Branch prefix",
        default="feature/"
    )
    valid, result = validate_branch_prefix(prefix)
    if valid:
        branch_prefix = result
        break
    console.print(f"[red]Error:[/] {result}")
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- subprocess with timeout for external commands
- Validation functions return tuple (bool, error_or_result)
- Rich for all user feedback

---

## Dev Notes

- Git integration is **mandatory** - ADW requires git for branch/worktree features
- If not a git repo, wizard exits with clear instructions to initialize git
- Branch prefix validation prevents common mistakes
- Auto-PR feature ties into existing PR creation in Epic 9

### Project Structure Notes

- git.py follows the pattern of other wizard step modules
- Validation could be shared with existing git hooks if similar
- require_git_repo() should be called early in the step (before any prompts)

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.3]
- [Source: _bmad-output/architecture-summary.md#Git-Worktree-Isolation]
- [Source: src/adw/hooks/ - existing git integration]

---

## Dev Agent Record

### Context Reference

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created git.py module with GitStepHandler class, run_git_step function, and placeholder functions for git repo requirement, branch prefix validation, and prompts. Exported from wizard package __init__.py. WizardStep.GIT already defined in flow.py.
- Task 2: Implemented is_git_repo() using subprocess to call `git rev-parse --is-inside-work-tree`. require_git_repo() shows Rich Panel error and exits with SystemExit(1) if not a git repo.
- Task 3: Implemented validate_branch_prefix() with regex pattern. Validates: no spaces, auto-appends trailing /, must start with letter, valid git chars only. Returns (bool, str) tuple.

### File List

- src/adw/cli/wizard/git.py (created)
- src/adw/cli/wizard/__init__.py (modified)

