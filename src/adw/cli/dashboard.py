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

    def create_header(self, title: str = "ADW GLOBAL DASHBOARD") -> Panel:
        """Create dashboard header with title and keyboard hints.

        Args:
            title: Dashboard title to display.

        Returns:
            Rich Panel containing the header.
        """
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


class DashboardController:
    """Controls dashboard state and rendering.

    Placeholder - will be implemented in Task 3.
    """

    pass


def run_dashboard(
    refresh_interval: int = 30,
    project_filter: str | None = None,
    no_auto_refresh: bool = False,
) -> None:
    """Run the dashboard (entry point for CLI command).

    Placeholder - will be implemented in Task 4.

    Args:
        refresh_interval: Seconds between auto-refreshes.
        project_filter: Optional project name filter.
        no_auto_refresh: If True, disable auto-refresh.
    """
    pass
