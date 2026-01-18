# Story 14.8: Security Configuration (Optional)

Status: done
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user in the wizard,
I want to configure security settings,
so that I can control what operations ADW is allowed to perform.

## Acceptance Criteria

- [ ] Prompts "Configure security settings? [y/N]"
- [ ] If No, uses safe defaults (allow_dangerous=false)
- [ ] If Yes:
  - [ ] "Allow dangerous operations (warns instead of blocking)? [y/N]"
  - [ ] Shows warning if Yes: "⚠️ This reduces safety. Only enable if you understand the risks."
  - [ ] "Add blocked command patterns? [y/N]"
  - [ ] If Yes, loop: "Regex pattern (empty to finish): ____"
  - [ ] "Add blocked env file patterns? [y/N]"
  - [ ] If Yes, loop: "File pattern (empty to finish): ____"
- [ ] Validates regex patterns are valid
- [ ] All values stored in wizard state for final generation

## Tasks / Subtasks

### Task 1: Create Security Step Module
- [x] Create `src/adw/cli/wizard/security.py`
- [x] Define `run_security_step(state: WizardState) -> WizardState`
- [x] Import and register in flow controller

### Task 2: Implement Regex Validation
- [x] Create function to validate regex patterns
- [x] Catch `re.error` for invalid patterns
- [x] Return helpful error message for invalid patterns

### Task 3: Implement Dangerous Operations Warning
- [x] Show warning panel when allow_dangerous=True
- [x] Require explicit confirmation
- [x] Display what "dangerous" means in context

### Task 4: Implement Blocked Patterns Loop
- [x] Prompt for adding blocked command patterns
- [x] If Yes, loop for regex patterns until empty input
- [x] Validate each pattern before accepting
- [x] Show examples of valid patterns

### Task 5: Implement Blocked Env Files Loop
- [x] Prompt for adding blocked env file patterns
- [x] If Yes, loop for file patterns (glob-style)
- [x] No validation needed for file patterns (they're globs)
- [x] Show defaults that are always blocked

### Task 6: Store Results in Wizard State
- [x] Update WizardState with:
  - `security_custom: bool`
  - `security_allow_dangerous: bool`
  - `security_blocked_commands: list[str]`
  - `security_blocked_env_files: list[str]`
- [x] Mark security step as completed

### Task 7: Write Unit Tests
- [x] Test regex validation (valid and invalid)
- [x] Test prompt flow with defaults
- [x] Test prompt flow with custom patterns
- [x] Test dangerous operations warning display
- [x] Test state update after step completion

---

## Dependencies

### Depends On
- 14.1 (Wizard Entry Point & Flow Control) - provides WizardState and flow controller
- 14.2 (Basics Configuration Step) - runs before this in wizard flow

### Blocks
- 14.10 (Summary) - displays security configuration

### Parallel With
- 14.7 (LLM Retry Configuration) - no dependencies
- 14.9 (Webhook Server Setup) - no dependencies

---

## Developer Context

### Technical Requirements

**Default Security Settings:**
```python
DEFAULT_SECURITY_CONFIG = {
    "allow_dangerous": False,
    "blocked_command_patterns": [],  # User adds extras, defaults in code
    "blocked_env_files": [],  # User adds extras, defaults in code
}

# These are always blocked (not configurable)
BUILTIN_BLOCKED_COMMANDS = [
    r"rm\s+-rf\s+/",
    r"sudo\s+rm",
    r":\(\)\s*\{\s*:\|\:&\s*\}",  # Fork bomb
]

BUILTIN_BLOCKED_ENV_FILES = [
    ".env",
    ".env.local",
    "*.pem",
    "*.key",
]
```

**Regex Validation:**
```python
import re

def validate_regex(pattern: str) -> tuple[bool, str]:
    """Validate regex pattern is syntactically correct.

    Returns:
        (is_valid, error_message_or_pattern)
    """
    if not pattern.strip():
        return False, "Pattern cannot be empty"

    try:
        re.compile(pattern)
        return True, pattern
    except re.error as e:
        return False, f"Invalid regex: {e}"
```

### Architecture Compliance

**Layer Boundaries:**
- Wizard step in `src/adw/cli/wizard/security.py`
- Security config models in `src/adw/models/config.py`
- Ensure compatibility with existing `SecurityConfig`

**Existing Security Implementation:**
- Check `src/adw/security/` for existing interceptor
- Check `src/adw/models/config.py` for `SecurityConfig`

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Rich | Prompts, warnings | `from rich.prompt import Prompt, Confirm` |
| re | Regex validation | `import re` |

**Warning Panel Pattern:**
```python
from rich.panel import Panel
from rich.console import Console

console = Console()

if allow_dangerous:
    console.print(Panel(
        "[yellow bold]⚠️ WARNING: Reduced Safety Mode[/]\n\n"
        "Enabling this option means:\n"
        "• Dangerous commands will show warnings instead of blocking\n"
        "• You'll be prompted to confirm risky operations\n"
        "• LLM may execute destructive commands with your approval\n\n"
        "[dim]Only enable if you understand the risks.[/]",
        title="Security Warning",
        border_style="yellow"
    ))

    really_sure = Confirm.ask(
        "Are you sure you want to enable dangerous operations?",
        default=False
    )
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
└── security.py           # Security configuration step
```

**Files to Modify:**
```
src/adw/cli/wizard/flow.py    # Register security step
src/adw/models/wizard.py      # Add security fields to WizardState
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
└── test_security.py      # Security step tests
```

**Test Cases:**
```python
# Regex validation
def test_validate_regex_valid():
    assert validate_regex(r"rm\s+-rf")[0] == True
    assert validate_regex(r"sudo\s+.*")[0] == True

def test_validate_regex_invalid():
    assert validate_regex(r"[invalid")[0] == False  # Unclosed bracket
    assert validate_regex(r"*invalid")[0] == False  # Bad quantifier

# Dangerous operations flow
def test_dangerous_operations_declined(mocker):
    # Mock Yes for allow_dangerous, then No for confirmation
    # Verify allow_dangerous stays False

def test_dangerous_operations_confirmed(mocker):
    # Mock Yes for both prompts
    # Verify allow_dangerous is True

# Pattern loops
def test_blocked_commands_loop(mocker):
    # Mock inputs: "rm.*", "sudo.*", "" (empty to finish)
    # Verify both patterns stored

def test_blocked_env_files_loop(mocker):
    # Mock inputs: ".secrets", "" (empty to finish)
    # Verify pattern stored
```

**Mock Requirements:**
- Mock Rich prompts
- No external dependencies to mock

---

## Previous Story Intelligence

**From Stories 14.1-14.7:**
- WizardState model structure
- Loop patterns for collecting multiple inputs
- Warning panel display pattern

**Expected State Structure:**
```python
# WizardState additions
security_custom: bool = False
security_allow_dangerous: bool = False
security_blocked_commands: list[str] = []
security_blocked_env_files: list[str] = []
```

---

## Git Intelligence

**Existing Security Implementation:**
- Check `src/adw/security/interceptor.py` for command interception
- Check `src/adw/security/patterns.py` for default patterns

**Search Commands:**
```bash
grep -r "SecurityConfig" src/
grep -r "allow_dangerous" src/
grep -r "blocked_command" src/
```

---

## Latest Technical Information

**ADW Security Features:**
- Command pattern matching before execution
- User confirmation for dangerous operations
- Env file protection (prevent committing secrets)
- Audit logging of security events

**Common Dangerous Patterns:**
| Pattern | Description |
|---------|-------------|
| `rm -rf /` | Delete everything |
| `sudo rm` | Delete with elevated privileges |
| `dd if=.* of=/dev/` | Direct disk writes |
| `curl.*\|.*sh` | Execute remote scripts |
| `chmod -R 777` | Insecure permissions |

**Common Blocked Env Files:**
| Pattern | Description |
|---------|-------------|
| `.env*` | Environment files |
| `*.pem` | SSL certificates |
| `*.key` | Private keys |
| `credentials.*` | Credential files |
| `secrets.*` | Secret files |

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- Security layer in `src/adw/security/`
- Config models in `src/adw/models/`
- Rich for all user feedback

---

## Dev Notes

- Security defaults are intentionally safe
- Warning panel is important for dangerous operations
- Users rarely need custom patterns - defaults cover most cases
- Regex validation prevents broken configs

### Prompt Flow Diagram
```
Configure security? [y/N]
├── No → Use safe defaults, DONE
└── Yes
    ├── Allow dangerous operations? [y/N]
    │   └── Yes → Show warning panel
    │       └── Really sure? [y/N]
    ├── Add blocked command patterns? [y/N]
    │   └── Yes → Regex loop until empty
    └── Add blocked env file patterns? [y/N]
        └── Yes → Pattern loop until empty
```

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.8]
- [Source: _bmad-output/architecture-summary.md#Security-First]
- [Source: src/adw/security/ - security implementation]

---

## Dev Agent Record

### Context Reference

- Reviewed existing wizard patterns from ports.py, flow.py
- Referenced SecurityConfig model from src/adw/models/security.py
- Followed test patterns from test_ports.py

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Implemented SecurityStepHandler and run_security_step following wizard patterns
- Created validate_regex function for command pattern validation
- Implemented dangerous operations warning with double confirmation
- Created pattern loops for both command and env file patterns
- Added comprehensive test coverage (27 tests)
- Registered module in wizard __init__.py

### File List

- src/adw/cli/wizard/security.py (new)
- src/adw/cli/wizard/__init__.py (modified)
- tests/unit/cli/wizard/test_security.py (new)

