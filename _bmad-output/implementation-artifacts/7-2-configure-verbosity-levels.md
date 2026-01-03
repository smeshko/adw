# Story 7.2: Configure Verbosity Levels

Status: done
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-03

---

## Story

As a user,
I want to control log verbosity,
so that I see the right amount of detail for my needs.

## Acceptance Criteria

**Given** command with `-q` or `--quiet`
**When** executing
**Then** only errors and final results are shown

**Given** command with no flags (default)
**When** executing
**Then** phase progress and key events are shown

**Given** command with `-v` or `--verbose`
**When** executing
**Then** detailed execution info including hook output is shown

**Given** command with `--trace`
**When** executing
**Then** all debug information including template rendering is shown

**Given** verbosity setting
**When** applied
**Then** it affects console output only, not file logs

## Tasks / Subtasks

### Task 1: Create Verbosity Model (models/logging.py)
- [x] Add `Verbosity` enum (QUIET, NORMAL, VERBOSE, TRACE)
- [x] Add verbosity-to-level mapping
- [x] Document level filtering rules

### Task 2: Add CLI Verbosity Options (cli/app.py)
- [x] Add `-q/--quiet` flag (Verbosity.QUIET)
- [x] Add `-v/--verbose` flag (Verbosity.VERBOSE)
- [x] Add `--trace` flag (Verbosity.TRACE)
- [x] Default to Verbosity.NORMAL
- [x] Store in Typer context for subcommands

### Task 3: Implement Console Filtering (logging/console.py)
- [x] Add verbosity parameter to ConsoleTransport
- [x] Implement `should_log(level, verbosity)` filtering
- [x] QUIET: only ERROR and FATAL
- [x] NORMAL: INFO and above
- [x] VERBOSE: DEBUG and above
- [x] TRACE: everything including TRACE

### Task 4: Configure Log Manager (logging/manager.py)
- [x] Add `set_verbosity(level)` method to LogManager
- [x] Apply verbosity to console transport only
- [x] File transports always log everything

### Task 5: Update CLI Commands
- [x] Wire verbosity from CLI context to LogManager
- [x] Ensure `adw run`, `adw resume`, etc. respect verbosity
- [x] Test all verbosity levels work correctly

### Task 6: Write Unit Tests
- [x] Test Verbosity enum values
- [x] Test CLI flag parsing for all verbosity options
- [x] Test console filtering at each verbosity level
- [x] Test file transports ignore verbosity
- [x] Integration test: run command with different verbosity flags

---

## Relevant Feature Documentation

<!-- Verbosity modes defined in docs/arch-logging.md -->

---

## Developer Context

### Technical Requirements

**From PRD:**
- CLI flags for verbosity control (FR46)
- Verbosity affects console only, not file logs (FR47)

**Verbosity Mapping:**
| Flag | Verbosity | Console Shows |
|------|-----------|---------------|
| `-q/--quiet` | QUIET | Errors only |
| (default) | NORMAL | Info + milestones |
| `-v/--verbose` | VERBOSE | Debug + detailed |
| `--trace` | TRACE | Everything |

### Architecture Compliance

**Files to Modify:**
```
src/adw/models/logging.py     # Add Verbosity enum (from Story 7.1)
src/adw/logging/console.py    # Add verbosity filtering
src/adw/logging/manager.py    # Add set_verbosity method
src/adw/cli/app.py            # Add CLI flags
```

**Integration:**
- Verbosity is set at CLI entry point
- Passed to LogManager on initialization
- Only ConsoleTransport respects verbosity
- File transports always capture everything

### Library & Framework Requirements

**Typer CLI Options:**
```python
import typer

app = typer.Typer()

@app.callback()
def main(
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Errors only"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Detailed output"),
    trace: bool = typer.Option(False, "--trace", help="Full debug output"),
):
    """ADW - Agentic Development Workflow SDK"""
    # Determine verbosity
    if quiet:
        verbosity = Verbosity.QUIET
    elif trace:
        verbosity = Verbosity.TRACE
    elif verbose:
        verbosity = Verbosity.VERBOSE
    else:
        verbosity = Verbosity.NORMAL

    # Store in context
    ctx = typer.get_current_context()
    ctx.obj = {"verbosity": verbosity}
```

**Level Filtering Logic:**
```python
def should_log(event_level: LogLevel, verbosity: Verbosity) -> bool:
    level_thresholds = {
        Verbosity.QUIET: LogLevel.ERROR,
        Verbosity.NORMAL: LogLevel.INFO,
        Verbosity.VERBOSE: LogLevel.DEBUG,
        Verbosity.TRACE: LogLevel.TRACE,
    }
    threshold = level_thresholds[verbosity]
    return event_level.value >= threshold.value
```

### File Structure Requirements

**CLI Flag Pattern:**
- Short flags: single letter (-q, -v)
- Long flags: kebab-case (--quiet, --verbose, --trace)
- Mutual exclusivity: -q and -v are mutually exclusive

### Testing Requirements

**Test Cases:**
```python
def test_quiet_only_shows_errors():
    # Given console with QUIET verbosity
    # When logging INFO, WARN, ERROR
    # Then only ERROR appears in output

def test_verbose_shows_debug():
    # Given console with VERBOSE verbosity
    # When logging DEBUG message
    # Then message appears in output

def test_file_ignores_verbosity():
    # Given file transport with QUIET verbosity set
    # When logging DEBUG message
    # Then message still written to file
```

---

## Previous Story Intelligence

**From Story 7.1:**
- LogLevel enum is defined in `models/logging.py`
- ConsoleTransport class in `logging/console.py`
- LogManager class in `logging/manager.py`
- These must exist before this story can be implemented

**Dependency:** Story 7.1 must be completed first.

---

## Git Intelligence

**Existing CLI patterns:**
- `cli/app.py` defines main Typer app
- Callback pattern used for global options
- Context object for sharing state between commands

---

## Latest Technical Information

**Typer 0.21.0:**
- Use `typer.Option()` for flags
- `typer.get_current_context()` for accessing context
- `ctx.obj` for storing custom data
- Subcommands inherit parent context

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- CLI commands in kebab-case
- Options with double-dash + kebab-case
- Short options as single letter

---

## Dev Notes

- This story depends on Story 7.1 being complete
- Verbosity is a console-only concept
- File logs always capture everything for debugging
- Consider environment variable override (ADW_VERBOSITY) for CI

### Project Structure Notes

- Modify existing files from Story 7.1
- Add CLI flags to main app callback
- No new files created

### References

- [Source: docs/arch-logging.md#Verbosity-Modes] - Verbosity specification
- [Source: _bmad-output/architecture.md] - CLI conventions
- [Source: src/adw/cli/app.py] - Existing CLI structure

---

## Dependencies

**Depends On:**
- Story 7.1: Multi-Tier Logging System (provides LogManager, ConsoleTransport)

**Blocks:** None

**Parallel With:**
- Story 7.3, 7.5, 7.6 can run in parallel after 7.1 completes

---

## Dev Agent Record

### Context Reference
- Story 7.1 provides base LogManager and ConsoleTransport
- Architecture spec defines verbosity levels in docs/arch-logging.md

### Agent Model Used
claude-opus-4-5-20251101

### Debug Log References
N/A

### Completion Notes List
- Verbosity enum added to models/logging.py alongside LogLevel
- CLI flags implemented in app.py callback with mutual exclusivity validation
- Console filtering uses VERBOSITY_LEVEL_MAP for threshold comparison
- File transports unaffected by verbosity (always log everything)
- Tests cover all verbosity levels and CLI flag combinations

### File List
- `src/adw/models/logging.py` - Added Verbosity enum and VERBOSITY_LEVEL_MAP
- `src/adw/cli/app.py` - Added -q/--quiet, -v/--verbose, --trace flags
- `src/adw/cli/bootstrap.py` - Added create_log_manager with verbosity support
- `src/adw/cli/resume.py` - Updated to use global verbosity from context
- `src/adw/logging/console.py` - Added should_log() and verbosity filtering
- `src/adw/logging/manager.py` - Added set_verbosity() method
- `tests/unit/models/test_logging.py` - Added Verbosity enum tests
- `tests/unit/cli/test_verbosity.py` - Added CLI verbosity flag tests + resume tests
- `tests/unit/logging/test_console.py` - Added console verbosity filtering tests
- `tests/unit/logging/test_manager.py` - Added LogManager verbosity tests
- `tests/unit/cli/test_run.py` - Updated for global verbosity flags

