# Story: UX Fix ISS-035 - Remove Duplicate Worktree Log Messages

Status: done
Linear Issue: not-configured
Epic: 10 - Worktree Isolation
Created: 2026-01-21

---

## Story

As a developer running ADW workflows,
I want to see only a single log message when a worktree is created,
so that logs are clean and not cluttered with redundant information.

## Acceptance Criteria

- [ ] Only one log message appears when a worktree is created
- [ ] The retained log message includes all relevant context (run_id, path, branch)
- [ ] Log level remains appropriate (INFO for success, DEBUG for internal details)
- [ ] No regression in functionality - worktree creation still works correctly
- [ ] Tests pass without modification (or updated appropriately if they check log output)

## Tasks / Subtasks

### Task 1: Remove Redundant Log from Orchestrator
- [ ] Remove or downgrade the `logger.info("Created worktree for run", ...)` call at `orchestrator.py:1902-1909`
- [ ] The manager already logs with full context at INFO level, so orchestrator's log is redundant
- [ ] **Decision**: Remove entirely (preferred) OR change to DEBUG level

### Task 2: Verify Log Output
- [ ] Run a test workflow with worktrees enabled
- [ ] Confirm only one "Worktree created" message appears in logs
- [ ] Ensure all context fields are present (run_id, path, branch)

### Task 3: Test Verification
- [ ] Run existing test suite to ensure no regressions
- [ ] Check if any tests specifically assert on log output for worktree creation
- [ ] Update tests if they expect the duplicate message

---

## Relevant Feature Documentation

No feature documentation specifically matches this issue context.

---

## Developer Context

### Technical Requirements

This is a minor log cleanup fix with minimal scope:

1. **Single code change**: Remove or downgrade one `logger.info()` call in `orchestrator.py`
2. **No behavior change**: Worktree creation logic remains unchanged
3. **Low risk**: Only affects log output, not functionality

### Architecture Compliance

- **Logging Standards**: Per `project-context.md`, use structured logging with `extra={}` for context
- **Log Levels**:
  - `INFO`: User-visible operational events (e.g., "Worktree created successfully")
  - `DEBUG`: Internal implementation details (e.g., intermediate steps)
- **Single Responsibility**: The `WorktreeManager` owns worktree creation and should be the authoritative source for logging this event

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Python logging | stdlib | `logging.getLogger(__name__)` |

No external library changes required.

### File Structure Requirements

| File | Change |
|------|--------|
| `src/adw/core/orchestrator.py` | Remove/downgrade log at line ~1902-1909 |
| `src/adw/worktree/manager.py` | Keep existing log at line 497-504 (no change) |

### Testing Requirements

- Run `uv run pytest tests/` to verify no regressions
- Specifically check:
  - `tests/unit/worktree/test_manager.py` - worktree creation tests
  - `tests/unit/core/test_orchestrator.py` - orchestrator tests (if any check logs)
  - `tests/integration/` - any integration tests that capture log output

---

## Previous Story Intelligence

This is a standalone bug fix story with no direct predecessor. However, related worktree stories have established patterns:

- **ISS-020**: `ux-fix-ISS-020-disable-worktree-auto-delete` - Modified worktree retention behavior
- **ISS-008**: `bugfix-ISS-008-worktree-cleanup-fails-with-untracked-files` - Fixed cleanup issues

**Pattern**: Worktree fixes typically require minimal changes focused on the specific behavior while preserving existing functionality.

---

## Git Intelligence

Recent worktree-related commits show:
- Worktree manager logs detailed context (run_id, path, branch) at INFO level
- Orchestrator adds a secondary log which duplicates this information

**Fix Pattern**: When a lower-level module already logs an event with full context, higher-level callers should either skip logging or use DEBUG level for tracing.

---

## Latest Technical Information

No external dependencies or API changes required. Standard Python logging.

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **Structured Logging**: `logger.info("Message", extra={"key": "value"})` - Always use `extra` dict
2. **PEP 8 Naming**: Function names use `snake_case`
3. **Type Annotations**: Required on all functions
4. **No bare exceptions**: Use ADW exception hierarchy

---

## Dev Notes

### Root Cause Analysis

The duplicate logging occurs because:

1. `WorktreeManager.create_worktree()` (manager.py:497-504) logs at INFO:
   ```python
   logger.info(
       "Worktree created successfully",
       extra={
           "run_id": run_id,
           "path": str(worktree_path),
           "branch": branch_name,
       },
   )
   ```

2. `Orchestrator._create_worktree_for_run()` (orchestrator.py:1902-1909) also logs at INFO:
   ```python
   logger.info(
       "Created worktree for run",
       extra={
           "run_id": run_id,
           "worktree_path": str(worktree_path),
           "branch_name": branch_name,
       },
   )
   ```

**Recommended Fix**: Remove the orchestrator log entirely since:
1. The manager's log has equivalent context
2. The manager is the authoritative source for worktree operations
3. Removing the orchestrator log reduces code and maintains clean separation of concerns

### Alternative Fix

If the orchestrator log serves a tracing purpose (showing where in the orchestration flow the worktree was created), consider:
- Change to `logger.debug()` instead of removing
- This preserves the trace for debugging while keeping INFO logs clean

### Project Structure Notes

- Alignment with unified project structure: Files are in correct locations
- No detected conflicts or variances

### References

- [Source: src/adw/worktree/manager.py:497-504] - Manager's worktree creation log
- [Source: src/adw/core/orchestrator.py:1902-1909] - Orchestrator's duplicate log
- [Source: _bmad-output/implementation-artifacts/issues/ISS-035-duplicate-worktree-log-messages.md] - Original issue report

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

### File List

- `src/adw/core/orchestrator.py` - Remove logger.info at ~line 1902-1909
