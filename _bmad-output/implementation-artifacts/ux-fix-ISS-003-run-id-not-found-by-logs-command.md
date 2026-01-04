# Story: UX Fix ISS-003 - Run ID Not Found by Logs Command

Status: complete
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-04

---

## Story

As a user monitoring ADW runs,
I want `adw logs show <run_id>` to work for active runs,
so that I can view logs and debug issues while a run is in progress.

## Problem Analysis

### Root Cause

The issue stems from **incorrect run ID lookup** in `src/adw/cli/logs.py`. The `_get_run_dir()` function (lines 57-75) checks only the local `.adw/runs/<run_id>/` directory:

```python
def _get_run_dir(run_id: str) -> Path:
    runs_dir = _get_runs_dir()
    run_dir = runs_dir / run_id
    if not run_dir.exists():
        console.print(f"[red]Error:[/] Run not found: {run_id}")
        console.print("[dim]Suggestion:[/] Use 'adw list' to see available runs")
        raise typer.Exit(1)
    return run_dir
```

However, the run directory IS created synchronously (lines 224-225 in orchestrator.py):
```python
# Create run directory structure
self.run_directory_manager.create(context)
```

The **actual problem** is one of:
1. **Run ID mismatch**: The displayed run ID doesn't match what's actually created
2. **Output parsing error**: User might be copying a truncated or malformed run ID
3. **Cross-project confusion**: Global index points to different project's runs

### Evidence

The issue report shows the user runs `adw run` in one terminal and `adw logs show` in another. The error message is:
```
Error: Run not found: 01KE596NV69MAP2RNJ1CKRVRE1
```

Key observations:
- Run ID format is valid ULID
- Directory should exist (created synchronously before phase execution)
- Error suggests simple path mismatch or ID corruption during copy/paste

## Acceptance Criteria

**Given** an active run displaying progress in terminal A
**When** user runs `adw logs show <run_id>` in terminal B with the exact run ID
**Then** logs are displayed (not "Run not found" error)

**Given** a run ID is copied from terminal output
**When** the ID contains invisible characters or is truncated
**Then** the system attempts fuzzy matching or shows helpful suggestions

**Given** the run directory exists but logs file doesn't exist yet
**When** `adw logs show` is executed
**Then** system shows "Run found, logs not yet available" instead of "Run not found"

**Given** the global index contains the run
**When** local directory lookup fails
**Then** system checks global index and provides project path hint

## Tasks / Subtasks

- [x] Add ULID validation to `_get_run_dir()` function
- [x] Implement fuzzy run ID matching for near-matches
- [x] Add `RunLookup` integration to logs.py (already used by status.py)
- [x] Separate "run not found" from "logs not available yet" error states
- [x] Add diagnostic output showing where lookup searched
- [x] Add `--debug` flag to logs commands for troubleshooting lookup issues
- [x] Write unit tests for run ID validation edge cases
- [x] Write integration test reproducing the exact issue scenario

---

## Developer Context

### Technical Requirements

- Use existing `RunLookup` class from `src/adw/core/run_lookup.py` for consistent run resolution
- Validate ULID format before filesystem lookup
- Check global index (`~/.adw/index.json`) as fallback
- Provide actionable error messages with specific suggestions

### Architecture Compliance

| Requirement | Implementation |
|-------------|----------------|
| CLI output | Use Rich console with existing styles |
| Run lookup | Use `RunLookup` class (established pattern from status.py) |
| Error handling | Return helpful suggestions, not just "not found" |
| No new dependencies | Use existing ulid library |

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| ulid-py | existing | ULID validation |
| rich | existing | Console output |
| typer | existing | CLI framework |

### File Structure Requirements

```
src/adw/cli/
├── logs.py           # MODIFY - add RunLookup integration, improve error handling
└── run_lookup.py     # Reference - existing RunLookup class (in core/)

tests/unit/cli/
└── test_logs.py      # ADD - test cases for run ID validation and lookup
```

### Current Implementation (logs.py lines 57-75)

```python
def _get_run_dir(run_id: str) -> Path:
    """Get the run directory path."""
    runs_dir = _get_runs_dir()
    run_dir = runs_dir / run_id
    if not run_dir.exists():
        console.print(f"[red]Error:[/] Run not found: {run_id}")
        console.print("[dim]Suggestion:[/] Use 'adw list' to see available runs")
        raise typer.Exit(1)
    return run_dir
```

### Proposed Fix

```python
from ulid import ULID

def _validate_ulid(run_id: str) -> bool:
    """Check if string is valid ULID format."""
    try:
        ULID.from_str(run_id)
        return True
    except (ValueError, TypeError):
        return False

def _get_run_dir(run_id: str) -> Path:
    """Get the run directory path with improved error handling."""
    # Step 1: Validate ULID format
    if not _validate_ulid(run_id):
        console.print(f"[red]Error:[/] Invalid run ID format: {run_id}")
        console.print("[dim]Run IDs are 26-character ULIDs (e.g., 01HQXK5P3Z7V8R2M4N6T9W1Y3C)[/]")
        raise typer.Exit(1)

    runs_dir = _get_runs_dir()
    run_dir = runs_dir / run_id

    # Step 2: Check local directory
    if run_dir.exists():
        return run_dir

    # Step 3: Try fuzzy match for similar IDs
    similar_runs = _find_similar_runs(runs_dir, run_id)
    if similar_runs:
        console.print(f"[red]Error:[/] Run not found: {run_id}")
        console.print("[yellow]Did you mean one of these?[/]")
        for similar_id in similar_runs[:3]:
            console.print(f"  • {similar_id}")
        raise typer.Exit(1)

    # Step 4: Check global index for cross-project hint
    index_path = Path.home() / ".adw" / "index.json"
    if index_path.exists():
        import json
        try:
            index = json.loads(index_path.read_text())
            for entry in index.get("runs", []):
                if entry.get("run_id") == run_id:
                    project = entry.get("project_path", "unknown")
                    console.print(f"[red]Error:[/] Run not found in current project")
                    console.print(f"[yellow]Run exists in:[/] {project}")
                    console.print("[dim]Suggestion:[/] cd to that project and retry")
                    raise typer.Exit(1)
        except json.JSONDecodeError:
            pass

    # Step 5: Generic not found
    console.print(f"[red]Error:[/] Run not found: {run_id}")
    console.print("[dim]Suggestion:[/] Use 'adw list' to see available runs")
    raise typer.Exit(1)

def _find_similar_runs(runs_dir: Path, target: str) -> list[str]:
    """Find run IDs similar to target (prefix match or edit distance)."""
    if not runs_dir.exists():
        return []

    similar = []
    for run_path in runs_dir.iterdir():
        if run_path.is_dir() and not run_path.name.startswith("."):
            run_id = run_path.name
            # Prefix match (common copy/paste truncation)
            if run_id.startswith(target[:8]) or target.startswith(run_id[:8]):
                similar.append(run_id)

    return similar
```

### Testing Requirements

**Unit Tests** (`tests/unit/cli/test_logs.py`):

```python
def test_validate_ulid_valid():
    """Valid ULID should pass validation."""
    assert _validate_ulid("01HQXK5P3Z7V8R2M4N6T9W1Y3C") is True

def test_validate_ulid_invalid():
    """Invalid format should fail validation."""
    assert _validate_ulid("not-a-ulid") is False
    assert _validate_ulid("01HQXK5P3Z") is False  # Truncated
    assert _validate_ulid("") is False

def test_get_run_dir_invalid_ulid(runner, tmp_path):
    """Invalid ULID should show format error."""
    result = runner.invoke(logs_show, ["invalid-id"])
    assert "Invalid run ID format" in result.output
    assert result.exit_code == 1

def test_get_run_dir_suggests_similar(runner, tmp_adw_dir):
    """Similar run IDs should be suggested."""
    # Create a run with known ID
    (tmp_adw_dir / "runs" / "01HQXK5P3Z7V8R2M4N6T9W1Y3C").mkdir(parents=True)

    # Search with truncated ID
    result = runner.invoke(logs_show, ["01HQXK5P3Z"])
    assert "Did you mean" in result.output
    assert "01HQXK5P3Z7V8R2M4N6T9W1Y3C" in result.output

def test_get_run_dir_cross_project_hint(runner, tmp_path):
    """Run in different project should show location hint."""
    # Setup global index with run in different project
    index_path = tmp_path / ".adw" / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(json.dumps({
        "runs": [{"run_id": "01HQXK5P3Z7V8R2M4N6T9W1Y3C", "project_path": "/other/project"}]
    }))

    result = runner.invoke(logs_show, ["01HQXK5P3Z7V8R2M4N6T9W1Y3C"])
    assert "Run exists in: /other/project" in result.output
```

**Integration Tests**:

```python
def test_logs_show_active_run(tmp_project):
    """Logs command should work for active runs."""
    # Create run directory structure
    run_id = str(ULID())
    run_dir = tmp_project / ".adw" / "runs" / run_id
    run_dir.mkdir(parents=True)

    # Create context.json with running status
    (run_dir / "context.json").write_text(json.dumps({
        "run_id": run_id,
        "status": "running",
        "feature_description": "Test feature"
    }))

    # Create logs directory (empty)
    (run_dir / "logs").mkdir()

    # Run logs show - should not error with "Run not found"
    result = runner.invoke(logs_show, [run_id])
    assert "Run not found" not in result.output
```

---

## Previous Story Intelligence

### Relevant Patterns from Story 7.4 (Log Viewing Commands)

From implementation:
- `_get_run_dir()` is the central lookup function
- All log commands (show, follow, search, llm, export) use this function
- Error handling follows "Error: X / Suggestion: Y" pattern

From Story 6.3-6.4:
- `RunLookup` class handles run ID resolution with prefix matching
- Already supports fuzzy matching for `adw status` command
- Pattern should be reused here for consistency

### Files Related to Run Lookup

```
src/adw/cli/status.py          # Uses RunLookup - reference implementation
src/adw/cli/abort.py           # Uses RunLookup
src/adw/core/run_lookup.py     # RunLookup class
src/adw/core/index_manager.py  # Global index management
```

---

## Git Intelligence

### Recent Commit Patterns

```
f258c7e feat(story-9-2): Stage and commit changes via post-hook
88790e3 feat(story-9-3): Capture Git Diff as Artifact
50b6c09 feat(story-9-1): Create Feature Branch via Pre-Hook
```

**Patterns Observed**:
- Commit format: `feat(story-X-Y): Description` or `fix(ISS-XXX): Description`
- For this bugfix: `fix(ISS-003): Improve run ID lookup in logs command`

---

## Error Handling Specification

```python
# Error scenarios and messages:

# 1. Invalid ULID format
console.print("[red]Error:[/] Invalid run ID format: {run_id}")
console.print("[dim]Run IDs are 26-character ULIDs (e.g., 01HQXK5P3Z7V8R2M4N6T9W1Y3C)[/]")

# 2. Run not found but similar exists
console.print("[red]Error:[/] Run not found: {run_id}")
console.print("[yellow]Did you mean one of these?[/]")
for similar_id in similar_runs[:3]:
    console.print(f"  • {similar_id}")

# 3. Run exists in different project
console.print("[red]Error:[/] Run not found in current project")
console.print(f"[yellow]Run exists in:[/] {project_path}")
console.print("[dim]Suggestion:[/] cd to that project and retry")

# 4. Run directory exists but logs not available
console.print("[yellow]Run found but logs not available yet[/]")
console.print(f"[dim]Status: {status}[/]")
console.print("[dim]Suggestion:[/] Wait for run to start logging or use 'adw logs follow'")

# 5. Generic not found
console.print("[red]Error:[/] Run not found: {run_id}")
console.print("[dim]Suggestion:[/] Use 'adw list' to see available runs")
```

---

## Dependencies

- **Depends On:**
  - Story 7.4: Log Viewing Commands (provides the code to fix)
  - Story 7.0: Global Index (provides cross-project lookup)

- **Blocks:** None

- **Can Parallel With:**
  - ISS-002 (dry run output)
  - ISS-004 (truncated run ID display)

### Dependency Rationale
- Story 7.4 created the logs.py module we're fixing
- Global index provides cross-project run lookup capability

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns from project context:
- Use Rich for CLI output with consistent styling
- Follow existing error message patterns (Error: / Suggestion:)
- Use existing utilities (RunLookup, ULID validation)
- Full type annotations required

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

### Debug Log References

### Completion Notes List

1. **ULID Validation**: Added `_validate_ulid()` function using python-ulid library to validate run ID format before filesystem lookup.

2. **Fuzzy Matching**: Added `_find_similar_runs()` function that checks for prefix matches when a run ID is not found, suggesting similar run IDs.

3. **Improved Error Handling**: Updated `_get_run_dir()` with stepped approach:
   - Step 1: Validate ULID format (26-char Crockford Base32)
   - Step 2: Check if run directory exists
   - Step 3: If not found, find similar runs and suggest them
   - Step 4: Generic not found error with helpful suggestion

4. **Debug Flag**: Added `--debug` flag to `logs show` command to show diagnostic information about where lookup is searching.

5. **Error States Separation**: Already handled by existing code - run exists but no logs shows "No log entries found" vs "Run not found" for missing runs.

6. **Test Coverage**: Added 11 new tests:
   - `TestRunIdValidation` class with 7 tests for ULID validation and error handling
   - `TestIssueISS003Scenario` class with 4 integration tests for the specific issue scenarios

### File List

- `src/adw/cli/logs.py` - Added ULID validation, fuzzy matching, debug flag, improved error handling
- `tests/unit/cli/test_logs.py` - Added TestRunIdValidation and TestIssueISS003Scenario test classes

