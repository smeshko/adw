# Story 6.4: List Recent Runs

Status: Ready for Review
Linear Issue: not-configured
Epic: 6 - Run Management & Recovery
Created: 2026-01-03

---

## Story

As a user,
I want to list my recent runs,
So that I can find runs to resume or inspect.

## Acceptance Criteria

**Given** command `adw list`
**When** runs exist
**Then** it displays recent runs (default: 10) sorted by creation time

**Given** the run list
**When** displayed
**Then** each entry shows: run_id, feature (truncated), status, started_at

**Given** command `adw list --limit 20`
**When** executed
**Then** up to 20 runs are displayed

**Given** command `adw list --status failed`
**When** executed
**Then** only failed runs are displayed

**Given** no runs exist
**When** list is requested
**Then** message "No runs found" is displayed

## Tasks / Subtasks

### Task 1: Implement CLI List Command
- [x] Create `src/adw/cli/list.py` with list command
- [x] Add `--limit/-n` option for result count (default: 10)
- [x] Add `--status/-s` option to filter by status
- [x] Add `--json` flag for machine-readable output
- [x] Register command in main app (use name `list_runs` to avoid Python keyword)

### Task 2: Create Run List Display
- [x] Create `src/adw/cli/list_display.py` with `ListDisplay` class
- [x] Implement `show_runs()` method using Rich Table
- [x] Display columns: ID (shortened), Feature, Status, Started
- [x] Color code status column
- [x] Truncate long feature descriptions

### Task 3: Implement Run Collection
- [x] Add `list_runs()` method to RunLookup class
- [x] Support `limit` parameter for max results
- [x] Support `status` filter parameter
- [x] Sort by creation time (newest first, via ULID)
- [x] Return list of RunContext objects

### Task 4: Handle Empty State
- [x] Show "No runs found" when no runs exist
- [x] Show "No runs match filter" when filter has no results
- [x] Suggest `adw run "feature"` to create first run

### Task 5: Implement JSON Output
- [x] Add `--json` flag to command
- [x] Output array of run summaries
- [x] Include: run_id, feature, status, started_at, completed_at
- [x] Clean JSON for scripting

### Task 6: Write Unit Tests
- [x] Create `tests/unit/cli/test_list.py`
- [x] Test list with default limit
- [x] Test list with custom limit
- [x] Test list with status filter
- [x] Test empty runs directory
- [x] Test JSON output format
- [x] Target: >80% coverage

### Task 7: Write Integration Tests
- [x] Create `tests/integration/cli/test_list_integration.py`
- [x] Test list with multiple runs
- [x] Test filter combinations
- [x] Verify sorting order

---

## Developer Context

### Technical Requirements

- **Rich Tables**: Use Rich Table for formatted list
- **Sorting**: Sort by creation time (ULID provides natural sort)
- **Filtering**: Support status filter (completed, failed, running, interrupted)
- **Pagination**: Default 10, configurable via --limit
- **JSON Output**: Clean JSON array for automation

### Architecture Compliance

**From architecture.md - CLI Command Patterns:**
```
# Commands: kebab-case
adw list-runs   # or just 'adw list'

# Options: double-dash + kebab-case
--limit, --status
```

**From architecture.md - Run Storage:**
```
.adw/runs/
├── 01HQXK5P3Z7V8R2M4N6T9W1Y3C/   # Newer (ULID sorts naturally)
├── 01HQXK4P2Z6V7R1M3N5T8W0Y2B/   # Older
└── 01HQXK3P1Z5V6R0M2N4T7W9Y1A/   # Oldest
```

### Library & Framework Requirements

**List Command Implementation:**
```python
import typer
from rich.console import Console
from rich.table import Table

from adw.core.run_lookup import RunLookup

console = Console()

@app.command(name="list")
def list_runs(
    limit: int = typer.Option(
        10,
        "--limit", "-n",
        help="Maximum number of runs to display",
        min=1,
        max=100,
    ),
    status: str | None = typer.Option(
        None,
        "--status", "-s",
        help="Filter by status (running, completed, failed, interrupted)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format",
    ),
) -> None:
    """List recent runs.

    Examples:
        adw list                       # List 10 most recent
        adw list --limit 20            # List 20 most recent
        adw list --status failed       # List only failed runs
        adw list --json                # JSON output
    """
    # Validate status filter
    valid_statuses = {"running", "completed", "failed", "interrupted"}
    if status and status not in valid_statuses:
        console.print(f"[red]Invalid status:[/] {status}")
        console.print(f"Valid values: {', '.join(valid_statuses)}")
        raise typer.Exit(code=1)

    lookup = RunLookup(runs_dir=get_runs_dir())
    runs = lookup.list_runs(limit=limit, status=status)

    if not runs:
        if status:
            console.print(f"[yellow]No runs with status '{status}'[/]")
        else:
            console.print("[yellow]No runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
        return

    if json_output:
        output_json_list(runs)
    else:
        display = ListDisplay(console)
        display.show_runs(runs)
```

**List Display Implementation:**
```python
from rich.console import Console
from rich.table import Table

from adw.models import RunContext

class ListDisplay:
    """Display run list using Rich."""

    STATUS_COLORS = {
        "running": "yellow",
        "completed": "green",
        "failed": "red",
        "interrupted": "orange1",
    }

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def show_runs(self, runs: list[RunContext]) -> None:
        """Display list of runs as a table.

        Args:
            runs: List of run contexts to display.
        """
        table = Table(title=f"Recent Runs ({len(runs)})")

        table.add_column("Run ID", style="cyan", no_wrap=True)
        table.add_column("Feature", max_width=40)
        table.add_column("Status", justify="center")
        table.add_column("Started", style="dim")

        for run in runs:
            # Shorten run_id for display
            short_id = run.run_id[:12] + "..."

            # Truncate feature
            feature = run.feature_description
            if len(feature) > 37:
                feature = f"{feature[:34]}..."

            # Color-code status
            color = self.STATUS_COLORS.get(run.status, "white")
            status = f"[{color}]{run.status}[/]"

            # Format timestamp
            started = run.started_at.strftime("%Y-%m-%d %H:%M") if run.started_at else "—"

            table.add_row(short_id, feature, status, started)

        self.console.print()
        self.console.print(table)
        self.console.print()
```

**RunLookup.list_runs():**
```python
def list_runs(
    self,
    limit: int = 10,
    status: str | None = None,
) -> list[RunContext]:
    """List runs with optional filtering.

    Args:
        limit: Maximum number of runs to return.
        status: Filter by status (optional).

    Returns:
        List of RunContext objects, sorted newest first.
    """
    if not self.runs_dir.exists():
        return []

    runs: list[RunContext] = []

    # List all run directories (ULID sorts naturally by time)
    run_dirs = sorted(self.runs_dir.iterdir(), reverse=True)

    for run_dir in run_dirs:
        if not run_dir.is_dir():
            continue

        try:
            context = self.context_manager.load(run_dir.name)

            # Apply status filter
            if status and context.status != status:
                continue

            runs.append(context)

            # Stop when we have enough
            if len(runs) >= limit:
                break

        except Exception:
            # Skip corrupted runs
            continue

    return runs
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── cli/
│   ├── list.py              # NEW - list command
│   └── list_display.py      # NEW - ListDisplay class
tests/
├── unit/
│   └── cli/
│       ├── test_list.py     # NEW
│       └── test_list_display.py  # NEW
└── integration/
    └── cli/
        └── test_list_integration.py  # NEW
```

**Files to modify:**
```
src/adw/
├── cli/
│   ├── __init__.py          # MODIFY - export list command
│   └── app.py               # MODIFY - register list command
├── core/
│   └── run_lookup.py        # MODIFY - add list_runs method
```

### Testing Requirements

**Test Framework:** pytest

**Test list with default limit:**
```python
def test_list_returns_default_limit(tmp_path):
    """Test that list returns default 10 runs."""
    # Create 15 runs
    for i in range(15):
        create_test_run(tmp_path, status="completed")

    lookup = RunLookup(tmp_path)
    runs = lookup.list_runs()

    assert len(runs) == 10

def test_list_sorted_newest_first(tmp_path):
    """Test that runs are sorted newest first."""
    # Create runs with different times
    older = create_test_run(tmp_path, age_hours=2)
    newer = create_test_run(tmp_path, age_hours=0)

    lookup = RunLookup(tmp_path)
    runs = lookup.list_runs()

    assert runs[0].run_id == newer.run_id
    assert runs[1].run_id == older.run_id
```

**Test list with status filter:**
```python
def test_list_filters_by_status(tmp_path):
    """Test that status filter works correctly."""
    create_test_run(tmp_path, status="completed")
    create_test_run(tmp_path, status="failed")
    create_test_run(tmp_path, status="completed")

    lookup = RunLookup(tmp_path)
    failed_runs = lookup.list_runs(status="failed")

    assert len(failed_runs) == 1
    assert all(r.status == "failed" for r in failed_runs)
```

**Test empty runs:**
```python
def test_list_empty_shows_message(tmp_path):
    """Test that empty list shows helpful message."""
    runner = CliRunner()
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No runs found" in result.output
```

**Coverage Target:** >80% overall

---

## Previous Story Intelligence

**From Story 6.2 and 6.3:**
- RunLookup class handles run finding
- StatusDisplay provides color coding patterns
- JSON output pattern established

**Key patterns:**
- Truncate long text for table display
- Color-code status column
- Sort by creation time

---

## Git Intelligence

**Existing patterns:**
- Rich Table used for structured display
- ULID provides natural sorting by time
- ContextManager loads individual runs

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **CLI Output**: Use Rich Table for lists
2. **Sorting**: Newest first (natural ULID order)
3. **Truncation**: Truncate long text with "..."
4. **JSON Output**: Use console.print_json() for arrays

---

## Dev Notes

### Key Implementation Points

1. **Table Format**:
   ```
           Recent Runs (10)
   ┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
   ┃ Run ID          ┃ Feature                ┃  Status   ┃ Started         ┃
   ┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
   │ 01HQXK5P3Z7V... │ Add user authentication│ completed │ 2026-01-03 10:30│
   │ 01HQXK4P2Z6V... │ Fix login bug          │   failed  │ 2026-01-03 09:15│
   │ 01HQXK3P1Z5V... │ Update dependencies... │  running  │ 2026-01-03 08:00│
   └─────────────────┴────────────────────────┴───────────┴─────────────────┘
   ```

2. **ULID Natural Sorting**:
   - ULIDs are lexicographically sortable by time
   - Just sort directory names in reverse order

3. **Filter Options**:
   - `--status failed` - Only failed runs
   - `--status running` - Currently running
   - `--limit 20` - Show more results

### Project Structure Notes

- ListDisplay is separate from command logic
- Extends RunLookup with list_runs method
- Reuses color patterns from StatusDisplay

### References

- [Source: _bmad-output/architecture.md#Run-Identification] - ULID sorting
- [Source: _bmad-output/architecture.md#CLI-Command-Patterns]

---

## Dev Agent Record

### Context Reference

Story 6.4 implements the list command for viewing recent runs.

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No issues encountered during implementation.

### Completion Notes List

- Implemented `adw list` command with full Rich Table display
- Added `--limit/-n`, `--status/-s`, and `--json` options
- Created ListDisplay class with color-coded status and truncation
- Extended RunLookup with list_runs() method supporting filtering and sorting
- All 1070 tests pass with 93% coverage
- Implementation follows project patterns (Rich for output, ULID for sorting, Pydantic models)

### File List

**New files:**
- src/adw/cli/list.py
- src/adw/cli/list_display.py
- tests/unit/cli/test_list.py
- tests/unit/cli/test_list_display.py
- tests/integration/cli/test_list_integration.py

**Modified files:**
- src/adw/cli/__init__.py
- src/adw/cli/app.py
- src/adw/core/run_lookup.py
- tests/unit/core/test_run_lookup.py

---

## Dependencies

- **Depends On:** Story 6.1 (runs must exist), Story 6.2 (RunLookup class)
- **Blocks:** None
- **Can Parallel With:** Story 6.3 (status), Story 6.5 (abort), Story 6.6 (init)

### Dependency Rationale
- Story 6.1: List needs runs to display
- Story 6.2: Extends RunLookup class

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-03 | BMAD Create-Epic | Initial story creation with comprehensive context |
| 2026-01-03 | Dev Agent (Opus 4.5) | Implemented all tasks - list command, display, tests |
