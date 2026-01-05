# Story 11.6: Validation State Persistence

Status: draft
Linear Issue: not-configured
Epic: 11 - Validation Loop
Created: 2026-01-05

---

## Story

As a developer,
I want validation state persisted,
so that I can resume validation after interruption.

## Acceptance Criteria

**Given** validation iteration completes
**When** state is saved
**Then** includes: current_iteration, issues_list, triage_decisions, fix_history

**Given** run is resumed
**When** validation was in progress
**Then** loop continues from last iteration

**Given** issues list
**When** persisted
**Then** stored at `.adw/runs/<id>/validation/issues.json`

**Given** triage decisions
**When** persisted
**Then** stored at `.adw/runs/<id>/validation/triage.json`

## Tasks / Subtasks

### Task 1: Create ValidationStateManager
- [x] Create `src/adw/validation/state_manager.py`
- [x] Define `ValidationStateManager` class
- [x] Inject run_id and base path for state storage
- [x] Support atomic writes for state files

### Task 2: Define Persistable State Models
- [x] Create `ValidationState` model with:
  - `run_id: str`
  - `current_iteration: int`
  - `total_iterations: int`
  - `loop_state: LoopState`
  - `started_at: datetime`
  - `last_updated: datetime`
- [x] Ensure all nested models are serializable

### Task 3: Implement Issues Persistence
- [x] Create `save_issues(issues: list[ValidationIssue]) -> None`
- [x] Create `load_issues() -> list[ValidationIssue]`
- [x] Store at `.adw/runs/<id>/validation/issues.json`
- [x] Handle empty issues list gracefully

### Task 4: Implement Triage Persistence
- [x] Create `save_triage(decisions: list[TriageResult]) -> None`
- [x] Create `load_triage() -> list[TriageResult]`
- [x] Store at `.adw/runs/<id>/validation/triage.json`
- [x] Preserve triage reasoning for audit

### Task 5: Implement Fix History Persistence
- [x] Create `save_fix_history(history: list[FixIterationResult]) -> None`
- [x] Create `load_fix_history() -> list[FixIterationResult]`
- [x] Store at `.adw/runs/<id>/validation/fix-history.json`
- [x] Include file modifications for each iteration

### Task 6: Implement State Snapshot
- [x] Create `save_state(state: ValidationState) -> None`
- [x] Create `load_state() -> ValidationState | None`
- [x] Store at `.adw/runs/<id>/validation/state.json`
- [x] Use atomic write (write to temp, then rename)

### Task 7: Add Resume Support
- [x] Create `can_resume() -> bool` method
- [x] Check if state file exists and is valid
- [x] Create `resume() -> ValidationState` method
- [x] Validate state integrity before resume

### Task 8: Integrate with ValidationPhase
- [ ] Save state after each iteration
- [ ] Check for resumable state at phase start
- [ ] Load and restore state if resuming
- [ ] Clear state on successful completion

### Task 9: Write Tests
- [ ] Unit tests for ValidationStateManager (6 tests)
- [ ] Unit tests for issues persistence (4 tests)
- [ ] Unit tests for triage persistence (3 tests)
- [ ] Unit tests for fix history persistence (3 tests)
- [ ] Unit tests for resume support (4 tests)
- [ ] Integration test for save→resume cycle (2 tests)

---

## Dependencies

- **Depends On:** Story 11.2
- **Blocks:** Story 11.5
- **Can Parallel With:** Story 11.3, Story 11.4

### Dependency Rationale
- Story 11.2: State persistence needs issue model schema for serialization
- Story 11.5: Exit conditions need persisted state to resume correctly after interruption

---

## Developer Context

### Technical Requirements

1. **Atomic State Writes**
   - Write to temp file, then rename
   - Prevent corruption on crash
   - Use file locks if concurrent access possible

2. **State File Structure**
   - JSON format for human readability
   - Pretty-printed for debugging
   - Include timestamps for tracking

3. **Resume Validation**
   - Verify state file integrity (valid JSON, required fields)
   - Check run_id matches current run
   - Validate iteration count is sensible

### Architecture Compliance

**File Location:** `src/adw/validation/state_manager.py`

**Storage Structure:**
```
.adw/runs/<run_id>/
└── validation/
    ├── state.json       # Current loop state
    ├── issues.json      # All issues with current status
    ├── triage.json      # All triage decisions with reasons
    └── fix-history.json # Fix attempt history
```

**Class Structure:**
```python
# src/adw/validation/state_manager.py
from pathlib import Path
from datetime import datetime
import json

class ValidationStateManager:
    def __init__(self, run_id: str, base_path: Path):
        self.run_id = run_id
        self.validation_dir = base_path / "validation"
        self.validation_dir.mkdir(parents=True, exist_ok=True)

    @property
    def state_file(self) -> Path:
        return self.validation_dir / "state.json"

    @property
    def issues_file(self) -> Path:
        return self.validation_dir / "issues.json"

    @property
    def triage_file(self) -> Path:
        return self.validation_dir / "triage.json"

    @property
    def fix_history_file(self) -> Path:
        return self.validation_dir / "fix-history.json"

    def save_state(self, state: ValidationState) -> None:
        """Save validation state atomically."""
        state.last_updated = datetime.utcnow()
        self._atomic_write(self.state_file, state.model_dump_json(indent=2))

    def load_state(self) -> ValidationState | None:
        """Load validation state if exists."""
        if not self.state_file.exists():
            return None
        try:
            data = json.loads(self.state_file.read_text())
            return ValidationState.model_validate(data)
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
            return None

    def save_issues(self, issues: list[ValidationIssue]) -> None:
        """Save all issues."""
        data = [i.model_dump() for i in issues]
        self._atomic_write(self.issues_file, json.dumps(data, indent=2, default=str))

    def load_issues(self) -> list[ValidationIssue]:
        """Load issues if exists."""
        if not self.issues_file.exists():
            return []
        try:
            data = json.loads(self.issues_file.read_text())
            return [ValidationIssue.model_validate(i) for i in data]
        except Exception as e:
            logger.warning(f"Failed to load issues: {e}")
            return []

    def save_triage(self, decisions: list[TriageResult]) -> None:
        """Save triage decisions."""
        data = [
            {
                "issue_id": d.issue.id,
                "decision": d.decision.value,
                "reason": d.reason,
                "auto_decided": d.auto_decided,
                "timestamp": datetime.utcnow().isoformat(),
            }
            for d in decisions
        ]
        self._atomic_write(self.triage_file, json.dumps(data, indent=2))

    def load_triage(self) -> dict[str, dict]:
        """Load triage decisions as issue_id -> decision mapping."""
        if not self.triage_file.exists():
            return {}
        try:
            data = json.loads(self.triage_file.read_text())
            return {d["issue_id"]: d for d in data}
        except Exception:
            return {}

    def save_fix_history(self, history: list[FixIterationResult]) -> None:
        """Save fix iteration history."""
        data = [
            {
                "iteration": h.iteration_number,
                "issues_fixed": h.issues_fixed,
                "issues_remaining": h.issues_remaining,
                "issues_deferred": h.issues_deferred,
                "files_modified": h.files_modified,
                "timestamp": datetime.utcnow().isoformat(),
            }
            for h in history
        ]
        self._atomic_write(self.fix_history_file, json.dumps(data, indent=2))

    def can_resume(self) -> bool:
        """Check if validation can be resumed."""
        state = self.load_state()
        if state is None:
            return False
        if state.run_id != self.run_id:
            return False
        # Validate state is in resumable condition
        return state.current_iteration > 0

    def clear(self) -> None:
        """Clear all validation state (on success)."""
        for f in [self.state_file, self.issues_file, self.triage_file, self.fix_history_file]:
            if f.exists():
                f.unlink()

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write file atomically using temp file + rename."""
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(content)
        temp_path.rename(path)
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| pathlib | stdlib | File operations |
| json | stdlib | JSON serialization |
| Pydantic | 2.12+ | Model serialization |
| datetime | stdlib | Timestamps |

### File Structure Requirements

**New Files:**
- `src/adw/validation/state_manager.py`

**Modified Files:**
- `src/adw/validation/__init__.py` - Export ValidationStateManager
- `src/adw/validation/phase.py` - Integrate state persistence
- `src/adw/validation/models.py` - Add ValidationState if not present

**Test Files:**
- `tests/unit/validation/test_state_manager.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/validation/test_state_manager.py
class TestValidationStateManager:
    def test_save_and_load_state(self, tmp_path):
        """State round-trips correctly."""

    def test_save_state_atomic(self, tmp_path):
        """Write uses temp file + rename."""

    def test_load_state_missing_file(self, tmp_path):
        """Returns None when no state file."""

    def test_load_state_corrupted(self, tmp_path):
        """Returns None on invalid JSON."""

    def test_can_resume_true(self, tmp_path, valid_state):
        """Returns True with valid resumable state."""

    def test_can_resume_wrong_run_id(self, tmp_path):
        """Returns False when run_id mismatch."""

class TestIssuesPersistence:
    def test_save_and_load_issues(self, tmp_path, sample_issues):
        """Issues round-trip correctly."""

    def test_load_empty_issues(self, tmp_path):
        """Returns empty list when no file."""

    def test_save_handles_datetime(self, tmp_path):
        """Datetime fields serialize correctly."""

    def test_load_validates_issues(self, tmp_path):
        """Invalid issues logged and skipped."""

class TestResumeCycle:
    def test_full_save_resume_cycle(self, tmp_path):
        """Save state, create new manager, resume successfully."""

    def test_resume_restores_iteration(self, tmp_path):
        """Resumed state has correct iteration number."""
```

---

## Previous Story Intelligence

**Learnings from Story 11.2:**
- ValidationIssue model is serializable
- Issues have timestamps for tracking

**Learnings from Story 11.5:**
- LoopState tracks iteration progress
- State includes stall detection data

**Relevant Patterns from Epic 4:**
- State persistence uses `.adw/runs/<id>/` structure
- Atomic writes for crash safety
- JSON format for debugging

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 4: State persistence implementation
- Context persistence patterns

**Established Patterns:**
- Atomic file writes (temp + rename)
- JSON with pretty-print for debugging
- State files in run directory structure

---

## Latest Technical Information

**State Persistence Best Practices (2025):**
- Always use atomic writes (temp + rename)
- Include timestamps in state for debugging
- Validate state on load (don't trust old state)
- Clear state on success (don't leave artifacts)

**JSON Serialization:**
- Use `default=str` for datetime fallback
- Pretty-print with indent=2 for readability
- Handle Pydantic models with `.model_dump()`

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **State in .adw/runs/**: All run state in run directory
- **Atomic writes**: Use temp + rename pattern
- **JSON format**: Human-readable state files
- **Structured logging**: Log state operations

---

## Dev Notes

### State File Examples

**state.json:**
```json
{
  "run_id": "01H...",
  "current_iteration": 3,
  "total_iterations": 5,
  "loop_state": {
    "issues_resolved": 5,
    "issues_dismissed": 2,
    "issues_deferred": 1,
    "issues_remaining": 3,
    "stall_count": 0
  },
  "started_at": "2026-01-05T10:00:00Z",
  "last_updated": "2026-01-05T10:15:00Z"
}
```

**issues.json:**
```json
[
  {
    "id": "VI-01H...",
    "source": "TEST",
    "severity": "ERROR",
    "description": "test_login fails",
    "triage_decision": "FIX",
    "fix_attempt_count": 1,
    "last_fix_result": "FAILED"
  }
]
```

### Implementation Approach

1. Create ValidationState model
2. Implement ValidationStateManager skeleton
3. Add atomic write utility
4. Add issues save/load
5. Add triage save/load
6. Add fix history save/load
7. Add resume support
8. Integrate with ValidationPhase
9. Write comprehensive tests

### References

- [Source: _bmad-output/epics/epic-11-validation-loop.md#Story 11.6]
- [Source: _bmad-output/architecture.md#State Management]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 11: Validation Loop - Story 11.6

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

### Completion Notes List

### File List
