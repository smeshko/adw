"""Global cross-project CLI commands.

This module provides the `global` command group for querying
runs across all projects using the global index.
"""

import json
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

# Valid status values for filtering (consistent with list.py)
VALID_STATUSES = frozenset({"running", "completed", "failed", "interrupted", "aborted"})


def parse_duration(duration_str: str) -> datetime:
    """Parse duration string to datetime threshold.

    Args:
        duration_str: Duration like "7d", "24h", "2w", "30m"

    Returns:
        datetime threshold (now - duration) in UTC

    Raises:
        ValueError: If format is invalid
    """
    pattern = r"^(\d+)([dhwm])$"
    match = re.match(pattern, duration_str.lower())

    if not match:
        raise ValueError(
            f"Invalid duration format: {duration_str}. "
            "Use format like '7d' (days), '24h' (hours), '2w' (weeks), '30m' (minutes)"
        )

    value = int(match.group(1))
    unit = match.group(2)

    unit_map = {
        "d": timedelta(days=value),
        "h": timedelta(hours=value),
        "w": timedelta(weeks=value),
        "m": timedelta(minutes=value),
    }

    return datetime.now(UTC) - unit_map[unit]


def _get_status_style(status: str) -> str:
    """Get Rich style for status value.

    Args:
        status: Run status string.

    Returns:
        Rich style string.
    """
    styles = {
        "running": "blue",
        "completed": "green",
        "failed": "red",
        "interrupted": "yellow",
        "aborted": "magenta",
    }
    return styles.get(status, "white")


def _format_duration(started_at: datetime, completed_at: datetime | None) -> str:
    """Format run duration for display.

    Args:
        started_at: When run started.
        completed_at: When run completed (None if still running).

    Returns:
        Formatted duration like "5m 32s" or elapsed time for running.
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


def _format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2h ago').

    Args:
        dt: The datetime to format.

    Returns:
        Relative time string like "just now", "5m ago", "2h ago", "3d ago".
    """
    now = datetime.now(UTC)
    delta = now - dt
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return "just now"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}m ago"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours}h ago"
    else:
        days = total_seconds // 86400
        return f"{days}d ago"


def _display_global_runs(entries: list[IndexEntry], title: str) -> None:
    """Display global runs in Rich table format.

    Args:
        entries: List of IndexEntry objects to display.
        title: Table title.
    """
    table = Table(title=title)
    table.add_column("Run ID", style="cyan", no_wrap=True)
    table.add_column("Project", style="green")
    table.add_column("Feature", max_width=30)
    table.add_column("Status", style="bold")
    table.add_column("Duration", style="dim")
    table.add_column("Started", style="dim")

    for entry in entries:
        # Format status with color
        status_style = _get_status_style(entry.status)

        # Format duration
        duration = _format_duration(entry.started_at, entry.completed_at)

        # Format started time as relative
        started = _format_relative_time(entry.started_at)

        # Truncate feature description if too long
        feature = entry.feature_description
        if len(feature) > 30:
            feature = feature[:27] + "..."

        table.add_row(
            entry.run_id,
            entry.project_name,
            feature,
            f"[{status_style}]{entry.status}[/{status_style}]",
            duration,
            started,
        )

    console.print(table)


def _output_json_entries(entries: list[IndexEntry]) -> None:
    """Output index entries as JSON array.

    Args:
        entries: List of IndexEntry objects.
    """
    output = []
    for entry in entries:
        # Calculate duration in seconds
        if entry.completed_at:
            duration_seconds = int(
                (entry.completed_at - entry.started_at).total_seconds()
            )
        else:
            duration_seconds = int(
                (datetime.now(UTC) - entry.started_at).total_seconds()
            )

        output.append(
            {
                "run_id": entry.run_id,
                "project_name": entry.project_name,
                "project_path": entry.project_path,
                "feature": entry.feature_description,
                "status": entry.status,
                "started_at": entry.started_at.isoformat(),
                "completed_at": (
                    entry.completed_at.isoformat() if entry.completed_at else None
                ),
                "duration_seconds": duration_seconds,
                "phase_reached": entry.phase_reached,
            }
        )

    console.print_json(json.dumps(output))


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
    # Validate status filter
    if status and status not in VALID_STATUSES:
        console.print(f"[red]Error:[/] Invalid status: {status}")
        console.print(f"Valid values: {', '.join(sorted(VALID_STATUSES))}")
        raise typer.Exit(code=1)

    # Validate --since if provided
    since_threshold: datetime | None = None
    if since:
        try:
            since_threshold = parse_duration(since)
        except ValueError as e:
            console.print(f"[red]Error:[/] {e}")
            raise typer.Exit(code=1) from None

    # Query the global index
    index_manager = IndexManager()

    # Request more entries to handle offset
    entries = index_manager.get_recent_runs(
        limit=limit + offset,
        project_name=project,
        status=status,
        since=since_threshold,
    )

    # Apply offset
    entries = entries[offset:]

    # Handle empty results
    if not entries:
        if json_output:
            # Return valid JSON empty array for scripts
            console.print_json("[]")
        else:
            _show_empty_results_message(project, status, since)
        return

    # Build title with applied filters
    title = _build_table_title(len(entries), project, status, since)

    # Output results
    if json_output:
        _output_json_entries(entries)
    else:
        _display_global_runs(entries, title)


def _show_empty_results_message(
    project: str | None, status: str | None, since: str | None
) -> None:
    """Show helpful message when no results found.

    Args:
        project: Project filter if applied.
        status: Status filter if applied.
        since: Since filter if applied.
    """
    console.print("[yellow]No runs found matching filters[/]")

    # Show applied filters
    filters = []
    if project:
        filters.append(f"  - Project: {project}")
    if status:
        filters.append(f"  - Status: {status}")
    if since:
        filters.append(f"  - Since: {since}")

    if filters:
        console.print("\nFilters applied:")
        for f in filters:
            console.print(f)

    console.print("\n[dim]Tip: Try broader filters or check 'adw global list' for all runs[/]")


def _build_table_title(
    count: int, project: str | None, status: str | None, since: str | None
) -> str:
    """Build descriptive table title with filter info.

    Args:
        count: Number of entries.
        project: Project filter if applied.
        status: Status filter if applied.
        since: Since filter if applied.

    Returns:
        Table title string.
    """
    parts = []
    if project:
        parts.append(project)
    if status:
        parts.append(status)
    if since:
        parts.append(f"last {since}")

    if parts:
        filter_str = ", ".join(parts)
        return f"Global Runs ({filter_str}) - {count} results"
    else:
        return f"Global Runs ({count} most recent)"
