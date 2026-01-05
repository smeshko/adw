# Story 10.2: Worktree Directory Structure

Status: ready-for-dev
Linear Issue: not-configured
Epic: 10 - Worktree Isolation
Created: 2026-01-05

---

## Story

As a developer,
I want worktrees organized predictably,
so that I can find and inspect them easily.

## Acceptance Criteria

**Given** worktree creation
**When** path is determined
**Then** it's created at `<project-root>/trees/<run_id>/`

**Given** the trees directory
**When** it doesn't exist
**Then** it's created with `.gitignore` entry added to project

**Given** worktree structure
**When** created
**Then** it includes full project copy with `.adw/` directory

**Given** `.adw/runs/<run_id>/` in worktree
**When** run executes
**Then** all artifacts are stored in the worktree's `.adw/` directory

**Given** run completion
**When** artifacts need preservation
**Then** key artifacts are copied to main `.adw/runs/<run_id>/` before worktree removal

## Tasks / Subtasks

### Task 1: Create Trees Directory Management
- [x] Add `ensure_trees_directory(project_root: Path) -> Path` to WorktreeManager
- [x] Create `trees/` directory if it doesn't exist
- [x] Create `trees/.gitignore` with `*` to ignore all worktree contents
- [x] Add `trees/` entry to project's root `.gitignore` if not present

### Task 2: Define Worktree Internal Structure
- [x] Document standard worktree structure in code comments
- [x] Ensure `.adw/` directory exists in worktree after creation
- [x] Create `runs/<run_id>/` directory structure matching main project

### Task 3: Implement Artifact Preservation
- [ ] Add `preserve_artifacts(worktree_path: Path, run_id: str, main_project: Path) -> list[Path]`
- [ ] Define list of artifacts to preserve:
  - `context.json` - run state
  - `logs/` - all log files
  - `artifacts/` - phase outputs
  - `llm/` - LLM interaction logs
- [ ] Copy artifacts to `main_project/.adw/runs/<run_id>/` before worktree removal
- [ ] Create manifest of preserved artifacts

### Task 4: Add Configuration for Artifact Preservation
- [ ] Add `preserve_artifacts: list[str]` to WorktreeConfig with defaults
- [ ] Add `artifact_manifest_file: str = "worktree-artifacts.json"` to config
- [ ] Allow users to specify additional files to preserve

### Task 5: Integrate with Worktree Lifecycle
- [ ] Call `ensure_trees_directory()` in `WorktreeManager.create_worktree()`
- [ ] Call `preserve_artifacts()` in `WorktreeManager.remove_worktree()` before removal
- [ ] Log artifact preservation operations

### Task 6: Write Tests
- [ ] Test trees directory creation and gitignore setup
- [ ] Test artifact preservation copies correct files
- [ ] Test artifact manifest is created correctly
- [ ] Test integration with full worktree lifecycle

---

## Dependencies

**Depends On:**
- 10-1: Worktree Creation and Lifecycle (needs base worktree creation)

**Blocks:**
- 10-5: Worktree Context in Phases (needs directory structure for phase execution)

**Can Parallel With:**
- 10-3: Port Allocation System
- 10-6: Worktree Branch Management

---

## Developer Context

### Technical Requirements

1. **Directory Operations**
   - Use `pathlib.Path.mkdir(parents=True, exist_ok=True)` for directory creation
   - Preserve file permissions when copying artifacts
   - Handle symlinks appropriately (don't follow)

2. **Gitignore Management**
   - Check if entry already exists before adding
   - Append to existing `.gitignore` with newline handling
   - Create `.gitignore` if it doesn't exist

3. **Artifact Copying**
   - Use `shutil.copytree()` for directory artifacts
   - Use `shutil.copy2()` for single files (preserves metadata)
   - Handle case where source doesn't exist gracefully

### Architecture Compliance

**File Changes:**

```python
# src/adw/worktree/manager.py - Add new methods
class WorktreeManager:
    # ... existing methods ...

    def ensure_trees_directory(self, project_root: Path) -> Path:
        """Ensure trees directory exists with proper gitignore."""
        ...

    def preserve_artifacts(
        self,
        worktree_path: Path,
        run_id: str,
        main_project: Path,
        artifacts_to_preserve: list[str] | None = None,
    ) -> list[Path]:
        """Copy key artifacts to main project before worktree removal."""
        ...
```

**Model Changes:**

```python
# src/adw/models/config.py - Extend WorktreeConfig
class WorktreeConfig(BaseModel):
    enabled: bool = True
    base_dir: str = "trees"
    preserve_on_failure: bool = True
    cleanup_branch_on_remove: bool = False
    # New fields
    preserve_artifacts: list[str] = Field(
        default=["context.json", "logs", "artifacts", "llm"]
    )
    artifact_manifest_file: str = "worktree-artifacts.json"
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| pathlib | stdlib | Path operations |
| shutil | stdlib | File/directory copying |
| json | stdlib | Artifact manifest serialization |

### File Structure Requirements

**Worktree Directory Layout:**
```
<project-root>/
├── trees/                      # Worktrees base directory
│   ├── .gitignore             # Contains: *
│   ├── 01HQXK5.../            # Active worktree
│   │   ├── (full project copy)
│   │   ├── .adw/
│   │   │   └── runs/01HQXK5.../
│   │   │       ├── context.json
│   │   │       ├── logs/
│   │   │       ├── artifacts/
│   │   │       └── llm/
│   │   └── .ports.env          # (Added by Story 10.3)
│   └── 01HQXK6.../             # Another concurrent run
└── .adw/
    └── runs/
        └── 01HQXK5.../         # Preserved artifacts after worktree removal
            ├── context.json
            ├── logs/
            ├── artifacts/
            ├── llm/
            └── worktree-artifacts.json  # Manifest of what was preserved
```

**Artifact Manifest Format:**
```json
{
  "run_id": "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
  "source_worktree": "/path/to/trees/01HQXK5.../",
  "preserved_at": "2026-01-05T10:30:00Z",
  "artifacts": [
    {"path": "context.json", "size": 2048, "type": "file"},
    {"path": "logs", "size": 15360, "type": "directory"},
    {"path": "artifacts", "size": 102400, "type": "directory"},
    {"path": "llm", "size": 51200, "type": "directory"}
  ]
}
```

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/worktree/test_directory_structure.py
class TestTreesDirectory:
    def test_ensure_creates_directory(self, tmp_path):
        """Creates trees/ directory when it doesn't exist."""

    def test_ensure_creates_gitignore(self, tmp_path):
        """Creates trees/.gitignore with * content."""

    def test_ensure_adds_to_root_gitignore(self, tmp_path):
        """Adds trees/ to project .gitignore if not present."""

    def test_ensure_idempotent(self, tmp_path):
        """Multiple calls don't duplicate .gitignore entries."""


class TestArtifactPreservation:
    def test_preserve_copies_context_json(self, worktree_with_artifacts):
        """context.json is copied to main project."""

    def test_preserve_copies_log_directory(self, worktree_with_artifacts):
        """logs/ directory is copied recursively."""

    def test_preserve_creates_manifest(self, worktree_with_artifacts):
        """worktree-artifacts.json manifest is created."""

    def test_preserve_handles_missing_artifacts(self, worktree_with_artifacts):
        """Missing artifacts are skipped without error."""

    def test_preserve_respects_config(self, worktree_with_artifacts):
        """Only configured artifacts are preserved."""
```

**Test Fixtures:**
```python
@pytest.fixture
def worktree_with_artifacts(tmp_path):
    """Create a worktree with sample artifacts for testing."""
    run_id = "01HQXK5TEST"
    worktree = tmp_path / "trees" / run_id
    adw_dir = worktree / ".adw" / "runs" / run_id

    adw_dir.mkdir(parents=True)
    (adw_dir / "context.json").write_text('{"run_id": "test"}')
    (adw_dir / "logs").mkdir()
    (adw_dir / "logs" / "run.log").write_text("log content")
    (adw_dir / "artifacts").mkdir()
    (adw_dir / "llm").mkdir()

    return worktree, run_id, tmp_path
```

---

## Previous Story Intelligence

**From Story 10-1:**
- WorktreeManager class established in `src/adw/worktree/manager.py`
- WorktreeConfig model in `src/adw/models/config.py`
- Git subprocess patterns for worktree operations

---

## Git Intelligence

**Relevant Patterns:**
- Artifact storage patterns from Epic 4 (State Persistence)
- Directory structure patterns from `core/context_manager.py`
- Gitignore handling patterns from project initialization

---

## Latest Technical Information

**shutil Best Practices (Python 3.13):**
- `shutil.copytree()` with `dirs_exist_ok=True` for merging directories
- Use `shutil.disk_usage()` for size calculations if needed
- `shutil.copy2()` preserves timestamps and permissions

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- **Structured logging**: Log each artifact preserved
- **Type annotations**: All paths typed as `Path`
- **Context managers**: Use for file operations where appropriate

---

## Dev Notes

### Implementation Order

1. `ensure_trees_directory()` - Foundation for worktree creation
2. Integrate with `create_worktree()` from Story 10-1
3. `preserve_artifacts()` - For cleanup phase
4. Integrate with `remove_worktree()` from Story 10-1
5. Tests

### Edge Cases

- Worktree directory exists but is corrupt
- Permission denied during artifact copy
- Disk space issues during preservation
- Interrupted preservation (partial copy)

### References

- [Source: _bmad-output/epics/epic-10-worktree-isolation.md#Story 10.2]
- [Source: _bmad-output/architecture.md#File Locations]

---

## Dev Agent Record

### Context Reference

Epic 10: Worktree Isolation - Story 10.2

### Agent Model Used

<!-- To be filled by dev agent -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
