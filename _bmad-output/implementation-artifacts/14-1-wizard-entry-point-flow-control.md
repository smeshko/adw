# Story 14.1: Wizard Entry Point & Flow Control

Status: ready-for-dev
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user running `adw init`,
I want to choose between guided setup and minimal setup,
so that I can get the level of configuration help I need.

## Acceptance Criteria

- [ ] `adw init` prompts "Would you like guided setup? [Y/n]"
- [ ] Answering No creates minimal config (language + name only)
- [ ] Answering Yes enters wizard flow
- [ ] `--no-interactive` flag skips prompt, uses minimal setup
- [ ] `--wizard` flag skips prompt, enters wizard directly
- [ ] Detects existing `.adw/` directory
- [ ] Shows warning: "Existing configuration found. This will overwrite all settings."
- [ ] Requires explicit confirmation to proceed with overwrite
- [ ] Wizard state tracks completed steps for back/forward navigation
- [ ] Ctrl+C at any point shows "Setup cancelled. No files created."

## Tasks / Subtasks

### Task 1: Create Wizard Package Structure
- [ ] Create `src/adw/cli/wizard/` package directory
- [ ] Create `__init__.py` with package exports
- [ ] Create `flow.py` for wizard flow controller

### Task 2: Implement WizardState Model
- [ ] Add `WizardState` Pydantic model to `src/adw/models/`
- [ ] Include fields: current_step, completed_steps, collected_config
- [ ] Include methods: mark_completed, can_go_back, can_go_forward
- [ ] Support for navigation history

### Task 3: Modify `init.py` Entry Point
- [ ] Add `--wizard` flag to force wizard mode
- [ ] Add `--no-interactive` flag to skip wizard
- [ ] Check for existing `.adw/` directory
- [ ] Show Rich confirmation panel for overwrite
- [ ] Prompt for guided vs minimal setup choice

### Task 4: Implement Flow Controller
- [ ] Create `WizardFlowController` class in `flow.py`
- [ ] Define step sequence enum/list
- [ ] Implement `run()` method for sequential step execution
- [ ] Implement signal handler for Ctrl+C cleanup
- [ ] Support step navigation (back/forward) when enabled

### Task 5: Implement Minimal Setup Path
- [ ] Auto-detect language from project markers
- [ ] Prompt for confirmation of detected language
- [ ] Generate minimal `project.yaml` with defaults
- [ ] Create `.adw/` directory structure

### Task 6: Add Interrupt Handler
- [ ] Register signal handler for SIGINT (Ctrl+C)
- [ ] On interrupt: display "Setup cancelled. No files created."
- [ ] Ensure no partial config files are left
- [ ] Clean up any temporary state

### Task 7: Write Unit Tests
- [ ] Test `--wizard` flag forces wizard mode
- [ ] Test `--no-interactive` flag skips wizard
- [ ] Test existing config detection and warning
- [ ] Test Ctrl+C cleanup (using signal mocking)
- [ ] Test WizardState navigation methods

---

## Dependencies

### Depends On
- None (Wave 1 - Foundation story)

### Blocks
- 14.2 (Basics Configuration Step) - needs flow controller
- 14.3 through 14.9 - all wizard steps use flow controller
- 14.10 (Summary) - aggregates state from all steps

### Parallel With
- 14.2 (Basics Configuration Step) - can be developed in parallel if interface is defined first

---

## Developer Context

### Technical Requirements

**Wizard Flow Controller Requirements:**
- Must support sequential step execution
- Must track completed steps for navigation
- Must collect configuration progressively
- Must handle interruption gracefully
- Must support both interactive and non-interactive modes

**CLI Flag Requirements:**
- `--wizard` / `-w`: Force wizard mode, skip initial prompt
- `--no-interactive` / `-n`: Force minimal mode, no prompts
- Flags are mutually exclusive

### Architecture Compliance

**Layer Boundaries:**
- CLI layer (`src/adw/cli/init.py`): Entry point, flag parsing, user prompts
- Wizard package (`src/adw/cli/wizard/`): Flow control, step coordination
- Models layer (`src/adw/models/`): WizardState model

**Existing Patterns to Follow:**
- Use Rich for all prompts (Confirm, Prompt, Panel)
- Use Typer for CLI flags and commands
- Follow existing config loading patterns from `src/adw/core/config/`

**File Creation Rules:**
- Create `.adw/` directory only at final step (14.10)
- No partial files on interrupt
- Use context managers for file operations

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Typer | CLI flags and app | `import typer` |
| Rich | Prompts, panels, formatting | `from rich.prompt import Confirm` |
| Pydantic | WizardState model | `from pydantic import BaseModel` |
| signal | Interrupt handling | `import signal` |

**Rich Prompt Patterns:**
```python
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.console import Console

console = Console()

# Confirmation prompt
proceed = Confirm.ask("Would you like guided setup?", default=True)

# Warning panel
console.print(Panel(
    "[yellow]⚠️ Existing configuration found.[/]\n"
    "This will overwrite all settings.",
    title="Warning",
    border_style="yellow"
))
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
├── __init__.py           # Package exports
├── flow.py               # WizardFlowController class

src/adw/models/
└── wizard.py             # WizardState model (or add to existing models)
```

**Files to Modify:**
```
src/adw/cli/init.py       # Add --wizard, --no-interactive flags
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
├── test_flow.py          # Flow controller tests
└── test_state.py         # WizardState model tests

tests/unit/cli/
└── test_init.py          # Updated init command tests
```

**Test Coverage:**
- 80%+ coverage for new code
- Test all flag combinations
- Test interrupt handling with signal mocking
- Test existing config detection

**Mock Requirements:**
- Mock `Path.exists()` for config detection
- Mock `signal.signal()` for interrupt testing
- Mock Rich prompts for non-interactive testing

---

## Previous Story Intelligence

This is the first story in Epic 14. No previous story learnings available.

**Related Implementation Context:**
- The existing `init.py` command at `src/adw/cli/init.py` implements minimal initialization
- Review this file to understand current patterns before modifying

---

## Git Intelligence

**Recent Patterns from Epic 13:**
- Webhook infrastructure added modular provider system
- Good example of plugin-like architecture that wizard steps can follow
- Clean separation between protocol and implementation

**File Organization Conventions:**
- Packages have `__init__.py` with public exports
- Implementation in separate module files
- Tests mirror source structure

---

## Latest Technical Information

**Rich Library (v14.1.0+):**
- Use `Confirm.ask()` for yes/no prompts
- Use `Prompt.ask()` for text input with choices
- Use `Panel()` for warning/info boxes
- Console markup: `[bold]`, `[green]`, `[yellow]`, etc.

**Signal Handling in Python:**
```python
import signal

def cleanup_handler(signum, frame):
    console.print("[yellow]Setup cancelled. No files created.[/]")
    raise SystemExit(0)

signal.signal(signal.SIGINT, cleanup_handler)
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models in `src/adw/models/`
- Rich for all CLI output (no print())
- Full type annotations required
- PEP 8 naming: snake_case for functions/variables, PascalCase for classes
- Exception hierarchy from `src/adw/exceptions.py`

---

## Dev Notes

- The wizard is conceptually a step-by-step state machine
- Each wizard step (14.2-14.9) will be a separate module that `flow.py` coordinates
- WizardState should be serializable in case we add "resume wizard" feature later
- Consider using an enum for step names to prevent typos

### Project Structure Notes

- Wizard package lives under `cli/` since it's UI-focused
- WizardState model goes in `models/` per architecture rules
- Flow controller is the orchestrator for all wizard steps

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.1]
- [Source: _bmad-output/project-context.md#Critical-Implementation-Rules]
- [Source: _bmad-output/architecture-summary.md#Presentation-Layer]

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

