# Story ISS-034: Fix Logging Context and Redundant Messages

Status: done
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-21

---

## Story

As a **developer running ADW pipelines**,
I want **log entries to show the actual phase name and display cleanly without overlapping spinner output**,
so that **I can effectively debug runs by knowing which phase each log belongs to and see clean error messages**.

## Acceptance Criteria

```gherkin
Feature: Phase context in logs and clean output

  Scenario: Log entries show actual phase name
    Given I run an ADW pipeline `adw run "any feature"`
    When I view the console or log file output
    Then log entries show the actual phase name like "[plan]" or "[build]"
    And entries do NOT show "[phase]" as a literal placeholder

  Scenario: Spinner stopped before error logging
    Given an LLM execution times out during a phase
    When the timeout error is logged
    Then the spinner is stopped before the error message appears
    And the error message displays cleanly on its own line
    And there is no overlapping output like "⠴ LLM executing...20:25:17 [WARN]"

  Scenario: Single phase completion message
    Given a phase completes successfully
    When the completion is displayed
    Then only ONE completion message appears (the Rich formatted one)
    And there is NO redundant "[INFO ] [phase] Phase completed" log line

  Scenario: Structured log files have phase context
    Given a completed run with logs.jsonl
    When I examine the log file contents
    Then each log entry has "context.phase" populated with actual phase name
    And the phase field is NOT null
```

## Tasks / Subtasks

### Task 1: Set Phase Context When Logging
- [x] Identify where `PhaseRunner` or `Orchestrator` creates/uses loggers
- [x] Ensure child logger is created with phase context before phase execution
- [x] Pass phase name to `LogManager.child(phase=phase)` when starting each phase
- [x] Verify LogContext flows through to all log entries during that phase

### Task 2: Stop Spinner Before Error Logging
- [x] In `Orchestrator._execute_phase_with_transitions()`, locate timeout/error handling code
- [x] Call `self.progress_display.on_llm_complete()` BEFORE any error logging
- [x] Verify this applies to both timeout errors and LLM execution failures
- [x] Ensure spinner cleanup is idempotent (safe to call multiple times)

### Task 3: Remove or Demote Redundant Log
- [x] Locate the "Phase completed" log at `orchestrator.py:1542-1545`
- [x] Change from `logger.info()` to `logger.debug()`
- [x] OR remove the log entirely since Rich progress display provides the same info
- [x] Ensure no other duplicate completion messages exist

### Task 4: Test Changes
- [x] Write test that verifies phase context appears in log entries
- [x] Write test that spinner is stopped before error display (mock ProgressDisplay)
- [x] Write test that only one completion message appears per phase
- [x] Run full integration test with `adw run` to verify clean output

---

## Relevant Feature Documentation

The following documentation from CONDITIONAL_DOCS.md is relevant to this story:

**Orchestrator Documentation:**
- `docs/arch-orchestrator.md` - Orchestrator Core deep dive with context manager, phase runner flow

**Logging Documentation:**
- Story ISS-006 established the LogManagerHandler bridge that connects Python logging to ADW's LogManager

---

## Developer Context

### Technical Requirements

**Root Cause Analysis:**

**Bug 1: [phase] Placeholder in Logs**
The `LogManager.child()` method is NOT being called with phase context. Looking at `orchestrator.py`:
```python
# orchestrator.py:85
logger = logging.getLogger(__name__)  # Module-level logger - no phase context!

# orchestrator.py:1492-1494
logger.info(
    "Starting phase",
    extra={"phase": phase, "run_id": context.run_id},  # Extra doesn't set LogContext!
)
```

The `extra` dict in Python logging doesn't propagate to ADW's `LogContext`. The logging bridge (`LogManagerHandler`) doesn't extract `extra` fields.

**Solution:** Create a phase-specific child LogManager at phase start and use it for all phase logging.

**Bug 2: Spinner/Error Overlap**
In `_execute_phase_with_transitions()`:
```python
# orchestrator.py:1555-1559
except ADWError as e:
    # Notify progress display of phase error (Story 5.5)
    if self.progress_display:
        self.progress_display.on_phase_error(phase, e)  # Calls on_llm_complete() inside
    raise
```

The `on_phase_error()` calls `on_llm_complete()`, but if error logging happens BEFORE this (e.g., in `PhaseRunner`), the spinner is still active. Need to ensure spinner is stopped BEFORE any error logging.

**Bug 3: Redundant Completion Log**
```python
# orchestrator.py:1541-1545
transition_time_ms = (time.monotonic() - transition_start) * 1000
logger.info(
    "Phase completed",
    extra={"phase": phase, "duration_ms": transition_time_ms},
)
```

This duplicates the Rich progress display at line 1507-1508:
```python
if self.progress_display:
    self.progress_display.on_phase_complete(phase, result)  # Shows: ✓ BUILD completed (229.5s...)
```

### Architecture Compliance

**File Locations:**
- Primary: `src/adw/core/orchestrator.py` - Phase context setup, spinner cleanup, log removal
- Secondary: `src/adw/logging/handler.py` - May need to extract extra fields (optional enhancement)

**Existing Patterns to Follow:**
- `LogManager.child(phase=phase)` creates a context-aware child logger
- `ProgressDisplay.on_llm_complete()` is idempotent (safe to call multiple times)
- Phase-specific logging should use structured logging with context

**DO NOT:**
- Remove all logger.info() calls (some are valuable for logs.jsonl)
- Break the structured file logging (logs.jsonl must still work)
- Add spinner management code throughout the codebase (keep centralized)

### Library & Framework Requirements

- Python `logging` module (stdlib) - use `extra` dict for structured data
- Rich library - `Live`, `Progress` components for spinner management
- ADW `LogManager` - use `child()` method for phase context

### File Structure Requirements

```
src/adw/
├── core/
│   └── orchestrator.py     # MODIFY: Fix all three bugs
├── cli/
│   └── progress.py         # READ-ONLY: Understand spinner lifecycle
└── logging/
    ├── manager.py          # READ-ONLY: Understand child() method
    ├── handler.py          # OPTIONAL: Extract extra fields from LogRecord
    └── console.py          # READ-ONLY: Understand context display
```

### Testing Requirements

**Test File:** `tests/unit/core/test_orchestrator.py`

```python
def test_phase_context_in_logs():
    """Verify logs include phase name in context."""
    # Mock LogManager and verify child(phase=...) is called

def test_spinner_stopped_before_error_log():
    """Verify spinner cleanup happens before error logging."""
    # Mock ProgressDisplay, trigger error, verify on_llm_complete() called first

def test_single_completion_message():
    """Verify only one completion message per phase."""
    # Count completion-related log calls
```

**Integration Test:** `tests/integration/cli/test_logging_integration.py`

```python
def test_logs_show_actual_phase_names():
    """Verify logs.jsonl has phase context."""
    # Run a phase, parse logs.jsonl, verify context.phase is populated
```

---

## Previous Story Intelligence

**ISS-006 (LogManager Bridge):** Established the `LogManagerHandler` that bridges Python logging to ADW's LogManager. The handler currently ignores `extra` dict fields - this could be enhanced to extract phase context.

**Story 7-1 (Multi-tier Logging):** Created the LogManager with `child()` method for context propagation. This is the intended mechanism for phase context.

**Story 5-5 (Phase Progress Display):** Implemented the Rich progress display with spinner. The `on_llm_complete()` method is designed to be called to stop the spinner.

Key learning: The logging infrastructure is well-designed but the wiring between orchestrator and LogManager is incomplete. The `child()` method exists but isn't being used for phase context.

---

## Git Intelligence

Recent relevant commits:
- `589a051 fix(ISS-031)` - PR creation timing changes in orchestrator
- `251b6c1 fix(ISS-029)` - Phase config handling in orchestrator
- `1c46dfe feat(story-15-8)` - Init wizard integration

The orchestrator has been actively modified. Be careful to preserve existing functionality while making these fixes.

---

## Latest Technical Information

**Rich Progress/Live Context:**
- `Live.stop()` and `Progress` are used via `ProgressDisplay` for spinner management
- The `transient=True` flag makes spinner output disappear after completion
- If spinner isn't stopped properly, its output persists and overlaps with subsequent output

**Python Logging Extra Fields:**
- The `extra` dict in `logger.info("msg", extra={...})` is available as `record.__dict__`
- `LogManagerHandler` could be enhanced to extract these into `LogContext.extra`
- However, the cleaner solution is to use `LogManager.child()` directly

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:
- All models in `src/adw/models/`
- Use Rich for CLI output (`console.print()`)
- Structured logging: `logger.info("message", extra={"key": value})`
- Full type annotations required

---

## Dev Notes

**Implementation Strategy:**

1. **Phase Context (Task 1):** The cleanest fix is to NOT rely on Python logging `extra` dict at all. Instead:
   - Create a phase-scoped `LogManager` child at phase start
   - Use this child logger for all phase-related logs
   - This requires passing the child logger through to PhaseRunner

2. **Spinner Cleanup (Task 2):** Add explicit `on_llm_complete()` call in error paths:
   ```python
   except ADWError as e:
       # Stop spinner FIRST before any error logging
       if self.progress_display:
           self.progress_display.on_llm_complete()
       logger.error("LLM execution failed", extra={"phase": phase})
       if self.progress_display:
           self.progress_display.on_phase_error(phase, e)
       raise
   ```

3. **Redundant Log (Task 3):** Simple change from `logger.info()` to `logger.debug()` at line 1542.

### Project Structure Notes

- The `orchestrator.py` is a large file (~1983 lines) - be surgical with changes
- `ProgressDisplay` is in CLI layer, `Orchestrator` is in core - maintain separation
- Phase context should flow through `LogContext.phase` field, not `extra` dict

### References

- [Source: src/adw/core/orchestrator.py:85] - Module-level logger creation
- [Source: src/adw/core/orchestrator.py:1492-1495] - Starting phase log (missing context)
- [Source: src/adw/core/orchestrator.py:1541-1545] - Redundant completion log
- [Source: src/adw/core/orchestrator.py:1555-1559] - Error handling (spinner issue)
- [Source: src/adw/cli/progress.py:177-183] - on_llm_complete() implementation
- [Source: src/adw/logging/manager.py:162-194] - child() method for context
- [Source: src/adw/logging/console.py:174-178] - Context display in logs
- [Source: ISS-034 issue file] - Full bug documentation with evidence

---

## Dev Agent Record

### Context Reference

- ISS-034-logging-context-and-redundancy.md

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

