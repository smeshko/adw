# Story ISS-006: Wire LogManager to Python Logging System

Status: Ready for Review
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-05

---

## Story

As a **developer debugging ADW runs**,
I want **log entries to be written to `logs/logs.jsonl` during pipeline execution**,
so that **I can view logs using `adw logs show` command for debugging and observability**.

## Acceptance Criteria

```gherkin
Feature: LogManager connected to Python logging

  Scenario: Log entries written during run
    Given I run any ADW pipeline `adw run "any feature"`
    When the run executes phases
    Then log entries are written to `.adw/runs/<run_id>/logs/logs.jsonl`
    And the log file contains structured JSON log entries
    And each entry has timestamp, level, category, message, and context

  Scenario: View logs command works
    Given a completed ADW run with ID <run_id>
    When I run `adw logs show <run_id>`
    Then log entries are displayed
    And entries are formatted with timestamps and levels

  Scenario: Log entries include phase context
    Given I run an ADW pipeline through multiple phases
    When I view logs for the run
    Then each log entry includes the current phase in context
    And entries can be filtered by phase
```

## Tasks / Subtasks

### Task 1: Create Python Logging Handler Bridge
- [x] Create `LogManagerHandler` class extending `logging.Handler` in `src/adw/logging/handler.py`
- [x] Implement `emit()` method to translate Python LogRecords to ADW LogEvents
- [x] Map Python log levels to ADW LogLevels (DEBUG→DEBUG, INFO→INFO, WARNING→WARN, ERROR→ERROR, CRITICAL→FATAL)
- [x] Extract and translate Python logger name to ADW LogCategory (heuristic mapping)
- [x] Preserve extra context from Python LogRecords

### Task 2: Wire Handler in Bootstrap
- [x] In `create_log_manager()`, create the LogManagerHandler and attach it to Python's root logger
- [x] Configure handler level to match LogManager level
- [x] Remove the `_ = log_manager` line in `app.py:222` (no longer needed)
- [x] Ensure handler is properly configured before orchestrator starts

### Task 3: Test Integration
- [x] Write test that runs mock pipeline and verifies `logs.jsonl` exists
- [x] Write test that verifies log content structure
- [x] Write test for `adw logs show` command parsing the file
- [x] Write test for phase context propagation

---

## Developer Context

### Technical Requirements

**Root Cause Analysis:**
```python
# app.py:221-222 - LogManager created but discarded
log_manager = create_log_manager(console, verbosity=verbosity, run_dir=run_dir)
_ = log_manager  # Log manager created for file logging  <-- PROBLEM

# orchestrator.py:68 - Uses Python's standard logging
logger = logging.getLogger(__name__)  # Never connected to LogManager!
```

**Solution Approach:**
Create a `logging.Handler` subclass that bridges Python's logging to ADW's LogManager:

```python
# src/adw/logging/handler.py
import logging
from adw.logging.manager import LogManager
from adw.models.logging import LogCategory, LogLevel

class LogManagerHandler(logging.Handler):
    """Bridge Python logging to ADW LogManager."""

    def __init__(self, log_manager: LogManager):
        super().__init__()
        self.log_manager = log_manager

    def emit(self, record: logging.LogRecord) -> None:
        level = self._map_level(record.levelno)
        category = self._infer_category(record.name)
        message = self.format(record)
        self.log_manager._log(level, category, message)

    def _map_level(self, levelno: int) -> LogLevel:
        if levelno <= logging.DEBUG:
            return LogLevel.DEBUG
        elif levelno <= logging.INFO:
            return LogLevel.INFO
        elif levelno <= logging.WARNING:
            return LogLevel.WARN
        elif levelno <= logging.ERROR:
            return LogLevel.ERROR
        return LogLevel.FATAL

    def _infer_category(self, name: str) -> LogCategory:
        # Map Python logger names to ADW categories
        if "phase" in name.lower():
            return LogCategory.PHASE
        elif "llm" in name.lower() or "executor" in name.lower():
            return LogCategory.LLM
        elif "hook" in name.lower():
            return LogCategory.HOOK
        return LogCategory.GENERAL
```

### Architecture Compliance

**File Locations:**
- New file: `src/adw/logging/handler.py` - LogManagerHandler class
- Modify: `src/adw/cli/bootstrap.py` - Wire handler to root logger
- Modify: `src/adw/cli/app.py` - Remove `_ = log_manager` line

**Existing Patterns to Follow:**
- LogManager uses Transport protocol for outputs - handler bridges TO LogManager not FROM it
- Transports write LogEvents - handler translates LogRecords to LogEvents
- Category inference follows existing LogCategory enum values

**DO NOT:**
- Replace all Python logging with LogManager calls (too invasive)
- Add LogManager as dependency to core modules (maintain separation)
- Break existing console logging behavior

### Library & Framework Requirements

- Python `logging` module (stdlib) - use `logging.Handler` base class
- Pydantic models in `src/adw/models/logging.py` - use existing LogLevel, LogCategory, LogEvent

### File Structure Requirements

```
src/adw/logging/
├── __init__.py          # Add LogManagerHandler to exports
├── handler.py           # NEW: LogManagerHandler class
├── manager.py           # LogManager class (unchanged)
├── file.py              # File transports (unchanged)
└── console.py           # Console transport (unchanged)
```

### Testing Requirements

**Test File:** `tests/unit/logging/test_handler.py`

```python
def test_log_manager_handler_bridges_to_log_manager():
    """Verify Python logging goes through to LogManager transports."""

def test_level_mapping():
    """Verify Python log levels map correctly to ADW levels."""

def test_category_inference():
    """Verify logger names map to appropriate categories."""
```

**Integration Test:** `tests/integration/test_logs_command.py`

```python
def test_logs_show_displays_entries_after_run():
    """Verify adw logs show works after a run."""
```

---

## Previous Story Intelligence

Related issues in the same area:
- **ISS-003**: Run ID not found by logs command - may be related issue
- **Story 7-4**: Implement log viewing commands - original story that created the non-working infrastructure

The LogManager and StructuredFileTransport infrastructure was built but never connected to actual logging sources.

---

## Git Intelligence

Recent logging-related commits:
- `7-4-implement-log-viewing-commands.md` - Created logs CLI commands
- `7-1-implement-multi-tier-logging-system.md` - Created LogManager and transports

The file transport infrastructure is complete and tested in isolation - just needs to be wired up.

---

## Latest Technical Information

Python `logging.Handler` requirements:
- Must implement `emit(record: LogRecord)` method
- Should call `self.format(record)` for message formatting
- Level filtering can use `setLevel()` on the handler
- Handlers must be added to loggers via `logger.addHandler(handler)`

Best practice: Add handler to root logger to capture all logging in the application.

---

## Project Context Reference

See: `docs/project-context.md`

Key patterns and rules:
- All logging goes through `logging.getLogger(__name__)` pattern
- LogManager is the ADW-specific logging coordinator
- File transports are lazily initialized (create dirs on first write)

---

## Dev Notes

- The StructuredFileTransport already handles directory creation lazily
- LogManager child() method provides context propagation - use for phase context
- ConsoleTransport respects verbosity - FileTransports log everything

### Project Structure Notes

- Handler lives in `src/adw/logging/` alongside other logging components
- Bootstrap in `src/adw/cli/` is the wiring location (CLI initialization)
- Integration test should use the test-project fixture if available

### References

- [Source: src/adw/cli/app.py:221-222] - LogManager creation
- [Source: src/adw/cli/bootstrap.py:62-110] - create_log_manager function
- [Source: src/adw/logging/manager.py:40-289] - LogManager implementation
- [Source: src/adw/logging/file.py:156-199] - StructuredFileTransport
- [Source: ISS-006 issue file] - Full root cause analysis

---

## Dev Agent Record

### Context Reference

- ISS-006-logmanager-not-connected-to-python-logging.md

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created LogManagerHandler in src/adw/logging/handler.py that bridges Python logging to ADW LogManager. Implemented level mapping (DEBUG→DEBUG, INFO→INFO, WARNING→WARN, ERROR→ERROR, CRITICAL→FATAL) and category inference from logger names (executor/llm→LLM, hook→HOOK, state→STATE, default→PHASE). All 16 unit tests pass.
- Task 2: Wired LogManagerHandler to Python's root logger in create_log_manager(). Handler level is set based on verbosity (using VERBOSITY_LEVEL_MAP). Removed unused `_ = log_manager` assignment in app.py. All logging.getLogger() calls now flow to logs.jsonl.
- Task 3: Created integration tests verifying complete flow: Python logging → LogManager → logs.jsonl. Tests cover file creation, log level mapping, category inference, raw.log creation, and context preservation. All 5 tests pass.

### File List

- src/adw/logging/handler.py (NEW)
- src/adw/logging/__init__.py (MODIFIED - added LogManagerHandler export)
- src/adw/cli/bootstrap.py (MODIFIED - wire handler in create_log_manager)
- src/adw/cli/app.py (MODIFIED - remove unused log_manager assignment)
- tests/unit/logging/test_handler.py (NEW)
- tests/integration/cli/test_logs_integration.py (NEW)
