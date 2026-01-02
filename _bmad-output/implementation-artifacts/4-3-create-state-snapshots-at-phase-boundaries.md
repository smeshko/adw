# Story 4.3: Create State Snapshots at Phase Boundaries

Status: ready-for-dev
Linear Issue: not-configured
Epic: 4 - State Persistence & Context Management
Created: 2026-01-01

---

## Story

As a developer,
I want state snapshots taken before and after each phase,
so that I can debug failures and resume from known-good states.

## Acceptance Criteria

**Given** a phase is about to start
**When** the orchestrator enters the phase
**Then** a snapshot is saved to `snapshots/<seq>_pre_<phase>.json`

**Given** a phase completes successfully
**When** the orchestrator exits the phase
**Then** a snapshot is saved to `snapshots/<seq>_post_<phase>.json`

**Given** snapshot creation
**When** I measure duration
**Then** it completes within 500ms (NFR4)

**Given** the snapshots directory
**When** I list snapshots
**Then** they are numbered sequentially (001, 002, etc.)

**Given** a snapshot file
**When** I load it
**Then** it's a complete StateSnapshot model with: context, phase_result, timestamp

## Tasks / Subtasks

### Task 1: Create StateSnapshot Model
- [x] Add `StateSnapshot` model to `src/adw/models/`
- [x] Include `context: RunContext` field
- [x] Include `phase_result: PhaseResult | None` field
- [x] Include `timestamp: datetime` field
- [x] Include `label: str` field (e.g., "pre_plan", "post_build")
- [x] Include `sequence: int` field

### Task 2: Create SnapshotManager Class
- [x] Create `src/adw/core/snapshot_manager.py`
- [x] Implement `create_pre_phase_snapshot()`
- [x] Implement `create_post_phase_snapshot()`
- [x] Use atomic write pattern from Story 4.2
- [x] Track sequence number across snapshots

### Task 3: Implement Snapshot Naming
- [x] Format: `<seq>_<timing>_<phase>.json`
- [x] Sequence: zero-padded 3 digits (001, 002, etc.)
- [x] Timing: "pre" or "post"
- [x] Phase: phase name (plan, build, verify, etc.)
- [x] Example: `001_pre_plan.json`, `002_post_plan.json`

### Task 4: Implement Snapshot Listing
- [x] Add `list_snapshots(run_id)` method
- [x] Return snapshots sorted by sequence
- [x] Include metadata without loading full content
- [x] Handle empty snapshots directory

### Task 5: Implement Snapshot Loading
- [ ] Add `load_snapshot(run_id, snapshot_id)` method
- [ ] Validate against StateSnapshot model
- [ ] Handle missing or corrupted snapshots
- [ ] Raise StateError with appropriate codes

### Task 6: Ensure Performance (NFR4)
- [ ] Benchmark snapshot creation
- [ ] Optimize if exceeds 500ms
- [ ] Consider async write if needed
- [ ] Log duration for monitoring

### Task 7: Write Unit Tests
- [ ] Create `tests/unit/core/test_snapshot_manager.py`
- [ ] Test pre-phase snapshot creation
- [ ] Test post-phase snapshot creation
- [ ] Test sequential numbering
- [ ] Test snapshot loading
- [ ] Test performance requirement
- [ ] Target: >90% coverage

### Task 8: Write Integration Tests
- [ ] Test full phase lifecycle with snapshots
- [ ] Test snapshot listing across phases
- [ ] Verify snapshot content integrity
- [ ] Test recovery from snapshots

---

## Developer Context

### Technical Requirements

- **Snapshot Model**: Pydantic model with context, phase_result, timestamp
- **Sequential Naming**: Zero-padded sequence numbers (001, 002, ...)
- **Atomic Writes**: Use same pattern as context_manager (temp + rename)
- **Performance**: Complete within 500ms (NFR4)
- **File Location**: `snapshots/<seq>_<timing>_<phase>.json`

### Architecture Compliance

**From architecture.md - State Persistence:**
```
.adw/runs/<run_id>/
├── context.json
├── snapshots/
│   └── <seq>_<label>.json  # StateSnapshot at key moments
└── artifacts/
```

**From architecture.md - NFR4:**
```
NFR4: State snapshots shall complete within 500ms
```

**From architecture.md - Observability:**
```
NFR13: State snapshots shall enable "time travel" debugging
```

**From architecture.md - Logging Models:**
```python
class StateSnapshot(BaseModel):
    """State captured at a specific moment."""
    context: RunContext
    phase_result: PhaseResult | None
    timestamp: datetime
    label: str  # e.g., "pre_plan", "post_build"
```

### Library & Framework Requirements

**Pydantic datetime handling:**
```python
from datetime import datetime, timezone

class StateSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

**Atomic write (same as context_manager):**
```python
import os
from pathlib import Path

def atomic_write(path: Path, content: str) -> None:
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    temp_path.rename(path)
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── core/
│   └── snapshot_manager.py   # NEW
├── models/
│   └── snapshot.py           # NEW - or add to existing log.py
tests/
├── unit/
│   └── core/
│       └── test_snapshot_manager.py  # NEW
```

**StateSnapshot Model:**
```python
# src/adw/models/snapshot.py
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from adw.models import PhaseResult, RunContext


class StateSnapshot(BaseModel):
    """State captured at phase boundaries for debugging and recovery.

    Snapshots are named: <seq>_<timing>_<phase>.json
    Example: 001_pre_plan.json, 002_post_plan.json
    """

    context: "RunContext"
    """Full run context at snapshot time."""

    phase_result: "PhaseResult | None" = None
    """Phase result (only for post-phase snapshots)."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """When snapshot was created."""

    label: str
    """Human-readable label (e.g., 'pre_plan', 'post_build')."""

    sequence: int
    """Sequential snapshot number (1, 2, 3, ...)."""
```

**SnapshotManager Class:**
```python
# src/adw/core/snapshot_manager.py
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from adw.exceptions import StateError
from adw.models.snapshot import StateSnapshot

if TYPE_CHECKING:
    from adw.models import PhaseResult, RunContext


class SnapshotManager:
    """Manages state snapshots at phase boundaries.

    Creates snapshots before and after each phase for:
    - Debugging failures
    - Resuming from known-good states
    - Time-travel debugging (NFR13)
    """

    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir
        self._sequence_cache: dict[str, int] = {}

    def create_pre_phase_snapshot(
        self,
        context: "RunContext",
        phase: str,
    ) -> Path:
        """Create snapshot before phase starts.

        Args:
            context: Current run context
            phase: Phase about to start

        Returns:
            Path to created snapshot file

        Raises:
            StateError: If snapshot creation fails
        """
        return self._create_snapshot(
            context=context,
            phase_result=None,
            phase=phase,
            timing="pre",
        )

    def create_post_phase_snapshot(
        self,
        context: "RunContext",
        phase: str,
        phase_result: "PhaseResult",
    ) -> Path:
        """Create snapshot after phase completes.

        Args:
            context: Current run context
            phase: Phase that just completed
            phase_result: Result of the phase

        Returns:
            Path to created snapshot file

        Raises:
            StateError: If snapshot creation fails
        """
        return self._create_snapshot(
            context=context,
            phase_result=phase_result,
            phase=phase,
            timing="post",
        )

    def _create_snapshot(
        self,
        context: "RunContext",
        phase_result: "PhaseResult | None",
        phase: str,
        timing: str,
    ) -> Path:
        """Internal method to create a snapshot.

        Must complete within 500ms (NFR4).
        """
        start_time = time.monotonic()

        run_id = context.run_id
        snapshots_dir = self.runs_dir / run_id / "snapshots"

        # Get next sequence number
        sequence = self._get_next_sequence(run_id, snapshots_dir)

        # Create snapshot
        label = f"{timing}_{phase}"
        snapshot = StateSnapshot(
            context=context,
            phase_result=phase_result,
            timestamp=datetime.now(timezone.utc),
            label=label,
            sequence=sequence,
        )

        # Generate filename: 001_pre_plan.json
        filename = f"{sequence:03d}_{label}.json"
        snapshot_path = snapshots_dir / filename
        temp_path = snapshot_path.with_suffix(".tmp")

        try:
            # Atomic write with fsync
            with open(temp_path, "w") as f:
                f.write(snapshot.model_dump_json(indent=2))
                f.flush()
                os.fsync(f.fileno())
            temp_path.rename(snapshot_path)

        except OSError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise StateError(
                code="SNAPSHOT_WRITE_FAILED",
                message=f"Failed to write snapshot: {e}",
                suggestion="Check filesystem permissions and disk space",
                recoverable=False,
            ) from e

        # Check performance requirement
        elapsed_ms = (time.monotonic() - start_time) * 1000
        if elapsed_ms > 500:
            # Log warning but don't fail
            logger.warning(
                "Snapshot creation exceeded 500ms",
                elapsed_ms=elapsed_ms,
                snapshot=filename,
            )

        return snapshot_path

    def _get_next_sequence(self, run_id: str, snapshots_dir: Path) -> int:
        """Get next sequence number for snapshots."""
        # Check cache first
        if run_id in self._sequence_cache:
            self._sequence_cache[run_id] += 1
            return self._sequence_cache[run_id]

        # Count existing snapshots
        if not snapshots_dir.exists():
            self._sequence_cache[run_id] = 1
            return 1

        existing = list(snapshots_dir.glob("*.json"))
        next_seq = len(existing) + 1
        self._sequence_cache[run_id] = next_seq
        return next_seq

    def list_snapshots(self, run_id: str) -> list[dict]:
        """List all snapshots for a run.

        Returns:
            List of snapshot metadata sorted by sequence
        """
        snapshots_dir = self.runs_dir / run_id / "snapshots"
        if not snapshots_dir.exists():
            return []

        snapshots = []
        for path in sorted(snapshots_dir.glob("*.json")):
            # Parse filename: 001_pre_plan.json
            name = path.stem
            parts = name.split("_", 2)
            if len(parts) >= 3:
                snapshots.append({
                    "sequence": int(parts[0]),
                    "timing": parts[1],
                    "phase": parts[2],
                    "path": path,
                    "filename": path.name,
                })

        return sorted(snapshots, key=lambda s: s["sequence"])

    def load_snapshot(self, run_id: str, sequence: int) -> StateSnapshot:
        """Load a specific snapshot by sequence number.

        Args:
            run_id: The run ID
            sequence: Snapshot sequence number

        Returns:
            Loaded StateSnapshot

        Raises:
            StateError: If snapshot not found or corrupted
        """
        snapshots = self.list_snapshots(run_id)
        matching = [s for s in snapshots if s["sequence"] == sequence]

        if not matching:
            raise StateError(
                code="SNAPSHOT_NOT_FOUND",
                message=f"Snapshot {sequence} not found for run {run_id}",
                suggestion="Use list_snapshots to see available snapshots",
                recoverable=False,
            )

        path = matching[0]["path"]
        try:
            content = path.read_text()
            return StateSnapshot.model_validate_json(content)
        except (json.JSONDecodeError, ValidationError) as e:
            raise StateError(
                code="SNAPSHOT_CORRUPTED",
                message=f"Snapshot {sequence} is corrupted: {e}",
                suggestion="Try loading an earlier snapshot",
                recoverable=True,
            ) from e
```

### Testing Requirements

**Test Framework:** pytest

**Test snapshot creation:**
```python
def test_pre_phase_snapshot_created(snapshot_manager, sample_context):
    """Test pre-phase snapshot is created correctly."""
    path = snapshot_manager.create_pre_phase_snapshot(
        context=sample_context,
        phase="plan",
    )

    assert path.exists()
    assert path.name == "001_pre_plan.json"

    # Load and verify content
    snapshot = StateSnapshot.model_validate_json(path.read_text())
    assert snapshot.label == "pre_plan"
    assert snapshot.phase_result is None
    assert snapshot.sequence == 1


def test_post_phase_snapshot_includes_result(snapshot_manager, sample_context, sample_result):
    """Test post-phase snapshot includes phase result."""
    path = snapshot_manager.create_post_phase_snapshot(
        context=sample_context,
        phase="plan",
        phase_result=sample_result,
    )

    snapshot = StateSnapshot.model_validate_json(path.read_text())
    assert snapshot.phase_result is not None
    assert snapshot.label == "post_plan"
```

**Test sequential numbering:**
```python
def test_snapshots_numbered_sequentially(snapshot_manager, sample_context, sample_result):
    """Test that snapshots are numbered 001, 002, etc."""
    snapshot_manager.create_pre_phase_snapshot(sample_context, "plan")
    snapshot_manager.create_post_phase_snapshot(sample_context, "plan", sample_result)
    snapshot_manager.create_pre_phase_snapshot(sample_context, "build")

    snapshots = snapshot_manager.list_snapshots(sample_context.run_id)

    assert [s["sequence"] for s in snapshots] == [1, 2, 3]
    assert [s["filename"] for s in snapshots] == [
        "001_pre_plan.json",
        "002_post_plan.json",
        "003_pre_build.json",
    ]
```

**Test performance:**
```python
def test_snapshot_creation_under_500ms(snapshot_manager, sample_context):
    """Test that snapshot creation completes within 500ms (NFR4)."""
    import time

    start = time.monotonic()
    snapshot_manager.create_pre_phase_snapshot(sample_context, "plan")
    elapsed_ms = (time.monotonic() - start) * 1000

    assert elapsed_ms < 500, f"Snapshot took {elapsed_ms}ms, should be <500ms"
```

**Coverage Target:** >80% overall, >90% for `snapshot_manager.py`

---

## Previous Story Intelligence

**From Story 4.1 (Run Directory Structure):**
- `snapshots/` directory already created as part of run structure
- Use same `runs_dir` path pattern

**From Story 4.2 (Atomic Writes):**
- Use same atomic write pattern (temp file + fsync + rename)
- Use same error handling patterns (StateError with codes)

**Key learnings:**
- Atomic writes prevent corruption
- Lock files for concurrent access
- Clear error codes and suggestions

---

## Git Intelligence

**From Epic 3:**
- PhaseResult model exists at `src/adw/models/phase.py`
- RunContext model exists at `src/adw/models/context.py`
- datetime handling patterns established

**Existing models:**
- `PhaseResult` - has `tokens_used`, `tool_calls`, etc.
- `RunContext` - has `run_id`, `current_phase`, `completed_phases`

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Atomic Writes**: Always use temp file + fsync + rename
2. **Performance**: NFR4 requires <500ms for snapshots
3. **Error Codes**: Use descriptive codes like "SNAPSHOT_CORRUPTED"
4. **Type Annotations**: Full annotations on all methods
5. **Sequential Naming**: Zero-padded numbers for sorting

---

## Dev Notes

### Key Implementation Points

1. **Snapshot Naming Convention**:
   ```
   <seq>_<timing>_<phase>.json
   001_pre_plan.json
   002_post_plan.json
   003_pre_build.json
   ```

2. **Performance Monitoring**:
   ```python
   start = time.monotonic()
   # ... create snapshot ...
   elapsed_ms = (time.monotonic() - start) * 1000
   if elapsed_ms > 500:
       logger.warning("Snapshot slow", elapsed_ms=elapsed_ms)
   ```

3. **Sequence Caching**:
   ```python
   # Cache sequence per run to avoid filesystem queries
   self._sequence_cache: dict[str, int] = {}
   ```

4. **Listing Snapshots**:
   ```python
   # Parse filename: 001_pre_plan.json -> (1, "pre", "plan")
   name = path.stem
   parts = name.split("_", 2)
   ```

### Project Structure Notes

- New `snapshot_manager.py` in `core/` alongside `context_manager.py`
- New `StateSnapshot` model in `models/`
- Follows established patterns from Stories 4.1 and 4.2

### References

- [Source: _bmad-output/architecture.md#State-Persistence]
- [Source: _bmad-output/architecture.md#NFR4]
- [Source: src/adw/models/phase.py] - PhaseResult
- [Source: src/adw/models/context.py] - RunContext

---

## Dev Agent Record

### Context Reference

Story 4.3 implements state snapshots at phase boundaries for debugging and recovery, enabling "time travel" debugging (NFR13).

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

- `src/adw/models/context.py` - Updated StateSnapshot model
- `src/adw/models/__init__.py` - Added model_rebuild() for forward ref resolution
- `tests/unit/models/test_state_snapshot.py` - New tests for StateSnapshot
- `tests/unit/models/test_context.py` - Updated tests for new StateSnapshot schema
- `src/adw/core/snapshot_manager.py` - New SnapshotManager class
- `src/adw/core/__init__.py` - Added SnapshotManager export

---

## Dependencies

- **Depends On:** Story 4.1 (needs snapshots directory), Story 4.2 (needs atomic write pattern)
- **Blocks:** Story 4.5 (recovery needs snapshots)
- **Can Parallel With:** None (sequential after 4.2)

### Dependency Rationale
- Story 4.1: Snapshots directory must exist
- Story 4.2: Uses same atomic write pattern
- Story 4.5: Recovery loads from snapshots

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-01 | BMAD Create-Story | Initial story creation with comprehensive context |
