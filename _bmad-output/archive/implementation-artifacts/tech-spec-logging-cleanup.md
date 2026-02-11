# Tech-Spec: ADW Pipeline Logging Cleanup

**Created:** 2026-01-22
**Status:** Completed
**Author:** Ivo

## Overview

### Problem Statement

The ADW pipeline output is noisy and confusing, making it difficult for users to follow run progress. Key issues:

1. **HTTP Request logs at INFO level** - httpx library logs every API call, cluttering output
2. **Issue UUIDs in log messages** - Messages like "Added label 'adw:running' to issue 23399760-fc82-49b7-b195-817295883263" are unnecessarily verbose
3. **Redundant sync logs** - Both `linear.py` and `sync.py` log the same operations
4. **Incorrect log ordering** - Phase completion message ("✓ PLAN completed") appears before sync operations finish, causing visual jumble
5. **Template warnings lack context** - "Unknown template variable left as-is" doesn't indicate which template file

### Solution

Clean up logging by:
- Simplifying log messages to remove technical details (UUIDs)
- Removing redundant logs from `sync.py` (keep `linear.py` as source of truth)
- Reordering orchestrator to sync before displaying completion
- Enhancing template warnings with file context

### Scope

**In Scope:**
- Log message simplification in `linear.py`
- Redundant log removal in `sync.py`
- Log ordering fix in `orchestrator.py`
- Template warning enhancement in `template.py`
- Verify httpx logging suppression

**Out of Scope:**
- New logging features
- Log format changes
- Logging infrastructure changes

## Context for Development

### Codebase Patterns

**Logging Pattern:**
```python
import logging
logger = logging.getLogger(__name__)

# Standard info log with extra context
logger.info("Action completed", extra={"key": "value"})

# Warning with string formatting
logger.warning("Failed to do X: %s", error_message)
```

**Test Pattern:**
```python
def test_something(caplog):
    with caplog.at_level(logging.INFO):
        # action
        assert "Expected message" in caplog.text
```

### Files to Reference

| File | Line(s) | Current Behavior |
|------|---------|------------------|
| `src/adw/task_managers/linear.py` | 219-223 | `"Updated Linear issue %s to state '%s'"` |
| `src/adw/task_managers/linear.py` | 360-363 | `"Closed Linear issue %s..."` |
| `src/adw/task_managers/linear.py` | 437-441 | `"Added label '%s' to issue %s"` |
| `src/adw/task_managers/linear.py` | 463-466 | `"Removed label '%s' from issue %s"` |
| `src/adw/task_managers/linear.py` | 487-490 | `"Posted comment to issue %s"` |
| `src/adw/task_managers/sync.py` | 200-207 | `"Status synced to task manager"` (redundant) |
| `src/adw/task_managers/sync.py` | 355-358 | `"Comment posted to task manager"` (redundant) |
| `src/adw/core/orchestrator.py` | 844-862 | `on_phase_complete` before `post_phase_comment` |
| `src/adw/commands/template.py` | 269-276 | `"Missing artifact reference in template"` |
| `src/adw/commands/template.py` | 568-572 | `"Unknown template variable left as-is"` |
| `src/adw/cli/progress.py` | 299-303 | `show_pipeline_summary()` with `pr_result` param |
| `src/adw/core/extensions/document.py` | TBD | `DocumentExtension.on_complete()` - creates PR |
| `src/adw/core/run_lifecycle.py` | TBD | `finalize_success()` - passes PR result to summary |

### Technical Decisions

1. **Remove UUIDs from user-facing logs** - UUIDs are for debugging; keep in `extra={}` dict for structured logging
2. **Remove redundant sync.py logs entirely** - Don't downgrade to DEBUG, just remove (linear.py already logs)
3. **Sync before display** - Move `post_phase_comment` before `on_phase_complete` in orchestrator
4. **Add template path to warnings** - Include which template file has the issue

## Implementation Plan

### Tasks

- [x] **Task 1:** Simplify `linear.py` log messages
  - Line 219-223: Change `"Updated Linear issue %s to state '%s'"` → `"Updated state to '%s'"`
  - Line 360-363: Change `"Closed Linear issue %s..."` → `"Closed issue"`
  - Line 437-441: Change `"Added label '%s' to issue %s"` → `"Added label '%s'"`
  - Line 463-466: Change `"Removed label '%s' from issue %s"` → `"Removed label '%s'"`
  - Line 487-490: Change `"Posted comment to issue %s"` → `"Posted sync comment"`

- [x] **Task 2:** Remove redundant logs from `sync.py`
  - Line 200-207: Remove `logger.info("Status synced to task manager", ...)` entirely
  - Line 355-358: Remove `logger.info("Comment posted to task manager", ...)` entirely

- [x] **Task 3:** Fix log ordering in `orchestrator.py`
  - Lines 844-862: Move `post_phase_comment` block BEFORE `on_phase_complete` block
  - This ensures sync operations complete before "✓ PHASE completed" is displayed

- [x] **Task 4:** Enhance template warnings in `template.py`
  - Line 269-276: Add template file path to "Missing artifact reference" warning
  - Line 568-572: Add variable context to "Unknown template variable" warning
  - Consider adding: which template file, which phase, what variable was expected

- [x] **Task 5:** Verify httpx logging suppression
  - Check that recent commit `411a9da` properly suppresses httpx logs
  - If not working, add `logging.getLogger("httpx").setLevel(logging.WARNING)` to CLI entry

- [x] **Task 6:** Fix PR link in pipeline summary
  - `progress.py` `show_pipeline_summary()` already supports `pr_result` parameter (lines 299-303)
  - Investigate: Is `pr_result` being passed correctly from `DocumentExtension`?
  - Trace the flow: `DocumentExtension.on_complete()` → `RunLifecycle.finalize_success()` → `show_pipeline_summary()`
  - Ensure PR URL appears in the Pipeline Summary panel when PR is created

- [x] **Task 7:** Update tests
  - Update any tests that assert on the old log message formats
  - Verify no regressions in test suite

### Acceptance Criteria

- [x] **AC 1:** Given a pipeline run, when Linear operations occur, then log messages do not contain UUIDs
- [x] **AC 2:** Given a pipeline run, when status sync occurs, then only one log message appears per operation (from linear.py)
- [x] **AC 3:** Given a phase completion, when sync comment is posted, then "Posted sync comment" appears BEFORE "✓ PHASE completed"
- [x] **AC 4:** Given a template with unknown variable, when rendered, then warning includes template file path
- [x] **AC 5:** Given a pipeline run, when Linear API is called, then no "HTTP Request: POST" messages appear at INFO level
- [x] **AC 6:** Given a successful run with PR creation, when pipeline summary is displayed, then PR URL appears in the summary panel
- [x] **AC 7:** All existing tests pass after changes

## Additional Context

### Dependencies

- No new dependencies required
- Uses existing `logging` module

### Testing Strategy

1. **Unit Tests:** Update existing tests in `tests/unit/task_managers/` for new log formats
2. **Integration Test:** Run full pipeline and verify clean output
3. **Manual Verification:** Visual inspection of pipeline output

### Example: Expected Output After Fix

**Before (noisy):**
```
07:21:22 [INFO] [phase] HTTP Request: POST https://api.linear.app/graphql "HTTP/1.1 200 OK"
07:21:22 [INFO] [phase] Added label 'adw:running' to issue 23399760-fc82-49b7-b195-817295883263
07:21:23 [INFO] [phase] Status synced to task manager
✓ PLAN completed (275.7s, 2 artifacts, 14719 tokens)
07:25:59 [INFO] [phase] HTTP Request: POST https://api.linear.app/graphql "HTTP/1.1 200 OK"
07:25:59 [INFO] [phase] Posted comment to issue 23399760-fc82-49b7-b195-817295883263
07:25:59 [INFO] [phase] Comment posted to task manager
```

**After (clean):**
```
07:21:22 [INFO] [phase] Added label 'adw:running'
07:25:59 [INFO] [phase] Posted sync comment
✓ PLAN completed (275.7s, 2 artifacts, 14719 tokens)
```

### Notes

- Keep UUIDs in `extra={}` dict for structured logging/debugging if needed
- The `progress.py` pipeline summary already supports PR URL display - verify it's working
- Consider future work: consolidate all phase-end logs into single summary line
