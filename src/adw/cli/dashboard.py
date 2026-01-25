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
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
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


# Placeholder classes for future implementation (Tasks 2-4)
class DashboardLayout:
    """Generates Rich renderables for dashboard layout.

    Placeholder - will be implemented in Task 2.
    """

    pass


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
