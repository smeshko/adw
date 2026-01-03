# Story 7.1: Implement Multi-Tier Logging System

Status: ready-for-dev
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-03

---

## Story

As a developer,
I want logs written to console, raw file, and structured JSONL,
so that I have appropriate output for different use cases.

## Acceptance Criteria

**Given** any log message
**When** logged
**Then** it appears in console (via Rich), raw.log, and logs.jsonl

**Given** console output
**When** TTY is detected
**Then** Rich formatting with colors is used

**Given** console output
**When** non-TTY (piped/redirected)
**Then** plain text without colors/animations (UX-7)

**Given** structured log entry
**When** written to JSONL
**Then** it includes: timestamp, level, category, message, context fields

**Given** the LogCategory enum
**When** logging
**Then** categories include: PHASE, LLM, HOOK, STATE, ERROR, PERFORMANCE

## Tasks / Subtasks

### Task 1: Create Logging Models (models/logging.py)
- [x] Create `LogLevel` enum (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
- [x] Create `LogCategory` enum per architecture spec
- [x] Create `LogEvent` Pydantic model with all fields
- [x] Create `LogContext` model for scoped context
- [x] Export from `models/__init__.py`

### Task 2: Implement Console Transport (logging/console.py)
- [x] Create `ConsoleTransport` class using Rich Console
- [x] Implement TTY detection via `sys.stdout.isatty()`
- [x] Use Rich formatting when TTY, plain text otherwise
- [x] Implement `write(event: LogEvent)` method
- [x] Support styling based on log level

### Task 3: Implement File Transport (logging/file.py)
- [x] Create `RawFileTransport` class for raw.log
- [x] Create `StructuredFileTransport` class for logs.jsonl
- [x] Implement atomic appends with file locking
- [x] Handle file rotation setup (optional for MVP) - deferred to future story
- [x] Ensure non-blocking writes per NFR3

### Task 4: Implement Log Manager (logging/manager.py)
- [x] Create `LogManager` singleton/global instance
- [x] Implement transport registration
- [x] Create `child(context)` method for scoped loggers
- [x] Implement level methods: trace, debug, info, warn, error, fatal
- [x] Route events to all registered transports

### Task 5: Update Package Exports (logging/__init__.py)
- [x] Export LogManager, transports, models
- [x] Create convenience `get_logger()` function
- [x] Document module-level docstring

### Task 6: Write Unit Tests
- [ ] Test LogEvent model creation and serialization
- [ ] Test ConsoleTransport TTY/non-TTY behavior (mock stdout)
- [ ] Test file transports write correctly
- [ ] Test LogManager routes to all transports
- [ ] Test child() context inheritance

---

## Relevant Feature Documentation

<!-- Logging architecture is fully specified in docs/arch-logging.md -->

---

## Developer Context

### Technical Requirements

**From PRD FR42-FR53 (Observability):**
- Multi-layer logging with console, raw files, structured JSONL (FR42-FR44)
- Log events include timestamp, level, category, message, context (FR45)
- Console output uses Rich for formatting (FR46)

**From NFR Requirements:**
- NFR3: Non-blocking artifact/log writes
- NFR10: Actionable error messages with Rich formatting
- NFR14: No secrets in logs (prepare for Story 7.6 integration)

### Architecture Compliance

**Module Location:** `src/adw/logging/`

**Files to Create:**
```
src/adw/logging/
├── __init__.py     # Package exports (update existing)
├── manager.py      # LogManager central hub
├── console.py      # Rich console transport
└── file.py         # Raw + structured file transports

src/adw/models/
└── logging.py      # LogEvent, LogLevel, LogCategory models (NEW)
```

**Dependencies:**
- Rich for console output (already installed)
- filelock for atomic file writes (already installed)
- Pydantic for models (already installed)

**Integration Points:**
- Orchestrator will use LogManager for run-level logging
- PhaseRunner will use child loggers for phase-scoped logging
- Executors will use for LLM interaction logging (Story 7.3)

### Library & Framework Requirements

**Rich Console (14.1.0):**
```python
from rich.console import Console

# Auto-detect TTY
console = Console(force_terminal=None)  # Uses isatty()

# Or explicit TTY check
if sys.stdout.isatty():
    console.print("[bold green]✓[/] Success")
else:
    print("✓ Success")  # Plain text
```

**Pydantic Models:**
```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class LogLevel(str, Enum):
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"
```

**JSONL File Format:**
```python
# One JSON object per line
with open("logs.jsonl", "a") as f:
    f.write(event.model_dump_json() + "\n")
```

### File Structure Requirements

**Naming Conventions:**
- Files: snake_case (e.g., `log_manager.py` or `manager.py`)
- Classes: PascalCase (e.g., `LogManager`, `ConsoleTransport`)
- Functions: snake_case (e.g., `get_logger()`)
- Constants: SCREAMING_SNAKE_CASE (e.g., `DEFAULT_LOG_LEVEL`)

**Location Rules:**
- All models in `src/adw/models/` - create `logging.py`
- All logging logic in `src/adw/logging/`
- Tests in `tests/unit/logging/`

### Testing Requirements

**Test File Structure:**
```
tests/unit/
├── logging/
│   ├── __init__.py
│   ├── test_manager.py
│   ├── test_console.py
│   └── test_file.py
└── models/
    └── test_logging.py
```

**Testing Patterns:**
- Use `pytest` fixtures for console/file setup
- Mock `sys.stdout.isatty()` for TTY testing
- Use `tmp_path` fixture for file transport tests
- Test model serialization to JSON

**Coverage Target:** >80%

---

## Previous Story Intelligence

This is the first story in Epic 7. Relevant patterns from previous epics:

**From Story 6.1-6.6 (Run Management):**
- Run directory structure: `.agent/runs/<run_id>/`
- Log files should go in `.agent/runs/<run_id>/logs/`
- Use ULID for event IDs (see `src/adw/utils/ulid.py`)

**From Story 4.1 (Run Directory):**
- `RunDirectory` class manages directory structure
- `create()` method creates subdirectories including `logs/`
- Reference: `src/adw/core/run_directory.py`

---

## Git Intelligence

Recent commits show patterns for:
- Pydantic model creation in `models/`
- Protocol-based abstractions in `executors/`
- Use of Rich Console in `cli/` modules

---

## Latest Technical Information

**Rich 14.1.0:**
- `Console(force_terminal=True/False/None)` - None auto-detects
- `Console.is_terminal` property for checking
- `console.print()` with markup for styled output

**Pydantic v2:**
- Use `model_dump_json()` not deprecated `json()`
- Use `Field(default_factory=...)` for mutable defaults
- ISO 8601 timestamps with `datetime.now(UTC).isoformat()`

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models in `src/adw/models/` - NO exceptions
- Use Rich for all CLI output - never bare `print()`
- Structured logging with context fields - no f-string log messages
- Full type annotations required
- Custom exception hierarchy for errors

---

## Dev Notes

- LogManager should be singleton-like (module-level instance)
- Console transport must handle both TTY and non-TTY gracefully
- File transports should use filelock for concurrent write safety
- Prepare for verbosity filtering (Story 7.2) but don't implement yet
- Prepare for secret redaction (Story 7.6) but don't implement yet

### Project Structure Notes

- Logging module exists but only has empty `__init__.py`
- Must create new files: `manager.py`, `console.py`, `file.py`
- Must add `logging.py` to models directory

### References

- [Source: docs/arch-logging.md] - Full logging architecture specification
- [Source: _bmad-output/architecture.md#Observability] - FR42-FR53 requirements
- [Source: _bmad-output/project-context.md] - Critical implementation rules

---

## Dependencies

- **Depends On:** None (foundation story)
- **Blocks:** Story 7.2, Story 7.3, Story 7.4, Story 7.5, Story 7.6
- **Can Parallel With:** None

### Dependency Rationale
- All other stories in Epic 7 depend on the logging infrastructure this story creates
- This is the foundation story that must be completed first

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

### Debug Log References

### Completion Notes List

- Task 1: Created LogLevel (6 levels), LogCategory (6 categories), LogEvent, and LogContext Pydantic models with full type annotations, docstrings, and serialization support. 22 unit tests passing with 97% coverage.
- Task 2: Implemented ConsoleTransport with TTY detection, Rich formatting for TTY output, plain text for non-TTY (UX-7 compliant). Level-based styling with distinct ERROR/FATAL formatting. 19 unit tests passing with 94% coverage.
- Task 3: Implemented RawFileTransport (human-readable) and StructuredFileTransport (JSONL) with file locking for concurrent write safety. Auto-creates parent directories. 26 unit tests passing with 96% coverage.
- Task 4: Implemented LogManager with transport registration, level filtering, child() for scoped loggers with context inheritance, and level methods (trace, debug, info, warn, error, fatal). Transport protocol for extensibility. 24 unit tests passing with 98% coverage.
- Task 5: Updated logging/__init__.py with all exports, get_logger() convenience function, configure_default_logger() for quick setup, and comprehensive module docstring. 20 unit tests passing with 100% coverage.

### File List

- src/adw/models/logging.py (NEW)
- src/adw/models/__init__.py (MODIFIED)
- tests/unit/models/test_logging.py (NEW)
- src/adw/logging/console.py (NEW)
- tests/unit/logging/__init__.py (NEW)
- tests/unit/logging/test_console.py (NEW)
- src/adw/logging/file.py (NEW)
- tests/unit/logging/test_file.py (NEW)
- src/adw/logging/manager.py (NEW)
- tests/unit/logging/test_manager.py (NEW)
- src/adw/logging/__init__.py (MODIFIED)
- tests/unit/logging/test_package.py (NEW)

