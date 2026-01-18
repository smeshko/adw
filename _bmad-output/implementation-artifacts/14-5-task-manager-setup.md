# Story 14.5: Task Manager Setup (Optional, Full)

Status: ready-for-dev
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user in the wizard,
I want to configure task manager integration,
so that ADW syncs with my project management tool.

## Acceptance Criteria

- [ ] Prompts "Set up task manager integration? [y/N]"
- [ ] If No, task_manager.type remains "none"
- [ ] If Yes:
  - [ ] "Task manager: [Linear]" (Linear only for MVP, extensible)
  - [ ] "Team key (e.g., 'RULE' for RULE-123): ____"
  - [ ] Validates team key format (uppercase letters)
  - [ ] "Sync comments on status changes? [y/N]"
  - [ ] If sync_comments=Yes: "Comment on failures only? [y/N]"
  - [ ] "PR title format: {task_id}: {description} [Enter or override]"
  - [ ] "Enable label management? [Y/n]"
  - [ ] If labels enabled: "Label prefix: adw: [Enter or override]"
  - [ ] "Auto-close task when PR merged? [y/N]"
  - [ ] "Include task labels in context? [Y/n]"
  - [ ] "Include parent task info? [Y/n]"
  - [ ] "Configure state mapping? [y/N]"
  - [ ] If Yes, for each state (plan, build, validate, document, failed):
    - [ ] "{phase} → {default} [Enter or override]"
- [ ] All values stored in wizard state for final generation

## Tasks / Subtasks

### Task 1: Create Task Manager Step Module
- [ ] Create `src/adw/cli/wizard/task_manager.py`
- [ ] Define `run_task_manager_step(state: WizardState) -> WizardState`
- [ ] Import and register in flow controller

### Task 2: Implement Team Key Validation
- [ ] Create validation function for team key
- [ ] Rules: uppercase letters only, 2-10 characters
- [ ] Examples: "RULE", "ENG", "ADW"
- [ ] Show error and re-prompt on invalid input

### Task 3: Implement Basic Configuration Prompts
- [ ] Prompt for task manager enable/disable (default No)
- [ ] If enabled:
  - Show task manager selection (Linear for now)
  - Prompt for team key with validation
  - Prompt for sync_comments option
  - Conditional: comment_on_failures_only

### Task 4: Implement PR and Label Configuration
- [ ] Prompt for PR title format
- [ ] Prompt for label management enable
- [ ] Conditional: label prefix prompt
- [ ] Prompt for auto-close option

### Task 5: Implement Context Options
- [ ] Prompt for include_labels_in_context
- [ ] Prompt for include_parent_info

### Task 6: Implement State Mapping Configuration
- [ ] Prompt for custom state mapping
- [ ] If Yes, prompt for each phase:
  - plan → (default: "In Progress")
  - build → (default: "In Progress")
  - validate → (default: "In Review")
  - document → (default: "In Review")
  - failed → (default: "Backlog")
- [ ] Store mappings in wizard state

### Task 7: Store Results in Wizard State
- [ ] Update WizardState with full task_manager config
- [ ] Mark task_manager step as completed

### Task 8: Write Unit Tests
- [ ] Test team key validation
- [ ] Test prompt flow when task manager disabled
- [ ] Test prompt flow with all options enabled
- [ ] Test state mapping configuration
- [ ] Test state update after step completion

---

## Dependencies

### Depends On
- 14.1 (Wizard Entry Point & Flow Control) - provides WizardState and flow controller
- 14.2 (Basics Configuration Step) - runs before this in wizard flow

### Blocks
- 14.10 (Summary) - displays task manager configuration

### Parallel With
- 14.3 (Git Integration Step) - no dependencies
- 14.4 (Port Configuration Step) - no dependencies
- 14.6 (Phase Customization) - no dependencies

---

## Developer Context

### Technical Requirements

**Team Key Validation:**
```python
import re

TEAM_KEY_PATTERN = re.compile(r"^[A-Z]{2,10}$")

def validate_team_key(key: str) -> tuple[bool, str]:
    """Validate Linear team key format.

    Returns:
        (is_valid, error_message_or_normalized_key)
    """
    key = key.strip().upper()

    if not key:
        return False, "Team key cannot be empty"

    if not TEAM_KEY_PATTERN.match(key):
        return False, "Team key must be 2-10 uppercase letters (e.g., 'RULE', 'ENG')"

    return True, key
```

**Default State Mappings:**
```python
DEFAULT_STATE_MAPPINGS = {
    "plan": "In Progress",
    "build": "In Progress",
    "validate": "In Review",
    "document": "In Review",
    "failed": "Backlog",
}
```

### Architecture Compliance

**Layer Boundaries:**
- Wizard step in `src/adw/cli/wizard/task_manager.py`
- Task manager models in `src/adw/models/task_manager.py`
- Ensure compatibility with existing `TaskManagerConfig` model

**Existing Task Manager Integration:**
- Check `src/adw/task_managers/` for existing implementations
- Check `src/adw/models/config.py` for `TaskManagerConfig`
- Ensure wizard produces compatible configuration

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Rich | Prompts and formatting | `from rich.prompt import Prompt, Confirm` |
| re | Team key validation | `import re` |

**Nested Prompt Pattern:**
```python
# This step has nested conditional prompts
sync_comments = Confirm.ask("Sync comments on status changes?", default=False)

if sync_comments:
    comment_failures_only = Confirm.ask(
        "Comment on failures only?",
        default=False
    )
else:
    comment_failures_only = False
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
└── task_manager.py       # Task manager configuration step
```

**Files to Modify:**
```
src/adw/cli/wizard/flow.py    # Register task_manager step
src/adw/models/wizard.py      # Add task_manager fields to WizardState
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
└── test_task_manager.py  # Task manager step tests
```

**Test Cases:**
```python
# Team key validation
def test_valid_team_key():
    assert validate_team_key("RULE") == (True, "RULE")
    assert validate_team_key("eng") == (True, "ENG")  # Auto-uppercase
    assert validate_team_key("AB") == (True, "AB")

def test_invalid_team_key():
    assert validate_team_key("R")[0] == False  # Too short
    assert validate_team_key("TOOLONGTEAMKEY")[0] == False  # Too long
    assert validate_team_key("rule-123")[0] == False  # Invalid chars

# Full step flow
def test_task_manager_disabled(mocker):
    # Mock No response
    # Verify task_manager.type = "none"

def test_task_manager_full_config(mocker):
    # Mock all prompts with various responses
    # Verify all state fields populated correctly
```

**Mock Requirements:**
- Mock Rich prompts for all variations
- No external service calls to mock

---

## Previous Story Intelligence

**From Stories 14.1-14.4:**
- WizardState model structure
- Validation loop patterns
- Nested conditional prompt patterns

**Expected State Structure:**
```python
# WizardState additions
task_manager_enabled: bool
task_manager_type: str  # "none" or "linear"
task_manager_team_key: str | None
task_manager_sync_comments: bool
task_manager_comment_failures_only: bool
task_manager_pr_title_format: str
task_manager_label_enabled: bool
task_manager_label_prefix: str | None
task_manager_auto_close: bool
task_manager_include_labels: bool
task_manager_include_parent: bool
task_manager_state_mapping: dict[str, str] | None
```

---

## Git Intelligence

**Existing Task Manager Config:**
- Check `src/adw/models/config.py` for `TaskManagerConfig`
- Check `src/adw/task_managers/linear.py` for Linear implementation

**Search Commands:**
```bash
grep -r "TaskManagerConfig" src/
grep -r "team_key\|team_id" src/
grep -r "state_mapping" src/
```

---

## Latest Technical Information

**Linear API:**
- Team keys are used as issue prefixes (e.g., "RULE-123")
- Status mapping maps ADW phases to Linear workflow states
- Label management allows ADW to add/remove labels

**ADW Task Manager Features:**
- Status sync at phase transitions
- Comment posting on events
- Label management
- Issue context injection into prompts

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- Validation functions return (bool, result_or_error)
- Rich for all user feedback
- Config models in `src/adw/models/`

---

## Dev Notes

- This is the most complex wizard step due to many options
- Consider grouping related options with Rich panels/headers
- State mapping is optional - most users will use defaults
- Future: add GitHub Issues, Jira support with similar structure

### Prompt Flow Diagram
```
Enable task manager? [y/N]
├── No → task_manager.type = "none", DONE
└── Yes → task_manager.type = "linear"
    ├── Team key → validate
    ├── Sync comments? [y/N]
    │   └── Yes → Comment failures only? [y/N]
    ├── PR title format
    ├── Enable labels? [Y/n]
    │   └── Yes → Label prefix
    ├── Auto-close? [y/N]
    ├── Include labels in context? [Y/n]
    ├── Include parent info? [Y/n]
    └── Configure state mapping? [y/N]
        └── Yes → For each phase...
```

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.5]
- [Source: _bmad-output/architecture-summary.md#Integration-Points]
- [Source: src/adw/task_managers/ - existing implementations]

---

## Dev Agent Record

### Context Reference

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

