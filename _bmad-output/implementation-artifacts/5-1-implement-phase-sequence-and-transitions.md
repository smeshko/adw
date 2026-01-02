# Story 5.1: Implement Phase Sequence and Transitions

Status: in-progress
Linear Issue: not-configured
Epic: 5 - Pipeline Orchestration
Created: 2026-01-02

---

## Story

As a developer,
I want phases executed in the fixed order with clean transitions,
so that the pipeline follows the defined workflow.

## Acceptance Criteria

**Given** a full run is requested
**When** the orchestrator executes
**Then** phases run in order: Plan → Build → Verify → Validate → Document

**Given** the orchestrator transitions between phases
**When** I measure transition time (excluding LLM)
**Then** it completes within 1 second (NFR2)

**Given** a phase completes successfully
**When** transitioning to the next phase
**Then** state is persisted before starting the next phase

**Given** a phase fails
**When** the error is not recoverable
**Then** the pipeline stops and run status is set to "failed"

**Given** a phase fails
**When** the error is recoverable
**Then** retry is attempted based on configuration

## Tasks / Subtasks

### Task 1: Define Phase Sequence Constant
- [x] Create `PHASE_SEQUENCE` constant: `["plan", "build", "verify", "validate", "document"]`
- [x] Add to `src/adw/core/constants.py` or `orchestrator.py`
- [x] Ensure order is immutable (tuple)

### Task 2: Create Orchestrator Class
- [x] Create `src/adw/core/orchestrator.py`
- [x] Implement `Orchestrator` class with constructor accepting dependencies
- [x] Accept `context_manager: ContextManager`, `snapshot_manager: SnapshotManager`
- [x] Accept `artifact_manager: ArtifactManager`
- [x] Store `runs_dir: Path` for file operations

### Task 3: Implement Phase Transition Logic
- [x] Add `_transition_to_next_phase(context: RunContext, current_phase: str)` method
- [x] Calculate next phase from `PHASE_SEQUENCE`
- [x] Persist state via `context_manager.save()` before transition
- [x] Create post-phase snapshot via `snapshot_manager.create_post_phase_snapshot()`
- [x] Update `context.phase_history` with completed phase
- [x] Return updated `RunContext` (immutable update pattern)

### Task 4: Implement run() Method
- [ ] Add `run(feature_description: str) -> RunContext` method
- [ ] Generate ULID for run_id
- [ ] Create initial `RunContext` with status="running"
- [ ] Iterate through `PHASE_SEQUENCE`
- [ ] Create pre-phase snapshot before each phase
- [ ] Execute phase (placeholder - delegate to PhaseRunner in 5.2)
- [ ] Handle phase result and transition
- [ ] Set final status to "completed" or "failed"

### Task 5: Implement Error Handling
- [ ] Catch exceptions during phase execution
- [ ] Check `recoverable` flag on `ADWError` subclasses
- [ ] For non-recoverable: set `status="failed"`, persist, and stop
- [ ] For recoverable: implement retry based on config (default: 3 attempts)
- [ ] Log error with structured fields: `phase`, `error_code`, `attempt`
- [ ] Ensure partial state is always persisted on failure

### Task 6: Implement Retry Logic
- [ ] Add `_retry_phase(context, phase, max_attempts)` method
- [ ] Track retry count per phase
- [ ] Use exponential backoff between retries (1s, 2s, 4s)
- [ ] Log each retry attempt
- [ ] Raise original error after max attempts exhausted

### Task 7: Ensure Performance (NFR2)
- [ ] Measure transition time (excluding LLM execution)
- [ ] Log transition duration with structured logging
- [ ] Verify < 1 second for phase transitions
- [ ] Optimize if needed (consider async writes)

### Task 8: Write Unit Tests
- [ ] Create `tests/unit/core/test_orchestrator.py`
- [ ] Test phase sequence order
- [ ] Test successful full run
- [ ] Test state persistence at transitions
- [ ] Test non-recoverable error stops pipeline
- [ ] Test recoverable error triggers retry
- [ ] Test retry exhaustion
- [ ] Test transition performance (<1s)
- [ ] Target: >90% coverage

### Task 9: Write Integration Tests
- [ ] Create `tests/integration/core/test_orchestrator_integration.py`
- [ ] Test full run with MockExecutor
- [ ] Verify snapshots created at each boundary
- [ ] Verify artifacts persisted correctly
- [ ] Test resume from interrupted run

---

## Developer Context

### Technical Requirements

- **Phase Order**: Fixed sequence - Plan → Build → Verify → Validate → Document
- **State Persistence**: Save context before each transition (NFR6)
- **Transition Performance**: < 1 second excluding LLM time (NFR2)
- **Error Classification**: Use `recoverable` flag to determine retry vs stop
- **Immutable Updates**: Use `context.model_copy(update={...})` pattern

### Architecture Compliance

**From architecture.md - Core Orchestration:**
```
src/adw/
├── core/
│   ├── orchestrator.py    # Main orchestrator
│   ├── phase_runner.py    # Single phase execution (Story 5.2)
│   └── context_manager.py # Context loading/saving
```

**From architecture.md - FR7:**
```
FR7: System executes phases in fixed order (Plan → Build → Verify → Validate → Document)
```

**From architecture.md - NFR2:**
```
NFR2: Phase transitions shall complete within 1 second (excluding LLM time)
```

**From architecture.md - NFR6:**
```
NFR6: System shall persist state before each phase transition
```

**From architecture.md - Async Model:**
```
The orchestrator and phase runner use synchronous Python. Async is used only within
the LLM executor for streaming subprocess output via `asyncio.run()`.
```

**From architecture.md - Error Handling:**
```python
class ADWError(Exception):
    code: str           # e.g., "HOOK_FAILED", "LLM_TIMEOUT"
    recoverable: bool   # Can this be retried?
    phase: str | None   # Which phase failed
    suggestion: str     # Actionable next step for user
```

### Library & Framework Requirements

**ULID Generation:**
```python
from ulid import ULID

run_id = str(ULID())  # "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
```

**Immutable Context Updates:**
```python
# CORRECT - immutable update via Pydantic
new_context = context.model_copy(update={
    "current_phase": "build",
    "phase_history": context.phase_history + ["plan"],
})

# WRONG - direct mutation
context.current_phase = "build"  # NO - loses audit trail
```

**Structured Logging:**
```python
import structlog
logger = structlog.get_logger()

logger.info("Phase transition", from_phase="plan", to_phase="build", duration_ms=45)
logger.error("Phase failed", phase="build", error_code="HOOK_FAILED", attempt=2)
```

**Retry with Exponential Backoff:**
```python
import time

def _retry_phase(self, context, phase, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return self._execute_phase(context, phase)
        except ADWError as e:
            if not e.recoverable or attempt == max_attempts - 1:
                raise
            delay = 2 ** attempt  # 1s, 2s, 4s
            logger.warning("Retrying phase", phase=phase, attempt=attempt+1, delay=delay)
            time.sleep(delay)
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── core/
│   ├── orchestrator.py       # NEW - Main Orchestrator class
│   └── constants.py          # NEW - PHASE_SEQUENCE constant
tests/
├── unit/
│   └── core/
│       └── test_orchestrator.py  # NEW
└── integration/
    └── core/
        └── test_orchestrator_integration.py  # NEW
```

**Orchestrator Class Skeleton:**
```python
# src/adw/core/orchestrator.py
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from ulid import ULID

from adw.core.constants import PHASE_SEQUENCE
from adw.core.context_manager import ContextManager
from adw.core.snapshot_manager import SnapshotManager
from adw.core.artifact_manager import ArtifactManager
from adw.exceptions import ADWError
from adw.models import RunContext, PhaseResult, PhaseStatus

if TYPE_CHECKING:
    from adw.core.phase_runner import PhaseRunner

import structlog
logger = structlog.get_logger()


class Orchestrator:
    """Main orchestrator for ADW pipeline execution.

    Coordinates phase execution in fixed order:
    Plan → Build → Verify → Validate → Document

    Handles:
    - Phase sequencing and transitions
    - State persistence at boundaries
    - Error handling and retry logic
    - Snapshot creation for debugging
    """

    def __init__(
        self,
        runs_dir: Path,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
        artifact_manager: ArtifactManager,
        *,
        max_retries: int = 3,
    ) -> None:
        self.runs_dir = runs_dir
        self.context_manager = context_manager
        self.snapshot_manager = snapshot_manager
        self.artifact_manager = artifact_manager
        self.max_retries = max_retries
        self._phase_runner: "PhaseRunner | None" = None

    def set_phase_runner(self, phase_runner: "PhaseRunner") -> None:
        """Set the phase runner (injected to avoid circular deps)."""
        self._phase_runner = phase_runner

    def run(self, feature_description: str) -> RunContext:
        """Execute the full pipeline for a feature.

        Args:
            feature_description: Description of the feature to implement

        Returns:
            Final RunContext with status and artifacts

        Raises:
            ADWError: If a non-recoverable error occurs
        """
        # Generate run ID
        run_id = str(ULID())

        # Create initial context
        context = RunContext(
            run_id=run_id,
            feature_description=feature_description,
            current_phase=PHASE_SEQUENCE[0],
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        # Persist initial state
        self.context_manager.save(context)

        logger.info("Starting run", run_id=run_id, feature=feature_description)

        try:
            for phase in PHASE_SEQUENCE:
                context = self._execute_phase_with_transitions(context, phase)

            # All phases complete
            context = context.model_copy(update={
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
            })
            self.context_manager.save(context)

            logger.info("Run completed", run_id=run_id)

        except ADWError as e:
            # Mark as failed and persist
            context = context.model_copy(update={
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
            })
            self.context_manager.save(context)

            logger.error("Run failed", run_id=run_id, phase=e.phase, error=e.code)
            raise

        return context

    def _execute_phase_with_transitions(
        self,
        context: RunContext,
        phase: str,
    ) -> RunContext:
        """Execute a single phase with proper transitions.

        1. Create pre-phase snapshot
        2. Update current_phase
        3. Execute phase (with retries if recoverable)
        4. Create post-phase snapshot
        5. Transition to next phase

        Args:
            context: Current run context
            phase: Phase to execute

        Returns:
            Updated context after phase completion
        """
        transition_start = time.monotonic()

        # Update current phase
        context = context.model_copy(update={"current_phase": phase})
        self.context_manager.save(context)

        # Pre-phase snapshot
        self.snapshot_manager.create_pre_phase_snapshot(context, phase)

        logger.info("Starting phase", phase=phase, run_id=context.run_id)

        # Execute phase with retry for recoverable errors
        result = self._execute_phase_with_retry(context, phase)

        # Post-phase snapshot
        self.snapshot_manager.create_post_phase_snapshot(context, phase, result)

        # Update context with phase completion
        context = context.model_copy(update={
            "phase_history": context.phase_history + [phase],
            "phase_tokens": {**context.phase_tokens, phase: result.tokens_used},
        })
        self.context_manager.save(context)

        transition_time = (time.monotonic() - transition_start) * 1000
        logger.info("Phase completed", phase=phase, duration_ms=transition_time)

        if transition_time > 1000:
            logger.warning("Transition exceeded 1s", phase=phase, duration_ms=transition_time)

        return context

    def _execute_phase_with_retry(
        self,
        context: RunContext,
        phase: str,
    ) -> PhaseResult:
        """Execute a phase with retry logic for recoverable errors.

        Args:
            context: Current run context
            phase: Phase to execute

        Returns:
            PhaseResult from successful execution

        Raises:
            ADWError: If error is non-recoverable or retries exhausted
        """
        last_error: ADWError | None = None

        for attempt in range(self.max_retries):
            try:
                # Delegate to PhaseRunner (Story 5.2)
                if self._phase_runner is None:
                    raise RuntimeError("PhaseRunner not set - call set_phase_runner()")
                return self._phase_runner.run(phase, context)

            except ADWError as e:
                last_error = e

                if not e.recoverable:
                    logger.error("Non-recoverable error", phase=phase, error=e.code)
                    raise

                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt  # 1, 2, 4 seconds
                    logger.warning(
                        "Retrying phase",
                        phase=phase,
                        attempt=attempt + 1,
                        max_attempts=self.max_retries,
                        delay=delay,
                    )
                    time.sleep(delay)

        # Retries exhausted
        logger.error("Retries exhausted", phase=phase, attempts=self.max_retries)
        raise last_error  # type: ignore[misc]

    def get_next_phase(self, current_phase: str) -> str | None:
        """Get the next phase in the sequence.

        Args:
            current_phase: Current phase name

        Returns:
            Next phase name, or None if current is last
        """
        try:
            idx = PHASE_SEQUENCE.index(current_phase)
            if idx < len(PHASE_SEQUENCE) - 1:
                return PHASE_SEQUENCE[idx + 1]
            return None
        except ValueError:
            return None
```

**Constants File:**
```python
# src/adw/core/constants.py
"""Core constants for ADW pipeline execution."""

# Fixed phase sequence - order is critical
PHASE_SEQUENCE: tuple[str, ...] = (
    "plan",
    "build",
    "verify",
    "validate",
    "document",
)
```

### Testing Requirements

**Test Framework:** pytest

**Test phase sequence:**
```python
from adw.core.constants import PHASE_SEQUENCE

def test_phase_sequence_order():
    """Test that phase sequence is in correct order."""
    assert PHASE_SEQUENCE == ("plan", "build", "verify", "validate", "document")


def test_phase_sequence_immutable():
    """Test that phase sequence cannot be modified."""
    assert isinstance(PHASE_SEQUENCE, tuple)
```

**Test orchestrator run:**
```python
def test_run_executes_all_phases(orchestrator, mock_phase_runner):
    """Test that run executes all phases in order."""
    orchestrator.set_phase_runner(mock_phase_runner)

    context = orchestrator.run("Add feature X")

    assert context.status == "completed"
    assert context.phase_history == list(PHASE_SEQUENCE)
    assert mock_phase_runner.run.call_count == len(PHASE_SEQUENCE)
```

**Test state persistence:**
```python
def test_state_persisted_at_transitions(orchestrator, mock_phase_runner, context_manager):
    """Test that state is saved before each phase transition."""
    orchestrator.set_phase_runner(mock_phase_runner)

    orchestrator.run("Add feature X")

    # Should save: initial + (pre each phase + post each phase) + final
    # Minimum: initial + 5 phases * 2 saves + final = at least 6+ saves
    assert context_manager.save.call_count >= 6
```

**Test error handling:**
```python
def test_non_recoverable_error_stops_pipeline(orchestrator, mock_phase_runner):
    """Test that non-recoverable errors stop the pipeline."""
    from adw.exceptions import HookError

    mock_phase_runner.run.side_effect = HookError(
        code="HOOK_FAILED",
        message="Pre-hook failed",
        suggestion="Check hook script",
        recoverable=False,
        phase="build",
    )
    orchestrator.set_phase_runner(mock_phase_runner)

    with pytest.raises(HookError):
        orchestrator.run("Add feature X")

    # Should only attempt once for non-recoverable
    assert mock_phase_runner.run.call_count == 1
```

**Test retry logic:**
```python
def test_recoverable_error_triggers_retry(orchestrator, mock_phase_runner):
    """Test that recoverable errors trigger retries."""
    from adw.exceptions import LLMTimeoutError

    call_count = 0
    def side_effect(*args):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise LLMTimeoutError(
                code="LLM_TIMEOUT",
                message="Request timed out",
                suggestion="Retry",
                recoverable=True,
                phase="plan",
            )
        return PhaseResult(phase="plan", status=PhaseStatus.COMPLETED, ...)

    mock_phase_runner.run.side_effect = side_effect
    orchestrator.set_phase_runner(mock_phase_runner)

    context = orchestrator.run("Add feature X")

    # Should succeed after retries
    assert context.status == "completed"
    assert call_count == 3  # 2 failures + 1 success
```

**Test transition performance:**
```python
def test_transition_under_1_second(orchestrator, mock_phase_runner):
    """Test that phase transitions complete under 1 second (NFR2)."""
    import time

    # Make phase runner return immediately
    mock_phase_runner.run.return_value = PhaseResult(
        phase="plan",
        status=PhaseStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    orchestrator.set_phase_runner(mock_phase_runner)

    start = time.monotonic()
    orchestrator.run("Add feature X")
    elapsed = time.monotonic() - start

    # All transitions (5 phases) should be under 5 seconds
    # Each transition should be under 1 second
    assert elapsed < 5.0, f"Total time {elapsed}s should be < 5s"
```

**Coverage Target:** >80% overall, >90% for `orchestrator.py`

---

## Previous Story Intelligence

**From Story 4.3 (State Snapshots):**
- `SnapshotManager` exists at `src/adw/core/snapshot_manager.py`
- Use `create_pre_phase_snapshot()` and `create_post_phase_snapshot()` methods
- Snapshots named: `<seq>_<timing>_<phase>.json`

**From Story 4.4 (Artifact Manager):**
- `ArtifactManager` exists at `src/adw/core/artifact_manager.py`
- Use `store()` and `get()` for artifact operations
- Artifacts at: `artifacts/<phase>/<name>`

**From Story 4.5 (Interruption & Recovery):**
- `InterruptionHandler` exists at `src/adw/core/interruption.py`
- Use `check_shutdown()` for graceful interruption detection
- `prepare_resume()` and `get_resume_phase()` for resume logic
- RunContext has `status`, `interrupted_phase`, `interrupted_at` fields

**Key patterns:**
- Atomic writes for all state persistence
- Immutable context updates via `model_copy()`
- Structured logging with phase context
- Error codes from exception hierarchy

---

## Git Intelligence

**Recent commits from Epic 4:**
```
d0032b0 chore(story-4-5): mark story and epic-4 complete in sprint status
fa8372f test(story-4-5): add integration tests for signal handling
b5471d1 docs(story-4-5): mark Task 7 complete - 49 unit tests written
17022c6 feat(story-4-5): add get_run_status function for status display
0cb5fe8 feat(story-4-5): add prepare_resume function for resume execution
d8e1a91 feat(story-4-5): add resume detection with get_resume_phase and can_resume
```

**Existing modules in src/adw/core/:**
- `context_manager.py` - Context persistence
- `snapshot_manager.py` - State snapshots
- `artifact_manager.py` - Artifact storage
- `run_directory.py` - Run directory structure
- `interruption.py` - Signal handling and recovery

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Naming**: Classes are PascalCase (`Orchestrator`), functions are snake_case (`run_phase`)
2. **Type Annotations**: Full annotations on all public methods
3. **Immutable Updates**: Use `context.model_copy(update={...})`
4. **Structured Logging**: Use `logger.info("message", key=value)`
5. **Error Handling**: Use exception hierarchy, never bare `Exception`
6. **Testing**: pytest with fixtures in `tests/fixtures/`

---

## Dev Notes

### Key Implementation Points

1. **Phase Sequence is Immutable**:
   ```python
   PHASE_SEQUENCE: tuple[str, ...] = ("plan", "build", "verify", "validate", "document")
   # Tuple ensures it cannot be accidentally modified
   ```

2. **State Persistence Pattern**:
   ```python
   # Before each transition
   context = context.model_copy(update={"current_phase": next_phase})
   self.context_manager.save(context)  # Persist before moving on
   ```

3. **Retry Logic for Recoverable Errors**:
   ```python
   if e.recoverable:
       time.sleep(2 ** attempt)  # Exponential backoff
       continue  # Retry
   else:
       raise  # Stop pipeline
   ```

4. **Transition Time Monitoring**:
   ```python
   start = time.monotonic()
   # ... execute transition ...
   elapsed_ms = (time.monotonic() - start) * 1000
   if elapsed_ms > 1000:
       logger.warning("Transition slow", elapsed_ms=elapsed_ms)
   ```

### Project Structure Notes

- Orchestrator coordinates with PhaseRunner (Story 5.2) for actual phase execution
- This story creates the orchestration skeleton; 5.2 adds PhaseRunner
- Story 5.3 adds artifact passing between phases
- Story 5.4 adds single-phase execution mode
- Story 5.5 adds progress display

### References

- [Source: _bmad-output/architecture.md#Core-Orchestration]
- [Source: _bmad-output/architecture.md#FR7]
- [Source: _bmad-output/architecture.md#NFR2]
- [Source: _bmad-output/architecture.md#NFR6]
- [Source: _bmad-output/prd.md#Phase-Execution]
- [Source: src/adw/core/context_manager.py] - ContextManager
- [Source: src/adw/core/snapshot_manager.py] - SnapshotManager
- [Source: src/adw/core/artifact_manager.py] - ArtifactManager

---

## Dev Agent Record

### Context Reference

Story 5.1 implements the core orchestrator for phase sequencing and transitions, building on the state management infrastructure from Epic 4.

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created PHASE_SEQUENCE constant as immutable tuple in src/adw/core/constants.py
- Added comprehensive unit tests in tests/unit/core/test_constants.py (6 tests)
- Exported PHASE_SEQUENCE from src/adw/core/__init__.py
- Task 2: Created Orchestrator class with full dependency injection (ContextManager, SnapshotManager, ArtifactManager, RunDirectoryManager)
- Added 11 unit tests for init, set_phase_runner, and get_next_phase
- Task 3: Implemented _execute_phase_with_transitions with state persistence, snapshots, and immutable context updates
- Added 6 comprehensive tests for phase transition behavior

### File List

- src/adw/core/constants.py (NEW)
- src/adw/core/orchestrator.py (NEW)
- src/adw/core/__init__.py (MODIFIED)
- tests/unit/core/test_constants.py (NEW)
- tests/unit/core/test_orchestrator.py (NEW)

---

## Dependencies

- **Depends On:** Epic 4 (Stories 4.1-4.5) - needs ContextManager, SnapshotManager, ArtifactManager, InterruptionHandler
- **Blocks:** Stories 5.2, 5.4, 5.5 - PhaseRunner and other orchestration features need Orchestrator
- **Can Parallel With:** None - this is the foundation for Epic 5

### Dependency Rationale
- Epic 4: Provides all state management infrastructure needed for orchestration
- Story 5.2: PhaseRunner needs Orchestrator to coordinate with
- Story 5.4: Single-phase execution builds on orchestrator
- Story 5.5: Progress display integrates with orchestrator events

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-02 | BMAD Create-Story | Initial story creation with comprehensive context |
