# Story 16.5: TUI Dashboard

Status: ready
Linear Issue: not-configured
Epic: 16 - Cross-Project Dashboard
Created: 2026-01-25

---

## Story

As a user,
I want a terminal dashboard showing my ADW activity,
So that I can monitor runs visually.

## Acceptance Criteria

**Given** command `adw global dashboard`
**When** executed
**Then** a Rich-based TUI dashboard is displayed

**Given** the dashboard
**When** displayed
**Then** shows:
- Summary panel (total runs, success rate, active runs)
- Recent runs table with status indicators
- Per-project breakdown
- Token/cost summary (if data available)

**Given** active runs exist
**When** dashboard is open
**Then** status updates periodically (polling the index)

**Given** keyboard navigation
**When** user presses arrow keys
**Then** can navigate between runs and view details

**Given** command `adw global dashboard --refresh 5`
**When** executed
**Then** dashboard refreshes every 5 seconds

## Tasks / Subtasks

### Task 1: Create Dashboard Data Models
- [x] Create `DashboardState` model in `src/adw/cli/dashboard.py`:
  - `selected_run_index: int` - Currently selected run in the list
  - `selected_project: str | None` - Currently filtered project (if any)
  - `scroll_offset: int` - Scroll position for runs list
  - `last_refresh: datetime` - When data was last refreshed
  - `paused: bool` - Auto-refresh paused flag
  - `view_mode: Literal["summary", "runs", "projects"]` - Current view
- [x] Create `DashboardData` model to hold fetched data:
  - `stats: GlobalStatistics` - From StatsAggregator
  - `recent_runs: list[IndexEntry]` - From IndexManager
  - `active_runs: list[IndexEntry]` - Running runs only
- [x] Write unit tests in `tests/unit/cli/test_dashboard.py`

### Task 2: Create Dashboard Layout Components
- [x] Create `DashboardLayout` class with Rich `Layout` and `Panel` components:
  - `_create_header()` - Title bar with [Q]uit, [R]efresh hints
  - `_create_summary_panel()` - Stats cards (total runs, week, today, success rate)
  - `_create_active_runs_panel()` - Active runs section (if any)
  - `_create_recent_runs_table()` - Recent runs with status indicators
  - `_create_projects_panel()` - Per-project breakdown table
  - `_create_footer()` - Refresh status, keyboard hints
- [x] Implement status indicators:
  - `● RUNNING` - yellow with spinner animation
  - `✓ COMPLETED` - green
  - `✗ FAILED` - red
  - `⊘ INTERRUPTED` - orange/yellow
  - `⦻ ABORTED` - dim red/magenta
- [x] Write unit tests for layout generation

### Task 3: Create Dashboard Controller Class
- [x] Create `DashboardController` class in `src/adw/cli/dashboard.py`:
  - `__init__(refresh_interval: int = 30, project_filter: str | None = None)`
  - `run()` - Main event loop
  - `refresh_data()` - Fetch latest data from IndexManager and StatsAggregator
  - `handle_key(key: str)` - Process keyboard input
  - `render()` - Generate Rich renderable for current state
- [x] Integrate with `IndexManager` for run queries
- [x] Integrate with `StatsAggregator` for statistics (from Story 16.3)
- [x] Write unit tests for controller logic

### Task 4: Implement Rich Live Display
- [x] Use Rich `Live` context manager for auto-refresh display
- [x] Configure refresh rate based on `--refresh` option
- [x] Handle terminal resize events gracefully
- [x] Use `transient=False` to preserve final state on exit
- [x] Implement spinner animation for active runs using `Spinner`
- [x] Write tests for Live display lifecycle

### Task 5: Implement Keyboard Navigation
- [x] Use Rich's keyboard input or `prompt_toolkit` for input:
  - `↑/k` - Move selection up
  - `↓/j` - Move selection down
  - `Enter` - View selected run details
  - `R` - Force refresh now
  - `P` - Pause/resume auto-refresh
  - `Q/Esc` - Quit dashboard
  - `1/2/3` - Switch views (Summary/Runs/Projects)
  - `/` - Filter by project (prompt for name)
  - `Esc` - Clear filter
- [x] Handle vim-style navigation (j/k for down/up)
- [x] Display keyboard hints in footer
- [x] Write unit tests for key handling

### Task 6: Implement Run Detail View
- [x] Create `_show_run_detail(run: IndexEntry)` method:
  - Display full run information in a modal-style panel
  - Show: run_id, project, feature (full), status, phases completed
  - Show: started_at, completed_at, duration
  - Show: token usage (if available from stats)
  - Show: path to run artifacts
- [x] Allow returning to main view with `Esc` or `Q`
- [x] Write unit tests for detail view rendering

### Task 7: Implement Project Filter View
- [x] When a project is selected (via `/` or clicking project):
  - Show project-specific header with path
  - Filter runs table to that project only
  - Show project-specific statistics
  - Show status breakdown bar chart
- [x] Implement clear filter (`Esc`) to return to global view
- [x] Write tests for filtered view

### Task 8: Implement Empty State Handling
- [x] Show helpful empty state when:
  - No index file exists
  - No runs found
  - No runs match current filter
- [x] Display guidance:
  ```
  No Projects Registered

  Run `adw init` in any project
  directory to register it and
  start tracking runs globally.

  Or use: adw register
  ```
- [x] Write tests for empty state display

### Task 9: Implement `adw global dashboard` Command
- [ ] Add `dashboard` command to `src/adw/cli/global_commands.py`:
  - `--refresh, -r INT` - Refresh interval in seconds (default: 30)
  - `--project, -p NAME` - Filter to specific project initially
  - `--no-auto-refresh` - Disable auto-refresh (manual R to refresh)
- [ ] Handle graceful exit on Ctrl+C
- [ ] Show "Loading..." state while fetching initial data
- [ ] Write unit tests for command options

### Task 10: Write Integration Tests
- [ ] Test full dashboard lifecycle: start -> interact -> quit
- [ ] Test with real IndexManager data (using `ADW_TEST_INDEX_PATH`)
- [ ] Test with real StatsAggregator data (using `ADW_TEST_STATS_CACHE_PATH`)
- [ ] Test keyboard navigation simulation
- [ ] Test empty state and error handling
- [ ] Test refresh behavior
- [ ] Create integration tests in `tests/integration/cli/test_dashboard_integration.py`

### Task 11: Update Documentation
- [ ] Add comprehensive docstrings to all classes and methods
- [ ] Update `adw global dashboard --help` with examples
- [ ] Document keyboard shortcuts in help text

---

## Dependencies

- **Depends On:**
  - Story 16.1 (Project Registry) - for project list and registry data
  - Story 16.2 (Global Run List) - for `global_app` subapp and IndexManager query extensions
  - Story 16.3 (Cross-Project Statistics) - for `StatsAggregator` and statistics models
- **Blocks:** None (final story in Epic 16, Wave 4)
- **Can Parallel With:** None

### Dependency Rationale
- This story is the culmination of Epic 16, combining all previous components
- Story 16.1 provides `ProjectRegistryManager` for the per-project breakdown panel
- Story 16.2 provides `global_app` Typer subapp and extended `IndexManager.get_recent_runs()`
- Story 16.3 provides `StatsAggregator` and `GlobalStatistics` model for the summary panel
- This story combines all three to create the visual dashboard

---

## Relevant Feature Documentation

**Related Patterns:**
- Rich Live display: See `src/adw/cli/progress.py` - `ProgressDisplay` class with `Live` context
- Rich Tables: See `src/adw/cli/list_display.py` - `ListDisplay` class
- Status colors: See `src/adw/cli/status_display.py` - `STATUS_COLORS` mapping
- CLI subapp commands: See `src/adw/cli/global_commands.py` (from Story 16.2)

**Key Files to Reference:**
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/progress.py` - Rich Live usage pattern
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/list_display.py` - Table display pattern
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/status_display.py` - Status formatting
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/core/index_manager.py` - Run queries
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/models/index.py` - IndexEntry model

---

## Developer Context

### Technical Requirements

1. **Rich Components to Use**
   ```python
   from rich.console import Console
   from rich.live import Live
   from rich.layout import Layout
   from rich.panel import Panel
   from rich.table import Table
   from rich.text import Text
   from rich.spinner import Spinner
   from rich.columns import Columns
   ```

2. **Dashboard Command Structure**
   ```
   adw global dashboard [OPTIONS]

   Options:
     --refresh, -r INT     Refresh interval in seconds [default: 30]
     --project, -p NAME    Filter to specific project
     --no-auto-refresh     Disable auto-refresh (press R to refresh)
     --help                Show this message and exit
   ```

3. **Keyboard Input Handling**
   - Primary option: Rich doesn't have built-in keyboard handling
   - Use `keyboard` library or `prompt_toolkit` for cross-platform input
   - Alternative: Simple `input()` polling in background thread
   - Fallback: No keyboard nav, just auto-refresh and Ctrl+C to exit

4. **Display Layout Structure**
   ```
   ┌─────────────────────────────────────────────────────────────────┐
   │ Header: Title + Keyboard Hints                                  │
   ├─────────────────────────────────────────────────────────────────┤
   │ Summary Panel: Stats Cards (total, week, today, success rate)   │
   ├─────────────────────────────────────────────────────────────────┤
   │ Active Runs Panel (if any running)                              │
   ├─────────────────────────────────────────────────────────────────┤
   │ Recent Runs Table (scrollable, selectable)                      │
   ├─────────────────────────────────────────────────────────────────┤
   │ Per-Project Breakdown Table                                     │
   ├─────────────────────────────────────────────────────────────────┤
   │ Footer: Refresh status + Keyboard hints                         │
   └─────────────────────────────────────────────────────────────────┘
   ```

### Architecture Compliance

**File Locations:**
```
src/adw/
├── cli/
│   ├── dashboard.py         # NEW: Dashboard module
│   └── global_commands.py   # MODIFY: Add dashboard command
tests/
├── unit/cli/
│   └── test_dashboard.py    # NEW: Unit tests
└── integration/cli/
    └── test_dashboard_integration.py  # NEW: Integration tests
```

**Dashboard Module Structure:**
```python
# src/adw/cli/dashboard.py
"""TUI Dashboard for cross-project ADW monitoring.

This module provides an interactive terminal dashboard for viewing
ADW runs across all projects using Rich Live display.

Features:
- Summary statistics (total runs, success rate, active runs)
- Recent runs table with status indicators
- Per-project breakdown
- Auto-refresh with configurable interval
- Keyboard navigation
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from adw.core.index_manager import IndexManager
    from adw.core.stats_aggregator import StatsAggregator
    from adw.models.index import IndexEntry
    from adw.models.stats import GlobalStatistics

__all__ = ["DashboardController", "run_dashboard"]


# Status indicators matching epic mockups
STATUS_INDICATORS: dict[str, tuple[str, str]] = {
    "running": ("●", "yellow"),
    "completed": ("✓", "green"),
    "failed": ("✗", "red"),
    "interrupted": ("⊘", "orange1"),
    "aborted": ("⦻", "bright_black"),
}


@dataclass
class DashboardState:
    """Mutable state for dashboard interaction."""
    selected_run_index: int = 0
    selected_project: str | None = None
    scroll_offset: int = 0
    last_refresh: datetime = field(default_factory=lambda: datetime.now(UTC))
    paused: bool = False
    view_mode: Literal["summary", "runs", "projects"] = "summary"
    quit_requested: bool = False


@dataclass
class DashboardData:
    """Cached data for dashboard display."""
    stats: GlobalStatistics | None = None
    recent_runs: list[IndexEntry] = field(default_factory=list)
    active_runs: list[IndexEntry] = field(default_factory=list)
    error: str | None = None


class DashboardLayout:
    """Generates Rich renderables for dashboard layout."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def create_header(self, title: str = "ADW GLOBAL DASHBOARD") -> Panel:
        """Create dashboard header with title and keyboard hints."""
        header_text = Text()
        header_text.append(title, style="bold white")
        header_text.append("  ", style="dim")
        header_text.append("[Q]", style="bold cyan")
        header_text.append("uit  ", style="dim")
        header_text.append("[R]", style="bold cyan")
        header_text.append("efresh", style="dim")

        return Panel(
            header_text,
            style="bold",
            border_style="blue",
        )

    def create_summary_panel(
        self,
        stats: GlobalStatistics | None,
    ) -> Panel:
        """Create summary panel with stats cards."""
        if stats is None:
            return Panel(
                "[dim]Loading statistics...[/]",
                title="SUMMARY",
                border_style="blue",
            )

        # Format success rate
        success_pct = f"{stats.success_rate * 100:.1f}%"

        # Format tokens
        total_tokens = stats.tokens.total_tokens
        if total_tokens >= 1_000_000:
            tokens_str = f"{total_tokens / 1_000_000:.1f}M"
        elif total_tokens >= 1_000:
            tokens_str = f"{total_tokens / 1_000:.1f}K"
        else:
            tokens_str = str(total_tokens)

        # Format cost
        cost_str = f"${stats.estimated_cost:.2f}"

        # Format average duration
        avg_ms = stats.average_duration_ms
        if avg_ms > 0:
            avg_min = avg_ms // 60000
            avg_sec = (avg_ms % 60000) // 1000
            duration_str = f"{avg_min}m {avg_sec}s"
        else:
            duration_str = "—"

        # Build summary content
        content = Text()
        content.append("\n")
        content.append("   TOTAL RUNS     ", style="bold")
        content.append("   THIS WEEK      ", style="bold")
        content.append("      TODAY       ", style="bold")
        content.append("  SUCCESS RATE\n", style="bold")
        content.append(f"     {stats.total_runs:,}           ", style="cyan bold")
        content.append(f"     {stats.runs_this_week}             ", style="cyan")
        content.append(f"      {stats.runs_today}             ", style="cyan")
        content.append(f"    {success_pct}\n", style="green bold")
        content.append("\n")
        content.append(f"   AVG DURATION: {duration_str}", style="dim")
        content.append("    │    ", style="dim")
        content.append(f"TOTAL TOKENS: {tokens_str}", style="dim")
        content.append("    │    ", style="dim")
        content.append(f"EST. COST: {cost_str}", style="dim")
        content.append("\n")

        return Panel(
            content,
            title="SUMMARY",
            border_style="blue",
        )

    def create_active_runs_panel(
        self,
        active_runs: list[IndexEntry],
    ) -> Panel | None:
        """Create active runs panel if any runs are active."""
        if not active_runs:
            return None

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Status", width=2)
        table.add_column("ID", width=10)
        table.add_column("Project", width=15)
        table.add_column("Feature", max_width=35)
        table.add_column("Duration", width=10)
        table.add_column("Tokens", width=10)

        for run in active_runs:
            # Calculate elapsed time
            elapsed = datetime.now(UTC) - run.started_at
            elapsed_min = int(elapsed.total_seconds()) // 60
            elapsed_sec = int(elapsed.total_seconds()) % 60
            duration = f"{elapsed_min}m {elapsed_sec:02d}s"

            # Truncate feature
            feature = run.feature_description
            if len(feature) > 32:
                feature = feature[:29] + "..."

            table.add_row(
                "[yellow]●[/]",
                run.run_id[:8] + "...",
                run.project_name,
                feature,
                f"[yellow]◐[/]  {duration}",
                "—",  # Tokens not available during run
            )

        return Panel(
            table,
            title=f"ACTIVE RUNS ({len(active_runs)})",
            border_style="yellow",
        )

    def create_recent_runs_table(
        self,
        runs: list[IndexEntry],
        selected_index: int = 0,
        max_rows: int = 6,
    ) -> Panel:
        """Create recent runs table with selection highlight."""
        if not runs:
            return Panel(
                "[dim]No recent runs[/]",
                title="RECENT RUNS",
                border_style="blue",
            )

        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("RUN ID", style="cyan", no_wrap=True, width=12)
        table.add_column("PROJECT", width=15)
        table.add_column("FEATURE", max_width=30)
        table.add_column("STATUS", justify="center", width=12)
        table.add_column("DURATION", width=10)
        table.add_column("STARTED", style="dim", width=12)

        for i, run in enumerate(runs[:max_rows]):
            # Status indicator
            indicator, color = STATUS_INDICATORS.get(
                run.status, ("?", "white")
            )
            status_text = f"[{color}]{indicator} {run.status.upper()}[/]"

            # Duration
            if run.completed_at:
                delta = run.completed_at - run.started_at
                total_sec = int(delta.total_seconds())
                duration = f"{total_sec // 60}m {total_sec % 60:02d}s"
            else:
                elapsed = datetime.now(UTC) - run.started_at
                total_sec = int(elapsed.total_seconds())
                duration = f"{total_sec // 60}m {total_sec % 60:02d}s"

            # Relative time
            age = datetime.now(UTC) - run.started_at
            if age.total_seconds() < 60:
                started = "just now"
            elif age.total_seconds() < 3600:
                started = f"{int(age.total_seconds() // 60)} min ago"
            elif age.total_seconds() < 86400:
                started = f"{int(age.total_seconds() // 3600)}h ago"
            else:
                started = f"{int(age.total_seconds() // 86400)}d ago"

            # Truncate feature
            feature = run.feature_description
            if len(feature) > 27:
                feature = feature[:24] + "..."

            # Highlight selected row
            if i == selected_index:
                table.add_row(
                    f"[bold reverse]{run.run_id[:10]}[/]",
                    f"[bold]{run.project_name}[/]",
                    f"[bold]{feature}[/]",
                    status_text,
                    duration,
                    started,
                )
            else:
                table.add_row(
                    run.run_id[:10] + "..",
                    run.project_name,
                    feature,
                    status_text,
                    duration,
                    started,
                )

        footer = (
            "[dim][↑/↓] Navigate   [Enter] View Details   [Page↓] More[/]"
        )

        return Panel(
            table,
            title=f"RECENT RUNS ({len(runs)} total)",
            subtitle=footer,
            border_style="blue",
        )

    def create_projects_panel(
        self,
        stats: GlobalStatistics | None,
    ) -> Panel:
        """Create per-project breakdown table."""
        if stats is None or not stats.projects:
            return Panel(
                "[dim]No project data available[/]",
                title="PER-PROJECT BREAKDOWN",
                border_style="blue",
            )

        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("PROJECT", width=15)
        table.add_column("PATH", max_width=35, style="dim")
        table.add_column("RUNS", justify="right", width=7)
        table.add_column("SUCCESS", justify="right", width=9)
        table.add_column("TOKENS", justify="right", width=10)
        table.add_column("COST", justify="right", width=9)

        for proj in stats.projects:
            # Format path (truncate from left)
            path = proj.path
            if len(path) > 32:
                path = "..." + path[-29:]

            # Format tokens
            tokens = proj.tokens.total_tokens
            if tokens >= 1_000_000:
                tokens_str = f"{tokens / 1_000_000:.1f}M"
            elif tokens >= 1_000:
                tokens_str = f"{tokens / 1_000:.1f}K"
            else:
                tokens_str = str(tokens)

            # Format success rate
            success_str = f"{proj.success_rate * 100:.1f}%"

            # Format cost
            cost_str = f"${proj.estimated_cost:.2f}"

            table.add_row(
                proj.name,
                path,
                str(proj.total_runs),
                success_str,
                tokens_str,
                cost_str,
            )

        return Panel(
            table,
            title="PER-PROJECT BREAKDOWN",
            border_style="blue",
        )

    def create_footer(
        self,
        last_refresh: datetime,
        paused: bool,
        refresh_interval: int,
    ) -> Text:
        """Create footer with refresh status."""
        footer = Text()

        # Refresh status
        age = datetime.now(UTC) - last_refresh
        if age.total_seconds() < 60:
            age_str = f"{int(age.total_seconds())}s ago"
        else:
            age_str = f"{int(age.total_seconds() // 60)}m ago"

        footer.append(f"  Last refreshed: {age_str}", style="dim")
        footer.append("    ", style="dim")

        if paused:
            footer.append("[P]aused", style="yellow")
        else:
            footer.append(f"Auto-refresh: {refresh_interval}s", style="dim")
            footer.append("  ", style="dim")
            footer.append("[P]ause", style="dim")

        return footer

    def create_empty_state(self) -> Panel:
        """Create empty state display."""
        content = Text()
        content.append("\n\n")
        content.append("          No Projects Registered\n\n", style="bold yellow")
        content.append("    ┌────────────────────────────────────────┐\n", style="dim")
        content.append("    │                                        │\n", style="dim")
        content.append("    │     Run `adw init` in any project      │\n", style="dim")
        content.append("    │     directory to register it and       │\n", style="dim")
        content.append("    │     start tracking runs globally.      │\n", style="dim")
        content.append("    │                                        │\n", style="dim")
        content.append("    │     Or use: adw register               │\n", style="dim")
        content.append("    │                                        │\n", style="dim")
        content.append("    └────────────────────────────────────────┘\n", style="dim")
        content.append("\n\n")

        return Panel(
            content,
            title="ADW GLOBAL DASHBOARD",
            border_style="yellow",
        )


class DashboardController:
    """Controls dashboard state and rendering.

    Manages data fetching, state updates, and keyboard handling
    for the interactive TUI dashboard.

    Attributes:
        console: Rich Console for output.
        index_manager: IndexManager for run queries.
        stats_aggregator: StatsAggregator for statistics.
        refresh_interval: Seconds between auto-refreshes.
        project_filter: Optional project name filter.

    Example:
        >>> controller = DashboardController(refresh_interval=30)
        >>> controller.run()  # Blocks until quit
    """

    def __init__(
        self,
        console: Console | None = None,
        index_manager: IndexManager | None = None,
        stats_aggregator: StatsAggregator | None = None,
        refresh_interval: int = 30,
        project_filter: str | None = None,
    ) -> None:
        """Initialize the DashboardController.

        Args:
            console: Rich Console for output.
            index_manager: Optional IndexManager instance.
            stats_aggregator: Optional StatsAggregator instance.
            refresh_interval: Seconds between auto-refreshes.
            project_filter: Optional initial project filter.
        """
        from adw.core.index_manager import IndexManager
        from adw.core.stats_aggregator import StatsAggregator

        self.console = console or Console()
        self.index_manager = index_manager or IndexManager()
        self.stats_aggregator = stats_aggregator or StatsAggregator(
            index_manager=self.index_manager
        )
        self.refresh_interval = refresh_interval
        self.project_filter = project_filter

        self.state = DashboardState()
        self.data = DashboardData()
        self.layout = DashboardLayout(self.console)

        if project_filter:
            self.state.selected_project = project_filter

    def refresh_data(self) -> None:
        """Fetch latest data from IndexManager and StatsAggregator."""
        try:
            # Fetch recent runs
            self.data.recent_runs = self.index_manager.get_recent_runs(
                limit=50,
                project_name=self.state.selected_project,
            )

            # Separate active runs
            self.data.active_runs = [
                r for r in self.data.recent_runs if r.status == "running"
            ]

            # Fetch statistics
            self.data.stats = self.stats_aggregator.get_global_stats(
                project_name=self.state.selected_project,
            )

            self.data.error = None
            self.state.last_refresh = datetime.now(UTC)

        except Exception as e:
            self.data.error = str(e)

    def render(self) -> Layout:
        """Generate Rich Layout for current state.

        Returns:
            Rich Layout renderable for the dashboard.
        """
        # Check for empty state
        if not self.data.recent_runs and not self.data.stats:
            # Show empty state
            return self.layout.create_empty_state()

        # Build layout
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="summary", size=7),
            Layout(name="body"),
            Layout(name="footer", size=1),
        )

        # Header
        layout["header"].update(self.layout.create_header())

        # Summary panel
        layout["summary"].update(
            self.layout.create_summary_panel(self.data.stats)
        )

        # Body: active runs (if any) + recent runs + projects
        body_parts = []

        # Active runs panel (optional)
        active_panel = self.layout.create_active_runs_panel(
            self.data.active_runs
        )
        if active_panel:
            body_parts.append(Layout(active_panel, name="active", size=5))

        # Recent runs table
        body_parts.append(
            Layout(
                self.layout.create_recent_runs_table(
                    self.data.recent_runs,
                    self.state.selected_run_index,
                ),
                name="runs",
            )
        )

        # Projects panel
        body_parts.append(
            Layout(
                self.layout.create_projects_panel(self.data.stats),
                name="projects",
                size=10,
            )
        )

        if len(body_parts) == 2:
            layout["body"].split_column(*body_parts)
        else:
            layout["body"].split_column(*body_parts)

        # Footer
        layout["footer"].update(
            self.layout.create_footer(
                self.state.last_refresh,
                self.state.paused,
                self.refresh_interval,
            )
        )

        return layout

    def handle_key(self, key: str) -> bool:
        """Process keyboard input.

        Args:
            key: Key pressed (single character or special key name).

        Returns:
            True if dashboard should continue, False to quit.
        """
        key_lower = key.lower()

        if key_lower in ("q", "escape"):
            return False

        if key_lower == "r":
            self.refresh_data()

        elif key_lower == "p":
            self.state.paused = not self.state.paused

        elif key_lower in ("j", "down"):
            max_index = len(self.data.recent_runs) - 1
            self.state.selected_run_index = min(
                self.state.selected_run_index + 1, max_index
            )

        elif key_lower in ("k", "up"):
            self.state.selected_run_index = max(
                self.state.selected_run_index - 1, 0
            )

        elif key_lower == "1":
            self.state.view_mode = "summary"

        elif key_lower == "2":
            self.state.view_mode = "runs"

        elif key_lower == "3":
            self.state.view_mode = "projects"

        return True

    def run(self) -> None:
        """Run the dashboard event loop.

        Blocks until user quits (Q or Ctrl+C).
        """
        # Initial data fetch
        self.refresh_data()

        # For simplicity, use Rich Live without keyboard input
        # Keyboard input requires additional dependencies or threading
        try:
            with Live(
                self.render(),
                console=self.console,
                refresh_per_second=4,
                screen=True,
            ) as live:
                last_refresh_time = time.time()

                while not self.state.quit_requested:
                    # Check if refresh needed
                    if not self.state.paused:
                        elapsed = time.time() - last_refresh_time
                        if elapsed >= self.refresh_interval:
                            self.refresh_data()
                            last_refresh_time = time.time()

                    # Update display
                    live.update(self.render())

                    # Sleep briefly to avoid CPU spin
                    time.sleep(0.25)

        except KeyboardInterrupt:
            # Clean exit on Ctrl+C
            pass


def run_dashboard(
    refresh_interval: int = 30,
    project_filter: str | None = None,
    no_auto_refresh: bool = False,
) -> None:
    """Run the dashboard (entry point for CLI command).

    Args:
        refresh_interval: Seconds between auto-refreshes.
        project_filter: Optional project name filter.
        no_auto_refresh: If True, disable auto-refresh.
    """
    console = Console()

    # Show loading message
    console.print("[dim]Loading dashboard...[/]")

    controller = DashboardController(
        console=console,
        refresh_interval=refresh_interval if not no_auto_refresh else 999999,
        project_filter=project_filter,
    )

    controller.run()

    console.print("\n[dim]Dashboard closed.[/]")
```

**CLI Command Pattern (add to global_commands.py):**
```python
@global_app.command(name="dashboard")
def dashboard_command(
    refresh: int = typer.Option(
        30,
        "--refresh",
        "-r",
        help="Refresh interval in seconds",
        min=1,
        max=300,
    ),
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Filter to specific project",
    ),
    no_auto_refresh: bool = typer.Option(
        False,
        "--no-auto-refresh",
        help="Disable auto-refresh (press R to refresh manually)",
    ),
) -> None:
    """Interactive TUI dashboard for cross-project monitoring.

    Displays a live terminal dashboard showing:
    - Summary statistics (total runs, success rate, active runs)
    - Recent runs with status indicators
    - Per-project breakdown with token/cost data

    The dashboard auto-refreshes periodically. Press Q to quit.

    Examples:
        adw global dashboard                    # Default 30s refresh
        adw global dashboard --refresh 10       # Refresh every 10 seconds
        adw global dashboard --project my-api   # Filter to one project
        adw global dashboard --no-auto-refresh  # Manual refresh only
    """
    from adw.cli.dashboard import run_dashboard

    run_dashboard(
        refresh_interval=refresh,
        project_filter=project,
        no_auto_refresh=no_auto_refresh,
    )
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Rich | 14.1.0 | Live display, Layout, Panel, Table, Spinner |
| Typer | 0.21.0 | CLI command |
| Pydantic | 2.12+ | Data models |

**No New Dependencies Required**

Rich already includes all needed components: `Live`, `Layout`, `Panel`, `Table`, `Spinner`, `Text`, `Columns`.

Note: Full keyboard navigation would require additional dependencies like `keyboard` or `prompt_toolkit`. The initial implementation uses auto-refresh only with Ctrl+C to exit. Keyboard navigation can be added as an enhancement.

### File Structure Requirements

**New Files:**
- `src/adw/cli/dashboard.py` - Dashboard module
- `tests/unit/cli/test_dashboard.py` - Unit tests
- `tests/integration/cli/test_dashboard_integration.py` - Integration tests

**Modified Files:**
- `src/adw/cli/global_commands.py` - Add `dashboard` command

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/cli/test_dashboard.py
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from adw.cli.dashboard import (
    DashboardController,
    DashboardData,
    DashboardLayout,
    DashboardState,
    STATUS_INDICATORS,
)


class TestDashboardState:
    def test_default_values(self):
        """State has sensible defaults."""
        state = DashboardState()
        assert state.selected_run_index == 0
        assert state.selected_project is None
        assert state.paused is False
        assert state.view_mode == "summary"
        assert state.quit_requested is False

    def test_mutable_state(self):
        """State is mutable."""
        state = DashboardState()
        state.selected_run_index = 5
        state.paused = True
        assert state.selected_run_index == 5
        assert state.paused is True


class TestDashboardLayout:
    def test_create_header(self):
        """Header contains title and keyboard hints."""
        layout = DashboardLayout(Console())
        header = layout.create_header()
        assert header is not None

    def test_create_summary_panel_with_stats(self, sample_global_stats):
        """Summary panel displays statistics."""
        layout = DashboardLayout(Console())
        panel = layout.create_summary_panel(sample_global_stats)
        assert panel is not None
        assert "SUMMARY" in str(panel.title)

    def test_create_summary_panel_loading(self):
        """Summary panel shows loading when stats is None."""
        layout = DashboardLayout(Console())
        panel = layout.create_summary_panel(None)
        assert "Loading" in str(panel.renderable)

    def test_create_empty_state(self):
        """Empty state shows helpful message."""
        layout = DashboardLayout(Console())
        panel = layout.create_empty_state()
        assert "No Projects Registered" in str(panel.renderable)

    def test_status_indicators_complete(self):
        """All statuses have indicators defined."""
        expected = {"running", "completed", "failed", "interrupted", "aborted"}
        assert set(STATUS_INDICATORS.keys()) == expected


class TestDashboardController:
    def test_init_with_defaults(self):
        """Controller initializes with default dependencies."""
        with patch("adw.cli.dashboard.IndexManager"):
            with patch("adw.cli.dashboard.StatsAggregator"):
                controller = DashboardController()
                assert controller.refresh_interval == 30
                assert controller.project_filter is None

    def test_init_with_project_filter(self):
        """Controller accepts project filter."""
        with patch("adw.cli.dashboard.IndexManager"):
            with patch("adw.cli.dashboard.StatsAggregator"):
                controller = DashboardController(project_filter="my-api")
                assert controller.project_filter == "my-api"
                assert controller.state.selected_project == "my-api"

    def test_handle_key_quit(self):
        """Q key returns False to quit."""
        with patch("adw.cli.dashboard.IndexManager"):
            with patch("adw.cli.dashboard.StatsAggregator"):
                controller = DashboardController()
                assert controller.handle_key("q") is False
                assert controller.handle_key("Q") is False

    def test_handle_key_refresh(self):
        """R key triggers refresh."""
        with patch("adw.cli.dashboard.IndexManager"):
            with patch("adw.cli.dashboard.StatsAggregator"):
                controller = DashboardController()
                controller.refresh_data = MagicMock()
                assert controller.handle_key("r") is True
                controller.refresh_data.assert_called_once()

    def test_handle_key_pause(self):
        """P key toggles pause."""
        with patch("adw.cli.dashboard.IndexManager"):
            with patch("adw.cli.dashboard.StatsAggregator"):
                controller = DashboardController()
                assert controller.state.paused is False
                controller.handle_key("p")
                assert controller.state.paused is True
                controller.handle_key("p")
                assert controller.state.paused is False

    def test_handle_key_navigation(self, sample_index_entries):
        """Arrow keys navigate selection."""
        with patch("adw.cli.dashboard.IndexManager"):
            with patch("adw.cli.dashboard.StatsAggregator"):
                controller = DashboardController()
                controller.data.recent_runs = sample_index_entries

                # Move down
                controller.handle_key("j")
                assert controller.state.selected_run_index == 1

                # Move up
                controller.handle_key("k")
                assert controller.state.selected_run_index == 0

                # Can't go below 0
                controller.handle_key("k")
                assert controller.state.selected_run_index == 0


@pytest.fixture
def sample_global_stats():
    """Create sample GlobalStatistics for testing."""
    from adw.models.stats import GlobalStatistics, ProjectStatistics, TokenUsage

    return GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=100,
        runs_this_week=25,
        runs_today=5,
        completed_runs=90,
        failed_runs=10,
        success_rate=0.9,
        average_duration_ms=300000,
        tokens=TokenUsage(input_tokens=1000000, output_tokens=200000),
        estimated_cost=45.50,
        projects=[
            ProjectStatistics(
                name="my-api",
                path="/path/to/my-api",
                total_runs=50,
                success_rate=0.92,
                tokens=TokenUsage(input_tokens=500000, output_tokens=100000),
                estimated_cost=22.50,
            )
        ],
    )


@pytest.fixture
def sample_index_entries():
    """Create sample IndexEntry list for testing."""
    from adw.models.index import IndexEntry

    return [
        IndexEntry(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            project_path="/path/to/my-api",
            project_name="my-api",
            feature_description="Add user authentication",
            started_at=datetime.now(UTC),
            status="completed",
            phases_completed=["plan", "build", "validate"],
        ),
        IndexEntry(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3D",
            project_path="/path/to/frontend",
            project_name="frontend",
            feature_description="Fix navigation bug",
            started_at=datetime.now(UTC),
            status="running",
            phases_completed=["plan"],
        ),
    ]
```

**Test Coverage Target:** >80%

---

## Previous Story Intelligence

**From Story 16.1 (Project Registry):**
- `ProjectRegistryManager` at `src/adw/core/project_registry.py`
- Registry file: `~/.adw/projects.yaml`
- `get_all()` returns list of `RegisteredProject` with `path`, `name`, `registered_at`
- Environment variable: `ADW_TEST_REGISTRY_PATH`

**From Story 16.2 (Global Run List):**
- `global_app` Typer subapp in `src/adw/cli/global_commands.py`
- `IndexManager.get_recent_runs()` with `project_name` and `since` filters
- Duration parsing: `parse_duration("7d")` returns datetime threshold
- Status color mapping: running=yellow, completed=green, failed=red, interrupted=orange1, aborted=bright_black

**From Story 16.3 (Cross-Project Statistics):**
- `StatsAggregator` at `src/adw/core/stats_aggregator.py`
- `GlobalStatistics` model with: total_runs, runs_this_week, runs_today, success_rate, tokens, estimated_cost, projects
- `ProjectStatistics` model for per-project breakdown
- `TokenUsage` model with input_tokens, output_tokens, total_tokens property
- Environment variable: `ADW_TEST_STATS_CACHE_PATH`

**Rich Live Pattern (from progress.py):**
```python
from rich.live import Live
from rich.progress import Progress

self._live = Live(self._progress, console=self.console, refresh_per_second=4)
self._live.start()
# ... update display ...
self._live.stop()
```

---

## Git Intelligence

**Recent Relevant Commits:**
- Story 16.3: Cross-project statistics with StatsAggregator
- Story 16.2: Global run list command with filters
- Story 16.1: Project registry and CLI commands
- Story 5.5: ProgressDisplay with Rich Live

**Established Patterns:**
- Rich Live for dynamic displays (progress.py)
- Status color mappings consistent across CLI
- Environment variables for test path overrides
- Dataclass for mutable state tracking
- Pydantic models for data transfer objects

---

## Latest Technical Information

**Rich Layout (2025):**
- `Layout` for complex terminal layouts with named regions
- `Layout.split_column()` and `Layout.split_row()` for divisions
- `Layout["name"].update(renderable)` to update regions
- Works well with `Live` for dynamic updates

**Rich Live Best Practices:**
- Use `screen=True` for full-screen takeover
- Use `refresh_per_second=4` for smooth updates without CPU overhead
- Use `transient=False` (default) to preserve final output
- Handle `KeyboardInterrupt` for clean Ctrl+C exit

**Keyboard Input Options:**
- `keyboard` library - cross-platform but requires root on Linux
- `prompt_toolkit` - full-featured but heavyweight
- `getch` - simple but platform-specific
- Rich doesn't have built-in keyboard input
- Recommendation: Start with auto-refresh only, add keyboard later

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Rich for CLI output**: Use Rich Console, Live, Panel, Table
- **Type annotations required**: All functions fully typed
- **CLI boundary**: Parse input, format output, delegate to core
- **Structured logging**: Use logger with structured fields
- **Context managers**: Use for Live display lifecycle

---

## Dev Notes

### Implementation Approach

1. **Start with DashboardLayout class** - Build static renders first
2. **Create DashboardController** - Wire up data fetching
3. **Implement Rich Live display** - Basic auto-refresh
4. **Add CLI command** - Wire into global_app
5. **Test extensively** - Unit and integration tests
6. **Add keyboard navigation** - Enhancement if time permits

### Key Design Decisions

1. **Rich Live over Textual**: Rich is already in the project; Textual would add a new dependency. Start simple with Rich Live, upgrade to Textual later if needed.

2. **Auto-refresh First**: Keyboard input requires additional complexity (threading, platform-specific code). Initial implementation uses auto-refresh with Ctrl+C to exit.

3. **Stateful Controller**: DashboardController holds state (selection, filter, pause) separate from data (runs, stats). This separation enables testing.

4. **Layout Composition**: DashboardLayout generates individual panels that DashboardController composes into the full Layout. This enables unit testing of individual components.

5. **Spinner Animation**: Use Rich Spinner for active runs status indicator to show activity.

### Visual Design Reference (ASCII Mockups)

#### Main Dashboard View
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                              ADW GLOBAL DASHBOARD                                    [Q]uit    ┃
┃                              ════════════════════                                    [R]efresh ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ SUMMARY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃   ╭─────────────────╮  ╭─────────────────╮  ╭─────────────────╮  ╭─────────────────╮           ┃
┃   │   TOTAL RUNS    │  │   THIS WEEK     │  │     TODAY       │  │  SUCCESS RATE   │           ┃
┃   │                 │  │                 │  │                 │  │                 │           ┃
┃   │      1,247      │  │       89        │  │       12        │  │     94.3%       │           ┃
┃   │                 │  │                 │  │                 │  │   ████████░░    │           ┃
┃   ╰─────────────────╯  ╰─────────────────╯  ╰─────────────────╯  ╰─────────────────╯           ┃
┃                                                                                                ┃
┃   AVG DURATION: 4m 23s    │    TOTAL TOKENS: 2.4M    │    EST. COST: $47.82                    ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ RECENT RUNS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃  RUN ID      PROJECT          FEATURE                      STATUS       DURATION    STARTED   ┃
┃  ─────────────────────────────────────────────────────────────────────────────────────────────  ┃
┃  a7f3c2e1    adw-final        Add user authentication...   ● RUNNING       2m 14s   just now  ┃
┃  b8e4d3f2    myapp-backend    Fix database connection...   ✓ COMPLETED     5m 32s   5 min ago ┃
┃  c9f5e4a3    adw-final        Implement caching layer...   ✓ COMPLETED     3m 18s   12 min ago┃
┃  d0a6f5b4    frontend-ui      Update navigation compo...   ✗ FAILED        1m 45s   18 min ago┃
┃  e1b7a6c5    myapp-backend    Add rate limiting middl...   ✓ COMPLETED     4m 52s   25 min ago┃
┃  f2c8b7d6    adw-final        Refactor error handling...   ⊘ INTERRUPTED   6m 03s   32 min ago┃
┃                                                                                                ┃
┃                          [↑/↓] Navigate   [Enter] View Details   [Page↓] More                  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━ PER-PROJECT BREAKDOWN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃  PROJECT            PATH                              RUNS    SUCCESS    TOKENS     COST       ┃
┃  ─────────────────────────────────────────────────────────────────────────────────────────────  ┃
┃  adw-final          ~/Developer/Projects/adw/adw...    423      96.2%     892K    $18.24       ┃
┃  myapp-backend      ~/Developer/Projects/myapp-b...    512      93.8%     1.1M    $21.45       ┃
┃  frontend-ui        ~/Developer/Projects/frontend...   312      91.7%     412K     $8.13       ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Last refreshed: 2s ago                                                   Auto-refresh: 30s [P]ause
```

#### Filtered by Project View
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━ PROJECT: adw-final ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃   Path: /Users/dev/Projects/adw/adw-final                                       [Esc] Clear   ┃
┃                                                                                                ┃
┃   ╭──────────────╮  ╭──────────────╮  ╭──────────────╮  ╭──────────────╮  ╭──────────────╮     ┃
┃   │    RUNS      │  │  THIS WEEK   │  │    TODAY     │  │   SUCCESS    │  │  AVG DURATION│     ┃
┃   │     423      │  │      34      │  │      5       │  │    96.2%     │  │    3m 47s    │     ┃
┃   ╰──────────────╯  ╰──────────────╯  ╰──────────────╯  ╰──────────────╯  ╰──────────────╯     ┃
┃                                                                                                ┃
┃   TOKENS: 892,341 (input: 743,892 / output: 148,449)         EST. COST: $18.24                 ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ STATUS BREAKDOWN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃   ✓ COMPLETED     407  ████████████████████████████████████████████████░░░░░░   96.2%          ┃
┃   ✗ FAILED          9  ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    2.1%          ┃
┃   ⊘ INTERRUPTED     6  █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    1.4%          ┃
┃   ⦻ ABORTED         1  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    0.2%          ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### Empty State
```
                         ╭────────────────────────────────────────────────╮
                         │                                                │
                         │            No Projects Registered              │
                         │                                                │
                         │   ┌────────────────────────────────────────┐   │
                         │   │                                        │   │
                         │   │     Run `adw init` in any project      │   │
                         │   │     directory to register it and       │   │
                         │   │     start tracking runs globally.      │   │
                         │   │                                        │   │
                         │   │     Or use: adw register               │   │
                         │   │                                        │   │
                         │   └────────────────────────────────────────┘   │
                         │                                                │
                         ╰────────────────────────────────────────────────╯
```

#### Active Runs State
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━ ACTIVE RUNS (2) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃  ● a7f3c2e1 │ adw-final      │ Add user authentication flow...      │ ◐  2m 14s │ 12.4K tok   ┃
┃  ● x2y9z8w7 │ myapp-backend  │ Implement webhook endpoint for...    │ ◑  0m 47s │  3.1K tok   ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### Keyboard Shortcuts Reference
```
  NAVIGATION                      ACTIONS                         VIEWS
  ──────────────────────────────────────────────────────────────────────────
  ↑/k      Move up                Enter    View run details       1    Summary
  ↓/j      Move down              R        Refresh now            2    Runs list
  PgUp     Page up                P        Pause/resume refresh   3    Projects
  PgDn     Page down              /        Filter by project
  Home     Go to top              Esc      Clear filter
  End      Go to bottom           Q        Quit dashboard
```

#### Status Indicators
```
  ● RUNNING      Active ADW session in progress (yellow, animated spinner)
  ✓ COMPLETED    Successfully finished (green)
  ✗ FAILED       Terminated with error (red)
  ⊘ INTERRUPTED  User cancelled mid-run (orange)
  ⦻ ABORTED      System/crash termination (dim red)
```

### Enhancement Roadmap

If time permits or as future work:

1. **Keyboard Navigation** - Add `keyboard` or `prompt_toolkit` for interactive navigation
2. **Run Detail Modal** - Show full run details when Enter is pressed
3. **Project Filter Prompt** - Press `/` to filter by typing project name
4. **Textual Migration** - Upgrade to Textual for richer TUI if needed

### References

- [Source: _bmad-output/epics/epic-16-cross-project-dashboard.md#Story 16.5]
- [Source: _bmad-output/epics/epic-16-cross-project-dashboard.md#Visual Design Reference]
- [Source: src/adw/cli/progress.py - Rich Live usage pattern]
- [Source: src/adw/cli/list_display.py - Table display pattern]
- [Source: src/adw/cli/status_display.py - Status formatting]
- [Source: _bmad-output/implementation-artifacts/16-3-cross-project-statistics.md - StatsAggregator]
- [Source: _bmad-output/implementation-artifacts/16-2-global-run-list.md - global_app pattern]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 16: Cross-Project Dashboard - Story 16.5 (Final Story)

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created DashboardState and DashboardData dataclass models in src/adw/cli/dashboard.py with proper type annotations and documentation. Added 7 unit tests covering default values, mutability, and state management.
- Task 2: Implemented full DashboardLayout class with 8 methods for Rich renderable generation (header, summary, active runs, recent runs table, projects panel, footer, empty state). Added STATUS_INDICATORS dictionary. Added 13 new unit tests for layout components.
- Task 3: Implemented DashboardController class with refresh_data(), handle_key(), and render() methods. Integrated IndexManager and StatsAggregator for data fetching. Added 14 unit tests for controller logic.
- Task 4: Implemented run() method with Rich Live display, auto-refresh loop, and keyboard input handling. Added run_dashboard() entry point function. Added 8 unit tests for Live display lifecycle.
- Task 5: Extended handle_key() with vim-style navigation (j/k), view mode switching (1/2/3), and Escape key support. Added 6 unit tests for keyboard navigation.
- Task 6: Added create_run_detail() method to DashboardLayout for modal-style run detail view. Added show_run_detail flag to DashboardState. Updated render() to show detail view. Added 4 unit tests.
- Task 7: Extended create_header() to show project filter indicator with yellow border. Added 1 unit test.
- Task 8: Empty state already implemented in Task 2 (create_empty_state method and test).

### File List

- src/adw/cli/dashboard.py (modified)
- tests/unit/cli/test_dashboard.py (modified)

---

## Dependencies

- **Depends On:** Story 16.1, Story 16.2, Story 16.3
- **Blocks:** None
- **Can Parallel With:** None

### Dependency Rationale
- Story 16.1: Dashboard displays registered projects in per-project breakdown
- Story 16.2: Dashboard reuses global list queries and display logic
- Story 16.3: Dashboard summary panel uses StatsAggregator for metrics
