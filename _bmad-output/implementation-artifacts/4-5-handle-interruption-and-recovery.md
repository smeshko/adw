# Story 4.5: Handle Interruption and Recovery

Status: ready-for-dev
Linear Issue: not-configured
Epic: 4 - State Persistence & Context Management
Created: 2026-01-01

---

## Story

As a developer,
I want interruptions (Ctrl+C) to save state cleanly,
so that the run can be resumed without data loss (NFR7).

## Acceptance Criteria

**Given** a run is in progress
**When** SIGINT (Ctrl+C) is received
**Then** the current context is saved before exit
**And** the run status is set to "interrupted"

**Given** a run was interrupted mid-phase
**When** resume is attempted
**Then** it starts from the last completed phase boundary (NFR8)

**Given** a run was interrupted during LLM execution
**When** resume is attempted
**Then** the phase is re-executed from the beginning

**Given** an interrupted run
**When** I check status
**Then** it shows "interrupted" with the phase where it stopped

## Tasks / Subtasks

### Task 1: Implement Signal Handling
- [x] Register SIGINT handler at run start
- [x] Register SIGTERM handler for graceful termination
- [x] Capture current run context in handler
- [x] Set flag for graceful shutdown

### Task 2: Implement Graceful Shutdown
- [ ] Check shutdown flag in main loop
- [ ] Save current context before exit
- [ ] Set run status to "interrupted"
- [ ] Save final snapshot
- [ ] Clean up resources

### Task 3: Update RunContext for Status
- [ ] Add `status` field to RunContext (running, completed, interrupted, failed)
- [ ] Add `interrupted_phase` field for tracking where interruption occurred
- [ ] Add `interrupted_at` timestamp
- [ ] Persist status changes immediately

### Task 4: Implement Resume Detection
- [ ] Check run status on resume
- [ ] Find last completed phase from `completed_phases`
- [ ] Determine next phase to execute
- [ ] Load context from snapshot if needed

### Task 5: Implement Resume Logic
- [ ] Start from phase after last completed
- [ ] Re-execute interrupted phase from beginning
- [ ] Update status to "running" on resume
- [ ] Clear interrupted state

### Task 6: Implement Status Command
- [ ] Add `get_run_status(run_id)` method
- [ ] Return status, current phase, interrupted phase
- [ ] Include run metadata
- [ ] Format for CLI display

### Task 7: Write Unit Tests
- [ ] Create `tests/unit/core/test_interruption.py`
- [ ] Test signal handler registration
- [ ] Test graceful shutdown saves context
- [ ] Test status tracking
- [ ] Test resume from interrupt
- [ ] Target: >90% coverage

### Task 8: Write Integration Tests
- [ ] Test actual SIGINT handling (subprocess)
- [ ] Test resume after real interruption
- [ ] Test status display after interrupt
- [ ] Verify no data loss

---

## Developer Context

### Technical Requirements

- **Signal Handling**: Handle SIGINT (Ctrl+C) and SIGTERM gracefully
- **State Preservation**: Save context before exit (NFR7)
- **Resume Semantics**: Resume from last completed phase (NFR8)
- **Status Tracking**: Track running, completed, interrupted, failed states
- **Immediate Persistence**: Persist status changes immediately

### Architecture Compliance

**From architecture.md - Reliability Requirements:**
```
NFR7: System shall recover from interruption (Ctrl+C) without data loss
NFR8: Resume shall succeed if the previous run reached a phase boundary
```

**From architecture.md - Run Context:**
```python
class RunContext(BaseModel):
    run_id: str
    status: RunStatus = "running"  # running, completed, interrupted, failed
    current_phase: str
    completed_phases: list[str] = []
    interrupted_phase: str | None = None
    interrupted_at: datetime | None = None
```

**From architecture.md - Error Handling:**
```python
# Graceful shutdown pattern
def handle_interrupt(signum, frame):
    global shutdown_requested
    shutdown_requested = True

signal.signal(signal.SIGINT, handle_interrupt)
signal.signal(signal.SIGTERM, handle_interrupt)
```

### Library & Framework Requirements

**Signal handling:**
```python
import signal
from typing import Any

shutdown_requested = False

def create_interrupt_handler(context_manager: ContextManager) -> callable:
    """Create signal handler that saves context on interrupt."""
    def handler(signum: int, frame: Any) -> None:
        global shutdown_requested
        shutdown_requested = True
    return handler

# Register handlers
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)
```

**Context manager for cleanup:**
```python
from contextlib import contextmanager

@contextmanager
def run_with_interruption_handling(
    context: RunContext,
    context_manager: ContextManager,
):
    """Context manager that ensures state is saved on interrupt."""
    original_handlers = {}

    def handler(signum, frame):
        # Mark as interrupted
        context.status = "interrupted"
        context.interrupted_phase = context.current_phase
        context.interrupted_at = datetime.now(timezone.utc)
        context_manager.save(context)
        raise KeyboardInterrupt

    # Install handlers
    original_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, handler)
    original_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, handler)

    try:
        yield
    finally:
        # Restore original handlers
        for sig, orig_handler in original_handlers.items():
            signal.signal(sig, orig_handler)
```

### File Structure Requirements

**Files to modify/create:**
```
src/adw/
├── core/
│   ├── interruption.py      # NEW - signal handling
│   └── context_manager.py   # MODIFY - add status methods
├── models/
│   ├── context.py           # MODIFY - add status fields
│   └── enums.py             # NEW or MODIFY - RunStatus enum
tests/
├── unit/
│   └── core/
│       └── test_interruption.py  # NEW
└── integration/
    └── test_resume.py            # NEW
```

**RunStatus Enum:**
```python
# src/adw/models/enums.py
from enum import Enum

class RunStatus(str, Enum):
    """Run execution status."""
    RUNNING = "running"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
```

**InterruptionHandler Class:**
```python
# src/adw/core/interruption.py
import signal
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from adw.core.context_manager import ContextManager
    from adw.core.snapshot_manager import SnapshotManager
    from adw.models import RunContext


class InterruptionHandler:
    """Handles graceful shutdown on interruption signals.

    Ensures:
    - Current context is saved before exit (NFR7)
    - Run status is set to "interrupted"
    - Final snapshot is created
    """

    def __init__(
        self,
        context_manager: "ContextManager",
        snapshot_manager: "SnapshotManager",
    ) -> None:
        self.context_manager = context_manager
        self.snapshot_manager = snapshot_manager
        self._shutdown_requested = False
        self._original_handlers: dict = {}
        self._current_context: "RunContext | None" = None

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested

    def set_context(self, context: "RunContext") -> None:
        """Set the current context to save on interrupt."""
        self._current_context = context

    def install_handlers(self) -> None:
        """Install signal handlers for interruption."""
        self._original_handlers[signal.SIGINT] = signal.signal(
            signal.SIGINT, self._handle_signal
        )
        self._original_handlers[signal.SIGTERM] = signal.signal(
            signal.SIGTERM, self._handle_signal
        )

    def restore_handlers(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()

    def _handle_signal(self, signum: int, frame: object) -> None:
        """Handle interruption signal."""
        self._shutdown_requested = True

        if self._current_context:
            # Update status
            self._current_context = self._current_context.model_copy(update={
                "status": "interrupted",
                "interrupted_phase": self._current_context.current_phase,
                "interrupted_at": datetime.now(timezone.utc),
            })

            # Save context and snapshot
            try:
                self.context_manager.save(self._current_context)
                self.snapshot_manager.create_post_phase_snapshot(
                    context=self._current_context,
                    phase=self._current_context.current_phase,
                    phase_result=None,  # Interrupted, no result
                )
            except Exception:
                pass  # Best effort on signal handler

        raise KeyboardInterrupt

    @contextmanager
    def protected_execution(
        self,
        context: "RunContext",
    ) -> Generator["RunContext", None, None]:
        """Context manager for protected execution.

        Ensures state is saved on interrupt.
        """
        self.set_context(context)
        self.install_handlers()
        try:
            yield context
        finally:
            self.restore_handlers()


def get_resume_phase(context: "RunContext") -> str | None:
    """Determine which phase to resume from.

    Args:
        context: The run context to examine

    Returns:
        Phase to start from, or None if run is complete
    """
    from adw.models.enums import RunStatus

    if context.status == RunStatus.COMPLETED:
        return None

    if context.status == RunStatus.INTERRUPTED:
        # Resume from interrupted phase (re-execute)
        return context.interrupted_phase

    # For running/failed, find next uncompleted phase
    phase_order = ["plan", "build", "verify", "validate", "document"]
    for phase in phase_order:
        if phase not in context.completed_phases:
            return phase

    return None
```

**Resume Logic:**
```python
def resume_run(
    run_id: str,
    context_manager: ContextManager,
    orchestrator: Orchestrator,
) -> RunContext:
    """Resume an interrupted or failed run.

    Args:
        run_id: The run to resume
        context_manager: For loading context
        orchestrator: For running phases

    Returns:
        Final run context

    Raises:
        StateError: If run cannot be resumed
    """
    context = context_manager.load(run_id)

    # Check if resumable
    if context.status == RunStatus.COMPLETED:
        raise StateError(
            code="RUN_ALREADY_COMPLETE",
            message=f"Run {run_id} is already complete",
            suggestion="Start a new run instead",
            recoverable=False,
        )

    # Determine resume point
    resume_phase = get_resume_phase(context)
    if resume_phase is None:
        raise StateError(
            code="CANNOT_DETERMINE_RESUME",
            message=f"Cannot determine resume point for run {run_id}",
            suggestion="Check run status and phase history",
            recoverable=False,
        )

    # Update status
    context = context.model_copy(update={
        "status": "running",
        "interrupted_phase": None,
        "interrupted_at": None,
    })
    context_manager.save(context)

    # Resume execution
    return orchestrator.continue_from_phase(context, resume_phase)
```

### Testing Requirements

**Test Framework:** pytest

**Test signal handling:**
```python
import signal
from unittest.mock import MagicMock

def test_install_handlers(interruption_handler):
    """Test that handlers are installed."""
    interruption_handler.install_handlers()

    # Verify handlers are changed
    assert signal.getsignal(signal.SIGINT) != signal.SIG_DFL

    interruption_handler.restore_handlers()


def test_context_saved_on_interrupt(
    interruption_handler,
    sample_context,
    mocker,
):
    """Test that context is saved when signal received."""
    save_spy = mocker.spy(interruption_handler.context_manager, "save")

    interruption_handler.set_context(sample_context)
    interruption_handler.install_handlers()

    with pytest.raises(KeyboardInterrupt):
        interruption_handler._handle_signal(signal.SIGINT, None)

    save_spy.assert_called_once()
    saved_context = save_spy.call_args[0][0]
    assert saved_context.status == "interrupted"
```

**Test resume detection:**
```python
def test_get_resume_phase_after_interrupt(sample_context):
    """Test resume phase detection after interrupt."""
    context = sample_context.model_copy(update={
        "status": "interrupted",
        "interrupted_phase": "build",
        "completed_phases": ["plan"],
    })

    resume_phase = get_resume_phase(context)
    assert resume_phase == "build"


def test_get_resume_phase_complete_returns_none(sample_context):
    """Test that completed runs return None."""
    context = sample_context.model_copy(update={
        "status": "completed",
    })

    resume_phase = get_resume_phase(context)
    assert resume_phase is None
```

**Coverage Target:** >80% overall, >90% for `interruption.py`

---

## Previous Story Intelligence

**From Story 4.2 (Atomic Writes):**
- Context save pattern established
- Error handling with StateError
- Lock acquisition patterns

**From Story 4.3 (Snapshots):**
- Snapshot creation on phase boundaries
- Sequential snapshot numbering

**Key learnings:**
- Save state immediately on changes
- Use atomic writes for durability
- Create snapshots for recovery

---

## Git Intelligence

**From Epic 3:**
- Exception patterns with codes and suggestions
- Status tracking patterns

**Existing models:**
- RunContext needs status, interrupted_phase, interrupted_at fields
- May need RunStatus enum

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Signal Handling**: Install handlers, restore on exit
2. **State Preservation**: Save immediately on status change
3. **Resume Semantics**: Re-execute interrupted phase from start
4. **Status Tracking**: Clear enum values for state machine
5. **Error Codes**: Use descriptive codes for resume errors

---

## Dev Notes

### Key Implementation Points

1. **Signal Handler Pattern**:
   ```python
   def _handle_signal(self, signum, frame):
       self._shutdown_requested = True
       # Save state
       self.context_manager.save(self._current_context)
       raise KeyboardInterrupt
   ```

2. **Resume Phase Detection**:
   ```python
   if context.status == "interrupted":
       return context.interrupted_phase  # Re-execute from start
   # Otherwise find next uncompleted
   ```

3. **Status Tracking**:
   ```python
   context = context.model_copy(update={
       "status": "interrupted",
       "interrupted_phase": current_phase,
       "interrupted_at": datetime.now(timezone.utc),
   })
   ```

4. **Protected Execution Context Manager**:
   ```python
   with handler.protected_execution(context) as ctx:
       # Run phases
       # If interrupted, handler saves state automatically
   ```

### Project Structure Notes

- New `interruption.py` in `core/`
- Enhances `RunContext` with status fields
- May need `RunStatus` enum in `models/`
- Integration with orchestrator for resume

### References

- [Source: _bmad-output/architecture.md#NFR7]
- [Source: _bmad-output/architecture.md#NFR8]
- [Source: src/adw/models/context.py] - RunContext
- [Source: src/adw/core/context_manager.py]

---

## Dev Agent Record

### Context Reference

Story 4.5 implements graceful interruption handling and resume capability, ensuring no data loss on Ctrl+C (NFR7) and successful resume from phase boundaries (NFR8).

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Task 1: Created `InterruptionHandler` class in `src/adw/core/interruption.py` with signal registration, context preservation, and graceful shutdown flag

### File List

- `src/adw/core/interruption.py` (NEW) - Signal handling for SIGINT/SIGTERM
- `src/adw/models/context.py` (MODIFIED) - Added `interrupted_phase`, `interrupted_at` fields, typed `status` field
- `src/adw/core/snapshot_manager.py` (MODIFIED) - Updated `create_post_phase_snapshot` to accept optional phase_result
- `tests/unit/core/test_interruption.py` (NEW) - 18 unit tests for interruption handling

---

## Dependencies

- **Depends On:** Story 4.1 (directory), 4.2 (context manager), 4.3 (snapshots)
- **Blocks:** None
- **Can Parallel With:** None (final story in epic)

### Dependency Rationale
- Story 4.1: Needs run directory structure
- Story 4.2: Uses context manager for saving state
- Story 4.3: Creates final snapshot on interrupt
- Final story - integrates all previous work

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-01 | BMAD Create-Story | Initial story creation with comprehensive context |
