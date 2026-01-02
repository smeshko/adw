# Story 4.1: Create Run Directory Structure

Status: completed
Linear Issue: not-configured
Epic: 4 - State Persistence & Context Management
Created: 2026-01-01

---

## Story

As a developer,
I want a consistent directory structure for each run,
so that all run data is organized and discoverable.

## Acceptance Criteria

**Given** a new run is started
**When** the run ID is generated (ULID format)
**Then** directory `.adw/runs/<run_id>/` is created with subdirectories:
  - `artifacts/` (for phase outputs)
  - `logs/` (for logging)
  - `llm/` (for LLM capture)
  - `snapshots/` (for state snapshots)

**Given** the run directory
**When** `context.json` is created
**Then** it contains the serialized RunContext model

**Given** file operations on the run directory
**When** concurrent access is attempted
**Then** filelock prevents corruption (ARCH-7)

**Given** I list `.adw/runs/`
**When** runs exist
**Then** they are sorted by ULID (chronological order)

## Tasks / Subtasks

### Task 1: Create Run Directory Module
- [x] Create `src/adw/core/run_directory.py` module
- [x] Implement `RunDirectoryManager` class with `create()` method
- [x] Use ULID for run ID generation via `python-ulid`
- [x] Create subdirectory structure atomically

### Task 2: Implement ULID Generation
- [x] Add `src/adw/utils/ulid.py` for ULID generation
- [x] Wrap `python-ulid` library
- [x] Ensure run IDs are lexicographically sortable
- [x] Add helper function `generate_run_id() -> str`

### Task 3: Implement Directory Structure Creation
- [x] Create `.adw/runs/<run_id>/` directory
- [x] Create `artifacts/` subdirectory
- [x] Create `logs/` subdirectory
- [x] Create `llm/` subdirectory
- [x] Create `snapshots/` subdirectory
- [x] Handle existing directory errors gracefully

### Task 4: Implement File Locking
- [x] Add `filelock` dependency (already in project)
- [x] Create `.lock` file in run directory
- [x] Implement context manager for acquiring lock
- [x] Prevent concurrent access corruption

### Task 5: Implement Context Serialization
- [x] Create `context.json` with serialized RunContext
- [x] Use Pydantic's `model_dump_json()` for serialization
- [x] Include all required RunContext fields
- [x] Handle serialization errors

### Task 6: Implement Run Listing
- [x] Add `list_runs()` method to RunDirectoryManager
- [x] Return runs sorted by ULID (chronological)
- [x] Handle empty `.adw/runs/` directory
- [x] Return list of `RunInfo` with id, path, created_at

### Task 7: Write Unit Tests
- [x] Create `tests/unit/core/test_run_directory.py`
- [x] Test directory creation with all subdirectories
- [x] Test ULID generation and sorting
- [x] Test file locking behavior
- [x] Test context.json creation and validation
- [x] Test run listing and sorting
- [x] Target: >90% coverage for new code (achieved: run_directory.py 96%, ulid.py 100%)

### Task 8: Write Integration Tests
- [x] Test full directory creation workflow
- [x] Test concurrent access with multiple processes
- [x] Test cleanup and recovery scenarios
- [x] Verify file permissions

---

## Developer Context

### Technical Requirements

- **ULID Generation**: Use `python-ulid` library for generating sortable unique IDs
- **Directory Creation**: Create atomic directory structure with all required subdirectories
- **File Locking**: Use `filelock` library for preventing concurrent access corruption
- **Context Serialization**: Use Pydantic's `model_dump_json()` for type-safe serialization
- **Error Handling**: Raise `StateError` with appropriate codes for failures

### Architecture Compliance

**From architecture.md - State Persistence Decision:**
```
File Locations:
.adw/runs/<run_id>/
├── context.json          # RunContext - live updated
├── snapshots/
│   └── <seq>_<label>.json  # StateSnapshot at key moments
└── artifacts/
    └── <phase>/
        └── <artifact>.json
```

**From architecture.md - Run Identification Decision:**
```
Decision: ULID via python-ulid

Run IDs are ULIDs (Universally Unique Lexicographically Sortable Identifiers).

Example: 01HQXK5P3Z7V8R2M4N6T9W1Y3C

Rationale:
- Sortable by creation time (unlike UUIDs)
- Timestamp embedded (debuggable)
- URL-safe, filesystem-safe
- No collisions in practice
```

**From architecture.md - Concurrency Control Decision:**
```
Decision: filelock per-run

Each run acquires .adw/runs/<run_id>/.lock before modification.

Rationale: Prevents corruption if user accidentally runs adw resume twice on same run.
```

**From architecture.md - Exception Hierarchy:**
```python
class StateError(ADWError):
    """State persistence/loading failures"""
    pass
```

### Library & Framework Requirements

**python-ulid:**
```python
from ulid import ULID

def generate_run_id() -> str:
    """Generate a new run ID in ULID format."""
    return str(ULID())
```

**filelock:**
```python
import filelock

# CORRECT - context manager pattern
with filelock.FileLock(lock_path, timeout=10):
    # Perform file operations
    pass
```

**Pydantic serialization:**
```python
# Serialize context to JSON file
context.model_dump_json()

# Load context from JSON file
RunContext.model_validate_json(json_string)
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── core/
│   └── run_directory.py    # NEW - RunDirectoryManager class
├── utils/
│   └── ulid.py             # NEW - ULID generation wrapper
tests/
├── unit/
│   └── core/
│       └── test_run_directory.py  # NEW
└── integration/
    └── test_run_directory.py      # NEW (optional)
```

**RunDirectoryManager class:**
```python
# src/adw/core/run_directory.py
from pathlib import Path
from typing import TYPE_CHECKING

import filelock

from adw.exceptions import StateError
from adw.utils.ulid import generate_run_id

if TYPE_CHECKING:
    from adw.models import RunContext


class RunDirectoryManager:
    """Manages run directory structure and lifecycle.

    Creates and manages the directory structure for ADW runs:
    .adw/runs/<run_id>/
    ├── context.json
    ├── .lock
    ├── artifacts/
    ├── logs/
    ├── llm/
    └── snapshots/
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.runs_dir = project_root / ".adw" / "runs"

    def create(self, context: "RunContext") -> Path:
        """Create run directory structure and save initial context.

        Args:
            context: Initial RunContext to serialize

        Returns:
            Path to created run directory

        Raises:
            StateError: If directory creation fails
        """
        run_id = context.run_id
        run_dir = self.runs_dir / run_id

        try:
            # Create directory structure
            run_dir.mkdir(parents=True, exist_ok=False)
            (run_dir / "artifacts").mkdir()
            (run_dir / "logs").mkdir()
            (run_dir / "llm").mkdir()
            (run_dir / "snapshots").mkdir()

            # Acquire lock and write context
            lock_path = run_dir / ".lock"
            with filelock.FileLock(lock_path, timeout=10):
                context_path = run_dir / "context.json"
                context_path.write_text(context.model_dump_json(indent=2))

            return run_dir

        except FileExistsError as e:
            raise StateError(
                code="RUN_ALREADY_EXISTS",
                message=f"Run directory already exists: {run_id}",
                suggestion="Use a different run ID or delete existing run",
                recoverable=False,
            ) from e
        except OSError as e:
            raise StateError(
                code="DIR_CREATION_FAILED",
                message=f"Failed to create run directory: {e}",
                suggestion="Check filesystem permissions",
                recoverable=False,
            ) from e

    def list_runs(self) -> list["RunInfo"]:
        """List all runs sorted by ULID (chronological order).

        Returns:
            List of RunInfo objects sorted by creation time
        """
        if not self.runs_dir.exists():
            return []

        runs = []
        for run_path in self.runs_dir.iterdir():
            if run_path.is_dir() and not run_path.name.startswith("."):
                runs.append(RunInfo(
                    run_id=run_path.name,
                    path=run_path,
                ))

        # ULID sorting is lexicographic = chronological
        return sorted(runs, key=lambda r: r.run_id)

    def acquire_lock(self, run_id: str, timeout: int = 10) -> filelock.FileLock:
        """Acquire lock for a run directory.

        Args:
            run_id: The run ID to lock
            timeout: Lock acquisition timeout in seconds

        Returns:
            FileLock context manager

        Raises:
            StateError: If lock acquisition fails
        """
        lock_path = self.runs_dir / run_id / ".lock"
        try:
            lock = filelock.FileLock(lock_path, timeout=timeout)
            return lock
        except filelock.Timeout as e:
            raise StateError(
                code="LOCK_TIMEOUT",
                message=f"Could not acquire lock for run {run_id}",
                suggestion="Another process may be using this run. Wait or kill it.",
                recoverable=True,
            ) from e


class RunInfo(BaseModel):
    """Information about a run directory."""

    run_id: str
    path: Path

    class Config:
        arbitrary_types_allowed = True
```

### Testing Requirements

**Test Framework:** pytest

**Unit test structure:**
```python
# tests/unit/core/test_run_directory.py
import pytest
from pathlib import Path
from adw.core.run_directory import RunDirectoryManager
from adw.models import RunContext


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def run_manager(temp_project):
    """Create a RunDirectoryManager for testing."""
    return RunDirectoryManager(temp_project)


@pytest.fixture
def sample_context():
    """Create a sample RunContext for testing."""
    from adw.utils.ulid import generate_run_id
    return RunContext(
        run_id=generate_run_id(),
        feature_request="Test feature",
        current_phase="plan",
        completed_phases=[],
    )


class TestRunDirectoryManager:
    def test_create_directory_structure(self, run_manager, sample_context):
        """Test that all required subdirectories are created."""
        run_dir = run_manager.create(sample_context)

        assert run_dir.exists()
        assert (run_dir / "artifacts").exists()
        assert (run_dir / "logs").exists()
        assert (run_dir / "llm").exists()
        assert (run_dir / "snapshots").exists()

    def test_context_json_created(self, run_manager, sample_context):
        """Test that context.json is created with valid content."""
        run_dir = run_manager.create(sample_context)
        context_path = run_dir / "context.json"

        assert context_path.exists()

        # Validate content can be loaded
        loaded = RunContext.model_validate_json(context_path.read_text())
        assert loaded.run_id == sample_context.run_id

    def test_lock_file_created(self, run_manager, sample_context):
        """Test that .lock file is created."""
        run_dir = run_manager.create(sample_context)
        assert (run_dir / ".lock").exists()

    def test_duplicate_run_raises_error(self, run_manager, sample_context):
        """Test that creating duplicate run raises StateError."""
        from adw.exceptions import StateError

        run_manager.create(sample_context)

        with pytest.raises(StateError) as exc_info:
            run_manager.create(sample_context)

        assert exc_info.value.code == "RUN_ALREADY_EXISTS"

    def test_list_runs_empty(self, run_manager):
        """Test listing runs when none exist."""
        runs = run_manager.list_runs()
        assert runs == []

    def test_list_runs_sorted_by_ulid(self, run_manager, sample_context):
        """Test that runs are sorted chronologically by ULID."""
        import time

        # Create multiple runs
        contexts = []
        for _ in range(3):
            from adw.utils.ulid import generate_run_id
            ctx = RunContext(
                run_id=generate_run_id(),
                feature_request="Test",
                current_phase="plan",
                completed_phases=[],
            )
            contexts.append(ctx)
            run_manager.create(ctx)
            time.sleep(0.01)  # Small delay to ensure different ULIDs

        runs = run_manager.list_runs()

        # Should be sorted chronologically
        assert [r.run_id for r in runs] == [c.run_id for c in contexts]
```

**Coverage Target:** >80% overall, >90% for `run_directory.py`

---

## Previous Story Intelligence

**From Epic 3 (Story 3.5 - Token Tracking):**
- RunContext model already exists at `src/adw/models/context.py`
- Pydantic serialization patterns established (`model_dump_json()`, `model_validate_json()`)
- Test fixtures use `tmp_path` for temporary directories
- Coverage target: >80% overall

**From Epic 1 (Story 1-2 - Core Models):**
- RunContext includes `run_id`, `feature_request`, `current_phase`, `completed_phases`
- All models use Pydantic v2 with `Field()` for defaults

**Relevant patterns:**
- Use `Path` from `pathlib` for all file operations
- Use context managers for file locking
- Raise typed exceptions with `code`, `message`, `suggestion` fields

---

## Git Intelligence

**Recent commits (Epic 3):**
- Token tracking implemented with structured logging
- PhaseResult enhanced with `tokens_used` and `tool_calls`
- RunContext has `phase_tokens` dict for aggregation

**Existing project structure:**
```
src/adw/
├── core/
│   ├── __init__.py
│   └── context_manager.py  # May need enhancement
├── models/
│   ├── context.py          # RunContext model
│   └── ...
├── exceptions.py           # StateError exists
└── utils/
    ├── __init__.py
    └── files.py            # File operation helpers
```

**Key files to reference:**
- `src/adw/models/context.py` - RunContext model definition
- `src/adw/exceptions.py` - StateError exception
- `src/adw/utils/files.py` - Existing file utilities

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **Type Annotations Required**: All public functions must have full type annotations
2. **Context Managers for Resources**: Always use `with` for file operations and locks
3. **Exception Hierarchy**: Never raise bare `Exception`, use `StateError` for state failures
4. **Pydantic Models**: Use `model_dump_json()` and `model_validate_json()` for serialization
5. **Structured Logging**: Log operations with context fields (e.g., `run_id=run_id`)

---

## Dev Notes

### Key Implementation Points

1. **ULID Generation** - Simple wrapper around python-ulid:
   ```python
   # src/adw/utils/ulid.py
   from ulid import ULID

   def generate_run_id() -> str:
       """Generate a new run ID in ULID format."""
       return str(ULID())
   ```

2. **Atomic Directory Creation** - Create structure in order:
   ```python
   run_dir.mkdir(parents=True, exist_ok=False)  # Fail if exists
   for subdir in ["artifacts", "logs", "llm", "snapshots"]:
       (run_dir / subdir).mkdir()
   ```

3. **Lock Before Write** - Always acquire lock before writing:
   ```python
   with filelock.FileLock(run_dir / ".lock", timeout=10):
       (run_dir / "context.json").write_text(context.model_dump_json())
   ```

4. **Error Handling** - Map exceptions to StateError:
   ```python
   except FileExistsError:
       raise StateError(code="RUN_ALREADY_EXISTS", ...)
   except OSError:
       raise StateError(code="DIR_CREATION_FAILED", ...)
   ```

### Project Structure Notes

- Alignment with unified project structure: ✓
- New files follow existing naming conventions
- ULID utility in `utils/` matches pattern for `files.py`, `yaml.py`
- RunDirectoryManager in `core/` alongside `context_manager.py`

### References

- [Source: _bmad-output/architecture.md#State-Persistence] - File structure decision
- [Source: _bmad-output/architecture.md#Run-Identification] - ULID decision
- [Source: _bmad-output/architecture.md#Concurrency-Control] - Filelock decision
- [Source: src/adw/models/context.py] - RunContext model
- [Source: src/adw/exceptions.py] - StateError exception

---

## Dev Agent Record

### Context Reference

Story 4.1 establishes the foundational run directory structure for all state persistence in ADW SDK. This is the first story in Epic 4 and blocks all other stories in the epic.

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Task 1: Created `src/adw/core/run_directory.py` with `RunDirectoryManager` class. Implemented class structure with `project_root` and `runs_dir` attributes. Added `create()` method placeholder (to be completed in Task 3). Added unit tests for module existence and basic instantiation.
- Task 2: Created `src/adw/utils/ulid.py` with `generate_run_id()` function. Wrapped python-ulid library. Added comprehensive tests for uniqueness, character validation, sortability, and RunContext validation compatibility.
- Task 3: Implemented full `create()` method in `RunDirectoryManager`. Creates `.adw/runs/<run_id>/` with all subdirectories (artifacts, logs, llm, snapshots). Raises `StateError` with code `RUN_ALREADY_EXISTS` for duplicate runs. Added comprehensive tests for directory creation.
- Task 4: Implemented file locking using filelock library. Creates `.lock` file during directory creation. Added `acquire_lock()` method that returns FileLock context manager. Raises `StateError` with code `RUN_NOT_FOUND` for nonexistent runs.
- Task 5: Implemented context serialization. Creates `context.json` with serialized RunContext using Pydantic's `model_dump_json(indent=2)` for human-readable output. Added tests for JSON creation, validation, and deserialization.
- Task 6: Implemented `list_runs()` method that returns list of `RunInfo` objects sorted by ULID (chronological order). Added `RunInfo` dataclass. Handles empty directory and ignores hidden directories.
- Task 7: Unit tests already written as part of TDD process during Tasks 1-6. Coverage: run_directory.py 96%, ulid.py 100%. 27 unit tests total covering all functionality.
- Task 8: Created integration tests in `tests/integration/core/test_run_directory_integration.py`. 8 tests covering full workflow, multiprocess locking, persistence across restarts, edge cases (unicode, special paths, deep nesting).

### File List

- `src/adw/core/run_directory.py` - NEW: Run directory management module
- `src/adw/utils/ulid.py` - NEW: ULID generation utility
- `tests/unit/core/__init__.py` - NEW: Test package init
- `tests/unit/core/test_run_directory.py` - NEW: Unit tests for run directory
- `tests/unit/utils/__init__.py` - NEW: Utils test package init
- `tests/unit/utils/test_ulid.py` - NEW: Unit tests for ULID generation
- `tests/integration/core/__init__.py` - NEW: Integration test package init
- `tests/integration/core/test_run_directory_integration.py` - NEW: Integration tests

---

## Dependencies

- **Depends On:** None (foundational story)
- **Blocks:** Story 4.2, 4.3, 4.4, 4.5 (all need directory structure)
- **Can Parallel With:** None

### Dependency Rationale
- This is the foundational story for Epic 4
- All other stories in Epic 4 require the run directory structure to exist
- Must complete first before any other Epic 4 work can begin

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-01 | BMAD Create-Story | Initial story creation with comprehensive context |
