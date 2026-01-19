# Story 15.8: Init Wizard Ship Phase Integration

Status: ready-for-dev
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-19

---

## Story

As a user running `adw init` with the wizard,
I want to configure ship phase settings during setup,
so that deployment commands and PR merge behavior are ready from the start.

## Acceptance Criteria

### AC1: Wizard Step Addition
- [ ] **Given** the init wizard flow (Epic 14 implemented)
  **When** ship phase step is added
  **Then** it appears after Phase Customization (Step 5) as a new optional step

- [ ] **Given** user reaches ship phase step
  **When** prompted
  **Then** wizard asks: "Configure ship phase settings? [y/N]"

- [ ] **Given** user selects No
  **When** wizard continues
  **Then** ship phase uses defaults (no commands, merge_on_success=False, squash strategy)

### AC2: Deployment Commands Configuration
- [ ] **Given** user selects Yes to configure ship phase
  **When** commands section presented
  **Then** wizard prompts:
  - "Version bump command: [none] (Enter to skip or type command)"
  - "Build command: [none] (Enter to skip or type command)"
  - "Publish command: [none] (Enter to skip or type command)"

- [ ] **Given** commands are entered
  **When** wizard validates
  **Then** it accepts any non-empty string (no validation of actual command)

### AC3: Post-Publish Hooks Configuration
- [ ] **Given** user is configuring ship phase
  **When** post-publish section presented
  **Then** wizard prompts: "Add post-publish hooks? [y/N]"

- [ ] **Given** user selects Yes
  **When** adding hooks
  **Then** wizard loops: "Hook command (empty to finish): ____"

- [ ] **Given** user enters empty line
  **When** loop evaluates
  **Then** hook collection ends, continues to next section

### AC4: PR Merge Settings Configuration
- [ ] **Given** user is configuring ship phase
  **When** PR settings section presented
  **Then** wizard shows: "--- PR Merge Settings ---"

- [ ] **Given** PR settings section active
  **When** prompts displayed
  **Then** wizard asks:
  - "Auto-merge after successful ship? [y/N]"
  - "Merge strategy: [squash] / merge / rebase"
  - "Delete branch after merge? [Y/n]"

- [ ] **Given** merge strategy prompt
  **When** user responds
  **Then** accepts: "squash", "merge", "rebase", or Enter for default (squash)

### AC5: Summary Display Update
- [ ] **Given** wizard reaches summary step (Story 14.10)
  **When** ship phase was configured
  **Then** summary panel includes ship section:
  ```
  Ship: Enabled
    Commands: version_bump, build, publish
    Post-hooks: 2 configured
    PR: squash merge, auto-delete branch
  ```

- [ ] **Given** ship phase uses defaults
  **When** summary displayed
  **Then** shows: "Ship: Default (no commands, manual merge)"

### AC6: Files to Generate
- [ ] **Given** wizard completes with ship configuration
  **When** files generated
  **Then** `project.yaml` includes ship section:
  ```yaml
  ship:
    enabled: true
    commands:
      version_bump: "npm version patch"  # if configured
      build: "npm run build"             # if configured
      publish: "npm publish"             # if configured
    post_publish:                        # if configured
      - "git push --tags"
    pr:
      merge_on_success: false
      delete_branch_on_merge: true
      merge_method: squash
  ```

### AC7: Test Coverage
- [ ] **Given** wizard ship step implementation
  **When** tests written
  **Then** coverage includes:
  - Unit tests for ship step prompts and validation
  - Unit tests for ship section in summary display
  - Unit tests for ship config in generated project.yaml

## Tasks / Subtasks

### Task 1: Create Ship Wizard Step Module
- [x] Create `src/adw/cli/wizard/ship.py`
- [x] Implement `ShipStepHandler` class following `StepHandler` protocol
- [x] Implement `run_ship_step()` function
- [x] Add deployment commands prompts (version_bump, build, publish)
- [x] Add post-publish hooks loop
- [x] Add PR merge settings prompts

### Task 2: Integrate Ship Step into Wizard Flow
- [x] Add `SHIP = "ship"` to `WizardStep` enum in `flow.py`
- [x] Add ship step to `STEP_SEQUENCE` after `PHASES`
- [x] Add ship step title to `STEP_TITLES` dictionary
- [x] Register `ShipStepHandler` in flow controller initialization

### Task 3: Update Summary Step
- [x] Add ship section to `generate_summary_panel()` in `summary.py`
- [x] Add ship config extraction from wizard state
- [x] Format ship summary with commands, hooks, and PR settings

### Task 4: Update Project YAML Generation
- [x] Add ship config to `generate_project_yaml()` in `summary.py`
- [x] Handle all ship sub-sections: commands, post_publish, pr
- [x] Only include ship section if configured (not defaults)

### Task 5: Write Unit Tests
- [ ] Create `tests/unit/cli/wizard/test_ship.py`
- [ ] Test skip flow (user says No)
- [ ] Test full configuration flow
- [ ] Test commands validation
- [ ] Test post-publish hooks loop
- [ ] Test PR settings with all merge strategies
- [ ] Update `test_summary.py` for ship section
- [ ] Update `test_flow.py` for ship step integration

---

## Relevant Feature Documentation

<!-- Populated from CONDITIONAL_DOCS.md matches - existing patterns and knowledge -->

### Related Architecture
- **Wizard Architecture**: `src/adw/cli/wizard/` contains the modular wizard implementation
- **Config Models**: `src/adw/models/config.py` defines `ShipConfig`, `ShipCommandsConfig`, `ShipPRConfig`

### Related Epic Stories
- **Story 14.6 (Phase Customization)**: Similar optional step pattern with nested prompts
- **Story 14.10 (Summary & File Generation)**: Summary panel and YAML generation patterns

---

## Developer Context

### Technical Requirements

1. **Follow Existing Wizard Patterns**
   - Use `StepHandler` protocol from `flow.py`
   - Return dict with collected config keys
   - Use Rich `Prompt` and `Confirm` for user input

2. **ShipConfig Model Alignment**
   - Must generate config matching `ShipConfig` model structure
   - Fields: `enabled`, `commands`, `post_publish`, `pr`
   - Sub-models: `ShipCommandsConfig`, `ShipPRConfig`

3. **Wizard State Management**
   - Store config via `state.update_config("ship", config)`
   - Retrieve via `state.get_step_config("ship")`

### Architecture Compliance

**File Locations (MUST follow):**
```
src/adw/cli/wizard/
├── ship.py           # NEW - Ship step handler
├── flow.py           # MODIFY - Add SHIP to enum and sequence
└── summary.py        # MODIFY - Add ship section to summary and YAML

tests/unit/cli/wizard/
├── test_ship.py      # NEW - Ship step tests
├── test_summary.py   # MODIFY - Add ship summary tests
└── test_flow.py      # MODIFY - Add ship step integration tests
```

**Boundary Rules:**
- `ship.py` handles ONLY ship step prompts and validation
- `summary.py` handles ship display and YAML generation
- `flow.py` handles step registration and sequencing

### Library & Framework Requirements

**Rich Components to Use:**
```python
from rich.prompt import Prompt, Confirm
from rich.console import Console

# For optional prompts (default No)
Confirm.ask("Configure ship phase settings?", default=False)

# For text input with default
Prompt.ask("Version bump command", default="")

# For choice selection
Prompt.ask("Merge strategy", choices=["squash", "merge", "rebase"], default="squash")
```

**Pydantic Models (already exist):**
```python
from adw.models.config import ShipConfig, ShipCommandsConfig, ShipPRConfig

# ShipCommandsConfig fields:
# - version_bump: str | None
# - build: str | None
# - publish: str | None

# ShipPRConfig fields:
# - merge_on_success: bool (default False)
# - delete_branch_on_merge: bool (default True)
# - merge_method: Literal["merge", "squash", "rebase"] (default "squash")
```

### File Structure Requirements

**New File: `src/adw/cli/wizard/ship.py`**
```python
"""Ship phase configuration step for the wizard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


class ShipStepHandler:
    """Handler for the ship phase configuration wizard step."""

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the ship configuration step."""
        return run_ship_step(state, console)


def run_ship_step(
    state: WizardState,
    console: Console,
) -> dict[str, Any]:
    """Execute the ship phase configuration step."""
    # Implementation here
    ...
```

**Modify: `flow.py` WizardStep enum**
```python
class WizardStep(Enum):
    BASICS = "basics"
    GIT = "git"
    PORTS = "ports"
    TASK_MANAGER = "task_manager"
    PHASES = "phases"
    SHIP = "ship"  # NEW - Add after PHASES
    LLM_RETRY = "llm_retry"
    SECURITY = "security"
    WEBHOOKS = "webhooks"
    SUMMARY = "summary"
```

**Modify: `flow.py` STEP_SEQUENCE**
```python
STEP_SEQUENCE: list[WizardStep] = [
    WizardStep.BASICS,
    WizardStep.GIT,
    WizardStep.PORTS,
    WizardStep.TASK_MANAGER,
    WizardStep.PHASES,
    WizardStep.SHIP,  # NEW
    WizardStep.LLM_RETRY,
    WizardStep.SECURITY,
    WizardStep.WEBHOOKS,
    WizardStep.SUMMARY,
]
```

### Testing Requirements

**Test Coverage Required:**
- `test_ship.py`:
  - `test_ship_step_skip_returns_defaults()` - User declines configuration
  - `test_ship_step_full_config()` - User configures all options
  - `test_ship_commands_empty_skipped()` - Empty commands not included
  - `test_ship_post_publish_loop()` - Hook collection loop
  - `test_ship_pr_merge_strategies()` - All merge strategy values

- `test_summary.py`:
  - `test_summary_includes_ship_configured()` - Ship section when configured
  - `test_summary_includes_ship_defaults()` - Ship section with defaults

- `test_flow.py`:
  - `test_flow_includes_ship_step()` - Ship in step sequence

**Test Pattern (follow existing):**
```python
def test_ship_step_skip_returns_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ship step returns defaults when user skips configuration."""
    from adw.cli.wizard.ship import run_ship_step
    from adw.models.wizard import WizardState

    # Mock Confirm.ask to return False
    monkeypatch.setattr("adw.cli.wizard.ship.Confirm.ask", lambda *a, **kw: False)

    state = WizardState()
    console = Console()
    result = run_ship_step(state, console)

    assert result["enabled"] is True  # Ship phase enabled by default
    assert result["commands"] == {}   # No commands configured
    assert result["post_publish"] == []
    assert result["pr"]["merge_on_success"] is False
```

---

## Previous Story Intelligence

### Patterns from Epic 14 Wizard Implementation
- Each step module exports a `*StepHandler` class and `run_*_step()` function
- Steps return dict with config keys matching the step name
- Optional steps ask "Configure X? [y/N]" first
- Loops for multiple items use empty input to exit
- Summary extracts config via `state.get_step_config("step_name")`

### Key Learnings from Similar Stories
- **14.6 Phase Customization**: Complex nested prompts pattern, multi-select
- **14.9 Webhook Setup**: Optional step with sub-configuration sections
- **14.10 Summary**: YAML generation pattern, only include non-default values

---

## Git Intelligence

### Recent Relevant Commits
- Epic 14 wizard implementation complete (14-1 through 14-10)
- Story 15-1 added ShipConfig models to `config.py`
- Story 15-2 added context gathering for ship phase

### Files Modified by Related Work
- `src/adw/models/config.py` - ShipConfig, ShipCommandsConfig, ShipPRConfig added
- `src/adw/cli/wizard/*.py` - Full wizard implementation
- `tests/unit/cli/wizard/*.py` - Comprehensive wizard tests

---

## Latest Technical Information

### Rich Library (v14.1.0)
- `Prompt.ask()` supports `choices` parameter for restricted input
- `Confirm.ask()` supports `default` parameter (True/False)
- Console output should use markup for styling

### Pydantic (v2.12+)
- Models use `Field(default=...)` pattern
- `Literal` type for restricted string values
- Model validation is automatic on instantiation

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Naming**: PEP 8 strict - snake_case functions, PascalCase classes
- **Models**: ALL Pydantic models in `src/adw/models/`
- **CLI Output**: Use Rich for all formatted output
- **Type Annotations**: Required on all public functions
- **Testing**: Mirror source structure in `tests/unit/`

---

## Dev Notes

- The ship step is an OPTIONAL step - user can skip with default "No"
- Ship phase is ENABLED by default even if not configured (it just won't run commands)
- Only include `ship` section in project.yaml if user configured something
- Match existing wizard step patterns exactly for consistency

### Project Structure Notes

- New file `ship.py` follows existing step module pattern
- Integrates with existing `WizardState` for config storage
- No new models needed - uses existing `ShipConfig` hierarchy

### References

- [Source: _bmad-output/epics/epic-15-ship-phase-deployment.md#Story 15.8]
- [Source: _bmad-output/architecture.md#Implementation Patterns]
- [Source: src/adw/cli/wizard/flow.py#WizardStep enum]
- [Source: src/adw/cli/wizard/summary.py#generate_summary_panel]
- [Source: src/adw/models/config.py#ShipConfig]

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

### File List

