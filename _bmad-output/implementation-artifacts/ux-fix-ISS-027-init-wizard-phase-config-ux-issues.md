# Story: UX Fix - Init Wizard Phase Configuration Issues

Status: ready-for-dev
Linear Issue: not-configured
Epic: 14 - Interactive Init Wizard
Created: 2026-01-19

---

## Story

As a first-time user running the init wizard,
I want a streamlined phase configuration experience with accurate messaging,
so that I only see relevant options and understand what each setting does.

## Acceptance Criteria

- [ ] **AC1**: Phase selection uses comma-separated input or multiselect instead of individual y/n prompts
  - User can type `plan,build,validate` or similar to select multiple phases at once
  - Alternative: numbered list (1=plan, 2=build, etc.) with comma-separated selection
- [ ] **AC2**: Pre-hook and post-hook script path prompts are removed from wizard
  - SDK always uses fixed `pre.sh`/`post.sh` in phase folder - these are not configurable
  - Remove `pre_hook` and `post_hook` prompts from `_configure_phase()`
- [ ] **AC3**: Focus options (security, error handling, edge cases) are removed from wizard
  - The `review_focus` list is collected but never used by the SDK
  - Remove `_prompt_review_focus()` calls and `REVIEW_FOCUS_AREAS` usage
- [ ] **AC4**: Danger mode warning message is accurate
  - Current message says "You'll be prompted to confirm risky operations" which contradicts danger mode
  - Update to explain that dangerous operations will show warnings but NOT be blocked
- [ ] **AC5**: Completion message is accurate
  - Remove "Note: Full configuration will be applied in the Summary step" from `_show_completion()`
  - Summary has already been displayed at this point
- [ ] **AC6**: All existing tests pass after changes
- [ ] **AC7**: Update tests to reflect new phase selection UX

## Tasks / Subtasks

### Task 1: Improve Phase Selection UX
**Files**: `src/adw/cli/wizard/phases.py`

1.1 Replace `_prompt_phase_selection()` with comma-separated or numbered input
   - Display numbered list: `1. plan  2. build  3. validate  4. document`
   - Accept input like `1,3` or `plan,validate` or `all`
   - Provide clear instructions: "Enter phase numbers separated by commas (e.g., 1,3) or 'all':"

1.2 Update `run_phases_step()` to use new selection method

### Task 2: Remove Non-Configurable Hook Path Prompts
**Files**: `src/adw/cli/wizard/phases.py`

2.1 Remove pre_hook prompt from `_configure_phase()` (lines 167-174)
2.2 Remove post_hook prompt from `_configure_phase()` (lines 176-183)
2.3 Remove pre_hook and post_hook from config dict (lines 191-192)
2.4 Update phase config generation in summary.py if needed

### Task 3: Remove Unused Focus Options
**Files**: `src/adw/cli/wizard/phases.py`

3.1 Remove `REVIEW_FOCUS_AREAS` constant (line 34)
3.2 Remove `_prompt_review_focus()` function (lines 296-317)
3.3 Remove call to `_prompt_review_focus()` in `_configure_validate_phase()` (line 240)
3.4 Remove `review_focus` from validate config return dict (line 248)

### Task 4: Fix Danger Mode Warning Message
**Files**: `src/adw/cli/wizard/security.py`

4.1 Update Panel content in `_prompt_dangerous_operations()` (lines 171-180)
   - Change "You'll be prompted to confirm risky operations" to:
   - "Dangerous commands will show warnings but will NOT be blocked"
   - Remove implication that confirmation is required

### Task 5: Fix Completion Message
**Files**: `src/adw/cli/wizard/flow.py`

5.1 Update `_show_completion()` (lines 225-236)
   - Remove "[dim]Note: Full configuration will be applied in the Summary step.[/]"
   - Message should just confirm completion without referencing Summary step

### Task 6: Update Tests
**Files**: `tests/unit/cli/wizard/test_phases.py`

6.1 Update `TestPhaseSelection` class tests for new comma-separated input
6.2 Remove tests for `_prompt_review_focus()` function
6.3 Update mock patterns in `TestValidatePhaseSpecialOptions` (no review_focus)
6.4 Update mock patterns in `TestBasePhaseConfiguration` (no pre_hook/post_hook)
6.5 Update `TestFullFlow` tests for new phase selection UX
6.6 Remove `TestReviewFocus` class entirely

---

## Developer Context

### Technical Requirements

- Use Rich library patterns consistent with existing wizard steps
- Maintain backward compatibility with existing config file format
- Pre/post hooks are still supported in the SDK but configured via file convention, not wizard

### Architecture Compliance

**Wizard Step Pattern**:
- Each step handler implements `StepHandler` protocol with `execute(state, console) -> dict`
- Steps return config dict that gets stored via `state.update_config(step_name, config)`
- Flow controller advances automatically after each step completes

**Config Generation Pattern**:
- `summary.py` generates `project.yaml` and phase configs from wizard state
- Phase configs only written for phases with `customized=True`
- Phase config files go to `.adw/commands/{phase}/config.yaml`

### Library & Framework Requirements

- **Rich**: Use `Prompt.ask()` for text input, `Confirm.ask()` for yes/no
- Pattern for comma-separated input:
  ```python
  selected = Prompt.ask(
      "Enter phase numbers (e.g., 1,3) or 'all'",
      default="",
      console=console,
  )
  # Parse: "1,3" -> ["plan", "validate"]
  ```

### File Structure Requirements

Files to modify:
```
src/adw/cli/wizard/
├── phases.py       # Main changes (Tasks 1-3)
├── security.py     # Task 4
└── flow.py         # Task 5

tests/unit/cli/wizard/
└── test_phases.py  # Task 6
```

### Testing Requirements

- All tests in `tests/unit/cli/wizard/test_phases.py` must pass
- Use `unittest.mock.patch` for Rich prompts
- Test edge cases: empty input, invalid phase numbers, duplicate selections
- Test new comma-separated parsing logic

---

## Previous Story Intelligence

**From Epic 14 implementation (stories 14-1 through 14-10)**:
- Wizard uses `WizardFlowController` with step handlers registered via `register_step_handler()`
- State management via `WizardState` model with `collected_config` dict
- All step handlers follow same pattern - see `basics.py`, `git.py`, `security.py` for examples
- Testing pattern: mock `Confirm.ask` and `Prompt.ask` with `side_effect` for sequential responses

**Recent commits show**:
- `fix(wizard): register all step handlers and auto-advance` - handlers must be registered to work
- `feat(wizard): Story 14-10 - Summary & File Generation` - summary generates files from config
- All wizard tests use `Console(force_terminal=True)` for Rich

---

## Git Intelligence

**Recent relevant commits**:
- `6a41b0b` - Fixed step handler registration and auto-advance
- `2eeb72d` - Summary step implementation shows config generation pattern
- `c85104a` - Security step shows warning Panel pattern to follow

**Code patterns observed**:
- Consistent use of Rich `Panel` for warnings/info
- All prompts use `console` parameter
- Tests mock `Prompt.ask` and `Confirm.ask` with `side_effect` lists

---

## Latest Technical Information

No external library updates required. All changes use existing Rich patterns already in codebase.

---

## Project Context Reference

See: docs/project-context.md (not found - use architecture from codebase analysis)

Key patterns and rules:
- Follow existing wizard step handler pattern
- Use pytest with unittest.mock for tests
- All wizard modules export their handlers in `__init__.py`

---

## Dev Notes

### Key Implementation Details

1. **Phase Selection Parsing**: Consider helper function `_parse_phase_selection(input_str) -> list[str]`:
   - Handle "all" -> returns all phases
   - Handle "1,3" -> returns ["plan", "validate"]
   - Handle "plan, validate" -> returns ["plan", "validate"]
   - Handle empty -> returns []
   - Handle invalid -> show error, reprompt

2. **Removal scope**: When removing review_focus:
   - Check if `review_focus` is used anywhere else in codebase (grep first)
   - If only in phases.py wizard, safe to remove entirely
   - Config generation in summary.py won't output unused fields

3. **Security warning update**: The message should clarify:
   - With dangerous mode OFF: Dangerous commands are BLOCKED
   - With dangerous mode ON: Dangerous commands show WARNING but EXECUTE

### Source References

- [Source: src/adw/cli/wizard/phases.py] - Main file with phase selection logic
- [Source: src/adw/cli/wizard/security.py:170-180] - Warning Panel to update
- [Source: src/adw/cli/wizard/flow.py:225-236] - Completion message to fix
- [Source: tests/unit/cli/wizard/test_phases.py] - Test patterns to follow

---

## Dev Agent Record

### Context Reference

Issue: `_bmad-output/implementation-artifacts/issues/ISS-027-init-wizard-phase-config-ux-issues.md`

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
