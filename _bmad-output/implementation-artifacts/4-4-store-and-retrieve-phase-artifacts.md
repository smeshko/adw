# Story 4.4: Store and Retrieve Phase Artifacts

Status: ready-for-dev
Linear Issue: not-configured
Epic: 4 - State Persistence & Context Management
Created: 2026-01-01

---

## Story

As a developer,
I want phase artifacts stored in a predictable location,
so that subsequent phases can access outputs from previous phases.

## Acceptance Criteria

**Given** the build phase produces a git diff
**When** the phase completes
**Then** the diff is stored in `artifacts/build/diff.txt`

**Given** a phase produces multiple artifacts
**When** storage completes
**Then** all artifacts are in `artifacts/<phase>/` directory

**Given** artifact storage
**When** I call `context_manager.get_artifact(phase, name)`
**Then** the artifact content is returned

**Given** a non-existent artifact requested
**When** get_artifact is called
**Then** None is returned (not an error)

**Given** artifacts from all phases
**When** the run context is serialized
**Then** it includes artifact paths (not content) for reference

## Tasks / Subtasks

### Task 1: Create ArtifactManager Class
- [x] Create `src/adw/core/artifact_manager.py`
- [x] Implement `store(phase, name, content)` method
- [x] Implement `get(phase, name)` method
- [x] Implement `list_artifacts(phase)` method
- [x] Use atomic write pattern

### Task 2: Implement Artifact Storage
- [x] Create phase directory if not exists: `artifacts/<phase>/`
- [x] Write artifact content to file
- [x] Support both text and binary content
- [x] Use atomic write for text files

### Task 3: Implement Artifact Retrieval
- [x] Load artifact by phase and name
- [x] Return content or None if not exists
- [x] Handle text vs binary appropriately
- [x] Support reading partial content (head/tail)

### Task 4: Implement Artifact Listing
- [x] List all artifacts for a phase
- [x] List all artifacts across all phases
- [x] Include metadata (size, modified time)
- [x] Return sorted list

### Task 5: Track Artifact Paths in Context
- [ ] Add `artifact_paths: dict[str, list[str]]` to RunContext
- [ ] Update after each artifact stored
- [ ] Serialize paths (not content) in context.json
- [ ] Enable cross-phase artifact discovery

### Task 6: Implement Common Artifact Types
- [ ] `store_json(phase, name, data)` - JSON serialized
- [ ] `store_text(phase, name, text)` - Plain text
- [ ] `get_json(phase, name)` - Parse JSON
- [ ] Auto-detect content type on retrieval

### Task 7: Write Unit Tests
- [ ] Create `tests/unit/core/test_artifact_manager.py`
- [ ] Test artifact storage and retrieval
- [ ] Test non-existent artifact returns None
- [ ] Test artifact listing
- [ ] Test JSON artifact convenience methods
- [ ] Test path tracking in context
- [ ] Target: >90% coverage

### Task 8: Write Integration Tests
- [ ] Test full phase lifecycle with artifacts
- [ ] Test artifact access from subsequent phase
- [ ] Test artifact persistence across runs
- [ ] Verify artifact content integrity

---

## Developer Context

### Technical Requirements

- **Artifact Location**: `artifacts/<phase>/<name>`
- **Atomic Writes**: Use temp file + rename pattern
- **Content Types**: Support text and binary
- **Path Tracking**: Store paths (not content) in context
- **Graceful Missing**: Return None for non-existent artifacts

### Architecture Compliance

**From architecture.md - State Persistence:**
```
.adw/runs/<run_id>/
├── context.json
├── snapshots/
└── artifacts/
    └── <phase>/
        └── <artifact>.json
```

**From architecture.md - Phase Execution Requirements:**
```
FR10: System captures artifacts at the end of each phase
FR11: System makes previous phase artifacts available to subsequent phases
```

**From architecture.md - Context Structure:**
```python
class RunContext(BaseModel):
    # ... other fields ...
    artifact_paths: dict[str, list[str]] = Field(default_factory=dict)
    """Map of phase -> list of artifact paths."""
```

### Library & Framework Requirements

**Path handling:**
```python
from pathlib import Path

artifacts_dir = self.runs_dir / run_id / "artifacts" / phase
artifacts_dir.mkdir(parents=True, exist_ok=True)
artifact_path = artifacts_dir / name
```

**Atomic write (same pattern):**
```python
import os

temp_path = artifact_path.with_suffix(".tmp")
with open(temp_path, "w") as f:
    f.write(content)
    f.flush()
    os.fsync(f.fileno())
temp_path.rename(artifact_path)
```

**JSON handling:**
```python
import json

# Store JSON
def store_json(self, phase: str, name: str, data: Any) -> Path:
    content = json.dumps(data, indent=2)
    return self.store(phase, name, content)

# Get JSON
def get_json(self, phase: str, name: str) -> Any | None:
    content = self.get(phase, name)
    if content is None:
        return None
    return json.loads(content)
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── core/
│   └── artifact_manager.py   # NEW
├── models/
│   └── context.py            # MODIFY - add artifact_paths
tests/
├── unit/
│   └── core/
│       └── test_artifact_manager.py  # NEW
```

**ArtifactManager Class:**
```python
# src/adw/core/artifact_manager.py
import json
import os
from pathlib import Path
from typing import Any

from adw.exceptions import StateError


class ArtifactManager:
    """Manages phase artifacts storage and retrieval.

    Artifacts are stored at:
    .adw/runs/<run_id>/artifacts/<phase>/<name>

    Example:
    - artifacts/build/diff.txt
    - artifacts/verify/evidence.json
    """

    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir

    def store(
        self,
        run_id: str,
        phase: str,
        name: str,
        content: str | bytes,
    ) -> Path:
        """Store an artifact.

        Args:
            run_id: The run ID
            phase: Phase that produced the artifact
            name: Artifact filename
            content: Artifact content (text or binary)

        Returns:
            Path to stored artifact

        Raises:
            StateError: If write fails
        """
        artifacts_dir = self.runs_dir / run_id / "artifacts" / phase
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = artifacts_dir / name
        temp_path = artifact_path.with_suffix(artifact_path.suffix + ".tmp")

        try:
            mode = "w" if isinstance(content, str) else "wb"
            with open(temp_path, mode) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            temp_path.rename(artifact_path)
            return artifact_path

        except OSError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise StateError(
                code="ARTIFACT_WRITE_FAILED",
                message=f"Failed to write artifact {phase}/{name}: {e}",
                suggestion="Check filesystem permissions and disk space",
                recoverable=False,
            ) from e

    def get(
        self,
        run_id: str,
        phase: str,
        name: str,
        *,
        binary: bool = False,
    ) -> str | bytes | None:
        """Retrieve an artifact.

        Args:
            run_id: The run ID
            phase: Phase that produced the artifact
            name: Artifact filename
            binary: If True, read as binary

        Returns:
            Artifact content or None if not found
        """
        artifact_path = self.runs_dir / run_id / "artifacts" / phase / name

        if not artifact_path.exists():
            return None

        try:
            if binary:
                return artifact_path.read_bytes()
            return artifact_path.read_text()
        except OSError:
            return None

    def store_json(
        self,
        run_id: str,
        phase: str,
        name: str,
        data: Any,
    ) -> Path:
        """Store JSON artifact with automatic serialization.

        Args:
            run_id: The run ID
            phase: Phase that produced the artifact
            name: Artifact filename (should end in .json)
            data: JSON-serializable data

        Returns:
            Path to stored artifact
        """
        content = json.dumps(data, indent=2, default=str)
        return self.store(run_id, phase, name, content)

    def get_json(
        self,
        run_id: str,
        phase: str,
        name: str,
    ) -> Any | None:
        """Retrieve and parse JSON artifact.

        Args:
            run_id: The run ID
            phase: Phase that produced the artifact
            name: Artifact filename

        Returns:
            Parsed JSON data or None if not found
        """
        content = self.get(run_id, phase, name)
        if content is None:
            return None

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def list_artifacts(
        self,
        run_id: str,
        phase: str | None = None,
    ) -> list[dict]:
        """List artifacts for a run.

        Args:
            run_id: The run ID
            phase: Optional phase filter

        Returns:
            List of artifact metadata
        """
        artifacts_dir = self.runs_dir / run_id / "artifacts"
        if not artifacts_dir.exists():
            return []

        results = []

        if phase:
            phase_dirs = [artifacts_dir / phase]
        else:
            phase_dirs = [d for d in artifacts_dir.iterdir() if d.is_dir()]

        for phase_dir in phase_dirs:
            if not phase_dir.exists():
                continue
            phase_name = phase_dir.name
            for artifact_path in sorted(phase_dir.iterdir()):
                if artifact_path.is_file():
                    stat = artifact_path.stat()
                    results.append({
                        "phase": phase_name,
                        "name": artifact_path.name,
                        "path": artifact_path,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    })

        return sorted(results, key=lambda a: (a["phase"], a["name"]))

    def get_artifact_paths(self, run_id: str) -> dict[str, list[str]]:
        """Get all artifact paths grouped by phase.

        Returns:
            Dict mapping phase -> list of artifact filenames
        """
        artifacts = self.list_artifacts(run_id)
        paths: dict[str, list[str]] = {}
        for artifact in artifacts:
            phase = artifact["phase"]
            if phase not in paths:
                paths[phase] = []
            paths[phase].append(artifact["name"])
        return paths
```

### Testing Requirements

**Test Framework:** pytest

**Test artifact storage:**
```python
def test_store_creates_artifact(artifact_manager, tmp_path):
    """Test that store creates artifact file."""
    run_id = "01TEST"
    run_dir = tmp_path / ".adw" / "runs" / run_id / "artifacts"
    run_dir.mkdir(parents=True)

    path = artifact_manager.store(run_id, "build", "diff.txt", "line1\nline2")

    assert path.exists()
    assert path.read_text() == "line1\nline2"
    assert path.parent.name == "build"


def test_get_returns_none_for_missing(artifact_manager):
    """Test that get returns None for non-existent artifact."""
    result = artifact_manager.get("nonexistent", "build", "missing.txt")
    assert result is None
```

**Test JSON convenience methods:**
```python
def test_store_and_get_json(artifact_manager, tmp_path):
    """Test JSON storage and retrieval."""
    run_id = "01TEST"
    # ... setup ...

    data = {"key": "value", "count": 42}
    artifact_manager.store_json(run_id, "verify", "result.json", data)

    loaded = artifact_manager.get_json(run_id, "verify", "result.json")
    assert loaded == data
```

**Test artifact listing:**
```python
def test_list_artifacts(artifact_manager, tmp_path):
    """Test listing artifacts."""
    run_id = "01TEST"
    # ... setup ...

    artifact_manager.store(run_id, "build", "diff.txt", "diff content")
    artifact_manager.store(run_id, "verify", "evidence.json", "{}")

    all_artifacts = artifact_manager.list_artifacts(run_id)
    assert len(all_artifacts) == 2

    build_only = artifact_manager.list_artifacts(run_id, phase="build")
    assert len(build_only) == 1
    assert build_only[0]["name"] == "diff.txt"
```

**Coverage Target:** >80% overall, >90% for `artifact_manager.py`

---

## Previous Story Intelligence

**From Story 4.1 (Run Directory Structure):**
- `artifacts/` directory created as part of run structure
- Phase subdirectories created on demand

**From Story 4.2 (Atomic Writes):**
- Use same atomic write pattern (temp + fsync + rename)
- Same error handling with StateError

**Key patterns:**
- Atomic writes for data integrity
- Return None for missing items (not error)
- Structured error codes

---

## Git Intelligence

**From Epic 3:**
- JSON serialization patterns established
- Error handling with StateError codes
- Test fixtures use `tmp_path`

**Existing models:**
- `RunContext` may need `artifact_paths` field added

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Atomic Writes**: Always use temp file + fsync + rename
2. **Graceful Missing**: Return None, don't raise error
3. **Path Tracking**: Store paths not content in context
4. **Type Annotations**: Full annotations on all methods
5. **JSON Convenience**: Provide store_json/get_json helpers

---

## Dev Notes

### Key Implementation Points

1. **Phase Directory Creation**:
   ```python
   artifacts_dir = self.runs_dir / run_id / "artifacts" / phase
   artifacts_dir.mkdir(parents=True, exist_ok=True)
   ```

2. **Binary vs Text**:
   ```python
   mode = "w" if isinstance(content, str) else "wb"
   with open(temp_path, mode) as f:
       f.write(content)
   ```

3. **Graceful Missing**:
   ```python
   if not artifact_path.exists():
       return None  # Not an error
   ```

4. **Path Tracking**:
   ```python
   # In RunContext
   artifact_paths: dict[str, list[str]] = Field(default_factory=dict)
   # {"build": ["diff.txt"], "verify": ["evidence.json"]}
   ```

### Project Structure Notes

- New `artifact_manager.py` in `core/`
- May need to update `RunContext` model
- Follows established patterns

### References

- [Source: _bmad-output/architecture.md#State-Persistence]
- [Source: _bmad-output/architecture.md#FR10-FR11]
- [Source: src/adw/models/context.py] - RunContext

---

## Dev Agent Record

### Context Reference

Story 4.4 implements artifact storage and retrieval for passing data between phases, enabling artifact continuity throughout the pipeline.

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Task 1: Created ArtifactManager class with store, get, list_artifacts, store_json, get_json, and get_artifact_paths methods. Used atomic write pattern (temp + fsync + rename). 17 unit tests added and passing.
- Task 2: Artifact storage already implemented in Task 1. store() method creates phase directories, writes text/binary content, uses atomic writes. 4 dedicated tests pass.
- Task 3: Added head/tail support to get() method for partial content retrieval. 3 new tests added (head, tail, precedence). 20 tests now pass.
- Task 4: Artifact listing already implemented in Task 1. list_artifacts() supports phase filter, includes metadata (size, modified), returns sorted. 4 tests pass.

### File List

- `src/adw/core/artifact_manager.py` - NEW
- `src/adw/core/__init__.py` - MODIFIED (exports ArtifactManager)
- `tests/unit/core/test_artifact_manager.py` - NEW

---

## Dependencies

- **Depends On:** Story 4.1 (needs artifacts directory)
- **Blocks:** None
- **Can Parallel With:** Story 4.2 (both need 4.1 but independent)

### Dependency Rationale
- Story 4.1: Artifacts directory must exist
- Story 4.2: Independent - uses same patterns but different files
- No blockers - other stories don't depend on artifacts

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-01 | BMAD Create-Story | Initial story creation with comprehensive context |
