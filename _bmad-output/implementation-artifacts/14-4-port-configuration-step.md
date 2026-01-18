# Story 14.4: Port Configuration Step (Optional)

Status: ready-for-dev
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user in the wizard,
I want to optionally configure port ranges,
so that concurrent runs don't conflict with my other services.

## Acceptance Criteria

- [ ] Prompts "Configure port ranges for concurrent runs? [y/N]"
- [ ] Default No uses defaults (9100, 9200)
- [ ] If Yes:
  - [ ] "Backend services start port: 9100 [Enter or override]"
  - [ ] "Frontend services start port: 9200 [Enter or override]"
- [ ] Validates ports are 1-65535
- [ ] Validates backend and frontend ranges don't overlap (given max_concurrent)
- [ ] Shows warning if ports conflict with common services (3000, 5000, 8080)
- [ ] All values stored in wizard state for final generation

## Tasks / Subtasks

### Task 1: Create Port Configuration Step Module
- [x] Create `src/adw/cli/wizard/ports.py`
- [x] Define `run_ports_step(state: WizardState) -> WizardState`
- [x] Import and register in flow controller

### Task 2: Implement Port Validation
- [x] Create port number validation function
- [x] Validate range: 1-65535
- [x] Validate integer parsing
- [x] Return normalized port or error message

### Task 3: Implement Port Range Overlap Check
- [x] Check if backend and frontend ranges would overlap
- [x] Assume max_concurrent = 10 (or read from config)
- [x] Backend range: backend_start to backend_start + max_concurrent
- [x] Frontend range: frontend_start to frontend_start + max_concurrent
- [x] Warn if ranges overlap

### Task 4: Implement Common Port Conflict Warning
- [x] Define list of common ports: 3000, 3001, 5000, 8000, 8080, 8888
- [x] Check if entered ports or ranges include common ports
- [x] Show warning (not blocking) if conflict detected

### Task 5: Implement Interactive Prompts
- [x] Prompt for port configuration (default No)
- [x] If Yes:
  - Prompt for backend start port (default 9100)
  - Validate and handle errors
  - Prompt for frontend start port (default 9200)
  - Validate and check overlap
  - Show warnings for common port conflicts
- [x] If No:
  - Use default values silently

### Task 6: Store Results in Wizard State
- [x] Update WizardState with:
  - `port_config_custom: bool`
  - `backend_port_start: int`
  - `frontend_port_start: int`
- [x] Mark ports step as completed

### Task 7: Write Unit Tests
- [x] Test port validation (valid and invalid)
- [x] Test range overlap detection
- [x] Test common port conflict detection
- [x] Test prompt flow when configuring
- [x] Test prompt flow when using defaults
- [x] Test state update after step completion

---

## Dependencies

### Depends On
- 14.1 (Wizard Entry Point & Flow Control) - provides WizardState and flow controller
- 14.2 (Basics Configuration Step) - runs before this in wizard flow

### Blocks
- 14.10 (Summary) - displays port configuration

### Parallel With
- 14.3 (Git Integration Step) - no dependencies
- 14.5 (Task Manager Setup) - no dependencies
- 14.6 (Phase Customization) - no dependencies

---

## Developer Context

### Technical Requirements

**Port Validation Rules:**
- Must be integer between 1 and 65535
- Privileged ports (< 1024) should show warning but not block
- Reserved ports warning: 3000, 3001, 5000, 8000, 8080, 8443, 8888

**Range Overlap Detection:**
```python
def check_port_overlap(
    backend_start: int,
    frontend_start: int,
    max_concurrent: int = 10
) -> bool:
    """Check if port ranges would overlap.

    Backend range: backend_start to backend_start + max_concurrent - 1
    Frontend range: frontend_start to frontend_start + max_concurrent - 1
    """
    backend_end = backend_start + max_concurrent - 1
    frontend_end = frontend_start + max_concurrent - 1

    # Overlap if ranges intersect
    return not (backend_end < frontend_start or frontend_end < backend_start)
```

### Architecture Compliance

**Layer Boundaries:**
- Wizard step in `src/adw/cli/wizard/ports.py`
- Port allocation logic exists in `src/adw/worktree/`
- Ensure compatibility with existing port models

**Existing Port Configuration:**
- Check `src/adw/models/config.py` for `PortConfig` model
- Check `src/adw/worktree/ports.py` for existing allocation logic

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Rich | Prompts and warnings | `from rich.prompt import Prompt, Confirm` |

**Warning Display Pattern:**
```python
from rich.console import Console
from rich.panel import Panel

console = Console()

# Warning for common port
console.print(Panel(
    f"[yellow]⚠️ Port {port} is commonly used by other services.[/]\n"
    "This may cause conflicts.",
    title="Port Warning",
    border_style="yellow"
))
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
└── ports.py              # Port configuration step
```

**Files to Modify:**
```
src/adw/cli/wizard/flow.py    # Register ports step
src/adw/models/wizard.py      # Add port fields to WizardState
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
└── test_ports.py         # Port step tests
```

**Test Cases:**
```python
# Port validation
def test_valid_port():
    assert validate_port("9100") == (True, 9100)
    assert validate_port("1") == (True, 1)
    assert validate_port("65535") == (True, 65535)

def test_invalid_port():
    assert validate_port("0")[0] == False
    assert validate_port("65536")[0] == False
    assert validate_port("abc")[0] == False
    assert validate_port("-1")[0] == False

# Range overlap
def test_no_overlap():
    assert not check_port_overlap(9100, 9200, max_concurrent=10)

def test_overlap():
    assert check_port_overlap(9100, 9105, max_concurrent=10)

# Common port detection
def test_common_port_warning():
    assert is_common_port(3000)
    assert is_common_port(8080)
    assert not is_common_port(9100)
```

**Mock Requirements:**
- Mock Rich prompts for automated testing
- No external dependencies to mock

---

## Previous Story Intelligence

**From Stories 14.1-14.3:**
- WizardState model structure
- Prompt patterns with validation loops
- Warning display patterns

**Expected Pattern:**
```python
def run_ports_step(state: WizardState) -> WizardState:
    configure = Confirm.ask(
        "Configure port ranges for concurrent runs?",
        default=False
    )

    if not configure:
        # Use defaults
        state.backend_port_start = 9100
        state.frontend_port_start = 9200
    else:
        # Interactive configuration
        ...

    return state
```

---

## Git Intelligence

**Existing Port Allocation:**
- Check `src/adw/worktree/ports.py` for existing logic
- Ensure wizard produces compatible configuration

**Search Commands:**
```bash
grep -r "port" src/adw/worktree/
grep -r "9100\|9200" src/
```

---

## Latest Technical Information

**ADW Port Allocation:**
- Backend services: start at configured port, increment per concurrent run
- Frontend services: separate range to avoid collision
- Default max_concurrent: typically 5-10

**Common Development Ports:**
| Port | Common Use |
|------|------------|
| 3000 | React dev server, Rails |
| 3001 | Alternative React port |
| 5000 | Flask default |
| 8000 | Django, FastAPI |
| 8080 | Common HTTP alternative |
| 8443 | HTTPS alternative |
| 8888 | Jupyter notebooks |

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- Validation functions return (bool, result_or_error)
- Rich for all user feedback
- Warnings are yellow panels, errors are red

---

## Dev Notes

- This step is optional (default No) since most users won't need custom ports
- Port conflict warnings are informational, not blocking
- Range overlap check prevents user configuration mistakes
- Consider showing the calculated ranges in the summary

### Project Structure Notes

- ports.py follows the pattern of other wizard step modules
- Port validation may be reusable elsewhere

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.4]
- [Source: _bmad-output/architecture-summary.md#Git-Worktree-Isolation]
- [Source: src/adw/worktree/ports.py - existing port allocation]

---

## Dev Agent Record

### Context Reference

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created ports.py with PortsStepHandler class and run_ports_step function following the established wizard step pattern from basics.py
- Task 2: Implemented validate_port() function that returns (bool, int|str) tuple for validation results with range checking (1-65535) and integer parsing
- Task 3: Implemented check_port_overlap() function with DEFAULT_MAX_CONCURRENT=10, calculates range intersection and _show_overlap_warning() displays red panel when overlap detected
- Task 4: Defined COMMON_PORTS set with 3000,3001,5000,8000,8080,8443,8888. is_common_port() and check_range_conflicts() detect conflicts, _check_and_warn_common_ports() shows yellow warning panel
- Task 5: Implemented full interactive flow in run_ports_step() with Confirm.ask for opt-in, _prompt_port() with validation loop, overlap re-prompt, and warning displays. Default No returns defaults silently
- Task 6: run_ports_step() returns dict with port_config_custom, backend_port_start, frontend_port_start. Flow controller stores via state.update_config() and marks complete via state.mark_completed()
- Task 7: Added 43 unit tests in test_ports.py covering validation, overlap detection, common port detection, prompt flows, and state integration

### File List

- `src/adw/cli/wizard/ports.py` (new) - Port configuration step module
- `src/adw/cli/wizard/__init__.py` (modified) - Added exports for ports module
- `tests/unit/cli/wizard/test_ports.py` (new) - Unit tests for port configuration step

