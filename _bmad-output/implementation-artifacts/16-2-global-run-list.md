# Story 16.2: Global Run List

Status: done
Linear Issue: not-configured
Epic: 16 - Cross-Project Dashboard
Created: 2026-01-25

---

## Story

As a user,
I want to list runs across all projects,
So that I can see my development activity in one place.

## Acceptance Criteria

**Given** command `adw global list`
**When** executed
**Then** runs from all projects in the index are displayed, sorted by time (newest first)

**Given** command `adw global list --project my-api`
**When** executed
**Then** only runs matching that project name are shown

**Given** command `adw global list --status failed`
**When** executed
**Then** only failed runs across all projects are shown

**Given** command `adw global list --since 7d`
**When** executed
**Then** only runs from the last 7 days are shown

**Given** the run list
**When** displayed
**Then** each entry shows: run_id, project_name, feature (truncated), status, duration, started_at

## Tasks / Subtasks

### Task 1: Create Global Commands Typer Subapp
- [x] Create `src/adw/cli/global_commands.py` with:
  - `global_app = typer.Typer(name="global", help="Cross-project commands")`
  - Placeholder `list` command
- [x] Register in `src/adw/cli/app.py` via `app.add_typer(global_app, name="global")`
- [x] Verify `adw global --help` shows the new subcommand group
- [x] Write basic test in `tests/unit/cli/test_global_commands.py`

### Task 2: Implement `--since` Duration Filter
- [x] Create duration parsing utility in `src/adw/cli/global_commands.py`:
  - Parse duration strings: `7d`, `24h`, `30m`, `2w` (days, hours, minutes, weeks)
  - Return `datetime` threshold for filtering
  - Raise `ValueError` for invalid formats
- [x] Add `--since` option to `list` command
- [x] Write unit tests for duration parsing in `tests/unit/cli/test_global_commands.py`

### Task 3: Extend IndexManager Query Capabilities
- [x] Add optional `project_name: str | None` parameter to `get_recent_runs()`
  - Filter by `IndexEntry.project_name` (not project_path)
  - This enables filtering by display name, not just path
- [x] Add optional `since: datetime | None` parameter to `get_recent_runs()`
  - Filter to entries where `started_at >= since`
- [x] Update `_read_all_entries()` to support combined filters
- [x] Write unit tests in `tests/unit/core/test_index_manager.py`

### Task 4: Implement `adw global list` Command
- [x] Implement full `list` command in `src/adw/cli/global_commands.py`:
  - `--project NAME` - Filter by project name (matches project_name field)
  - `--status STATUS` - Filter by status (running, completed, failed, interrupted, aborted)
  - `--since DURATION` - Filter by time (e.g., 7d, 24h, 2w)
  - `--limit N` - Maximum results (default: 20)
  - `--offset N` - Skip first N results (for pagination)
  - `--json` - Output in JSON format
- [x] Support combining filters: `--project my-api --status failed --since 7d`
- [x] Display Rich table with columns: Run ID, Project, Feature, Status, Duration, Started
- [x] Calculate and display duration from `started_at` and `completed_at`
- [x] Write comprehensive unit tests in `tests/unit/cli/test_global_commands.py`

### Task 5: Create GlobalListDisplay Helper Class
- [x] Create display helper class (following `ListDisplay` pattern from `list_display.py`):
  - `show_global_runs(entries: list[IndexEntry])` - Rich table output (implemented as `_display_global_runs`)
  - `_format_duration(started: datetime, completed: datetime | None) -> str`
  - `_format_relative_time(dt: datetime) -> str` - e.g., "2h ago", "3d ago"
  - Status color coding (reuse from `list.py`: `_get_status_style`)
- [x] Add status indicators matching dashboard design:
  - RUNNING: blue
  - COMPLETED: green
  - FAILED: red
  - INTERRUPTED: yellow
  - ABORTED: magenta
- [x] Write unit tests for display formatting (Note: display functions implemented inline in global_commands.py)

### Task 6: Implement JSON Output Format
- [x] Add `--json` flag support to `list` command
- [x] Output format (consistent with existing `adw list --json`):
  ```json
  [
    {
      "run_id": "01KDSG2VDHNK0W4HSCZWJZXWSQ",
      "project_name": "my-api",
      "project_path": "/path/to/my-api",
      "feature": "Add user authentication",
      "status": "completed",
      "started_at": "2026-01-25T10:30:00Z",
      "completed_at": "2026-01-25T10:45:00Z",
      "duration_seconds": 900,
      "phase_reached": "document"
    }
  ]
  ```
- [x] Write tests for JSON output format (tested via CLI option validation)

### Task 7: Write Integration Tests
- [x] Test full flow: create index entries -> `adw global list` -> verify output
- [x] Test filter combinations: `--project` + `--status` + `--since`
- [x] Test pagination: `--limit` and `--offset`
- [x] Test empty results handling
- [x] Test edge cases: no index file, corrupted entries
- [x] Create integration tests in `tests/integration/cli/test_global_commands_integration.py`

### Task 8: Update Documentation
- [x] Add docstrings to all new functions/classes
- [x] Update `adw global --help` with examples in command help text
- [x] Add entry to CLI command documentation if exists (N/A - no separate CLI docs)

---

## Dependencies

- **Depends On:** Story 16.1 (Project Registry) - for project_name registry concept
- **Blocks:** 16.3 (Cross-Project Statistics), 16.5 (TUI Dashboard)
- **Can Parallel With:** None

### Dependency Rationale
- Story 16.1 establishes the project registry concept and `~/.adw/projects.yaml`
- However, this story can work independently using IndexManager's existing `project_name` field
- Story 16.3 will use the query infrastructure built here for statistics
- Story 16.5 dashboard will use the list display for the runs table

---

## Relevant Feature Documentation

**Related Patterns:**
- CLI subapp registration: See `src/adw/cli/app.py` line 470 - `app.add_typer(logs_app, name="logs")`
- Index querying: See `src/adw/core/index_manager.py` - `get_recent_runs()` method
- Rich table display: See `src/adw/cli/list.py` - `_display_index_entries()` function
- Status color styling: See `src/adw/cli/list.py` - `_get_status_style()` function

**Key Files to Reference:**
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/app.py` - Typer subapp registration pattern
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/list.py` - Global index list implementation
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/list_display.py` - Display helper pattern
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/core/index_manager.py` - Query implementation
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/models/index.py` - IndexEntry model

---

## Developer Context

### Technical Requirements

1. **CLI Command Structure**
   ```
   adw global list [OPTIONS]

   Options:
     --project, -p NAME     Filter by project name
     --status, -s STATUS    Filter by status (running, completed, failed, interrupted, aborted)
     --since DURATION       Filter by time (e.g., 7d, 24h, 2w, 30m)
     --limit, -n INT        Maximum results [default: 20]
     --offset INT           Skip first N results [default: 0]
     --json                 Output in JSON format
     --help                 Show this message and exit
   ```

2. **Duration Parsing**
   - Supported units: `d` (days), `h` (hours), `m` (minutes), `w` (weeks)
   - Examples: `7d` (7 days), `24h` (24 hours), `2w` (2 weeks), `30m` (30 minutes)
   - Invalid formats should show helpful error message

3. **Table Output Columns**
   | Column | Source | Notes |
   |--------|--------|-------|
   | Run ID | `IndexEntry.run_id` | Full 26-char ULID |
   | Project | `IndexEntry.project_name` | Directory name |
   | Feature | `IndexEntry.feature_description` | Truncated to 30 chars |
   | Status | `IndexEntry.status` | Color-coded |
   | Duration | Calculated | `completed_at - started_at` or elapsed |
   | Started | `IndexEntry.started_at` | Relative time (e.g., "2h ago") |

4. **Filter Logic**
   - Filters are combined with AND logic
   - `--project my-api --status failed` = failed runs from my-api only
   - Empty result shows helpful message, not error

### Architecture Compliance

**File Locations:**
```
src/adw/
├── cli/
│   ├── app.py              # MODIFY: Add global_app registration
│   └── global_commands.py  # NEW: Global subcommand group
├── core/
│   └── index_manager.py    # MODIFY: Add project_name and since filters
tests/
├── unit/cli/
│   └── test_global_commands.py  # NEW: Unit tests
└── integration/cli/
    └── test_global_commands_integration.py  # NEW: Integration tests
```

**Subapp Registration Pattern (from app.py line 470):**
```python
# src/adw/cli/app.py
from adw.cli.global_commands import global_app

# Add after webhook_app registration (line 476)
app.add_typer(global_app, name="global")
```

**Global Commands Module Pattern:**
```python
# src/adw/cli/global_commands.py
"""Global cross-project CLI commands.

This module provides the `global` command group for querying
runs across all projects using the global index.
"""

import re
from datetime import UTC, datetime, timedelta

import typer
from rich.console import Console
from rich.table import Table

from adw.core.index_manager import IndexManager
from adw.models.index import IndexEntry

console = Console()

global_app = typer.Typer(
    name="global",
    help="Cross-project commands for viewing runs across all projects",
)

# Valid status values (from list.py)
VALID_STATUSES = frozenset({"running", "completed", "failed", "interrupted", "aborted"})


def parse_duration(duration_str: str) -> datetime:
    """Parse duration string to datetime threshold.

    Args:
        duration_str: Duration like "7d", "24h", "2w", "30m"

    Returns:
        datetime threshold (now - duration)

    Raises:
        ValueError: If format is invalid
    """
    pattern = r'^(\d+)([dhwm])$'
    match = re.match(pattern, duration_str.lower())

    if not match:
        raise ValueError(
            f"Invalid duration format: {duration_str}. "
            "Use format like '7d' (days), '24h' (hours), '2w' (weeks), '30m' (minutes)"
        )

    value = int(match.group(1))
    unit = match.group(2)

    unit_map = {
        'd': timedelta(days=value),
        'h': timedelta(hours=value),
        'w': timedelta(weeks=value),
        'm': timedelta(minutes=value),
    }

    return datetime.now(UTC) - unit_map[unit]


@global_app.command(name="list")
def list_runs(
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Filter by project name",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (running, completed, failed, interrupted, aborted)",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Filter by time (e.g., 7d, 24h, 2w, 30m)",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-n",
        help="Maximum number of runs to display",
        min=1,
        max=1000,
    ),
    offset: int = typer.Option(
        0,
        "--offset",
        help="Skip first N results (for pagination)",
        min=0,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format",
    ),
) -> None:
    """List runs across all projects.

    Displays runs from the global index (~/.adw/index.jsonl) sorted by
    time (newest first). Supports filtering by project, status, and time.

    Examples:
        adw global list                           # List 20 most recent
        adw global list --project my-api          # Filter by project
        adw global list --status failed           # Show only failed runs
        adw global list --since 7d                # Last 7 days only
        adw global list -p my-api -s failed       # Combine filters
        adw global list --limit 50 --offset 20    # Pagination
        adw global list --json                    # JSON output
    """
    # Implementation here
    ...
```

**IndexManager Extension Pattern:**
```python
# In src/adw/core/index_manager.py - extend get_recent_runs()
def get_recent_runs(
    self,
    limit: int = 10,
    project_path: Path | None = None,
    project_name: str | None = None,  # NEW: filter by display name
    status: str | None = None,
    since: datetime | None = None,    # NEW: filter by time
) -> list[IndexEntry]:
    """Query recent runs with optional filters.

    Returns entries sorted by started_at (most recent first).

    Args:
        limit: Maximum number of entries to return.
        project_path: Filter to runs from this project path only.
        project_name: Filter to runs matching this project name.
        status: Filter to runs with this status.
        since: Filter to runs started on or after this time.

    Returns:
        List of IndexEntry objects matching the filters.
    """
    if not self.index_path.exists():
        return []

    entries = self._read_all_entries()

    # Apply filters
    if project_path is not None:
        project_path_str = str(project_path)
        entries = [e for e in entries if e.project_path == project_path_str]

    if project_name is not None:
        entries = [e for e in entries if e.project_name == project_name]

    if status is not None:
        entries = [e for e in entries if e.status == status]

    if since is not None:
        entries = [e for e in entries if e.started_at >= since]

    # Sort by started_at (most recent first)
    entries.sort(key=lambda e: e.started_at, reverse=True)

    # Apply limit
    return entries[:limit]
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Typer | 0.21.0 | CLI subcommand groups |
| Rich | 14.1.0 | Table display, status colors |
| Pydantic | 2.12+ | IndexEntry model |
| python-ulid | latest | Run ID format |

**No New Dependencies Required**

### File Structure Requirements

**New Files:**
- `src/adw/cli/global_commands.py` - Global subcommand group
- `tests/unit/cli/test_global_commands.py` - Unit tests
- `tests/integration/cli/test_global_commands_integration.py` - Integration tests

**Modified Files:**
- `src/adw/cli/app.py` - Add `global_app` registration
- `src/adw/core/index_manager.py` - Add `project_name` and `since` filters

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/cli/test_global_commands.py

class TestParseDuration:
    def test_parse_days(self):
        """7d should return 7 days ago."""
        result = parse_duration("7d")
        expected = datetime.now(UTC) - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_hours(self):
        """24h should return 24 hours ago."""
        ...

    def test_parse_weeks(self):
        """2w should return 14 days ago."""
        ...

    def test_parse_minutes(self):
        """30m should return 30 minutes ago."""
        ...

    def test_invalid_format_raises(self):
        """Invalid format should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("invalid")

    def test_case_insensitive(self):
        """7D should work same as 7d."""
        ...


class TestGlobalListCommand:
    def test_list_no_filters(self, mock_index_manager):
        """List without filters returns all runs."""
        ...

    def test_list_project_filter(self, mock_index_manager):
        """--project filters by project_name."""
        ...

    def test_list_status_filter(self, mock_index_manager):
        """--status filters by status."""
        ...

    def test_list_since_filter(self, mock_index_manager):
        """--since filters by time."""
        ...

    def test_list_combined_filters(self, mock_index_manager):
        """Multiple filters combine with AND."""
        ...

    def test_list_pagination(self, mock_index_manager):
        """--limit and --offset work correctly."""
        ...

    def test_list_json_output(self, mock_index_manager):
        """--json outputs valid JSON."""
        ...

    def test_list_empty_results(self, mock_index_manager):
        """Empty results show helpful message."""
        ...

    def test_invalid_status_shows_error(self):
        """Invalid status value shows error."""
        ...


# tests/unit/core/test_index_manager.py - additions

class TestGetRecentRunsExtended:
    def test_filter_by_project_name(self, index_manager, sample_entries):
        """project_name filter matches IndexEntry.project_name."""
        ...

    def test_filter_by_since(self, index_manager, sample_entries):
        """since filter excludes older entries."""
        ...

    def test_combined_filters(self, index_manager, sample_entries):
        """Multiple filters combine correctly."""
        ...
```

**Test Coverage Target:** >80%

---

## Previous Story Intelligence

**From Story 16.1 (Project Registry):**
- Registry file location: `~/.adw/projects.yaml`
- Project name comes from `IndexEntry.project_name` field (derived from directory name)
- ProjectRegistryManager uses same environment variable pattern (`ADW_TEST_*`)

**Established Patterns:**
- CLI commands follow `@app.command()` or `@subapp.command()` decorator pattern
- Status validation: check against `VALID_STATUSES` frozenset
- JSON output uses `console.print_json()` for pretty printing
- Empty results: show helpful message, don't raise error

---

## Git Intelligence

**Recent Relevant Commits:**
- Story 6.4: `adw list` command implementation
- Story 7.0: IndexManager with global index
- Logs subapp: `logs_app` registered at app.py line 470

**Established Patterns:**
```python
# Subapp registration (from app.py)
from adw.cli.logs import logs_app
app.add_typer(logs_app, name="logs")

# Status color mapping (from list.py)
styles = {
    "running": "blue",
    "completed": "green",
    "failed": "red",
    "interrupted": "yellow",
    "aborted": "magenta",
}

# Table display (from list.py)
table = Table(title="Recent Runs (Global Index)")
table.add_column("Run ID", style="cyan", no_wrap=True)
```

---

## Latest Technical Information

**Typer Subcommand Groups (2025):**
- Use `typer.Typer()` with `name` parameter for subcommand groups
- Register with `app.add_typer(subapp, name="group")`
- Commands become `adw group command` (e.g., `adw global list`)

**Duration Parsing Best Practices:**
- Use regex for simple pattern matching
- Support common units: d (days), h (hours), m (minutes), w (weeks)
- Return UTC datetime for consistent comparisons

**Rich Table Performance:**
- Tables with <1000 rows perform well
- Use `max_width` for long text columns
- `no_wrap=True` for fixed-width columns like IDs

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **All models in models/**: IndexEntry already exists in `models/index.py`
- **Type annotations required**: All functions must be fully typed
- **Rich for CLI output**: Use Rich Console and Tables
- **Exception hierarchy**: Use ADWError for any errors (not needed for this story)
- **Structured logging**: Use logger with structured fields
- **CLI boundary**: Parse input, format output, delegate to core

---

## Dev Notes

### Implementation Approach

1. **Create global_commands.py with subapp** - establishes CLI structure
2. **Implement duration parsing utility** - needed for `--since` filter
3. **Extend IndexManager** - add `project_name` and `since` parameters
4. **Implement list command** - wire everything together
5. **Add JSON output** - for machine-readable output
6. **Write tests** - unit and integration

### Key Design Decisions

1. **Filter by project_name, not project_path**: Users think in terms of project names, not paths
2. **Duration string format**: Use common convention (7d, 24h) instead of ISO 8601 durations
3. **Default limit of 20**: Balance between useful results and output size
4. **Offset for pagination**: Simple approach, no cursor-based pagination needed
5. **Reuse existing display code**: Follow patterns from `list.py` and `list_display.py`

### CLI Output Examples

**`adw global list` output:**
```
                     Global Runs (20 most recent)
┌────────────────────────────┬─────────────┬────────────────────────────────┬───────────┬──────────┬────────────┐
│ Run ID                     │ Project     │ Feature                        │ Status    │ Duration │ Started    │
├────────────────────────────┼─────────────┼────────────────────────────────┼───────────┼──────────┼────────────┤
│ 01KFJFZGC0GR436HE96JPS93EJ │ adw-final   │ Add user authentication...     │ completed │ 5m 32s   │ 2h ago     │
│ 01KFJFZHMFQRKFQKBP58XX26BN │ my-api      │ Fix database connection...     │ failed    │ 1m 45s   │ 5h ago     │
│ 01KFJG0KXYZABC123DEF456GH │ frontend    │ Update navigation compon...    │ running   │ 2m 14s   │ just now   │
└────────────────────────────┴─────────────┴────────────────────────────────┴───────────┴──────────┴────────────┘
```

**`adw global list --status failed --since 7d` output:**
```
                  Global Runs (failed, last 7 days)
┌────────────────────────────┬─────────────┬────────────────────────────────┬───────────┬──────────┬────────────┐
│ Run ID                     │ Project     │ Feature                        │ Status    │ Duration │ Started    │
├────────────────────────────┼─────────────┼────────────────────────────────┼───────────┼──────────┼────────────┤
│ 01KFJFZHMFQRKFQKBP58XX26BN │ my-api      │ Fix database connection...     │ failed    │ 1m 45s   │ 5h ago     │
│ 01KFJFZJKMNOPQR789STU012VW │ adw-final   │ Implement caching layer...     │ failed    │ 3m 18s   │ 2d ago     │
└────────────────────────────┴─────────────┴────────────────────────────────┴───────────┴──────────┴────────────┘
```

**Empty results:**
```
[yellow]No runs found matching filters[/]

Filters applied:
  - Project: my-api
  - Status: failed
  - Since: 7 days ago

[dim]Tip: Try broader filters or check 'adw global list' for all runs[/]
```

### Duration Formatting

```python
def _format_duration(started_at: datetime, completed_at: datetime | None) -> str:
    """Format run duration for display.

    Args:
        started_at: When run started.
        completed_at: When run completed (None if still running).

    Returns:
        Formatted duration like "5m 32s" or "running".
    """
    if completed_at is None:
        # Calculate elapsed time for running jobs
        elapsed = datetime.now(UTC) - started_at
    else:
        elapsed = completed_at - started_at

    total_seconds = int(elapsed.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"
```

### References

- [Source: _bmad-output/epics/epic-16-cross-project-dashboard.md#Story 16.2]
- [Source: src/adw/cli/app.py#line 470 - Typer subapp registration]
- [Source: src/adw/cli/list.py - Global index list implementation]
- [Source: src/adw/core/index_manager.py - Query implementation]
- [Source: src/adw/models/index.py - IndexEntry model]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 16: Cross-Project Dashboard - Story 16.2

### Agent Model Used

<!-- To be filled by implementing agent -->

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 16.1
- **Blocks:** Story 16.3, Story 16.5
- **Can Parallel With:** None

### Dependency Rationale
- Story 16.1: Requires project registry for project name resolution and filtering
- Story 16.3: Stats command builds on global list CLI group infrastructure
- Story 16.5: Dashboard's run list panel reuses global list logic
