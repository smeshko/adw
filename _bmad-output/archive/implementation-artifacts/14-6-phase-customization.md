# Story 14.6: Phase Customization (Optional, Full)

Status: Done
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user in the wizard,
I want to customize individual phase settings,
so that I can tune timeouts, hooks, and inputs for my workflow.

## Acceptance Criteria

- [ ] Prompts "Customize phase settings? [y/N]"
- [ ] If No, uses all defaults
- [ ] If Yes:
  - [ ] "Which phases to customize?" [multi-select checklist]
  - [ ] Options: plan, build, validate, document
  - [ ] For each selected phase:
    - [ ] "─── {PHASE} Phase ───"
    - [ ] "Enabled? [Y/n]"
    - [ ] "Timeout (seconds): {default} [Enter or override]"
    - [ ] "Pre-hook script path: [none]"
    - [ ] "Post-hook script path: [none]"
    - [ ] "Add input files? [y/N]"
    - [ ] If Yes, loop: "key=path (empty to finish): ____"
  - [ ] **IF validate phase selected**, additional prompts:
    - [ ] "Enable code review? [Y/n]"
    - [ ] "Enable tests? [Y/n]"
    - [ ] "Test timeout (seconds): 300 [Enter or override]"
    - [ ] "Max validation iterations: 5 [Enter or override]"
    - [ ] "Triage mode: [auto] / manual / hybrid"
    - [ ] "Review focus areas? [multi-select: security, error_handling, edge_cases]"
- [ ] All values stored in wizard state for final generation

## Tasks / Subtasks

### Task 1: Create Phase Customization Step Module
- [x] Create `src/adw/cli/wizard/phases.py`
- [x] Define `run_phases_step(state: WizardState) -> WizardState`
- [x] Import and register in flow controller

### Task 2: Implement Multi-Select Phase Picker
- [x] Create multi-select prompt for phases
- [x] Options: plan, build, validate, document
- [x] Return list of selected phases

### Task 3: Implement Base Phase Configuration
- [x] For each selected phase:
  - Prompt for enabled (default Yes)
  - Prompt for timeout with language-aware default
  - Prompt for pre-hook path (optional)
  - Prompt for post-hook path (optional)
  - Prompt for input files (key=path loop)

### Task 4: Implement Validate Phase Special Options
- [x] Detect when validate phase is selected
- [x] Add additional prompts:
  - code_review enabled
  - tests enabled
  - test timeout
  - max iterations
  - triage mode selection
  - review focus areas (multi-select)

### Task 5: Implement Input File Loop
- [x] Prompt for key=path pairs
- [x] Continue until empty input
- [x] Validate path format (relative or absolute)
- [x] Store as dictionary

### Task 6: Store Results in Wizard State
- [x] Update WizardState with phase configurations
- [x] Structure: phases dict with phase name keys
- [x] Mark phases step as completed

### Task 7: Write Unit Tests
- [x] Test multi-select phase picker
- [x] Test base phase configuration flow
- [x] Test validate phase special options
- [x] Test input file loop
- [x] Test state update after step completion

---

## Dependencies

### Depends On
- 14.1 (Wizard Entry Point & Flow Control) - provides WizardState and flow controller
- 14.2 (Basics Configuration Step) - language may affect timeout defaults

### Blocks
- 14.10 (Summary) - displays phase configuration

### Parallel With
- 14.3 (Git Integration Step) - no dependencies
- 14.4 (Port Configuration Step) - no dependencies
- 14.5 (Task Manager Setup) - no dependencies

---

## Developer Context

### Technical Requirements

**Default Timeouts by Phase:**
```python
DEFAULT_TIMEOUTS = {
    "plan": 300,      # 5 minutes
    "build": 600,     # 10 minutes
    "validate": 900,  # 15 minutes
    "document": 300,  # 5 minutes
}
```

**Multi-Select Implementation:**
```python
from rich.prompt import Prompt

# Rich doesn't have built-in multi-select, use checkbox style
phases = ["plan", "build", "validate", "document"]
selected = []

for phase in phases:
    if Confirm.ask(f"Customize [cyan]{phase}[/] phase?", default=False):
        selected.append(phase)
```

**Or use inquirer/questionary library for true multi-select:**
```python
# Alternative: use questionary for better UX
import questionary

selected = questionary.checkbox(
    "Which phases to customize?",
    choices=["plan", "build", "validate", "document"]
).ask()
```

### Architecture Compliance

**Layer Boundaries:**
- Wizard step in `src/adw/cli/wizard/phases.py`
- Phase config models in `src/adw/models/config.py`
- Ensure compatibility with existing `PhaseConfig` model

**Existing Phase Configuration:**
- Check `src/adw/models/config.py` for `PhaseConfig`
- Check `src/adw/core/` for phase execution logic
- Ensure wizard produces compatible configuration

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Rich | Prompts, panels | `from rich.prompt import Prompt, Confirm` |
| questionary (optional) | Multi-select | `import questionary` |

**Note:** If adding questionary, add to dependencies in pyproject.toml

**Phase Header Display:**
```python
from rich.console import Console
from rich.rule import Rule

console = Console()

console.print(Rule(f"[bold cyan]{phase.upper()}[/] Phase", style="cyan"))
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
└── phases.py             # Phase customization step
```

**Files to Modify:**
```
src/adw/cli/wizard/flow.py    # Register phases step
src/adw/models/wizard.py      # Add phase config to WizardState
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
└── test_phases.py        # Phase step tests
```

**Test Cases:**
```python
# Multi-select
def test_phase_selection_none(mocker):
    # All Confirm.ask return False
    # Verify no phases customized

def test_phase_selection_all(mocker):
    # All Confirm.ask return True
    # Verify all phases in selection

# Base phase config
def test_phase_config_defaults(mocker):
    # Accept all defaults
    # Verify timeout, hooks, inputs are default values

def test_phase_config_custom(mocker):
    # Override values
    # Verify custom values stored

# Validate special options
def test_validate_phase_special_options(mocker):
    # Select validate phase
    # Verify code_review, tests, iterations prompts shown

# Input file loop
def test_input_file_loop(mocker):
    # Mock multiple inputs then empty
    # Verify all key=path pairs stored
```

**Mock Requirements:**
- Mock Rich/questionary prompts
- No external dependencies to mock

---

## Previous Story Intelligence

**From Stories 14.1-14.5:**
- WizardState model structure
- Validation and loop patterns
- Conditional prompt handling

**Expected State Structure:**
```python
# WizardState additions for phases
phases_customized: bool
phase_configs: dict[str, PhaseWizardConfig]

@dataclass
class PhaseWizardConfig:
    enabled: bool = True
    timeout: int = 300
    pre_hook: str | None = None
    post_hook: str | None = None
    input_files: dict[str, str] = field(default_factory=dict)
    # Validate-specific
    code_review: bool = True
    tests: bool = True
    test_timeout: int = 300
    max_iterations: int = 5
    triage_mode: str = "auto"
    review_focus: list[str] = field(default_factory=list)
```

---

## Git Intelligence

**Existing Phase Config:**
- Check `src/adw/models/config.py` for `PhaseConfig`
- Check `src/adw/core/orchestrator.py` for phase execution

**Search Commands:**
```bash
grep -r "PhaseConfig" src/
grep -r "pre_hook\|post_hook" src/
grep -r "input_files" src/
```

---

## Latest Technical Information

**ADW Phase Pipeline:**
- plan → build → validate → document
- Each phase can be enabled/disabled
- Validate phase has special sub-operations:
  - Code review (via Codex or similar)
  - Test execution
  - Iterative fix loop

**Triage Modes:**
- `auto`: AI decides which issues to fix
- `manual`: User approves each fix
- `hybrid`: AI proposes, user confirms batches

**Review Focus Areas:**
- `security`: Check for security vulnerabilities
- `error_handling`: Check error paths
- `edge_cases`: Check boundary conditions
- `performance`: Check efficiency (optional)

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- Config models in `src/adw/models/`
- Phase execution in `src/adw/core/`
- Hooks in `src/adw/hooks/`

---

## Dev Notes

- This is the most complex step due to nested loops and conditionals
- Consider breaking into sub-functions for each phase
- Multi-select UX is important - consider questionary for better experience
- Validate phase has extra options that only appear when validate is selected

### Prompt Flow Diagram
```
Customize phases? [y/N]
├── No → Use all defaults, DONE
└── Yes
    ├── Select phases to customize (multi-select)
    └── For each selected phase:
        ├── "─── PHASE Phase ───"
        ├── Enabled? [Y/n]
        ├── Timeout: {default}
        ├── Pre-hook: [none]
        ├── Post-hook: [none]
        ├── Add input files? [y/N]
        │   └── Yes → key=path loop
        └── IF VALIDATE:
            ├── Code review? [Y/n]
            ├── Tests? [Y/n]
            ├── Test timeout: 300
            ├── Max iterations: 5
            ├── Triage mode: [auto/manual/hybrid]
            └── Review focus: [multi-select]
```

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.6]
- [Source: _bmad-output/architecture-summary.md#Phase-Based-Pipeline]
- [Source: src/adw/core/orchestrator.py - phase execution]

---

## Dev Agent Record

### Context Reference

- Project Context: `_bmad-output/project-context.md`
- ADR-001 Test Strategy: `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - Clean implementation

### Completion Notes List

- Implemented phases customization wizard step with full interactive flow
- Created multi-select phase picker using Rich Confirm prompts
- Implemented base phase configuration (enabled, timeout, hooks, input files)
- Added validate phase special options (code review, tests, triage mode, review focus)
- Input file loop validates key=path format and handles invalid entries
- 32 unit tests with 100% coverage of phases.py
- All 124 wizard tests pass

### File List

**New Files:**
- `src/adw/cli/wizard/phases.py` - Phase customization step implementation
- `tests/unit/cli/wizard/test_phases.py` - Comprehensive unit tests

**Modified Files:**
- `src/adw/cli/wizard/__init__.py` - Export PhasesStepHandler and run_phases_step
- `_bmad-output/implementation-artifacts/14-6-phase-customization.md` - Task completion

