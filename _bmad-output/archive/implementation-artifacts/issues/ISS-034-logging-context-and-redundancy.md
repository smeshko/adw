# Issue: Logging Context Missing and Redundant Messages

**ID:** ISS-034
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-21
**Reporter:** Ivo

## Related

- **Epic:** Epic 7 (Observability & Logging)
- **Story:** N/A
- **Component:** Logging System (orchestrator.py, progress.py, console.py)

## Description

Three related logging issues degrade the observability and UX of ADW runs:

### Bug 1: [phase] Placeholder in Logs
All log entries show `[phase]` as a literal string instead of the actual phase name (e.g., `[plan]`, `[build]`). The phase context is not being set when creating child loggers.

**Location:** `src/adw/core/orchestrator.py` (log context setup)

### Bug 2: Spinner/Error Message Overlap
When errors or warnings occur during LLM execution, the Rich spinner output overlaps with log messages, creating garbled output like:
```
⠴ LLM executing... · Tokens: 0 · 0:14:5920:25:17 [WARN ] [llm] Claude Code execution timed out
```

**Location:** `src/adw/core/orchestrator.py` (missing `on_llm_complete()` call before error logging)

### Bug 3: Redundant "Phase completed" Message
Two completion messages appear for every phase:
```
✓ BUILD completed (229.5s, 4 artifacts, 8589 tokens)
20:29:07 [INFO ] [phase] Phase completed
```

**Location:** `src/adw/core/orchestrator.py:1543-1545`

## Reproduction Steps

1. Run any ADW workflow: `adw run "any feature"`
2. Observe logs show `[phase]` instead of actual phase name
3. If a timeout occurs, observe spinner and error message overlap
4. Observe duplicate phase completion messages

**Evidence from project-rulebook-be run:**
```
20:10:17 [INFO ] [phase] Starting phase
20:10:17 [INFO ] [phase] Phase starting
...
20:25:17 [WARN ] [llm] Claude Code execution timed out
⠇ LLM executing... · Tokens: 0 · 0:15:0020:25:17 [ERROR] [phase] LLM execution failed
...
✓ BUILD completed (229.5s, 4 artifacts, 8589 tokens)
20:29:07 [INFO ] [phase] Phase completed
```

## Expected Behavior

1. Logs should show actual phase name: `[plan]`, `[build]`, `[validate]`, etc.
2. Spinner should be stopped before logging errors/warnings
3. Single completion message (the rich one with metrics) is sufficient

## Actual Behavior

1. All logs show `[phase]` placeholder
2. Spinner and error messages overlap, creating unreadable output
3. Two completion messages per phase

## Impact

- **Debugging difficulty**: Can't tell which phase logs belong to
- **Poor UX**: Garbled terminal output when errors occur
- **Log noise**: Redundant messages clutter output

## Workaround

None effective. Raw log files can be parsed but terminal experience is degraded.

## Environment

- **OS:** macOS / Any
- **App Version:** adw-sdk (current staging)
- **DPI Scaling:** N/A

## Evidence

### logs.jsonl showing null phase context
```json
{"timestamp":"2026-01-20T20:03:49.283323Z","level":"info","category":"phase","message":"Phase starting","context":{"run_id":null,"phase":null,"extra":{}}}
```

### Terminal output showing overlap
```
⠴ LLM executing... · Tokens: 0 · 0:14:5920:25:17 [WARN ] [llm] Claude Code execution timed out
⠇ LLM executing... · Tokens: 0 · 0:15:0020:25:17 [ERROR] [phase] LLM execution failed
```

## Proposed Fix

### 1. Set phase context when logging
**File:** `src/adw/core/orchestrator.py`
```python
# When starting a phase, create child logger with phase context
logger = self._log_manager.child(run_id=context.run_id, phase=phase)
```

### 2. Stop spinner before error logging
**File:** `src/adw/core/orchestrator.py`
```python
# In timeout/error handling code
if self.progress_display:
    self.progress_display.on_llm_complete()  # Stop spinner first
logger.warn("Claude Code execution timed out")
```

### 3. Remove or demote redundant log
**File:** `src/adw/core/orchestrator.py:1543-1545`
```python
# Change from INFO to DEBUG or remove entirely
logger.debug(  # Changed from info
    "Phase completed",
    extra={"phase": phase, "duration_ms": transition_time_ms},
)
```

## Files Affected

| File | Change |
|------|--------|
| `src/adw/core/orchestrator.py` | Set phase context, stop spinner before errors, remove redundant log |
| `src/adw/logging/handler.py` | Possibly update category inference |

## Resolution

- **Fix Story:** [ux-fix-ISS-034-logging-context-and-redundancy.md](../ux-fix-ISS-034-logging-context-and-redundancy.md)
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

These issues affect the core observability of ADW runs. While the structured log files (logs.jsonl) capture data correctly, the console output experience is degraded.
