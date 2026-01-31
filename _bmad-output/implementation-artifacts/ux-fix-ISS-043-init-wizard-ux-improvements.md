# Story: UX Fix - Init Wizard UX Improvements

Status: ready-for-dev
Linear Issue: not-configured
Epic: 14 - Interactive Init Wizard
Created: 2026-01-31

---

## Story

As a first-time user running the init wizard,
I want consistent navigation, complete phase customization, and intelligent prompts,
so that I can efficiently configure my project without redundant questions or missing options.

## Acceptance Criteria

- [ ] **AC1**: Ship phase appears in phase selection list alongside plan, build, validate, document
  - User can select ship for customization in the phases step
  - Ship configuration routed through `_configure_phase()` pattern when selected

- [ ] **AC2**: Ship configuration follows common phase pattern (enabled, timeout, input_files first)
  - When ship is selected for customization, prompt for enabled/timeout/input_files BEFORE ship-specific settings
  - Maintains consistency with other phase configurations

- [ ] **AC3**: Navigation keys (b/c) work throughout the wizard
  - `b` goes back to previous step
  - `c` cancels wizard
  - All prompts intercept these keys before processing as input

- [ ] **AC4**: Project registration actually registers the project in global dashboard
  - `GlobalRegistryStepHandler` registered in init.py
  - Registration persisted when summary step completes

- [ ] **AC5**: Custom language/platform can be typed directly without selecting "other" first
  - Remove `choices` restriction from Prompt.ask()
  - Show numbered list as hint, accept number or direct text input

- [ ] **AC6**: Validate phase allows configuring multiple linter commands
  - New `_prompt_linter_commands()` function collects linter commands
  - Commands stored in validate config and used during validation

- [ ] **AC7**: Auto-merge NO skips merge_method and delete_branch questions
  - Only prompt for merge strategy and delete branch if `merge_on_success == True`

- [ ] **AC8**: Default timeouts are increased to realistic values
  - plan: 900 seconds (15 minutes)
  - build: 1800 seconds (30 minutes)
  - document: 900 seconds (15 minutes)
  - validate: 900 seconds (unchanged)

## Tasks / Subtasks

### Task 1: Add Ship to AVAILABLE_PHASES and Update Timeouts
**Files**: `src/adw/cli/wizard/phases.py`

- [ ] 1.1 Add `"ship"` to `AVAILABLE_PHASES` list (line 20)
- [ ] 1.2 Update `DEFAULT_TIMEOUTS` dictionary (lines 23-28):
  ```python
  DEFAULT_TIMEOUTS: dict[str, int] = {
      "plan": 900,       # 15 minutes
      "build": 1800,     # 30 minutes
      "validate": 900,   # 15 minutes
      "document": 900,   # 15 minutes
      "ship": 1200,      # 20 minutes
  }
  ```
- [ ] 1.3 Update phase selection hints/instructions to include ship (line 158: "Use numbers (1-5), phase names, or 'all'")

### Task 2: Refactor Ship Configuration to Follow Common Pattern
**Files**: `src/adw/cli/wizard/ship.py`, `src/adw/cli/wizard/phases.py`

- [ ] 2.1 When ship is selected in phases step, route to `_configure_phase("ship", console)` first
- [ ] 2.2 After common config (enabled, timeout, input_files), call ship-specific functions:
  - `_prompt_ship_commands()`
  - `_prompt_post_publish_hooks()`
  - `_prompt_pr_settings()`
- [ ] 2.3 Remove ship as a separate wizard step OR keep it as fallback when not selected in phases
- [ ] 2.4 Update `run_ship_step()` in ship.py to use common pattern if ship step is kept

### Task 3: Implement Navigation Key Handling
**Files**: `src/adw/cli/wizard/flow.py`, possibly new `src/adw/cli/wizard/prompts.py`

- [ ] 3.1 Create `NavigationPrompt` wrapper class or helper functions:
  ```python
  class NavigationSignal(Enum):
      BACK = "b"
      CANCEL = "c"

  def nav_prompt_ask(question: str, **kwargs) -> str | NavigationSignal:
      """Prompt.ask wrapper that intercepts navigation keys."""
      result = Prompt.ask(question, **kwargs)
      if result.lower() == "b":
          return NavigationSignal.BACK
      if result.lower() == "c":
          return NavigationSignal.CANCEL
      return result
  ```
- [ ] 3.2 Update `WizardFlowController.run()` to handle NavigationSignal
- [ ] 3.3 Replace `Prompt.ask()` calls in step handlers with navigation-aware version
- [ ] 3.4 Handle navigation signals by calling `go_back()` or `cancel()`

### Task 4: Register GlobalRegistryStepHandler and Wire Registration
**Files**: `src/adw/cli/init.py`, `src/adw/cli/wizard/summary.py`

- [ ] 4.1 Add missing handler registration in `init.py` (after line 197):
  ```python
  controller.register_step_handler(
      WizardStep.GLOBAL_REGISTRY,
      GlobalRegistryStepHandler()
  )
  ```
- [ ] 4.2 Verify `_register_in_global_dashboard()` in summary.py is called correctly
- [ ] 4.3 Ensure `ProjectRegistryManager.register()` is invoked with collected config
- [ ] 4.4 Test that registration persists to global registry file

### Task 5: Fix Custom Language/Platform Entry
**Files**: `src/adw/cli/wizard/basics.py`

- [ ] 5.1 Modify `_prompt_language()` (lines 191-210):
  - Remove `choices=SUPPORTED_LANGUAGES` from Prompt.ask()
  - Display numbered list before prompt: "1. python  2. javascript  3. go  ..."
  - Accept either number (1-8) or direct text input
  - Parse input: if digit, map to language; else use as custom language
  ```python
  # Show options
  for i, lang in enumerate(SUPPORTED_LANGUAGES, 1):
      console.print(f"  {i}. {lang}")

  # Accept number or direct input
  selection = Prompt.ask("Select language (number or type custom)", ...)
  if selection.isdigit() and 1 <= int(selection) <= len(SUPPORTED_LANGUAGES):
      language = SUPPORTED_LANGUAGES[int(selection) - 1]
  else:
      language = selection
  ```

- [ ] 5.2 Apply same pattern to `_prompt_platform()` (lines 224-242):
  - Remove choices restriction
  - Show numbered list for SUPPORTED_PLATFORMS
  - Accept number or custom text

### Task 6: Add Linter Commands to Validate Phase
**Files**: `src/adw/cli/wizard/phases.py`

- [ ] 6.1 Create `_prompt_linter_commands()` function (similar to ship.py:_prompt_post_publish_hooks):
  ```python
  def _prompt_linter_commands(console: Console) -> list[str]:
      """Collect multiple linter commands for validate phase."""
      linters: list[str] = []
      console.print("[dim]Enter linter commands (empty to finish):[/]")
      console.print("[dim]Examples: 'ruff check .', 'mypy src/', 'eslint .'[/]")
      while True:
          cmd = Prompt.ask("Linter command", default="", console=console).strip()
          if not cmd:
              break
          linters.append(cmd)
      return linters
  ```

- [ ] 6.2 Call `_prompt_linter_commands()` in `_configure_validate_phase()` after test config:
  - Add prompt: "Add linter commands? [y/N]"
  - If yes, call `_prompt_linter_commands()`
  - Store in config: `"linter_commands": linters`

- [ ] 6.3 Update validate phase config generation in summary.py to include linter_commands

### Task 7: Fix Auto-merge Follow-up Questions
**Files**: `src/adw/cli/wizard/ship.py`

- [ ] 7.1 Modify `_prompt_pr_settings()` (lines 203-226):
  - Move merge_method and delete_branch prompts inside conditional
  ```python
  merge_on_success = Confirm.ask("Auto-merge after successful ship?", ...)

  merge_method = "squash"  # default
  delete_branch = True      # default

  if merge_on_success:
      merge_method = Prompt.ask("Merge strategy", choices=["squash", "merge", "rebase"], ...)
      delete_branch = Confirm.ask("Delete branch after merge?", ...)

  return {
      "merge_on_success": merge_on_success,
      "merge_method": merge_method,
      "delete_branch": delete_branch,
  }
  ```

### Task 8: Update Tests
**Files**: `tests/unit/cli/wizard/test_phases.py`, `tests/unit/cli/wizard/test_ship.py`, `tests/unit/cli/wizard/test_basics.py`

- [ ] 8.1 Update phase selection tests to include ship phase
- [ ] 8.2 Add tests for new timeout defaults
- [ ] 8.3 Add tests for `_prompt_linter_commands()`
- [ ] 8.4 Update ship tests for conditional merge questions
- [ ] 8.5 Update basics tests for new language/platform selection pattern
- [ ] 8.6 Add navigation key handling tests (if flow.py changes are testable)

---

## Relevant Feature Documentation

**ISS-027 Fix Story** (Previous wizard UX fixes):
- Established comma-separated phase selection pattern
- Helper function returns `tuple[list[str], list[str]]` for (valid, invalid) feedback
- Tests use `side_effect` lists for sequential mock responses
- Removed unused hook path prompts (SDK uses fixed `pre.sh`/`post.sh`)

**ISS-032 Fix Story** (Complete config file generation):
- Config registry pattern for settings with defaults and descriptions
- YAML generation with commented defaults
- All phases generate config files (not just customized ones)
- `atomic_write_config()` handles rollback on failure

---

## Developer Context

### Technical Requirements

- Use Rich library patterns consistent with existing wizard steps
- Maintain backward compatibility with existing config file format
- Navigation handling should be non-intrusive (opt-in via wrapper function)
- All linter commands should be strings that can be shell-executed
- Ship phase should support the same timeout/input_files pattern as other phases

### Architecture Compliance

**Wizard Step Pattern** (from flow.py):
- Each step handler implements `StepHandler` protocol with `execute(state, console) -> dict`
- Steps return config dict that gets stored via `state.update_config(step_name, config)`
- Flow controller calls `advance()`, `go_back()`, `cancel()` for navigation
- Steps are registered in init.py via `controller.register_step_handler()`

**Phase Configuration Pattern** (from phases.py):
```python
def _configure_phase(phase: str, console: Console) -> dict[str, Any]:
    """Configure a single phase with common options."""
    enabled = Confirm.ask(f"Enable {phase} phase?", default=True, console=console)
    timeout = IntPrompt.ask("Timeout (seconds)", default=DEFAULT_TIMEOUTS.get(phase, 300), ...)
    input_files = _prompt_input_files(console) if _ask_for_input_files else {}

    config = {"enabled": enabled, "timeout_seconds": timeout, "input_files": input_files}

    if phase == "validate":
        config.update(_configure_validate_phase(console))
    elif phase == "ship":
        config.update(_configure_ship_phase(console))  # NEW

    return config
```

**Multi-Input Loop Pattern** (from ship.py:_prompt_post_publish_hooks):
```python
hooks: list[str] = []
console.print("[dim]Enter hook commands (empty to finish):[/]")
while True:
    hook = Prompt.ask("Hook command", default="", console=console).strip()
    if not hook:
        break
    hooks.append(hook)
return hooks
```

### Library & Framework Requirements

- **Rich 14.1.0**: Use `Prompt.ask()` for text, `Confirm.ask()` for yes/no, `IntPrompt.ask()` for numbers
- **Pydantic 2.12+**: Config models in `src/adw/models/config.py`
- **Python 3.13+**: Use modern syntax (`X | None` not `Optional[X]`)

**Navigation Key Pattern (new)**:
```python
from enum import Enum

class NavigationSignal(Enum):
    BACK = "back"
    CANCEL = "cancel"

def check_navigation(value: str) -> NavigationSignal | None:
    """Check if input is a navigation command."""
    lower = value.lower().strip()
    if lower == "b":
        return NavigationSignal.BACK
    if lower == "c":
        return NavigationSignal.CANCEL
    return None
```

### File Structure Requirements

**Files to Modify:**
```
src/adw/cli/wizard/
├── phases.py          # Tasks 1, 2 (partial), 6 - AVAILABLE_PHASES, timeouts, linter commands
├── ship.py            # Tasks 2 (partial), 7 - common config pattern, auto-merge fix
├── flow.py            # Task 3 - navigation key handling
├── basics.py          # Task 5 - language/platform selection
├── global_registry.py # Task 4 (verify) - registration implementation
└── summary.py         # Task 4, 6 (partial) - registration call, linter config output

src/adw/cli/
└── init.py            # Task 4 - register GlobalRegistryStepHandler

tests/unit/cli/wizard/
├── test_phases.py     # Task 8.1, 8.2, 8.3
├── test_ship.py       # Task 8.4
└── test_basics.py     # Task 8.5
```

### Testing Requirements

- All tests in `tests/unit/cli/wizard/` must pass
- Use `unittest.mock.patch` for Rich prompts: `@patch("rich.prompt.Prompt.ask")`
- Test edge cases: empty input, invalid selections, b/c navigation keys
- Test new linter commands collection with multiple entries

**Test Pattern from ISS-027:**
```python
@patch("rich.prompt.Confirm.ask")
@patch("rich.prompt.Prompt.ask")
def test_example(mock_prompt, mock_confirm):
    mock_confirm.side_effect = [True, False]
    mock_prompt.side_effect = ["value1", "value2"]
    # Execute and assert
```

---

## Previous Story Intelligence

**From ISS-027 (Init Wizard Phase Config UX):**
- `_parse_phase_selection()` helper function pattern for user input parsing
- Returns `tuple[list[str], list[str]]` for (valid_phases, invalid_entries)
- User feedback on invalid input: "Ignored invalid entries: ..."
- Reprompt loop when only invalid entries provided

**From ISS-032 (Complete Config File Generation):**
- Config registry extracts defaults from Pydantic `model_fields`
- YAML generator handles commented defaults
- All phases now generate config files (changed from customized-only)
- Ship phase included in file generation

**From Epic 14 Stories (14.1-14.10):**
- `WizardFlowController` with STEP_SEQUENCE defines step order
- State management via `WizardState.collected_config` dict
- Step handlers follow protocol: `execute(state, console) -> dict[str, Any]`
- Navigation methods exist: `advance()`, `go_back()`, `cancel()` but not wired to prompts

**Key Learnings:**
1. Pre/post hooks are NOT configurable via wizard (SDK uses fixed `pre.sh`/`post.sh`)
2. Ship was added as separate wizard step after initial Epic 14 implementation
3. GlobalRegistryStepHandler exists but was never registered in init.py
4. Navigation hints (b/c for back/cancel) shown in welcome but never implemented in prompts

---

## Git Intelligence

**Recent relevant commits:**
- `4b87e9c` feat(dashboard): adaptive refresh rate for active runs
- `f33a6d3` fix(ISS-042): fix arrow key handling in global dashboard
- `6bb858c` fix(ISS-042): dashboard layout and selection improvements

**Wizard-specific commits (from ISS-027/032):**
- Comma-separated phase selection implemented
- Config registry and YAML generator added
- Ship step added to wizard flow

**Code patterns observed:**
- Consistent use of Rich `Panel` for info/warnings
- All prompts use `console` parameter
- Tests mock `Prompt.ask` and `Confirm.ask` with `side_effect` lists
- Validation patterns return `tuple[bool, result_or_error]`

---

## Latest Technical Information

**Rich Library Patterns (current project usage):**
- `Prompt.ask()` with `choices` parameter restricts to listed values only
- `Confirm.ask()` returns bool for yes/no questions
- `IntPrompt.ask()` for numeric input with validation
- Remove `choices` to accept any text input

**Navigation Implementation Considerations:**
- Rich prompts don't natively support intercepting single keys
- Need wrapper that checks result after Enter is pressed
- Can't implement real-time key detection without additional libraries
- Approach: Check if input is exactly "b" or "c" after user presses Enter

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:
- **All Models in models/**: If `NavigationSignal` needs persistence, place in models
- **Rich for CLI output**: All wizard output uses Rich console
- **Type annotations required**: Full typing on all new functions
- **Naming conventions**: snake_case for functions/variables, PascalCase for classes
- **No bare exceptions**: Use exception hierarchy for config errors

---

## Dev Notes

### Implementation Priority

Recommend implementing in this order:
1. **Task 1** (timeouts) - Quick win, immediate user value
2. **Task 7** (auto-merge fix) - Quick win, simple conditional
3. **Task 5** (language/platform) - Moderate, improves UX significantly
4. **Task 6** (linter commands) - Moderate, follows existing pattern
5. **Task 4** (global registry) - Important, but may be low-usage feature
6. **Task 2** (ship common pattern) - Complex, refactoring involved
7. **Task 3** (navigation keys) - Most complex, affects all prompts

### Specific Code Locations

| Issue | File | Lines | Change |
|-------|------|-------|--------|
| Ship not in phases | phases.py | 20 | Add `"ship"` to AVAILABLE_PHASES |
| Default timeouts | phases.py | 23-28 | Update DEFAULT_TIMEOUTS values |
| Phase selection hint | phases.py | 158 | Update "1-4" to "1-5" |
| Auto-merge fix | ship.py | 209-220 | Wrap in `if merge_on_success:` |
| Language choices | basics.py | 191-196 | Remove `choices=`, show numbered list |
| Platform choices | basics.py | 224-236 | Same pattern as language |
| Missing handler | init.py | after 197 | Add GlobalRegistryStepHandler registration |
| Linter commands | phases.py | after 241 | Add _prompt_linter_commands() call |

### Edge Cases to Handle

1. **Ship in both phases step AND ship step**: If user selects ship in phases customization, skip or merge with ship step config
2. **Navigation mid-prompt**: Single "b" or "c" should trigger navigation, but "build" as phase name should not
3. **Empty linter commands**: Handle gracefully, don't add empty strings to list
4. **Custom language validation**: Accept any non-empty string, warn if unusual

### Source References

- [Source: src/adw/cli/wizard/phases.py:20] - AVAILABLE_PHASES definition
- [Source: src/adw/cli/wizard/phases.py:23-28] - DEFAULT_TIMEOUTS definition
- [Source: src/adw/cli/wizard/phases.py:115-158] - _prompt_phase_selection()
- [Source: src/adw/cli/wizard/phases.py:161-204] - _configure_phase()
- [Source: src/adw/cli/wizard/phases.py:207-249] - _configure_validate_phase()
- [Source: src/adw/cli/wizard/ship.py:50-109] - run_ship_step()
- [Source: src/adw/cli/wizard/ship.py:156-191] - _prompt_post_publish_hooks() (pattern for linter commands)
- [Source: src/adw/cli/wizard/ship.py:194-226] - _prompt_pr_settings()
- [Source: src/adw/cli/wizard/flow.py:195-198] - Navigation hints in welcome
- [Source: src/adw/cli/wizard/flow.py:253-290] - Navigation methods (advance, go_back, cancel)
- [Source: src/adw/cli/wizard/basics.py:169-210] - Language selection
- [Source: src/adw/cli/wizard/basics.py:224-242] - Platform selection
- [Source: src/adw/cli/init.py:186-199] - Step handler registration
- [Source: src/adw/cli/wizard/global_registry.py:43-101] - GlobalRegistryStepHandler
- [Source: src/adw/cli/wizard/summary.py:540-561] - _register_in_global_dashboard()
- [Source: _bmad-output/implementation-artifacts/issues/ISS-043-init-wizard-ux-improvements.md] - Issue details

---

## Dev Agent Record

### Context Reference

Issue: `_bmad-output/implementation-artifacts/issues/ISS-043-init-wizard-ux-improvements.md`

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

_To be filled by dev agent_
