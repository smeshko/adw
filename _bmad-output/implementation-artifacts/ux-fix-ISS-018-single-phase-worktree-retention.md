# Story: UX Fix ISS-018 - Single-Phase Worktree Retention

Status: ready-for-dev
Linear Issue: not-configured
Epic: 10 - Worktree Isolation
Created: 2026-01-07

---

## Story

As a **CLI user running single-phase workflows**,
I want **the worktree to be preserved after single-phase completion**,
so that **I can inspect, iterate, and continue work from where I left off**.

## Acceptance Criteria

- [ ] When running `adw run "desc" --phase <phase>`, the worktree is preserved after phase completion
- [ ] A clear message is printed showing the worktree path and cleanup instructions
- [ ] The message format is: `Phase '<phase>' complete. Worktree: <path>. Run 'adw cleanup <run_id>' when done.`
- [ ] Multi-phase runs continue to clean up worktrees on success (existing behavior)
- [ ] Resume runs continue to clean up worktrees on completion (existing behavior)
- [ ] Failed runs preserve worktrees for debugging (existing behavior unchanged)
- [ ] Unit tests verify single-phase vs multi-phase cleanup behavior
- [ ] Integration test verifies worktree preserved after single-phase run

## Tasks / Subtasks

### Task 1: Identify Cleanup Call Points
- [x] Examine `orchestrator.py:619` - single-phase success cleanup
- [x] Compare with `orchestrator.py:362` - multi-phase success cleanup
- [x] Document the difference in behavior we need

### Task 2: Modify Single-Phase Cleanup Logic
- [ ] In `run_single_phase()`, change success path to preserve worktree
- [ ] Change `self._cleanup_worktree(run_id, preserve=False)` to `preserve=True` for single-phase
- [ ] Keep `preserve=False` for multi-phase in `run()` method
- [ ] Keep `preserve=False` for resume in `resume()` method

### Task 3: Add User-Facing Output
- [ ] After single-phase completes, print worktree location to console
- [ ] Include cleanup instruction: `adw cleanup <run_id>`
- [ ] Use Rich console for styled output consistent with rest of CLI
- [ ] Log the preservation action with structured logging

### Task 4: Write Tests
- [ ] Unit test: `test_single_phase_preserves_worktree_on_success`
- [ ] Unit test: `test_multi_phase_removes_worktree_on_success`
- [ ] Unit test: `test_resume_removes_worktree_on_success`
- [ ] Integration test: End-to-end single-phase run → verify worktree exists after

---

## Relevant Feature Documentation

N/A - No conditional docs matched this story context.

---

## Developer Context

### Issue Report Reference

**ISS-018:** Single-phase runs delete worktree unexpectedly
- **Reported:** 2026-01-07
- **Severity:** Major
- **Type:** UX Issue
- **File:** `_bmad-output/implementation-artifacts/issues/ISS-018-single-phase-runs-delete-worktree-unexpectedly.md`

**Root Cause:**
The `_cleanup_worktree()` call in `run_single_phase()` uses `preserve=False` on success, identical to multi-phase runs. This treats single-phase completion as "finished" when the user's intent is "stop here and inspect before deciding next steps."

**User Intent Analysis:**
- If user wanted full pipeline, they'd omit `--phase` flag
- Single-phase = intentional stopping point for inspection/iteration
- Deleting worktree contradicts this intent

### Technical Requirements

**Current Code Flow (PROBLEM):**
```
orchestrator.py:619 (run_single_phase success)
  self._cleanup_worktree(run_id, preserve=False)
    → WorktreeManager.remove_worktree(run_id)
    → Worktree deleted
    → User cannot inspect working state
```

**Required Code Flow (FIX):**
```
orchestrator.py:619 (run_single_phase success)
  # Skip cleanup for single-phase - preserve for inspection
  console.print(f"✓ Phase '{phase}' complete")
  console.print(f"Worktree: {worktree_path}")
  console.print(f"Run 'adw cleanup {run_id}' when done")
  # DON'T call _cleanup_worktree()
```

**Key Code Locations:**

| File | Line | Current Behavior | Required Change |
|------|------|------------------|-----------------|
| `orchestrator.py` | 619 | `_cleanup_worktree(run_id, preserve=False)` | Skip cleanup, print message |
| `orchestrator.py` | 362 | `_cleanup_worktree(context.run_id, preserve=False)` | Keep as-is (multi-phase) |
| `orchestrator.py` | 827 | `_cleanup_worktree(context.run_id, preserve=False)` | Keep as-is (resume) |

### Architecture Compliance

**File Location:** `src/adw/core/orchestrator.py`
- Primary file to modify
- Method: `run_single_phase()` (lines 490-693)
- Success path cleanup at line 619

**Console Output:** Use Rich library (already imported in orchestrator)
```python
from rich.console import Console
console = Console()
```

**Structured Logging:** Follow existing patterns
```python
logger.info(
    "Worktree preserved for inspection",
    extra={
        "run_id": run_id,
        "worktree_path": str(worktree_path),
        "phase": phase,
        "reason": "single_phase_execution",
    },
)
```

**No New Exceptions Required:** This is a UX change, not error handling

**No New Pydantic Models Required:** This uses existing RunContext

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| rich | >=13.0.0 | Console output styling |
| structlog | stdlib bound | Structured logging |

**Rich Output Pattern:**
```python
console.print(f"[green]✓[/green] Phase '{phase}' complete")
console.print(f"[blue]Worktree:[/blue] {worktree_path}")
console.print(f"Run [yellow]adw cleanup {run_id}[/yellow] when done")
```

### File Structure Requirements

**Files to Modify:**
- `src/adw/core/orchestrator.py` - Modify `run_single_phase()` success path

**Test Files:**
- `tests/unit/core/test_orchestrator.py` - Add single-phase preservation tests
- `tests/integration/worktree/test_single_phase_preservation.py` - New integration test

**No New Files Required** (except tests)

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/core/test_orchestrator.py
class TestSinglePhaseWorktreeRetention:
    def test_single_phase_preserves_worktree_on_success(self):
        """Single-phase run preserves worktree after success."""
        # Setup: run_single_phase with mocked worktree
        # Execute: call run_single_phase
        # Assert: _cleanup_worktree NOT called

    def test_multi_phase_removes_worktree_on_success(self):
        """Multi-phase run removes worktree after success."""
        # Setup: run with mocked worktree
        # Execute: call run
        # Assert: _cleanup_worktree called with preserve=False

    def test_single_phase_prints_worktree_location(self):
        """Single-phase run prints worktree path and cleanup instructions."""
        # Setup: run_single_phase with mocked console
        # Execute: call run_single_phase
        # Assert: console.print called with worktree path
```

**Integration Tests:**
```python
# tests/integration/worktree/test_single_phase_preservation.py
def test_worktree_preserved_after_single_phase_run():
    """End-to-end: single-phase run completes, worktree still exists."""
    # 1. Start single-phase run: adw run "test" --phase plan
    # 2. Let phase complete
    # 3. Verify worktree directory still exists
    # 4. Verify cleanup command works: adw cleanup <run_id>
    # 5. Verify worktree now removed
```

---

## Previous Story Intelligence

**bugfix-ISS-008 (Worktree Cleanup Fails with Untracked Files):**
- Added `force=True` to successful run cleanup
- Fixed parameter name mismatch `cleanup_branch` → `delete_branch`
- **Key Learning:** Cleanup calls are already in try-except blocks, safe to modify
- **Key Pattern:** Success/failure paths have different cleanup behaviors

**Story 10-1 through 10-6 (Worktree Isolation):**
- Established worktree lifecycle patterns
- `preserve_on_failure` config option exists
- Concurrent run management integrated with cleanup

**Story 5-4 (Execute Single Phase in Isolation):**
- Implemented `run_single_phase()` method
- Created single-phase execution path
- **Didn't consider** worktree retention for single-phase

---

## Git Intelligence

**Recent Commits Related to Worktrees:**
- `527174d` - Fixes (general)
- `27a5818` - feat(ISS-016): Per-Phase Config.yaml Loading
- Earlier: Stories 10-1 through 10-6 implemented worktree system

**Key Files Modified Recently:**
- `src/adw/core/orchestrator.py` - Main orchestration, cleanup logic
- `src/adw/worktree/manager.py` - Worktree operations
- `src/adw/cli/cleanup.py` - Manual cleanup command

**Existing Cleanup Command:**
The `adw cleanup <run_id>` command already exists and works correctly. Users just need to be told about it.

---

## Latest Technical Information

**Rich Console Output:**
- Project already uses Rich for styled console output
- Pattern: `console.print(f"[color]text[/color]")`
- Colors: green for success, blue for info, yellow for commands

**ADW CLI Conventions:**
- Success messages use `[green]✓[/green]` prefix
- Commands shown in `[yellow]` for visibility
- File paths shown in `[blue]`

---

## Project Context Reference

See: `**/project-context.md`

Key patterns and rules from project context:
- Use structured logging with `extra={}` dict for metadata
- Rich console for user-facing output
- pytest with fixtures for unit tests
- Integration tests in `tests/integration/`
- Follow existing patterns in codebase

---

## Dev Notes

### Implementation Approach

**Option 1 (Recommended - Minimal Change):**
1. In `run_single_phase()` success path, check `use_worktree`
2. If worktree used: skip cleanup, print message
3. If no worktree: continue as normal

**Option 2 (More Thorough):**
1. Add `keep_worktree: bool` parameter to `run_single_phase()`
2. Default to `True` for single-phase runs
3. Allow override via CLI flag `--cleanup` if user wants immediate cleanup

**Recommendation:** Start with Option 1. It's simpler, matches user intent, and doesn't require CLI changes. Option 2 can be added later if users request explicit cleanup control.

### Edge Cases to Consider

1. **No worktree used:** If `--no-worktree` flag was passed, nothing to preserve
2. **Worktree already removed:** Check existence before printing path
3. **Resume after single-phase:** User should be able to run `adw resume <run_id>` to continue

### Verification Checklist

- [ ] `adw run "test" --phase plan` → worktree preserved, message shown
- [ ] `adw run "test"` (all phases) → worktree cleaned up on success
- [ ] `adw resume <run_id>` → worktree cleaned up on completion
- [ ] `adw cleanup <run_id>` → manually removes preserved worktree
- [ ] Failed runs → worktree preserved (unchanged behavior)

### References

- [Source: _bmad-output/implementation-artifacts/issues/ISS-018-single-phase-runs-delete-worktree-unexpectedly.md]
- [Source: src/adw/core/orchestrator.py#run_single_phase - line 490]
- [Source: src/adw/core/orchestrator.py#_cleanup_worktree - line 1765]
- [Source: src/adw/cli/cleanup.py#cleanup_command - line 22]
- [Source: _bmad-output/implementation-artifacts/bugfix-ISS-008-worktree-cleanup-fails-with-untracked-files.md]

---

## Dev Agent Record

### Context Reference

- Issue: ISS-018-single-phase-runs-delete-worktree-unexpectedly.md
- Related: bugfix-ISS-008 (worktree cleanup patterns)

### Agent Model Used

TBD (to be filled by dev agent)

### Debug Log References

N/A

### Completion Notes List

_To be filled by implementing developer_

### File List

_To be filled by implementing developer_
