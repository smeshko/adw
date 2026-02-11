# Tech-Spec: Clean Phase Logging Output

**Created:** 2026-01-21
**Status:** Completed

## Overview

### Problem Statement

Phase logging output is cluttered and redundant:
1. Log levels have unnecessary padding (`[INFO ]` instead of `[INFO]`)
2. Phase name `[build]` duplicates information already shown in the phase header panel
3. Run ID `(01KFGE9SBDAMJ29MH58NA0E488)` clutters every log line (useful in files, not console)
4. Log messages printed during spinner don't get a newline, causing visual corruption
5. Three redundant "starting phase" messages appear (panel + 2 log lines)

**Current output:**
```
╭─────────────────────────────────────────────────────── Phase 1/4 ────────────────────────────────────────────────────────╮
│ PLAN Starting phase...                                                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
14:10:56 [INFO ] [phase] (01KFGE9SBDAMJ29MH58NA0E488) [plan] Starting phase
14:10:56 [INFO ] [phase] (01KFGE9SBDAMJ29MH58NA0E488) [plan] Phase starting
⠧ LLM executing... · Tokens: 0 · 0:20:0014:36:35 [WARN ] [llm] Claude Code execution timed out
```

### Solution

Clean up the logging format by:
1. Removing level padding
2. Removing phase name from log context display
3. Removing run_id from console output only (preserve in file logs and run header)
4. Ensuring newline before log messages during active spinner
5. Removing the two redundant "starting phase" log statements

**Target output:**
```
╭─────────────────────────────────────────────────────── Phase 1/4 ────────────────────────────────────────────────────────╮
│ PLAN Starting phase...                                                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
⠧ LLM executing... · Tokens: 0 · 0:20:00
14:36:35 [WARN] [llm] Claude Code execution timed out
```

### Scope

**In scope:**
- Console log formatting changes
- Removing redundant phase start log messages
- Spinner/log coordination for newlines

**Out of scope:**
- File logging format (keep run_id there)
- Run header panel (keep run_id there)
- Any other logging changes

## Context for Development

### Codebase Patterns

- Logging uses a multi-transport architecture: `ConsoleTransport`, `RawFileTransport`, `StructuredFileTransport`
- `LogEvent` contains `LogContext` with `run_id`, `phase`, and `extra` fields
- Console uses Rich library for formatting (TTY) and plain text (non-TTY)
- Progress display uses Rich `Live` with `transient=True` for spinner

### Files to Modify

| File | Change |
|------|--------|
| `src/adw/logging/console.py` | Format changes: remove padding, remove phase, remove run_id |
| `src/adw/core/orchestrator.py` | Remove "Starting phase" log at line ~1493 |
| `src/adw/core/phase_runner.py` | Remove "Phase starting" log at line 155 |
| `tests/unit/logging/test_console.py` | Update tests that assert on run_id/phase in output |

### Technical Decisions

1. **Run ID removal scope:** Console only. The `_write_rich()` and `_write_plain()` methods skip the run_id output, but the `LogEvent` still contains it for file transports.

2. **Spinner newline handling:** The spinner uses `transient=True` which clears itself. When a log is printed while spinner is active, the Live display should be temporarily stopped/paused. Options:
   - Add a module-level or singleton reference to active Live display
   - Have ConsoleTransport print `\n` before messages when a spinner is known to be active
   - Use Rich's `console.print()` with proper live context handling

3. **Phase context removal:** Remove only the `[phase]` display in console output, not the phase from the LogContext (still useful for filtering/routing).

## Implementation Plan

### Tasks

- [x] Task 1: Remove level padding in console.py
  - Changed `f"[{level_name:5}]"` to `f"[{level_name}]"` in `_write_rich()` (line 169)
  - Changed `f"[{level_name:5}]"` to `f"[{level_name}]"` in `_write_plain()` (line 212)

- [x] Task 2: Remove phase name from console output
  - Removed lines 177-178 in `_write_rich()` that append phase context
  - Removed phase from context_parts in `_write_plain()` (lines 202-203)

- [x] Task 3: Remove run_id from console output
  - Removed lines 175-176 in `_write_rich()` that append run_id
  - Removed run_id from context_parts in `_write_plain()` (lines 199-200)

- [x] Task 4: Remove redundant phase start logs
  - Removed the log statement at `orchestrator.py:1493`
  - Removed the log statement at `phase_runner.py:155`

- [x] Task 5: Handle spinner/log newline coordination
  - Added module-level `_active_live` reference in console.py
  - Added `set_active_live()` and `get_active_live()` functions for coordination
  - ConsoleTransport now stops active Live display before writing to prevent overlap
  - ProgressDisplay registers/unregisters Live display on spinner start/stop

- [x] Task 6: Update tests
  - Updated `test_includes_run_id_when_present` to `test_excludes_run_id_from_console`
  - Updated `test_includes_phase_when_present` to `test_excludes_phase_from_console`
  - Added `TestLogLevelFormatting` class with tests for no-padding verification

### Acceptance Criteria

- [x] AC 1: Log levels show without padding: `[INFO]` not `[INFO ]`
- [x] AC 2: Phase name `[build]` does not appear in console log lines
- [x] AC 3: Run ID does not appear in console log lines
- [x] AC 4: Run ID still appears in:
  - Run header panel
  - File logs (logs.txt and logs.jsonl)
- [x] AC 5: Only one "starting phase" indicator appears (the panel)
- [x] AC 6: Log messages during spinner appear on new line, not concatenated
- [x] AC 7: All existing tests pass (with updates for new format)

## Additional Context

### Dependencies

- No new dependencies required
- Existing: Rich library for console formatting

### Testing Strategy

1. Unit tests: Update `tests/unit/logging/test_console.py`
   - `test_includes_run_id_when_present` - update to verify run_id NOT in output
   - `test_includes_phase_when_present` - update to verify phase NOT in output
   - Add test verifying level has no padding

2. Manual testing:
   - Run `adw run` and verify log format
   - Verify spinner/log interaction works correctly
   - Verify file logs still contain run_id and phase

### Notes

- The `LogEvent` and `LogContext` models remain unchanged - this is purely a display change
- File transports (`RawFileTransport`, `StructuredFileTransport`) are not modified
- The phase color change (originally item 4) is no longer needed since we're removing the phase display entirely
