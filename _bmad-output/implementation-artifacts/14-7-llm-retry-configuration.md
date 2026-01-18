# Story 14.7: LLM Retry Configuration (Optional)

Status: ready-for-dev
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user in the wizard,
I want to configure LLM retry behavior,
so that I can tune how ADW handles transient failures.

## Acceptance Criteria

- [ ] Prompts "Configure LLM retry behavior? [y/N]"
- [ ] If No, uses defaults (3 retries, 1s base, 60s max, 2x multiplier)
- [ ] If Yes:
  - [ ] "Max retries: 3 [Enter or override]"
  - [ ] "Base delay (seconds): 1.0 [Enter or override]"
  - [ ] "Max delay (seconds): 60.0 [Enter or override]"
  - [ ] "Delay multiplier: 2.0 [Enter or override]"
- [ ] Validates multiplier > 1.0
- [ ] Validates max_delay >= base_delay
- [ ] All values stored in wizard state for final generation

## Tasks / Subtasks

### Task 1: Create LLM Retry Step Module
- [x] Create `src/adw/cli/wizard/retry.py`
- [x] Define `run_retry_step(state: WizardState) -> WizardState`
- [x] Import and register in flow controller

### Task 2: Implement Value Validations
- [x] Create validation for max_retries (positive integer, 1-10)
- [x] Create validation for base_delay (positive float, 0.1-60)
- [x] Create validation for max_delay (positive float, must be >= base_delay)
- [x] Create validation for multiplier (float > 1.0, typically 1.5-3.0)

### Task 3: Implement Interactive Prompts
- [x] Prompt for retry configuration (default No)
- [x] If Yes:
  - Prompt for max_retries with validation
  - Prompt for base_delay with validation
  - Prompt for max_delay with cross-validation
  - Prompt for multiplier with validation

### Task 4: Store Results in Wizard State
- [x] Update WizardState with:
  - `retry_custom: bool`
  - `retry_max_retries: int`
  - `retry_base_delay: float`
  - `retry_max_delay: float`
  - `retry_multiplier: float`
- [x] Mark retry step as completed

### Task 5: Write Unit Tests
- [x] Test all validations (valid and invalid)
- [x] Test cross-validation (max_delay >= base_delay)
- [x] Test prompt flow when using defaults
- [x] Test prompt flow with custom values
- [x] Test state update after step completion

---

## Dependencies

### Depends On
- 14.1 (Wizard Entry Point & Flow Control) - provides WizardState and flow controller
- 14.2 (Basics Configuration Step) - runs before this in wizard flow

### Blocks
- 14.10 (Summary) - displays retry configuration

### Parallel With
- 14.8 (Security Configuration) - no dependencies
- 14.9 (Webhook Server Setup) - no dependencies

---

## Developer Context

### Technical Requirements

**Default Retry Values:**
```python
DEFAULT_RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 1.0,
    "max_delay": 60.0,
    "multiplier": 2.0,
}
```

**Exponential Backoff Formula:**
```
delay = min(base_delay * (multiplier ^ attempt), max_delay)

Example with defaults:
- Attempt 1: min(1.0 * 2^0, 60) = 1.0s
- Attempt 2: min(1.0 * 2^1, 60) = 2.0s
- Attempt 3: min(1.0 * 2^2, 60) = 4.0s
```

**Validation Functions:**
```python
def validate_max_retries(value: str) -> tuple[bool, int | str]:
    try:
        retries = int(value)
        if retries < 1:
            return False, "Max retries must be at least 1"
        if retries > 10:
            return False, "Max retries cannot exceed 10"
        return True, retries
    except ValueError:
        return False, "Must be a valid integer"

def validate_delay(value: str, min_val: float = 0.1) -> tuple[bool, float | str]:
    try:
        delay = float(value)
        if delay < min_val:
            return False, f"Delay must be at least {min_val}s"
        if delay > 300:
            return False, "Delay cannot exceed 300s"
        return True, delay
    except ValueError:
        return False, "Must be a valid number"

def validate_multiplier(value: str) -> tuple[bool, float | str]:
    try:
        mult = float(value)
        if mult <= 1.0:
            return False, "Multiplier must be greater than 1.0"
        if mult > 5.0:
            return False, "Multiplier cannot exceed 5.0"
        return True, mult
    except ValueError:
        return False, "Must be a valid number"
```

### Architecture Compliance

**Layer Boundaries:**
- Wizard step in `src/adw/cli/wizard/retry.py`
- Retry config models in `src/adw/models/config.py`
- Ensure compatibility with existing retry configuration

**Existing Retry Configuration:**
- Check `src/adw/models/config.py` for `RetryConfig`
- Check `src/adw/executors/` for retry implementation

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Rich | Prompts | `from rich.prompt import Prompt, Confirm` |

**Prompt Pattern with Validation:**
```python
def prompt_with_validation(
    prompt_text: str,
    default: str,
    validator: Callable[[str], tuple[bool, Any]]
) -> Any:
    """Prompt with validation loop."""
    while True:
        value = Prompt.ask(prompt_text, default=default)
        valid, result = validator(value)
        if valid:
            return result
        console.print(f"[red]Error:[/] {result}")
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
└── retry.py              # LLM retry configuration step
```

**Files to Modify:**
```
src/adw/cli/wizard/flow.py    # Register retry step
src/adw/models/wizard.py      # Add retry fields to WizardState
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
└── test_retry.py         # Retry step tests
```

**Test Cases:**
```python
# Validation tests
def test_validate_max_retries_valid():
    assert validate_max_retries("3") == (True, 3)
    assert validate_max_retries("1") == (True, 1)
    assert validate_max_retries("10") == (True, 10)

def test_validate_max_retries_invalid():
    assert validate_max_retries("0")[0] == False
    assert validate_max_retries("11")[0] == False
    assert validate_max_retries("abc")[0] == False

def test_validate_multiplier_valid():
    assert validate_multiplier("2.0") == (True, 2.0)
    assert validate_multiplier("1.5") == (True, 1.5)

def test_validate_multiplier_invalid():
    assert validate_multiplier("1.0")[0] == False  # Must be > 1.0
    assert validate_multiplier("0.5")[0] == False

# Cross-validation
def test_max_delay_greater_than_base():
    # max_delay must be >= base_delay
    # Test in context of full step

# Full flow
def test_retry_step_defaults(mocker):
    # Mock No response
    # Verify default values in state

def test_retry_step_custom(mocker):
    # Mock Yes + custom values
    # Verify custom values in state
```

**Mock Requirements:**
- Mock Rich prompts for automated testing

---

## Previous Story Intelligence

**From Stories 14.1-14.6:**
- WizardState model structure
- Validation loop patterns
- prompt_with_validation helper pattern

**Expected State Structure:**
```python
# WizardState additions
retry_custom: bool = False
retry_max_retries: int = 3
retry_base_delay: float = 1.0
retry_max_delay: float = 60.0
retry_multiplier: float = 2.0
```

---

## Git Intelligence

**Existing Retry Config:**
- Check `src/adw/models/config.py` for `RetryConfig`
- Check `src/adw/executors/claude_code.py` for retry implementation

**Search Commands:**
```bash
grep -r "RetryConfig" src/
grep -r "max_retries\|base_delay" src/
grep -r "exponential.*backoff" src/
```

---

## Latest Technical Information

**Exponential Backoff Best Practices:**
- Jitter: Add randomness to prevent thundering herd (optional for local tool)
- Cap retries: Don't retry indefinitely
- Cap delay: Don't wait too long between attempts
- Log retries: Help debugging transient issues

**Common Retry Configurations:**
| Use Case | Max Retries | Base Delay | Max Delay | Multiplier |
|----------|-------------|------------|-----------|------------|
| Aggressive | 5 | 0.5s | 30s | 1.5 |
| Default | 3 | 1.0s | 60s | 2.0 |
| Patient | 5 | 2.0s | 120s | 2.0 |

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- Config models in `src/adw/models/`
- Executor implementations in `src/adw/executors/`
- Retry logic integrated with executor

---

## Dev Notes

- This step is relatively simple (just 4 values)
- Cross-validation important: max_delay must be >= base_delay
- Consider showing a preview of retry timing (optional enhancement)
- Users rarely need to customize this - defaults work well

### Prompt Flow Diagram
```
Configure retry behavior? [y/N]
├── No → Use defaults, DONE
└── Yes
    ├── Max retries: 3
    ├── Base delay: 1.0
    ├── Max delay: 60.0 (validate >= base_delay)
    └── Multiplier: 2.0 (validate > 1.0)
```

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.7]
- [Source: _bmad-output/architecture-summary.md#Key-Design-Decisions]
- [Source: src/adw/executors/ - retry implementation]

---

## Dev Agent Record

### Context Reference

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

