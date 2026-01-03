# Story 7.0: Workflow Execution Index

Status: ready-for-dev
Linear Issue: pending
Epic: 7 - Observability & Logging
Created: 2026-01-03
Priority: MVP (pulled forward from post-MVP via Course Correction 2026-01-03)

---

## Story

As a developer,
I want a central index of all workflow runs,
so that I can quickly find and reference past executions across all projects.

## Acceptance Criteria

**Given** a new run starts
**When** the orchestrator initializes
**Then** an entry is added to `~/.adw/index.jsonl` with: run_id, project_path, feature_description, started_at, status

**Given** a run completes or fails
**When** the status changes
**Then** the index entry is updated with: completed_at, final_status, phase_reached

**Given** command `adw list`
**When** executed without project context (outside any ADW project)
**Then** shows recent runs from the global index (across all projects)

**Given** command `adw list --project`
**When** executed in a project directory
**Then** filters to runs from current project only

**Given** the index file
**When** it grows large (>10,000 entries)
**Then** older entries are archived to `~/.adw/index-archive/YYYY-MM.jsonl`

## Tasks / Subtasks

### Task 1: Create IndexEntry Model
- [ ] Create `src/adw/models/index.py`
- [ ] Define `IndexEntry` Pydantic model with all required fields
- [ ] Add JSON serialization support
- [ ] Export from `src/adw/models/__init__.py`

### Task 2: Implement IndexManager
- [ ] Create `src/adw/core/index_manager.py`
- [ ] Implement `register_run()` - append new entry on run start
- [ ] Implement `update_run()` - update existing entry on status change
- [ ] Implement `get_recent_runs()` - query with filters
- [ ] Implement `_archive_old_entries()` - archive when >10,000 entries
- [ ] Handle concurrent access safely (JSONL is append-only)

### Task 3: Integrate with Orchestrator
- [ ] Modify `src/adw/core/orchestrator.py`
- [ ] Call `index_manager.register_run()` on run initialization
- [ ] Call `index_manager.update_run()` on phase transitions
- [ ] Call `index_manager.update_run()` on run completion/failure

### Task 4: Update CLI List Command
- [ ] Modify `src/adw/cli/list.py`
- [ ] Detect when outside project context
- [ ] Use global index when outside project
- [ ] Add `--project` flag to filter to current project
- [ ] Add `--global` flag to force global view even inside project

### Task 5: Write Unit Tests
- [ ] `tests/unit/models/test_index.py` - IndexEntry model tests
- [ ] `tests/unit/core/test_index_manager.py` - IndexManager tests
- [ ] Update `tests/unit/core/test_orchestrator.py` - index integration
- [ ] Update `tests/unit/cli/test_list.py` - global list tests

---

## Developer Context

### Technical Requirements

| Requirement | Specification |
|-------------|---------------|
| Index Location | `~/.adw/index.jsonl` (user home directory) |
| Index Format | JSONL (JSON Lines) - one JSON object per line |
| Archive Location | `~/.adw/index-archive/YYYY-MM.jsonl` |
| Archive Threshold | 10,000 entries |
| Concurrency Model | Append-only writes (no locking needed for basic ops) |
| Read Consistency | Read full file, parse all lines |

### Architecture Compliance

**MUST Follow:**
1. **Model Location:** `IndexEntry` model MUST be in `src/adw/models/index.py`
2. **Naming:** All snake_case for functions/variables, PascalCase for classes
3. **Type Annotations:** Full type hints on all public functions
4. **Exception Hierarchy:** Use `StateError` for index operation failures
5. **Rich Output:** Use Rich for any CLI output related to index display
6. **Immutable Updates:** When updating index entries, create new entry objects

**Existing Patterns to Follow:**
- `RunContext` model in `src/adw/models/context.py` - similar Pydantic pattern
- `context_manager.py` - similar file I/O patterns
- `run_lookup.py` - similar query patterns

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | IndexEntry model definition |
| pathlib | stdlib | Path handling for `~/.adw/` |
| json | stdlib | JSONL serialization |
| datetime | stdlib | Timestamps (UTC) |
| filelock | latest | Optional - for archive operations only |

**JSONL Pattern:**
```python
# CORRECT - JSONL append
def append_entry(path: Path, entry: IndexEntry) -> None:
    with open(path, "a") as f:
        f.write(entry.model_dump_json() + "\n")

# CORRECT - JSONL read all
def read_entries(path: Path) -> list[IndexEntry]:
    entries = []
    with open(path, "r") as f:
        for line in f:
            if line.strip():
                entries.append(IndexEntry.model_validate_json(line))
    return entries
```

### File Structure Requirements

**New Files to Create:**

```
src/adw/
├── models/
│   └── index.py              # NEW - IndexEntry model
├── core/
│   └── index_manager.py      # NEW - Index operations
tests/unit/
├── models/
│   └── test_index.py         # NEW - Model tests
├── core/
│   └── test_index_manager.py # NEW - Manager tests
```

**Files to Modify:**

```
src/adw/
├── models/
│   └── __init__.py           # MODIFY - export IndexEntry
├── core/
│   └── orchestrator.py       # MODIFY - integrate index
├── cli/
│   └── list.py               # MODIFY - global list support
tests/unit/
├── core/
│   └── test_orchestrator.py  # MODIFY - add index tests
├── cli/
│   └── test_list.py          # MODIFY - add global tests
```

### Testing Requirements

**Unit Tests Required:**

1. **IndexEntry Model Tests:**
   - Serialization/deserialization round-trip
   - Field validation (run_id format, timestamps)
   - Optional fields handling

2. **IndexManager Tests:**
   - `register_run()` - creates file if not exists, appends entry
   - `update_run()` - finds and updates entry by run_id
   - `get_recent_runs()` - returns correct entries with filters
   - `_archive_old_entries()` - moves old entries to archive
   - Edge cases: empty file, corrupted lines, missing file

3. **Integration Tests:**
   - Orchestrator creates index entry on run start
   - Orchestrator updates index on completion
   - CLI list shows global runs when outside project

**Test Patterns:**
```python
# Use tmp_path fixture for isolated testing
def test_register_run(tmp_path: Path) -> None:
    # Override index path to tmp_path
    manager = IndexManager(index_path=tmp_path / "index.jsonl")
    ...

# Use MockExecutor for orchestrator tests
def test_orchestrator_registers_run(mock_executor: MockExecutor) -> None:
    ...
```

---

## Previous Story Intelligence

**Recent Epic 7 Work (Stories 7.2, 7.3, 7.5, 7.6):**
- Logging infrastructure is being built out in parallel
- `src/adw/logging/` module structure established
- State snapshots already capture run state at phase boundaries
- Secret redaction patterns established in Story 7.6

**Patterns Established:**
- JSONL format used for structured logs (`logs/structured.jsonl`)
- Timestamp format: ISO 8601 with UTC timezone
- Run identification: 26-character ULID

---

## Git Intelligence

**Recent Commits:**
```
d05c093 docs(story-7-3): mark story complete
fa520d4 feat(story-7-5): Implement State Inspection Commands
0916446 chore(story-7-6): mark secret redaction story complete
b5ff558 feat(story-7-2): Configure Verbosity Levels
```

**Relevant Files from Recent Work:**
- `src/adw/logging/` - logging infrastructure
- `src/adw/core/snapshot_manager.py` - state snapshots
- `src/adw/cli/status.py` - CLI patterns for state display

---

## Latest Technical Information

**JSONL Best Practices (2025):**
- JSONL is ideal for append-only logging scenarios
- No parsing overhead - each line is independent
- Natural for streaming reads/writes
- `json.loads()` per line vs full file parse

**Python Path Expansion:**
```python
from pathlib import Path

# CORRECT - expand ~ to user home
index_path = Path.home() / ".adw" / "index.jsonl"

# WRONG - ~ won't expand
index_path = Path("~/.adw/index.jsonl")  # NO
```

**Pydantic 2.x Patterns:**
```python
# JSON serialization
entry.model_dump_json()  # Returns JSON string

# JSON deserialization
IndexEntry.model_validate_json(json_string)

# Dict conversion
entry.model_dump()
IndexEntry.model_validate(dict_data)
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **All models in `src/adw/models/`** - IndexEntry MUST go there
2. **Full type annotations** - Every function needs return types
3. **Rich for CLI output** - Any index display uses Rich tables/panels
4. **Exception hierarchy** - Use `StateError` for index failures
5. **Immutable state updates** - Use `model_copy()` pattern
6. **Test coverage >80%** - Full unit test coverage required

---

## Implementation Guide

### IndexEntry Model Schema

```python
# src/adw/models/index.py
from datetime import datetime
from pydantic import BaseModel, Field

class IndexEntry(BaseModel):
    """Entry in the global workflow execution index."""

    run_id: str = Field(..., description="ULID run identifier")
    project_path: str = Field(..., description="Absolute path to project")
    project_name: str = Field(..., description="Project directory name")
    feature_description: str = Field(..., description="Feature being developed")
    started_at: datetime = Field(..., description="Run start timestamp (UTC)")
    completed_at: datetime | None = Field(default=None)
    status: str = Field(..., description="running|completed|failed|interrupted|aborted")
    phase_reached: str | None = Field(default=None, description="Last phase executed")
    phases_completed: list[str] = Field(default_factory=list)

    model_config = {"frozen": False, "validate_assignment": True}
```

### IndexManager Interface

```python
# src/adw/core/index_manager.py
class IndexManager:
    """Manages the global workflow execution index."""

    def __init__(self, index_path: Path | None = None) -> None:
        self.index_path = index_path or (Path.home() / ".adw" / "index.jsonl")
        self.archive_dir = self.index_path.parent / "index-archive"

    def register_run(self, context: RunContext, project_path: Path) -> None:
        """Add new run to index on orchestrator start."""
        ...

    def update_run(self, run_id: str, **updates: Any) -> None:
        """Update existing run entry (status, phase_reached, etc.)."""
        ...

    def get_recent_runs(
        self,
        limit: int = 10,
        project_path: Path | None = None,
        status: str | None = None,
    ) -> list[IndexEntry]:
        """Query recent runs with optional filters."""
        ...

    def _archive_old_entries(self) -> None:
        """Archive entries when index exceeds threshold."""
        ...
```

### CLI Integration

```python
# Update src/adw/cli/list.py
@app.command()
def list_runs(
    limit: int = 10,
    status: str | None = None,
    project: bool = False,  # Filter to current project
    global_: bool = typer.Option(False, "--global"),  # Force global view
    json_output: bool = False,
) -> None:
    """List recent ADW runs."""
    ...
```

---

## Dev Notes

- This story has **no dependencies** on other Epic 7 stories
- Can be implemented independently and in parallel with 7.1-7.6
- Index is separate from per-run logs in `.adw/runs/<id>/`
- Foundation for Epic 10 (Cross-Project Dashboard)
- Archive logic can be simple: move all entries older than newest 5000

### Project Structure Notes

- Alignment: New files follow established module structure
- No conflicts with existing logging infrastructure
- IndexManager is separate concern from LogManager

### References

- [Source: _bmad-output/epics/epic-7-observability-logging.md#Story 7.0]
- [Source: _bmad-output/architecture.md#Project Structure]
- [Source: src/adw/models/context.py - RunContext pattern]
- [Source: src/adw/core/context_manager.py - file I/O patterns]

---

## Dev Agent Record

### Context Reference

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

