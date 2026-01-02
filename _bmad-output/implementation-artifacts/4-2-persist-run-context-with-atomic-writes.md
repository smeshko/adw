# Story 4.2: Persist Run Context with Atomic Writes

Status: in-progress
Linear Issue: not-configured
Epic: 4 - State Persistence & Context Management
Created: 2026-01-01

---

## Story

As a developer,
I want run context persisted atomically,
so that power loss or crashes don't corrupt state (ASR-5).

## Acceptance Criteria

**Given** a RunContext to be saved
**When** `context_manager.save(context)` is called
**Then** it writes to a temp file first, then atomically renames to `context.json`

**Given** atomic write in progress
**When** the process is killed mid-write
**Then** either the old context.json exists or the new one, never a partial file

**Given** context.json on disk
**When** I call `context_manager.load(run_id)`
**Then** it returns a validated RunContext instance

**Given** corrupted context.json (invalid JSON)
**When** load is attempted
**Then** StateError is raised with code "CONTEXT_CORRUPTED" and suggestion to check snapshots

**Given** context save
**When** fsync is called
**Then** data is guaranteed to be on disk (NFR6)

## Tasks / Subtasks

### Task 1: Enhance ContextManager with Atomic Writes
- [x] Update `src/adw/core/context_manager.py` with atomic save
- [x] Implement write-to-temp-then-rename pattern
- [x] Add fsync for data durability guarantee
- [x] Handle write errors gracefully

### Task 2: Implement Temp File Pattern
- [x] Create temp file in same directory (for atomic rename)
- [x] Use `.context.json.tmp` naming pattern
- [x] Clean up temp files on error
- [x] Ensure rename is atomic on POSIX systems

### Task 3: Implement fsync for Durability
- [x] Call `f.flush()` before close
- [x] Call `os.fsync(f.fileno())` for disk sync
- [x] Consider platform-specific durability

### Task 4: Implement Load with Validation
- [x] Load JSON from `context.json`
- [x] Validate using Pydantic `model_validate_json()`
- [x] Handle missing file (return None or raise)
- [x] Handle invalid JSON with proper error

### Task 5: Implement Corruption Detection
- [x] Catch JSON decode errors
- [x] Catch Pydantic validation errors
- [x] Raise StateError with code "CONTEXT_CORRUPTED"
- [x] Include suggestion to check snapshots

### Task 6: Add Lock Integration
- [x] Acquire run lock before save
- [x] Acquire run lock before load
- [x] Use context manager pattern

### Task 7: Write Unit Tests
- [x] Create/update `tests/unit/core/test_context_manager.py`
- [x] Test atomic write (temp file + rename)
- [x] Test fsync is called
- [x] Test load with valid context
- [x] Test load with corrupted file
- [x] Test load with missing file
- [x] Test lock acquisition
- [x] Target: >90% coverage

### Task 8: Write Durability Tests
- [x] Test that partial writes don't corrupt
- [x] Simulate process kill during write
- [x] Verify old or new context exists, never partial
- [x] Test temp file cleanup

---

## Developer Context

### Technical Requirements

- **Atomic Writes**: Write to temp file, then rename (atomic on POSIX)
- **Data Durability**: fsync before close (NFR6)
- **Pydantic Validation**: Validate JSON on load
- **Error Handling**: Proper StateError for corruption
- **Lock Integration**: Acquire lock before file operations

### Architecture Compliance

**From architecture.md - State Persistence Decision:**
```
All state objects (RunContext, PhaseResult, Artifact) are Pydantic models
serialized via model_dump_json() and loaded via model_validate_json().
```

**From architecture.md - Reliability Requirements:**
```
NFR6: System shall persist state before each phase transition
NFR7: System shall recover from interruption (Ctrl+C) without data loss
```

**From architecture.md - Error Handling:**
```python
class StateError(ADWError):
    code: str           # e.g., "CONTEXT_CORRUPTED"
    recoverable: bool
    suggestion: str     # Actionable next step for user
```

**Atomic Write Pattern (from architecture.md):**
```python
# CORRECT - atomic write pattern
import os
from pathlib import Path

def atomic_write(path: Path, content: str) -> None:
    """Write content atomically using temp file + rename."""
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    temp_path.rename(path)  # Atomic on POSIX
```

### Library & Framework Requirements

**Pydantic Serialization:**
```python
# Save
content = context.model_dump_json(indent=2)

# Load with validation
context = RunContext.model_validate_json(json_string)
```

**fsync for durability:**
```python
import os

with open(path, "w") as f:
    f.write(content)
    f.flush()
    os.fsync(f.fileno())  # Guarantee on disk
```

**filelock for concurrent access:**
```python
import filelock

with filelock.FileLock(lock_path, timeout=10):
    # Perform file operations
    pass
```

### File Structure Requirements

**Files to modify:**
```
src/adw/
├── core/
│   └── context_manager.py   # MODIFY - add atomic save/load
tests/
├── unit/
│   └── core/
│       └── test_context_manager.py  # CREATE/MODIFY
```

**ContextManager enhancements:**
```python
# src/adw/core/context_manager.py
import os
from pathlib import Path
from typing import TYPE_CHECKING

import filelock

from adw.exceptions import StateError

if TYPE_CHECKING:
    from adw.models import RunContext


class ContextManager:
    """Manages RunContext persistence with atomic writes.

    Ensures data durability through:
    - Atomic writes (temp file + rename)
    - fsync before rename
    - Filelock for concurrent access prevention
    """

    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir

    def save(self, context: "RunContext") -> None:
        """Save context atomically with fsync.

        Args:
            context: RunContext to persist

        Raises:
            StateError: If write fails
        """
        run_dir = self.runs_dir / context.run_id
        context_path = run_dir / "context.json"
        temp_path = run_dir / ".context.json.tmp"
        lock_path = run_dir / ".lock"

        try:
            with filelock.FileLock(lock_path, timeout=10):
                # Write to temp file with fsync
                with open(temp_path, "w") as f:
                    f.write(context.model_dump_json(indent=2))
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic rename
                temp_path.rename(context_path)

        except filelock.Timeout as e:
            raise StateError(
                code="LOCK_TIMEOUT",
                message=f"Could not acquire lock for run {context.run_id}",
                suggestion="Another process may be using this run",
                recoverable=True,
            ) from e
        except OSError as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise StateError(
                code="CONTEXT_WRITE_FAILED",
                message=f"Failed to write context: {e}",
                suggestion="Check filesystem permissions and disk space",
                recoverable=False,
            ) from e

    def load(self, run_id: str) -> "RunContext":
        """Load context with validation.

        Args:
            run_id: The run ID to load

        Returns:
            Validated RunContext instance

        Raises:
            StateError: If file missing, corrupted, or invalid
        """
        from adw.models import RunContext

        run_dir = self.runs_dir / run_id
        context_path = run_dir / "context.json"
        lock_path = run_dir / ".lock"

        if not context_path.exists():
            raise StateError(
                code="CONTEXT_NOT_FOUND",
                message=f"Context not found for run {run_id}",
                suggestion="Check if run ID is correct",
                recoverable=False,
            )

        try:
            with filelock.FileLock(lock_path, timeout=10):
                content = context_path.read_text()
                return RunContext.model_validate_json(content)

        except json.JSONDecodeError as e:
            raise StateError(
                code="CONTEXT_CORRUPTED",
                message=f"Invalid JSON in context.json: {e}",
                suggestion="Check snapshots directory for recoverable state",
                recoverable=True,
            ) from e
        except ValidationError as e:
            raise StateError(
                code="CONTEXT_CORRUPTED",
                message=f"Context validation failed: {e}",
                suggestion="Check snapshots directory for recoverable state",
                recoverable=True,
            ) from e
        except filelock.Timeout as e:
            raise StateError(
                code="LOCK_TIMEOUT",
                message=f"Could not acquire lock for run {run_id}",
                suggestion="Another process may be using this run",
                recoverable=True,
            ) from e
```

### Testing Requirements

**Test Framework:** pytest

**Test atomic write:**
```python
def test_save_uses_temp_file(context_manager, sample_context, tmp_path, mocker):
    """Test that save uses temp file pattern."""
    # Spy on rename to verify atomic pattern
    rename_spy = mocker.spy(Path, "rename")

    context_manager.save(sample_context)

    # Should have called rename (atomic)
    rename_spy.assert_called_once()


def test_save_calls_fsync(context_manager, sample_context, mocker):
    """Test that save calls fsync for durability."""
    fsync_spy = mocker.spy(os, "fsync")

    context_manager.save(sample_context)

    fsync_spy.assert_called_once()
```

**Test corruption detection:**
```python
def test_load_corrupted_json_raises_error(context_manager, tmp_path):
    """Test that corrupted JSON raises CONTEXT_CORRUPTED."""
    run_id = "01TEST"
    run_dir = tmp_path / ".adw" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "context.json").write_text("not valid json {{{")
    (run_dir / ".lock").touch()

    with pytest.raises(StateError) as exc_info:
        context_manager.load(run_id)

    assert exc_info.value.code == "CONTEXT_CORRUPTED"
    assert "snapshots" in exc_info.value.suggestion
```

**Coverage Target:** >80% overall, >90% for `context_manager.py`

---

## Previous Story Intelligence

**From Story 4.1 (Run Directory Structure):**
- Run directory structure created at `.adw/runs/<run_id>/`
- Lock file at `.lock` in run directory
- Context file at `context.json`
- RunDirectoryManager creates initial context

**Key learnings:**
- Use `filelock.FileLock` with timeout=10 for lock acquisition
- Raise `StateError` with appropriate codes
- Use `Path` for all file operations

---

## Git Intelligence

**From Epic 3:**
- Pydantic serialization patterns: `model_dump_json()`, `model_validate_json()`
- Exception patterns: raise with `code`, `message`, `suggestion`
- Test patterns: use `tmp_path`, `mocker` from pytest

**Existing files:**
- `src/adw/core/context_manager.py` - May already exist, needs enhancement
- `src/adw/models/context.py` - RunContext model
- `src/adw/exceptions.py` - StateError exception

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Context Managers**: Always use `with` for files and locks
2. **Atomic Operations**: Write to temp, fsync, then rename
3. **Error Codes**: Use descriptive codes like "CONTEXT_CORRUPTED"
4. **Suggestions**: Always include actionable suggestion in errors
5. **Type Annotations**: Full annotations on all functions

---

## Dev Notes

### Key Implementation Points

1. **Atomic Write Pattern**:
   ```python
   temp_path = context_path.with_name(".context.json.tmp")
   with open(temp_path, "w") as f:
       f.write(content)
       f.flush()
       os.fsync(f.fileno())
   temp_path.rename(context_path)  # Atomic on POSIX
   ```

2. **Lock Before Any Operation**:
   ```python
   with filelock.FileLock(lock_path, timeout=10):
       # All file operations inside lock
   ```

3. **Cleanup on Error**:
   ```python
   except OSError:
       if temp_path.exists():
           temp_path.unlink()  # Clean up temp file
       raise
   ```

4. **Validation on Load**:
   ```python
   try:
       return RunContext.model_validate_json(content)
   except json.JSONDecodeError:
       raise StateError(code="CONTEXT_CORRUPTED", ...)
   except ValidationError:
       raise StateError(code="CONTEXT_CORRUPTED", ...)
   ```

### Project Structure Notes

- Enhances existing `context_manager.py` if it exists
- Creates new file if it doesn't exist
- Follows established patterns from Epic 3

### References

- [Source: _bmad-output/architecture.md#State-Persistence]
- [Source: _bmad-output/architecture.md#Reliability]
- [Source: src/adw/exceptions.py] - StateError
- [Source: src/adw/models/context.py] - RunContext

---

## Dev Agent Record

### Context Reference

Story 4.2 implements atomic context persistence to ensure data durability and corruption prevention, addressing ASR-5 (highest risk score in architecture).

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Created `src/adw/core/context_manager.py` with ContextManager class
- Implemented atomic save with temp file + rename pattern
- Implemented fsync for data durability (NFR6 compliance)
- Implemented load with Pydantic validation
- Added corruption detection with StateError(code="CONTEXT_CORRUPTED")
- Added lock integration with filelock.FileLock
- Created comprehensive unit tests (13 tests)
- Added durability tests (6 tests) to verify atomic write guarantees
- All 19 tests pass, 505 total tests in suite pass

### File List

- `src/adw/core/context_manager.py` (created)
- `tests/unit/core/test_context_manager.py` (created)

---

## Dependencies

- **Depends On:** Story 4.1 (needs run directory structure)
- **Blocks:** Story 4.3, Story 4.5 (snapshots and recovery need context manager)
- **Can Parallel With:** Story 4.4 (artifact storage)

### Dependency Rationale
- Story 4.1: Context manager needs the run directory to exist before saving
- Story 4.3: Snapshots build on context manager's save functionality
- Story 4.4: Artifact storage is independent but uses similar patterns
- Story 4.5: Recovery needs both context manager and snapshots

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-01 | BMAD Create-Story | Initial story creation with comprehensive context |
| 2026-01-02 | Dev Agent | Implemented Tasks 1-7: ContextManager with atomic writes, unit tests |
| 2026-01-02 | Dev Agent | Added Task 8: Durability tests for atomic write guarantees |
