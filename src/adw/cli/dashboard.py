"""TUI Dashboard for cross-project ADW monitoring.

This module provides an interactive terminal dashboard for viewing
ADW runs across all projects using Rich Live display.

Features:
- Summary statistics (total runs, success rate, active runs)
- Recent runs table with status indicators
- Per-project breakdown
- Auto-refresh with configurable interval
- Keyboard navigation

Classes:
    DashboardState: Mutable state for dashboard interaction.
    DashboardData: Cached data for dashboard display.
    DashboardLayout: Generates Rich renderables for dashboard layout.
    DashboardController: Controls dashboard state and rendering.

Functions:
    run_dashboard: Entry point for CLI command.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from adw.models.index import IndexEntry
from adw.models.stats import GlobalStatistics

__all__ = [
    "DashboardController",
    "DashboardData",
    "DashboardLayout",
    "DashboardState",
    "STATUS_INDICATORS",
    "run_dashboard",
]


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
    """Mutable state for dashboard interaction.

    Tracks the current selection, filters, scroll position, and view mode
    for the interactive dashboard. All fields are mutable to allow
    real-time updates during dashboard operation.

    Attributes:
        selected_run_index: Index of currently selected run in the list.
        selected_project: Project name filter (None for all projects).
        scroll_offset: Scroll position for runs list.
        last_refresh: When data was last refreshed.
        paused: Whether auto-refresh is paused.
        view_mode: Current view (summary, runs, or projects).
        quit_requested: Flag to signal dashboard shutdown.
        show_run_detail: Whether to show run detail view.

    Example:
        >>> state = DashboardState()
        >>> state.selected_run_index = 5
        >>> state.paused = True
    """

    selected_run_index: int = 0
    selected_project: str | None = None
    scroll_offset: int = 0
    last_refresh: datetime = field(default_factory=lambda: datetime.now(UTC))
    paused: bool = False
    view_mode: Literal["summary", "runs", "projects"] = "summary"
    quit_requested: bool = False
    show_run_detail: bool = False


@dataclass
class DashboardData:
    """Cached data for dashboard display.

    Holds the fetched data from IndexManager and StatsAggregator
    for rendering. Separates data from state to enable clean updates.

    Attributes:
        stats: Global statistics from StatsAggregator.
        recent_runs: List of recent runs from IndexManager.
        active_runs: Filtered list of currently running runs.
        error: Error message if data fetch failed.

    Example:
        >>> data = DashboardData()
        >>> data.recent_runs = index_manager.get_recent_runs(limit=50)
        >>> data.active_runs = [r for r in data.recent_runs if r.status == "running"]
    """

    stats: GlobalStatistics | None = None
    recent_runs: list[IndexEntry] = field(default_factory=list)
    active_runs: list[IndexEntry] = field(default_factory=list)
    registered_names: dict[str, str] = field(default_factory=dict)
    error: str | None = None


class DashboardLayout:
    """Generates Rich renderables for dashboard layout.

    Creates Rich Panel, Table, and Text components for the TUI dashboard.
    Each method generates a specific section of the dashboard display.

    Attributes:
        console: Rich Console for output.

    Example:
        >>> console = Console()
        >>> layout = DashboardLayout(console)
        >>> header = layout.create_header()
        >>> console.print(header)
    """

    def __init__(self, console: Console) -> None:
        """Initialize the DashboardLayout.

        Args:
            console: Rich Console for output.
        """
        self.console = console
        self.registered_names: dict[str, str] = {}

    def get_display_name(self, run: IndexEntry) -> str:
        """Get display name for a run, using registered name if available.

        Args:
            run: IndexEntry to get display name for.

        Returns:
            Registered project name or fallback to index project_name.
        """
        return self.registered_names.get(run.project_path, run.project_name)

    def create_header(
        self,
        title: str = "ADW GLOBAL DASHBOARD",
        project_filter: str | None = None,
    ) -> Panel:
        """Create dashboard header with title and keyboard hints.

        Args:
            title: Dashboard title to display.
            project_filter: Currently active project filter, if any.

        Returns:
            Rich Panel containing the header.
        """
        header_text = Text()
        header_text.append(title, style="bold white")

        if project_filter:
            header_text.append("  ", style="dim")
            header_text.append("[", style="dim")
            header_text.append(project_filter, style="yellow bold")
            header_text.append("]", style="dim")

        header_text.append("  ", style="dim")
        header_text.append("[Q]", style="bold cyan")
        header_text.append("uit  ", style="dim")
        header_text.append("[R]", style="bold cyan")
        header_text.append("efresh", style="dim")

        return Panel(
            header_text,
            style="bold",
            border_style="yellow" if project_filter else "blue",
        )

    def create_summary_panel(
        self,
        stats: GlobalStatistics | None,
    ) -> Panel:
        """Create summary panel with stats cards.

        Args:
            stats: Global statistics to display, or None if loading.

        Returns:
            Rich Panel containing summary statistics.
        """
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
        """Create active runs panel if any runs are active.

        Args:
            active_runs: List of currently running IndexEntry objects.

        Returns:
            Rich Panel with active runs, or None if no active runs.
        """
        if not active_runs:
            return None

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Status", width=2)
        table.add_column("ID", width=28, no_wrap=True)
        table.add_column("Project", width=12)
        table.add_column("Feature", max_width=25)
        table.add_column("Phase", width=10)
        table.add_column("Duration", width=12, no_wrap=True)

        for run in active_runs:
            # Calculate elapsed time with human-readable format
            elapsed = datetime.now(UTC) - run.started_at
            total_seconds = int(elapsed.total_seconds())
            total_minutes = total_seconds // 60

            # Format duration: use hours if >= 60 minutes
            if total_minutes >= 60:
                hours = total_minutes // 60
                minutes = total_minutes % 60
                duration = f"{hours}h {minutes:02d}m"
            else:
                seconds = total_seconds % 60
                duration = f"{total_minutes}m {seconds:02d}s"

            # Truncate feature
            feature = run.feature_description
            if len(feature) > 22:
                feature = feature[:19] + "..."

            # Current phase (phase_reached shows last/current phase)
            current_phase = run.phase_reached or "starting"

            table.add_row(
                "[yellow]●[/]",
                run.run_id,
                self.get_display_name(run),
                feature,
                f"[cyan]{current_phase}[/]",
                f"[yellow]◐[/] {duration}",
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
        """Create recent runs table with selection highlight.

        Args:
            runs: List of IndexEntry objects to display.
            selected_index: Index of selected run for highlighting.
            max_rows: Maximum number of rows to display.

        Returns:
            Rich Panel containing the runs table.
        """
        if not runs:
            return Panel(
                "[dim]No recent runs[/]",
                title="RECENT RUNS",
                border_style="blue",
            )

        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("RUN ID", style="cyan", no_wrap=True, width=28)
        table.add_column("PROJECT", width=12)
        table.add_column("FEATURE", max_width=25)
        table.add_column("STATUS", justify="left", width=14)
        table.add_column("DURATION", width=10)
        table.add_column("STARTED", style="dim", width=10)

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

            # Get display name (registered name or fallback)
            display_name = self.get_display_name(run)

            # Highlight selected row
            if i == selected_index:
                table.add_row(
                    f"[bold reverse]{run.run_id}[/]",
                    f"[bold]{display_name}[/]",
                    f"[bold]{feature}[/]",
                    status_text,
                    duration,
                    started,
                )
            else:
                table.add_row(
                    run.run_id,
                    display_name,
                    feature,
                    status_text,
                    duration,
                    started,
                )

        footer = "[dim][↑/↓] Navigate   [Enter] View Details[/]"

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
        """Create per-project breakdown table.

        Args:
            stats: Global statistics with project list.

        Returns:
            Rich Panel containing project breakdown.
        """
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
        """Create footer with refresh status.

        Args:
            last_refresh: When data was last refreshed.
            paused: Whether auto-refresh is paused.
            refresh_interval: Refresh interval in seconds.

        Returns:
            Rich Text containing footer content.
        """
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
        """Create empty state display with guidance.

        Returns:
            Rich Panel with empty state message.
        """
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

    def create_run_detail(self, run: IndexEntry) -> Panel:
        """Create run detail view.

        Args:
            run: The IndexEntry to display details for.

        Returns:
            Rich Panel with run details.
        """
        content = Text()
        content.append("\n")

        # Run ID
        content.append("  RUN ID       ", style="bold")
        content.append(run.run_id, style="cyan")
        content.append("\n\n")

        # Project
        content.append("  PROJECT      ", style="bold")
        content.append(self.get_display_name(run), style="green")
        content.append("\n")
        content.append("  PATH         ", style="bold dim")
        content.append(run.project_path, style="dim")
        content.append("\n\n")

        # Feature
        content.append("  FEATURE      ", style="bold")
        content.append("\n")
        content.append(f"    {run.feature_description}\n", style="white")
        content.append("\n")

        # Status
        indicator, color = STATUS_INDICATORS.get(run.status, ("?", "white"))
        content.append("  STATUS       ", style="bold")
        content.append(f"{indicator} ", style=color)
        content.append(run.status.upper(), style=f"bold {color}")
        content.append("\n\n")

        # Timing
        content.append("  STARTED      ", style="bold")
        content.append(run.started_at.strftime("%Y-%m-%d %H:%M:%S UTC"), style="dim")
        content.append("\n")

        if run.completed_at:
            content.append("  COMPLETED    ", style="bold")
            content.append(
                run.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC"), style="dim"
            )
            content.append("\n")

            # Duration
            delta = run.completed_at - run.started_at
            total_sec = int(delta.total_seconds())
            minutes = total_sec // 60
            seconds = total_sec % 60
            content.append("  DURATION     ", style="bold")
            content.append(f"{minutes}m {seconds}s", style="cyan")
            content.append("\n")
        else:
            # Running duration
            delta = datetime.now(UTC) - run.started_at
            total_sec = int(delta.total_seconds())
            minutes = total_sec // 60
            seconds = total_sec % 60
            content.append("  ELAPSED      ", style="bold")
            content.append(f"{minutes}m {seconds}s", style="yellow")
            content.append(" (running)\n")

        content.append("\n")

        # Phases
        content.append("  PHASES       ", style="bold")
        if run.phases_completed:
            content.append(" → ".join(run.phases_completed), style="green")
        else:
            content.append("(none)", style="dim")
        content.append("\n")

        if run.phase_reached:
            content.append("  LAST PHASE   ", style="bold dim")
            content.append(run.phase_reached, style="dim")
            content.append("\n")

        content.append("\n")

        # Artifacts path
        artifacts_path = f"{run.project_path}/.adw/runs/{run.run_id}"
        content.append("  ARTIFACTS    ", style="bold dim")
        content.append(artifacts_path, style="dim")
        content.append("\n\n")

        # Footer hint
        content.append(
            "  Press [Q] or [Esc] to return to dashboard", style="dim italic"
        )
        content.append("\n")

        return Panel(
            content,
            title="RUN DETAILS",
            border_style="cyan",
        )


class DashboardController:
    """Controls dashboard state and rendering.

    Coordinates between data fetching (IndexManager, StatsAggregator),
    state management (DashboardState), and rendering (DashboardLayout).

    Attributes:
        refresh_interval: Seconds between auto-refreshes.
        project_filter: Optional project name filter.
        state: Mutable dashboard state.
        data: Cached dashboard data.
        layout: Layout renderer.
        console: Rich Console for output.
        index_manager: IndexManager for run queries.
        stats_aggregator: StatsAggregator for statistics.

    Example:
        >>> controller = DashboardController(refresh_interval=30)
        >>> controller.refresh_data()
        >>> renderable = controller.render()
    """

    def __init__(
        self,
        refresh_interval: int = 30,
        project_filter: str | None = None,
        console: Console | None = None,
    ) -> None:
        """Initialize the DashboardController.

        Args:
            refresh_interval: Seconds between auto-refreshes.
            project_filter: Optional project name filter.
            console: Optional Rich Console (creates one if not provided).
        """
        # Import here to avoid circular imports
        from adw.core.index_manager import IndexManager
        from adw.core.project_registry import ProjectRegistryManager
        from adw.core.stats_aggregator import StatsAggregator

        self.refresh_interval = refresh_interval
        self.project_filter = project_filter
        self.console = console or Console()

        # Initialize state and data containers
        self.state = DashboardState()
        self.data = DashboardData()

        # Initialize layout renderer
        self.layout = DashboardLayout(self.console)

        # Initialize data sources
        self.index_manager = IndexManager()
        self.project_registry = ProjectRegistryManager()
        self.stats_aggregator = StatsAggregator()

        # Flag to signal run() to reset its local auto-refresh timer
        self._manual_refresh_triggered = False

    def refresh_data(self) -> None:
        """Fetch latest data from IndexManager and StatsAggregator.

        Updates self.data with fresh run list and statistics.
        Also clamps selected_run_index to valid range to prevent IndexError.
        """
        try:
            # Build registered names lookup and share with layout
            self.data.registered_names = {
                p.path: p.name for p in self.project_registry.get_all()
            }
            self.layout.registered_names = self.data.registered_names

            # Fetch recent runs
            recent_runs = self.index_manager.get_recent_runs(
                limit=100,
                project_name=self.project_filter,
            )
            self.data.recent_runs = recent_runs

            # Filter to active runs only
            self.data.active_runs = [
                run for run in recent_runs if run.status == "running"
            ]

            # Fetch global statistics
            self.data.stats = self.stats_aggregator.get_global_stats(
                project_name=self.project_filter,
            )

            # Clamp selected_run_index to valid range after data refresh
            if recent_runs:
                max_index = len(recent_runs) - 1
                if self.state.selected_run_index > max_index:
                    self.state.selected_run_index = max_index
            else:
                self.state.selected_run_index = 0
                # Disable detail view if no runs available
                self.state.show_run_detail = False

            # Clear any previous error
            self.data.error = None

            # Update last refresh time
            self.state.last_refresh = datetime.now(UTC)

        except Exception as e:
            self.data.error = str(e)

    def handle_key(self, key: str) -> None:
        """Process keyboard input.

        Supported keys:
            q, Esc: Quit dashboard
            p: Pause/resume auto-refresh
            r: Force refresh now
            up, k: Move selection up
            down, j: Move selection down
            Enter: View selected run details (placeholder)
            1: Switch to summary view
            2: Switch to runs view
            3: Switch to projects view

        Args:
            key: Key string (e.g., "q", "up", "down", "r", "p").
        """
        key_lower = key.lower()

        # Handle escape key - either exit detail view or quit
        if key == "\x1b":  # Escape key
            if self.state.show_run_detail:
                self.state.show_run_detail = False
            else:
                self.state.quit_requested = True
            return

        # Handle 'q' in detail view - close detail view
        if key_lower == "q" and self.state.show_run_detail:
            self.state.show_run_detail = False
            return

        # Quit commands
        if key_lower == "q":
            self.state.quit_requested = True

        # Pause/resume auto-refresh
        elif key_lower == "p":
            self.state.paused = not self.state.paused

        # Force refresh (sets _manual_refresh_triggered flag for run() to sync timer)
        elif key_lower == "r":
            self.refresh_data()
            self._manual_refresh_triggered = True

        # Navigation: up arrow or k (vim-style)
        elif key_lower == "up" or key_lower == "k":
            if self.state.selected_run_index > 0:
                self.state.selected_run_index -= 1

        # Navigation: down arrow or j (vim-style)
        elif key_lower == "down" or key_lower == "j":
            # Limit to visible rows (max_rows=6 in create_recent_runs_table)
            max_visible = min(len(self.data.recent_runs), 6)
            max_index = max_visible - 1
            if max_index >= 0 and self.state.selected_run_index < max_index:
                self.state.selected_run_index += 1

        # Enter: View run details
        elif key == "\r" or key == "\n":
            if self.data.recent_runs:
                self.state.show_run_detail = True

        # View mode switching
        elif key == "1":
            self.state.view_mode = "summary"
        elif key == "2":
            self.state.view_mode = "runs"
        elif key == "3":
            self.state.view_mode = "projects"

    def render(self) -> "Panel | Group":
        """Generate Rich renderable for current state.

        Returns:
            Rich renderable (Panel for detail view, Group for main view).
        """
        from rich.console import Group

        # Clamp selected index to valid range (handles data refresh edge cases)
        max_visible = min(len(self.data.recent_runs), 6) if self.data.recent_runs else 0
        if self.state.selected_run_index >= max_visible:
            self.state.selected_run_index = max(0, max_visible - 1)

        # Handle run detail view
        if self.state.show_run_detail and self.data.recent_runs:
            selected_run = self.data.recent_runs[self.state.selected_run_index]
            return self.layout.create_run_detail(selected_run)

        # Build components list - Group sizes to content automatically
        components: list = []

        # Header
        components.append(
            self.layout.create_header(project_filter=self.project_filter)
        )

        # Build body based on data availability
        if self.data.stats is None and not self.data.recent_runs:
            # Empty state
            components.append(Text())  # Spacing
            components.append(self.layout.create_empty_state())
        else:
            # Build body with content based on view_mode
            if self.state.view_mode == "projects":
                # Projects-only view
                components.append(Text())  # Spacing
                components.append(
                    self.layout.create_summary_panel(self.data.stats)
                )
                components.append(Text())  # Spacing between sections
                components.append(
                    self.layout.create_projects_panel(self.data.stats)
                )
            elif self.state.view_mode == "runs":
                # Runs-only view (no summary)
                active_panel = self.layout.create_active_runs_panel(
                    self.data.active_runs
                )
                if active_panel:
                    components.append(Text())  # Spacing
                    components.append(active_panel)
                components.append(Text())  # Spacing
                components.append(
                    self.layout.create_recent_runs_table(
                        self.data.recent_runs,
                        selected_index=self.state.selected_run_index,
                    )
                )
            else:
                # Summary view (default) - shows summary, runs, and projects
                # Summary panel
                components.append(Text())  # Spacing after header
                components.append(
                    self.layout.create_summary_panel(self.data.stats)
                )

                # Active runs section (if any)
                active_panel = self.layout.create_active_runs_panel(
                    self.data.active_runs
                )
                if active_panel:
                    components.append(Text())  # Spacing
                    components.append(active_panel)

                # Recent runs
                components.append(Text())  # Spacing between sections
                components.append(
                    self.layout.create_recent_runs_table(
                        self.data.recent_runs,
                        selected_index=self.state.selected_run_index,
                    )
                )

                # Projects panel
                components.append(Text())  # Spacing between sections
                components.append(
                    self.layout.create_projects_panel(self.data.stats)
                )

        # Footer - show faster interval when active runs exist
        effective_interval = 5 if self.data.active_runs else self.refresh_interval
        components.append(Text())  # Spacing before footer
        components.append(
            self.layout.create_footer(
                last_refresh=self.state.last_refresh,
                paused=self.state.paused,
                refresh_interval=effective_interval,
            )
        )

        return Group(*components)

    def run(self, no_auto_refresh: bool = False) -> None:
        """Run the main dashboard event loop with Rich Live display.

        Args:
            no_auto_refresh: If True, start with auto-refresh paused.
        """
        from rich.live import Live

        # Initial data refresh
        self.refresh_data()

        # Set initial pause state if no_auto_refresh
        if no_auto_refresh:
            self.state.paused = True

        try:
            with Live(
                self.render(),
                console=self.console,
                refresh_per_second=1,
                transient=False,
                vertical_overflow="visible",
            ) as live:
                # Set up keyboard AFTER Live context starts to avoid mode conflicts
                keyboard_enabled = self._setup_keyboard()

                try:
                    last_refresh_time = datetime.now(UTC)

                    while not self.state.quit_requested:
                        # Check for keyboard input (non-blocking)
                        key = self._read_key() if keyboard_enabled else None

                        if key:
                            self.handle_key(key)
                            live.update(self.render())
                            # Sync timer if manual refresh was triggered
                            if self._manual_refresh_triggered:
                                last_refresh_time = datetime.now(UTC)
                                self._manual_refresh_triggered = False

                        # Auto-refresh if not paused
                        # Use faster refresh when there are active runs
                        if not self.state.paused:
                            now = datetime.now(UTC)
                            elapsed = (now - last_refresh_time).total_seconds()
                            # Refresh every 5s when active runs exist, else use normal interval
                            effective_interval = (
                                5 if self.data.active_runs else self.refresh_interval
                            )
                            if elapsed >= effective_interval:
                                self.refresh_data()
                                last_refresh_time = now
                                live.update(self.render())

                        # Small sleep to prevent CPU spinning when no keyboard
                        if not keyboard_enabled:
                            import time

                            time.sleep(0.25)
                finally:
                    self._cleanup_keyboard()

        except Exception:
            self._cleanup_keyboard()
            raise

    def _setup_keyboard(self) -> bool:
        """Set up terminal for keyboard input.

        Configures terminal for cbreak mode (character-by-character input, no echo).

        Returns:
            True if keyboard input is available, False otherwise.
        """
        import sys

        self._old_settings = None

        try:
            import termios
            import tty

            self._old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            return True
        except (ImportError, OSError, AttributeError):
            # Not a TTY or termios not available
            return False

    def _cleanup_keyboard(self) -> None:
        """Restore terminal settings."""
        import sys

        if self._old_settings is not None:
            try:
                import termios

                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
            except (ImportError, OSError):
                pass
            self._old_settings = None

    def _read_key(self) -> str | None:
        """Read a key from stdin with timeout (non-blocking).

        Handles escape sequences for arrow keys by reading all available bytes
        when an escape character is detected.

        Returns:
            Key string ("up", "down", "q", etc.), or None if no key available.
        """
        import fcntl
        import os
        import select
        import sys

        try:
            # Check if input is available (non-blocking with 0.25s timeout)
            if not select.select([sys.stdin], [], [], 0.25)[0]:
                return None

            # Set stdin to non-blocking mode temporarily
            fd = sys.stdin.fileno()
            old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

            try:
                # Read all available bytes (up to 10 for safety)
                data = sys.stdin.read(10)
            except OSError:
                data = ""
            finally:
                # Restore blocking mode
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)

            if not data:
                return None

            # Handle escape sequences for arrow keys
            if data == "\x1b":
                # Standalone Escape key
                return "\x1b"
            elif data == "\x1b[A":
                return "up"
            elif data == "\x1b[B":
                return "down"
            elif data == "\x1b[C":
                return "right"
            elif data == "\x1b[D":
                return "left"
            elif data.startswith("\x1b"):
                # Unknown escape sequence - treat as Escape
                return "\x1b"
            else:
                # Regular character(s) - return first one
                return data[0]

        except OSError:
            pass
        return None


def run_dashboard(
    refresh_interval: int = 30,
    project_filter: str | None = None,
    no_auto_refresh: bool = False,
) -> None:
    """Run the interactive TUI dashboard.

    Entry point for the `adw global dashboard` CLI command.
    Creates a DashboardController and starts the live display.

    Args:
        refresh_interval: Seconds between auto-refreshes.
        project_filter: Optional project name filter.
        no_auto_refresh: If True, disable auto-refresh.
    """
    controller = DashboardController(
        refresh_interval=refresh_interval,
        project_filter=project_filter,
    )
    controller.run(no_auto_refresh=no_auto_refresh)
