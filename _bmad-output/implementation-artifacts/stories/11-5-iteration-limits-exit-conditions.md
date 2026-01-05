# Story 11.5: Iteration Limits and Exit Conditions

Status: draft
Linear Issue: not-configured
Epic: 11 - Validation Loop
Created: 2026-01-05

---

## Story

As a developer,
I want configurable limits on validation iterations,
so that runs don't loop forever.

## Acceptance Criteria

**Given** validation loop
**When** max_iterations reached (default: 5)
**Then** loop exits with remaining issues as DEFERRED

**Given** validation loop
**When** all issues are resolved, dismissed, or deferred
**Then** loop exits successfully

**Given** validation loop
**When** no progress made (same issues after fix attempt)
**Then** remaining FIX issues auto-defer after 2 stalls

**Given** configuration
**When** limits are set
**Then** these are configurable:
```yaml
validation:
  max_iterations: 5
  max_fix_attempts_per_issue: 2
  stall_threshold: 2
```

## Tasks / Subtasks

### Task 1: Create ValidationLoopController
- [x] Create `src/adw/validation/loop_controller.py`
- [x] Define `ValidationLoopController` class
- [x] Track iteration count, stall count
- [x] Inject ValidationConfig for limits

### Task 2: Implement Exit Condition Checks
- [x] Create `should_exit() -> tuple[bool, str]` method
- [x] Check `iteration_count >= max_iterations`
- [x] Check `all_issues_resolved_or_deferred()`
- [x] Check `stall_count >= stall_threshold`
- [x] Return (should_exit, reason)

### Task 3: Implement Stall Detection
- [x] Create `check_progress(prev_issues, curr_issues) -> bool`
- [x] Compare issue counts and states
- [x] Detect "same issues, same state" stall
- [x] Increment stall counter when no progress

### Task 4: Implement Auto-Defer on Exit
- [x] When loop exits with remaining FIX issues
- [x] Auto-change to DEFER for all remaining
- [x] Set reason based on exit condition:
  - "Max iterations reached (5)"
  - "No progress after 2 iterations"
- [x] Log auto-defer decisions

### Task 5: Add Loop State Tracking
- [ ] Create `LoopState` model with:
  - `current_iteration: int`
  - `total_issues_found: int`
  - `issues_resolved: int`
  - `issues_dismissed: int`
  - `issues_deferred: int`
  - `stall_count: int`
  - `last_progress_iteration: int`
- [ ] Update state after each iteration

### Task 6: Integrate with ValidationPhase
- [ ] Modify ValidationPhase to use LoopController
- [ ] Main loop: validate → triage → fix → repeat
- [ ] Check exit conditions after each iteration
- [ ] Handle graceful exit with summary

### Task 7: Add Loop Progress Display
- [ ] Display iteration progress: "Iteration 2/5"
- [ ] Show issues: "3 fixed, 2 remaining, 1 deferred"
- [ ] Indicate stall warning if detected
- [ ] Show exit reason when loop completes

### Task 8: Write Tests
- [ ] Unit tests for ValidationLoopController (6 tests)
- [ ] Unit tests for exit condition checks (5 tests)
- [ ] Unit tests for stall detection (4 tests)
- [ ] Unit tests for auto-defer logic (3 tests)
- [ ] Integration test for full loop execution (2 tests)

---

## Dependencies

- **Depends On:** Story 11.3, Story 11.4, Story 11.6
- **Blocks:** Story 11.7
- **Can Parallel With:** None

### Dependency Rationale
- Story 11.3: Exit conditions need triage decisions to determine if all issues resolved/deferred
- Story 11.4: Exit conditions need fix loop behavior to enforce max_fix_attempts
- Story 11.6: Exit conditions need persisted state to resume correctly after interruption
- Story 11.7: Report generation needs to know final exit state and limits reached

---

## Developer Context

### Technical Requirements

1. **Loop Control**
   - Central controller manages iteration state
   - Checks exit conditions after each iteration
   - Provides clear exit reasons

2. **Stall Detection**
   - Compare issue fingerprints between iterations
   - "No progress" = same issues with same fix_attempt_counts
   - Track consecutive stalls separately from total iterations

3. **Graceful Exit**
   - Always exit cleanly, never infinite loop
   - Remaining issues auto-deferred with explanation
   - Summary displayed on exit

### Architecture Compliance

**File Location:** `src/adw/validation/loop_controller.py`

**Class Structure:**
```python
# src/adw/validation/loop_controller.py
from enum import Enum
from dataclasses import dataclass, field

class ExitReason(str, Enum):
    ALL_RESOLVED = "ALL_RESOLVED"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    STALL_DETECTED = "STALL_DETECTED"
    USER_CANCELLED = "USER_CANCELLED"

@dataclass
class LoopState:
    current_iteration: int = 0
    total_issues_found: int = 0
    issues_resolved: int = 0
    issues_dismissed: int = 0
    issues_deferred: int = 0
    issues_remaining: int = 0
    stall_count: int = 0
    last_progress_iteration: int = 0
    previous_issue_fingerprints: set[str] = field(default_factory=set)

class ValidationLoopController:
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.state = LoopState()

    def start_iteration(self) -> int:
        """Start a new iteration, return iteration number."""
        self.state.current_iteration += 1
        return self.state.current_iteration

    def should_exit(self) -> tuple[bool, ExitReason | None]:
        """Check if loop should exit."""
        # Check max iterations
        if self.state.current_iteration >= self.config.max_iterations:
            return True, ExitReason.MAX_ITERATIONS

        # Check all issues resolved/deferred
        if self.state.issues_remaining == 0:
            return True, ExitReason.ALL_RESOLVED

        # Check stall threshold
        if self.state.stall_count >= self.config.stall_threshold:
            return True, ExitReason.STALL_DETECTED

        return False, None

    def check_progress(self, issues: list[ValidationIssue]) -> bool:
        """Check if progress was made since last iteration."""
        current_fingerprints = self._compute_fingerprints(issues)

        if current_fingerprints == self.state.previous_issue_fingerprints:
            self.state.stall_count += 1
            return False
        else:
            self.state.stall_count = 0
            self.state.last_progress_iteration = self.state.current_iteration
            self.state.previous_issue_fingerprints = current_fingerprints
            return True

    def _compute_fingerprints(
        self,
        issues: list[ValidationIssue],
    ) -> set[str]:
        """Compute fingerprints for stall detection."""
        return {
            f"{i.id}:{i.triage_decision}:{i.fix_attempt_count}"
            for i in issues
            if i.triage_decision == "FIX"  # Only track FIX issues for progress
        }

    def update_counts(self, issues: list[ValidationIssue]) -> None:
        """Update issue counts in state."""
        self.state.issues_resolved = sum(
            1 for i in issues if i.last_fix_result == FixResult.RESOLVED
        )
        self.state.issues_dismissed = sum(
            1 for i in issues if i.triage_decision == "DISMISS"
        )
        self.state.issues_deferred = sum(
            1 for i in issues if i.triage_decision == "DEFER"
        )
        self.state.issues_remaining = sum(
            1 for i in issues if i.triage_decision == "FIX"
        )

    def auto_defer_remaining(
        self,
        issues: list[ValidationIssue],
        reason: ExitReason,
    ) -> list[ValidationIssue]:
        """Auto-defer all remaining FIX issues."""
        reason_text = {
            ExitReason.MAX_ITERATIONS: f"Max iterations reached ({self.config.max_iterations})",
            ExitReason.STALL_DETECTED: f"No progress after {self.state.stall_count} iterations",
        }.get(reason, "Loop exited")

        for issue in issues:
            if issue.triage_decision == "FIX":
                issue.triage_decision = "DEFER"
                issue.triage_reason = reason_text

        return issues

    def get_summary(self) -> dict:
        """Get loop execution summary."""
        return {
            "iterations_run": self.state.current_iteration,
            "total_issues": self.state.total_issues_found,
            "resolved": self.state.issues_resolved,
            "dismissed": self.state.issues_dismissed,
            "deferred": self.state.issues_deferred,
            "stalls_detected": self.state.stall_count,
        }
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| dataclasses | stdlib | State tracking |
| Pydantic | 2.12+ | Model validation |
| Rich | 13.9+ | Progress display |

### File Structure Requirements

**New Files:**
- `src/adw/validation/loop_controller.py`

**Modified Files:**
- `src/adw/validation/__init__.py` - Export ValidationLoopController
- `src/adw/validation/phase.py` - Integrate loop controller

**Test Files:**
- `tests/unit/validation/test_loop_controller.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/validation/test_loop_controller.py
class TestValidationLoopController:
    def test_should_exit_max_iterations(self, config):
        """Exit when max_iterations reached."""

    def test_should_exit_all_resolved(self):
        """Exit when no remaining issues."""

    def test_should_exit_stall_threshold(self):
        """Exit when stall_threshold exceeded."""

    def test_check_progress_detects_stall(self):
        """Stall detected when issues unchanged."""

    def test_check_progress_resets_on_change(self):
        """Stall counter resets on progress."""

    def test_auto_defer_sets_reason(self):
        """Auto-defer includes exit reason."""

class TestStallDetection:
    def test_fingerprint_includes_fix_count(self):
        """Fingerprint changes when fix_attempt_count changes."""

    def test_fingerprint_ignores_resolved(self):
        """Resolved issues excluded from fingerprint."""

    def test_consecutive_stalls_counted(self):
        """Multiple stalls increment counter."""

    def test_progress_resets_counter(self):
        """Progress resets stall counter to 0."""
```

---

## Previous Story Intelligence

**Learnings from Story 11.3:**
- Triage decisions are: FIX, DISMISS, DEFER
- Issues track their triage_decision and reason

**Learnings from Story 11.4:**
- Fix loop updates fix_attempt_count
- Auto-defer on max fix attempts per issue
- Need to coordinate with overall iteration limits

**Learnings from Story 11.6:**
- State must be persistable for resume
- LoopState should be serializable

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 5: Pipeline orchestration patterns
- Epic 4: State management patterns

**Established Patterns:**
- Controllers manage state and flow
- Exit conditions checked explicitly
- Progress displayed via Rich

---

## Latest Technical Information

**Loop Control Best Practices (2025):**
- Always have hard limits on iterations
- Detect stalls (no progress) separately from iteration count
- Provide clear exit reasons for debugging
- Auto-defer is better than failing

**Stall Detection:**
- Use fingerprints based on actionable state
- Exclude resolved/deferred from progress tracking
- Reset counter on any progress

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Configuration-driven**: All limits configurable
- **Structured logging**: Log iteration progress
- **State tracking**: State must be serializable
- **Graceful degradation**: Always exit cleanly

---

## Dev Notes

### Loop Flow

```
ValidationPhase.run():
    controller = ValidationLoopController(config)

    while True:
        iteration = controller.start_iteration()
        display(f"Iteration {iteration}/{config.max_iterations}")

        # Run validators
        issues = self._run_validators()
        controller.state.total_issues_found = len(issues)

        # Triage
        issues = await self.triage_system.triage(issues)

        # Check if done (all resolved/dismissed/deferred)
        controller.update_counts(issues)
        should_exit, reason = controller.should_exit()
        if should_exit:
            if reason != ExitReason.ALL_RESOLVED:
                issues = controller.auto_defer_remaining(issues, reason)
            break

        # Attempt fixes for FIX issues
        fix_result = await self.fix_engine.attempt_fixes(issues)

        # Check progress
        if not controller.check_progress(issues):
            display("Warning: No progress made this iteration")

    return controller.get_summary()
```

### Implementation Approach

1. Create LoopState dataclass
2. Create ExitReason enum
3. Implement ValidationLoopController
4. Add exit condition checks
5. Add stall detection
6. Add auto-defer on exit
7. Integrate with ValidationPhase
8. Write comprehensive tests

### References

- [Source: _bmad-output/epics/epic-11-validation-loop.md#Story 11.5]
- [Source: _bmad-output/architecture.md#Pipeline Orchestration]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 11: Validation Loop - Story 11.5

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

### Completion Notes List

### File List
