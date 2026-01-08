# Story: UX Fix ISS-020 - Disable Worktree Auto-Delete

Status: done
Linear Issue: not-configured
Epic: 10 - Worktree Isolation
Created: 2026-01-07

---

## Story

As a **CLI user running ADW workflows**,
I want **worktrees to NEVER be automatically deleted**,
So that **I always have full control over worktree lifecycle and can inspect, debug, or continue work at any time**.

## Acceptance Criteria

- [x] Worktrees are NEVER deleted automatically after successful run completion (multi-phase or single-phase)
- [x] Worktrees are NEVER deleted automatically after resume completion
- [x] Worktrees are NEVER deleted automatically after failed runs
- [x] The only way to delete a worktree is via explicit `adw cleanup <run_id>` command
- [x] After any run completes (success or failure), a message is displayed showing worktree location and cleanup instructions
- [x] The `preserve_on_failure` config option is deprecated and ignored (breaking change documented)
- [x] All existing tests updated to reflect new behavior
- [x] New tests verify no auto-deletion occurs in any scenario

## Tasks / Subtasks

### Task 1: Remove Auto-Cleanup from Orchestrator Success Paths
- [x] Remove `_cleanup_worktree(preserve=False)` call from `run()` method (line ~362)
- [x] Remove `_cleanup_worktree(preserve=False)` call from `resume()` method (line ~827)
- [x] Verify single-phase path already preserves (ISS-018 fix in review)
- [x] Add worktree info message to all completion paths

### Task 2: Remove Auto-Cleanup from Failure Paths
- [x] Change `preserve_on_failure` behavior - worktree always preserved regardless of config
- [x] Remove conditional cleanup based on `preserve_on_failure` config
- [x] Update failure paths to show worktree location and cleanup instructions

### Task 3: Deprecate preserve_on_failure Config
- [x] Mark `preserve_on_failure` as deprecated (option is now ignored)
- [x] Update `WorktreeConfig` model in `src/adw/models/config.py`
- [x] Document breaking change in migration notes

### Task 4: Standardize Completion Messages
- [x] Create consistent message format for all run completion scenarios:
  ```
  ✓ Run complete (or ✗ Run failed)
  Worktree: <path>
  Run 'adw cleanup <run_id>' to remove
  ```
- [x] Use Rich console for styled output
- [x] Log worktree preservation with structured logging

### Task 5: Update Tests
- [x] Update `test_multi_phase_removes_worktree_on_success` → `test_multi_phase_preserves_worktree_on_success`
- [x] Update `test_resume_removes_worktree_on_success` → `test_resume_preserves_worktree_on_success`
- [x] Add `test_failed_run_preserves_worktree`
- [x] Add `test_cleanup_is_only_deletion_method`
- [x] Remove/update tests for `cleanup_on_success` config

### Task 6: Update Documentation
- [x] Update CLI help text if needed
- [x] Document new worktree lifecycle behavior
- [x] Add migration note for users relying on auto-cleanup

---

## Relevant Feature Documentation

N/A - No conditional docs matched this story context.

---

## Developer Context

### Issue Report Reference

**ISS-020:** Worktrees should not auto-delete - only via cleanup command
- **Reported:** 2026-01-07
- **Severity:** Major
- **Type:** UX Issue
- **File:** `_bmad-output/implementation-artifacts/issues/ISS-020-worktrees-should-not-auto-delete.md`

**Related Issue:**
- **ISS-018:** Single-phase runs delete worktree unexpectedly (in review)
- ISS-020 extends ISS-018 to ALL scenarios, not just single-phase

**Root Cause:**
The current implementation auto-deletes worktrees on successful run completion. This is based on the assumption that "success = done = cleanup". However, users want full control over worktree lifecycle:
- Inspect completed work
- Resume work in worktree
- Debug issues
- Maintain predictable behavior

**Design Principle:**
Worktrees are USER resources. The system should never delete user resources automatically. Only explicit user action (`adw cleanup`) should remove them.

### Technical Requirements

**Current Auto-Deletion Points (TO REMOVE):**

| Location | Line | Current Behavior |
|----------|------|------------------|
| `orchestrator.py` | ~362 | `_cleanup_worktree(run_id, preserve=False)` on multi-phase success |
| `orchestrator.py` | ~827 | `_cleanup_worktree(run_id, preserve=False)` on resume success |
| `orchestrator.py` | failure paths | Conditional based on `preserve_on_failure` |

**Required Behavior (ALL PATHS):**
```python
# After ANY run completion (success or failure):
# 1. Do NOT call _cleanup_worktree with preserve=False
# 2. Show worktree info message
# 3. Leave worktree in place

if context.use_worktree and context.worktree_path:
    logger.info(
        "Worktree preserved",
        extra={"run_id": run_id, "worktree_path": str(worktree_path)},
    )
    if self.progress_display:
        console = self.progress_display.console
        console.print(f"[blue]Worktree:[/blue] {worktree_path}")
        console.print(f"Run [yellow]adw cleanup {run_id}[/yellow] to remove")
```

**_cleanup_worktree Usage After This Fix:**
- Should ONLY be called from `adw cleanup` CLI command
- The `_cleanup_worktree` method itself doesn't need changes
- Just remove all AUTOMATIC calls to it

### Architecture Compliance

**Files to Modify:**

| File | Purpose |
|------|---------|
| `src/adw/core/orchestrator.py` | Remove auto-cleanup calls, add messages |
| `src/adw/models/config.py` | Deprecate/remove `cleanup_on_success` |
| `tests/unit/core/test_orchestrator.py` | Update tests for new behavior |

**Console Output Pattern (Rich):**
```python
from rich.console import Console
console = Console()

# Success completion
console.print("[green]✓[/green] Run complete")
console.print(f"[blue]Worktree:[/blue] {worktree_path}")
console.print(f"Run [yellow]adw cleanup {run_id}[/yellow] to remove")

# Failure completion
console.print("[red]✗[/red] Run failed")
console.print(f"[blue]Worktree:[/blue] {worktree_path}")
console.print(f"Run [yellow]adw cleanup {run_id}[/yellow] to remove")
```

**Structured Logging Pattern:**
```python
logger.info(
    "Worktree preserved for user inspection",
    extra={
        "run_id": run_id,
        "worktree_path": str(worktree_path),
        "outcome": "success" | "failure",
        "reason": "user_control_policy",
    },
)
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| rich | >=13.0.0 | Console output styling |
| structlog | stdlib bound | Structured logging |

No new dependencies required.

### File Structure Requirements

**Files to Modify:**
- `src/adw/core/orchestrator.py` - Remove auto-cleanup, add messages
- `src/adw/models/config.py` - Deprecate `cleanup_on_success`
- `tests/unit/core/test_orchestrator.py` - Update cleanup tests

**No New Files Required**

### Testing Requirements

**Unit Tests to Update:**

```python
# tests/unit/core/test_orchestrator.py

class TestWorktreeNoAutoDelete:
    """ISS-020: Worktrees should never be auto-deleted."""

    def test_multi_phase_success_preserves_worktree(self):
        """Multi-phase success preserves worktree for user inspection."""
        # Setup: Mock worktree manager
        # Execute: run() to completion
        # Assert: _cleanup_worktree NOT called with preserve=False
        # Assert: worktree info message printed

    def test_resume_success_preserves_worktree(self):
        """Resume success preserves worktree for user inspection."""
        # Setup: Mock worktree manager, existing run
        # Execute: resume() to completion
        # Assert: _cleanup_worktree NOT called with preserve=False
        # Assert: worktree info message printed

    def test_failed_run_preserves_worktree(self):
        """Failed runs preserve worktree regardless of config."""
        # Setup: Mock worktree manager, config with preserve_on_failure=False
        # Execute: run() that fails
        # Assert: worktree NOT deleted
        # Assert: worktree info message printed

    def test_cleanup_command_is_only_deletion_path(self):
        """Only adw cleanup command should delete worktrees."""
        # This is more of an integration test - verify cleanup CLI works
        pass

    def test_worktree_info_message_on_success(self):
        """Success completion shows worktree path and cleanup command."""
        # Setup: Mock console
        # Execute: run() to completion
        # Assert: console.print called with worktree path
        # Assert: console.print called with cleanup command

    def test_worktree_info_message_on_failure(self):
        """Failure completion shows worktree path and cleanup command."""
        # Setup: Mock console
        # Execute: run() that fails
        # Assert: console.print called with worktree path
        # Assert: console.print called with cleanup command
```

**Tests to Remove/Update:**
- Any test asserting auto-cleanup on success
- Any test for `cleanup_on_success` config behavior

---

## Previous Story Intelligence

**ux-fix-ISS-018 (Single-Phase Worktree Retention) - In Review:**
- Changed single-phase path to preserve worktree
- Added worktree info message for single-phase
- **Key Pattern:** Success path now has `# Skip cleanup, preserve for inspection` pattern
- **Key Learning:** Console output with worktree path and cleanup command works well
- **This story extends that pattern to ALL completion paths**

**bugfix-ISS-008 (Worktree Cleanup Fails with Untracked Files):**
- Added `force=True` to cleanup for untracked files
- This is still relevant for `adw cleanup` command (which keeps working)
- Cleanup command behavior is unchanged

**Stories 10-1 through 10-6 (Worktree Isolation):**
- Established worktree lifecycle
- Original design assumed auto-cleanup on success
- This story changes that assumption based on user feedback

---

## Git Intelligence

**Recent Related Commits:**
- ISS-018 fix (in review) - single-phase worktree retention
- Earlier: Epic 10 stories implemented worktree system

**Key Files in Play:**
- `src/adw/core/orchestrator.py` - Main orchestration, cleanup calls
- `src/adw/worktree/manager.py` - Worktree operations (unchanged)
- `src/adw/cli/cleanup.py` - Manual cleanup command (unchanged)

**Cleanup Command Already Exists:**
The `adw cleanup <run_id>` command works correctly. This story just makes it the ONLY way to delete worktrees.

---

## Latest Technical Information

**ADW CLI Conventions (from ISS-018 implementation):**
- Success: `[green]✓[/green]` prefix
- Failure: `[red]✗[/red]` prefix
- Commands: `[yellow]` for visibility
- Paths: `[blue]`

**Config Breaking Change:**
If removing `cleanup_on_success`, document in CHANGELOG:
```markdown
### Breaking Changes
- `worktree.cleanup_on_success` config option removed
- Worktrees are no longer auto-deleted on success
- Use `adw cleanup <run_id>` to remove worktrees
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Rich console for user-facing output
- Structured logging with `extra={}` dict
- pytest for unit tests
- Follow existing patterns in codebase
- PEP 8 naming conventions

---

## Dev Notes

### Implementation Approach

**Simple Removal Strategy:**
1. Find all `_cleanup_worktree(..., preserve=False)` calls
2. Remove them (or change to `preserve=True` + skip the call entirely)
3. Add worktree info message at each completion point
4. Update tests

**Key Insight:**
The `_cleanup_worktree` method doesn't need changes. We just stop CALLING it automatically. The `adw cleanup` CLI command still uses it directly via `worktree_manager.remove_worktree()`.

### Edge Cases

1. **`--no-worktree` mode:** No worktree to preserve - skip message
2. **Worktree already removed:** Check existence before printing path (unlikely in normal flow)
3. **Resume after preservation:** Works fine - worktree exists, can resume

### Breaking Change Consideration

Removing `cleanup_on_success` is a minor breaking change for users who:
- Explicitly set `cleanup_on_success: true` (but this is the default behavior being changed)
- Relied on auto-cleanup in CI/CD scripts

**Mitigation:**
- Document in CHANGELOG
- Suggest adding `adw cleanup <run_id>` to CI scripts
- Or keep config but ignore it with deprecation warning

### Verification Checklist

- [x] `adw run "test"` (all phases) → worktree preserved, message shown
- [x] `adw run "test" --phase plan` → worktree preserved (ISS-018 behavior)
- [x] `adw resume <run_id>` → worktree preserved, message shown
- [x] Failed run → worktree preserved, message shown
- [x] `adw cleanup <run_id>` → successfully removes worktree
- [x] All tests pass

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-020-worktrees-should-not-auto-delete.md]
- [Source: _bmad-output/implementation-artifacts/issues/ISS-018-single-phase-runs-delete-worktree-unexpectedly.md]
- [Source: src/adw/core/orchestrator.py#run - line 362 (cleanup call)]
- [Source: src/adw/core/orchestrator.py#resume - line 827 (cleanup call)]
- [Source: src/adw/core/orchestrator.py#_cleanup_worktree - line 1787]
- [Source: _bmad-output/implementation-artifacts/ux-fix-ISS-018-single-phase-worktree-retention.md]

---

## Dev Agent Record

### Context Reference

- Issue: ISS-020-worktrees-should-not-auto-delete.md
- Related: ISS-018 (single-phase, in review - this extends it)
- Epic: 10 (Worktree Isolation)

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

| File | Changes |
|------|---------|
| `src/adw/core/orchestrator.py` | Removed auto-cleanup calls from run(), resume(), run_single_phase() success and failure paths. Added worktree preservation messages with cleanup instructions. Updated docstring. |
| `src/adw/models/config.py` | Marked `preserve_on_failure` as deprecated in WorktreeConfig with deprecation notice in description. |
| `tests/unit/core/test_orchestrator.py` | Added TestWorktreeNoAutoDelete class with tests for single-phase, multi-phase, resume, and failed run preservation. Added test_cleanup_command_is_only_deletion_method. |

