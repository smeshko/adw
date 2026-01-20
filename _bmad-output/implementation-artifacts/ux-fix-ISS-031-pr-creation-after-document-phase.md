# Story: UX Fix ISS-031 - PR Creation After Document Phase

Status: ready-for-dev
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-20

---

## Story

As a **CLI user**,
I want **the PR to be created immediately after the document phase completes (before ship)**,
so that **the ship phase can validate and merge the PR as intended**.

## Acceptance Criteria

- [ ] PR creation logic moves from post-run (after all phases) to post-document (before ship)
- [ ] When `auto_create_pr: true` and document phase completes, PR is created before ship starts
- [ ] Ship phase `pre.sh` hook successfully finds the PR created by document phase
- [ ] If PR creation fails, ship phase is skipped (not the entire run)
- [ ] PR result is stored in context and available to ship phase
- [ ] Existing behavior preserved when ship phase is disabled
- [ ] Unit tests cover the new timing logic

## Tasks / Subtasks

### Task 1: Move PR Creation into Phase Loop
- [x] In `orchestrator.py`, detect when document phase completes
- [x] Call `try_auto_create_pr()` immediately after document phase (not after loop)
- [x] Store `pr_result` in a variable accessible to subsequent logic
- [x] Remove PR creation from post-run completion block (lines ~386-394)

### Task 2: Add Post-Document PR Creation Hook Point
- [ ] In `_execute_phase_with_transitions()`, add special handling for document phase
- [ ] After document phase completes successfully, invoke PR creation
- [ ] Log PR creation attempt with structured logging
- [ ] Handle PR creation failure gracefully (warn, don't fail)

### Task 3: Update Ship Phase Dependency
- [ ] If PR creation fails and ship phase is enabled, skip ship with warning
- [ ] Add `--skip-ship-on-pr-failure` behavior (implicit when no PR)
- [ ] Ensure ship phase receives PR context (number, URL) if available

### Task 4: Store PR Result in Context
- [ ] Add `pr_result` field to track PR creation outcome
- [ ] Pass PR result to ship phase via context or environment
- [ ] Ship pre.sh can use `ADW_PR_URL` if set by SDK

### Task 5: Update Completion Summary Logic
- [ ] PR result should still appear in completion summary
- [ ] Handle case where PR was created mid-run (not end-of-run)
- [ ] Ensure PR URL is available for task manager completion comment

### Task 6: Write Tests
- [ ] Unit test: PR is created after document phase, before ship
- [ ] Unit test: Ship phase receives PR context when PR exists
- [ ] Unit test: Ship phase skipped when PR creation fails
- [ ] Unit test: Backward compatibility when ship disabled
- [ ] Integration test: Full flow plan→build→validate→document→PR→ship

---

## Relevant Feature Documentation

### Conditional Docs Loaded

- **docs/arch-orchestrator.md** - Orchestrator architecture, phase execution flow
- **docs/arch-phase-pipeline.md** - Phase sequence, artifact flow, ship phase details
- **_bmad-output/project-context.md** - Coding standards, patterns, anti-patterns

---

## Developer Context

### Issue Report Reference

**ISS-031:** Auto-PR creation runs after all phases instead of after document phase

- **Reported:** 2026-01-20
- **Severity:** Major
- **Type:** Bug
- **File:** `_bmad-output/implementation-artifacts/issues/ISS-031-pr-creation-after-document-phase.md`

**Root Cause Location:** `src/adw/core/orchestrator.py:386-394`
```python
# This code is AFTER the phase loop completes - too late!
# Ship phase already failed because no PR exists
pr_result = None
if self.progress_display:
    pr_result = self.progress_display.try_auto_create_pr(
        run_id=context.run_id,
        context=context,
        runs_dir=self.runs_dir,
        auto_create_pr_enabled=self.git_config.auto_create_pr,
    )
```

**Expected Flow:**
```
plan → build → validate → document → [CREATE PR] → ship (validates & merges PR)
```

**Actual Flow:**
```
plan → build → validate → document → ship (FAILS: no PR) → [PR creation never runs]
```

### Technical Requirements

**Phase Sequence:** `PHASE_SEQUENCE = ("plan", "build", "validate", "document", "ship")`

**PR Creation Trigger Point:**
- After `document` phase completes in `_execute_phase_with_transitions()`
- Before the next iteration moves to `ship` phase
- Must store result for ship phase and completion summary

**Recommended Implementation Approach:**

```python
# In orchestrator.py run() method, inside phase loop
for phase in PHASE_SEQUENCE:
    # ... existing phase execution ...
    context = self._execute_phase_with_transitions(context, phase)

    # NEW: Create PR after document phase (before ship)
    if phase == "document" and self.git_config.auto_create_pr:
        pr_result = self._maybe_create_pr_after_document(context)
        if pr_result and not pr_result.success:
            # PR failed - consider skipping ship
            if self._phase_runner.is_phase_enabled("ship"):
                logger.warning(
                    "PR creation failed, ship phase may fail",
                    extra={"reason": pr_result.reason}
                )
```

**Alternative: Phase Callback System**
```python
# Add phase completion callback for extensibility
def _on_phase_complete(self, phase: str, context: RunContext) -> None:
    """Hook called after each phase completes."""
    if phase == "document":
        self._handle_post_document(context)
```

### Architecture Compliance

**File Locations:**
- Primary change: `src/adw/core/orchestrator.py`
- No new files needed - reuse existing `try_auto_create_pr()`

**Pydantic Models:**
- No model changes needed
- `GitConfig.auto_create_pr` already exists

**Exception Handling:**
- PR creation errors should warn, not fail the run
- Ship phase should fail gracefully if no PR (existing pre.sh behavior)

**Logging Requirements:**
```python
# Structured logging for PR creation timing
logger.info(
    "Creating PR after document phase",
    extra={"run_id": context.run_id, "phase": "document"}
)
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Rich | 14.1.0 | Console output for PR creation status |
| subprocess | stdlib | gh CLI invocation (existing) |

**No new dependencies required.**

### File Structure Requirements

**Files to Modify:**

1. **`src/adw/core/orchestrator.py`** (PRIMARY)
   - Move PR creation from lines ~386-394 into phase loop
   - Add post-document phase hook point
   - Pass PR result to completion summary

2. **`src/adw/cli/progress.py`** (MINOR)
   - Ensure `try_auto_create_pr()` works when called mid-run
   - May need to handle repeated calls gracefully

**Files NOT to Modify:**
- `src/adw/defaults/commands/ship/pre.sh` - Works correctly, expects PR to exist
- `src/adw/models/config.py` - GitConfig already has `auto_create_pr`
- `src/adw/cli/pr.py` - PR creation utilities work correctly

### Testing Requirements

**Unit Tests (Required):**

```python
# tests/unit/core/test_orchestrator.py

class TestPRCreationTiming:
    """Tests for PR creation after document phase (ISS-031)."""

    def test_pr_created_after_document_before_ship(self):
        """PR should be created after document phase completes."""
        # Mock all phases to succeed
        # Verify try_auto_create_pr called after document, before ship
        pass

    def test_ship_receives_pr_context(self):
        """Ship phase should have access to PR info if created."""
        pass

    def test_ship_skipped_when_pr_fails(self):
        """Ship phase should be skipped gracefully when PR creation fails."""
        pass

    def test_pr_not_created_when_disabled(self):
        """No PR creation when auto_create_pr=False."""
        pass

    def test_pr_not_created_when_document_fails(self):
        """No PR creation if document phase failed."""
        pass
```

**Integration Tests:**
- Full pipeline test with mock gh CLI
- Verify ship phase can read PR created by document phase

---

## Previous Story Intelligence

**Story ISS-011 (UX Fix - ADW Run Should Auto-Create PR):**
- Implemented auto-PR creation functionality
- Added `try_auto_create_pr()` in `progress.py`
- Added `auto_create_pr` config option
- **Issue:** Placed PR creation at end of run, not accounting for ship phase

**Story 15.6 (PR Merge & Completion):**
- Ship phase merges the PR
- Pre-hook validates PR exists with `gh pr view`
- Depends on PR being created before ship runs

**Key Learning:**
The original ISS-011 implementation assumed document was the last phase. When ship phase was added (Epic 15), the timing became incorrect.

---

## Git Intelligence

**Recent Commits:**
```
024ee2a chore: bump version to 0.1.20
251b6c1 fix(ISS-029): Honor phase configuration from command configs
1c46dfe feat(story-15-8): Init Wizard Ship Phase Integration
f238eba feat(ship): Ship Report Generation (Story 15.7)
80550cb feat(ship): PR Merge & Completion (Story 15.6)
```

**Key Observation:**
The ship phase (15.6) was added after ISS-011's auto-PR feature. The ISS-011 implementation assumed "document" was the final phase, but ship phase now comes after document.

**Files Changed in ISS-011:**
- `src/adw/core/orchestrator.py` - Added auto-PR after run completion
- `src/adw/cli/progress.py` - Added `try_auto_create_pr()`
- `src/adw/models/config.py` - Added `auto_create_pr` to GitConfig
- `src/adw/cli/pr.py` - PR detection utilities

---

## Latest Technical Information

**GitHub CLI (gh):**
- PR creation: `gh pr create --title "..." --body "..."`
- PR view: `gh pr view <branch> --json number,url,state,mergeable`
- Both commands work correctly; timing is the issue

**No version updates needed - existing tooling is correct.**

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns from project context:

1. **Structured Logging:**
   ```python
   logger.info("PR created after document phase", phase="document", run_id=run_id)
   ```

2. **Immutable State Updates:**
   ```python
   context = context.model_copy(update={"pr_result": pr_result})
   ```

3. **Exception Handling:**
   - PR creation errors should warn, not fail
   - Use existing `GitError` hierarchy if needed

4. **Rich Console Output:**
   ```python
   console.print("[bold green]✓[/] PR created: [cyan]{url}[/]")
   ```

---

## Dev Notes

### Implementation Strategy

**Minimal Change Approach:**
1. Add a single check after document phase completion in the main loop
2. Call existing `try_auto_create_pr()` at that point
3. Store result for later use
4. Remove duplicate call from post-run block

**Code Location (orchestrator.py:348-364):**
```python
for phase in PHASE_SEQUENCE:
    # ... existing checks ...
    context = self._execute_phase_with_transitions(context, phase)

    # ISS-031: Create PR immediately after document phase
    if phase == "document":
        pr_result = self._try_create_pr_after_document(context)
```

### Edge Cases to Handle

1. **Ship phase disabled:** PR should still be created (for manual merge)
2. **Document phase failed:** No PR creation attempted
3. **PR already exists:** `gh pr create` will fail - handle gracefully
4. **No git remote:** Skip PR creation (existing behavior)
5. **gh not installed:** Skip PR creation with warning (existing behavior)

### Backward Compatibility

- If `auto_create_pr: false`, no behavior change
- If ship phase disabled, PR creation still happens after document
- Completion summary continues to show PR result

### References

- [Source: src/adw/core/orchestrator.py:386-394] - Current PR creation location
- [Source: src/adw/core/orchestrator.py:348-364] - Phase loop where PR should be created
- [Source: src/adw/defaults/commands/ship/pre.sh] - Ship pre-hook that validates PR
- [Source: _bmad-output/implementation-artifacts/issues/ISS-031-pr-creation-after-document-phase.md]
- [Source: _bmad-output/implementation-artifacts/ux-fix-ISS-011-adw-run-should-auto-create-pr.md]

---

## Dev Agent Record

### Context Reference

- Issue: ISS-031-pr-creation-after-document-phase.md
- Related: ISS-011 (original auto-PR), Story 15.6 (ship PR merge)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

N/A

### Completion Notes List

(To be filled by dev agent)

### File List

**Expected files to modify:**
- `src/adw/core/orchestrator.py` - Move PR creation timing
- `tests/unit/core/test_orchestrator.py` - Add timing tests
