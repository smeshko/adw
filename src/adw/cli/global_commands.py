"""Global cross-project CLI commands.

This module provides the `global` command group for querying
runs across all projects using the global index.
"""

import json
import re
from datetime import UTC, datetime, timedelta

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adw.core.index_manager import IndexManager
from adw.core.project_registry import ProjectRegistryManager
from adw.core.stats_aggregator import StatsAggregator
from adw.models.index import IndexEntry
from adw.models.stats import GlobalStatistics

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


def _display_global_runs(
    entries: list[IndexEntry],
    title: str,
    registered_names: dict[str, str] | None = None,
) -> None:
    """Display global runs in Rich table format.

    Args:
        entries: List of IndexEntry objects to display.
        title: Table title.
        registered_names: Optional mapping of project_path -> registered name.
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

        # Use registered name if available, fallback to index name
        project_name = entry.project_name
        if registered_names and entry.project_path in registered_names:
            project_name = registered_names[entry.project_path]

        table.add_row(
            entry.run_id,
            project_name,
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
                "phases_completed": entry.phases_completed,
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
    registry_manager = ProjectRegistryManager()

    # Build lookup of registered project names
    registered_names = {
        p.path: p.name for p in registry_manager.get_all()
    }

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
        _display_global_runs(entries, title, registered_names)


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

    console.print(
        "\n[dim]Tip: Try broader filters or check 'adw global list' for all runs[/]"
    )


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


# ============================================================================
# Statistics Command and Helpers
# ============================================================================


def _format_tokens(count: int) -> str:
    """Format token count for display.

    Args:
        count: Number of tokens.

    Returns:
        Formatted string like "1.2M", "450K", or "999".

    Examples:
        >>> _format_tokens(1234)
        '1.2K'
        >>> _format_tokens(1234567)
        '1.2M'
    """
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


def _format_cost(amount: float) -> str:
    """Format cost for display.

    Args:
        amount: Cost in USD.

    Returns:
        Formatted string like "$47.82" or "$1,234.56".

    Examples:
        >>> _format_cost(47.82)
        '$47.82'
        >>> _format_cost(1234.56)
        '$1,234.56'
    """
    if amount >= 1000:
        return f"${amount:,.2f}"
    return f"${amount:.2f}"


def _format_duration_ms(ms: int) -> str:
    """Format duration in milliseconds for display.

    Args:
        ms: Duration in milliseconds.

    Returns:
        Formatted string like "45s", "2m 5s", or "1h 2m".
    """
    total_seconds = ms // 1000

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


def _format_rate(rate: float) -> str:
    """Format rate as percentage.

    Args:
        rate: Rate as decimal (0.0-1.0).

    Returns:
        Formatted string like "94.3%".
    """
    return f"{rate * 100:.1f}%"


def _show_global_stats(stats: GlobalStatistics) -> None:
    """Display global statistics with Rich panels and tables.

    Args:
        stats: GlobalStatistics to display.
    """
    # Handle empty stats
    if stats.total_runs == 0:
        console.print(
            Panel(
                "[dim]No statistics available\n\n"
                "No runs found in the global index.\n\n"
                "Get started:\n"
                "  1. Run 'adw init' in a project directory\n"
                "  2. Run 'adw run \"your feature\"' to create runs\n"
                "  3. Run 'adw global stats' to see statistics[/]",
                title="[bold]ADW Global Statistics[/]",
                border_style="dim",
            )
        )
        return

    # Build summary text
    summary_lines = [
        f"[bold cyan]TOTAL RUNS[/]      {stats.total_runs:,}",
        f"[bold blue]THIS WEEK[/]       {stats.runs_this_week:,}",
        f"[bold green]TODAY[/]           {stats.runs_today:,}",
        f"[bold yellow]SUCCESS RATE[/]    {_format_rate(stats.success_rate)}",
        "",
        f"[dim]AVG DURATION[/]    {_format_duration_ms(stats.average_duration_ms)}",
        f"[dim]TOTAL TOKENS[/]    {_format_tokens(stats.tokens.total_tokens)}",
        f"[dim]EST. COST[/]       {_format_cost(stats.estimated_cost)}",
    ]

    summary_text = "\n".join(summary_lines)

    # Show summary panel
    console.print(
        Panel(
            summary_text,
            title="[bold]ADW Global Statistics[/]",
            border_style="cyan",
        )
    )

    # Show per-project breakdown if there are projects
    if stats.projects:
        table = Table(title="Per-Project Breakdown")
        table.add_column("Project", style="green")
        table.add_column("Path", style="dim", max_width=35)
        table.add_column("Runs", justify="right")
        table.add_column("Success", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right")

        for proj in stats.projects:
            # Truncate path if too long
            path = proj.path
            if len(path) > 35:
                path = "..." + path[-32:]

            table.add_row(
                proj.name,
                path,
                f"{proj.total_runs:,}",
                _format_rate(proj.success_rate),
                _format_tokens(proj.tokens.total_tokens),
                _format_cost(proj.estimated_cost),
            )

        console.print(table)

    # Show cache info
    cache_age = (datetime.now(UTC) - stats.generated_at).total_seconds()
    if cache_age < 60:
        cache_info = "just now"
    elif cache_age < 3600:
        cache_info = f"{int(cache_age // 60)} minutes ago"
    else:
        cache_info = f"{int(cache_age // 3600)} hours ago"

    console.print(f"\n[dim]Generated: {cache_info}[/]")


def _output_stats_json(stats: GlobalStatistics) -> None:
    """Output statistics as JSON.

    Args:
        stats: GlobalStatistics to output.
    """
    output = {
        "generated_at": stats.generated_at.isoformat(),
        "total_runs": stats.total_runs,
        "runs_this_week": stats.runs_this_week,
        "runs_today": stats.runs_today,
        "success_rate": stats.success_rate,
        "average_duration_ms": stats.average_duration_ms,
        "total_tokens": {
            "input": stats.tokens.input_tokens,
            "output": stats.tokens.output_tokens,
            "total": stats.tokens.total_tokens,
        },
        "estimated_cost": stats.estimated_cost,
        "projects": [
            {
                "name": proj.name,
                "path": proj.path,
                "runs": proj.total_runs,
                "success_rate": proj.success_rate,
                "tokens": {
                    "input": proj.tokens.input_tokens,
                    "output": proj.tokens.output_tokens,
                    "total": proj.tokens.total_tokens,
                },
                "cost": proj.estimated_cost,
            }
            for proj in stats.projects
        ],
    }

    console.print_json(json.dumps(output))


# Valid output format values for stats command
VALID_FORMATS = frozenset({"table", "json"})


@global_app.command(name="stats")
def stats_command(
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Filter to specific project name",
    ),
    format_output: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table or json",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Ignore cache, recalculate statistics",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Only include runs from this period (e.g., 7d, 30d)",
    ),
) -> None:
    """Show aggregate statistics across all projects.

    Displays run counts, success rates, token usage, and estimated costs
    for all registered ADW projects.

    Examples:
        adw global stats                    # Show all statistics
        adw global stats --project my-api   # Stats for one project
        adw global stats --format json      # JSON output
        adw global stats --since 30d        # Last 30 days only
        adw global stats --force            # Ignore cache
    """
    # Validate --format
    if format_output not in VALID_FORMATS:
        console.print(f"[red]Error:[/] Invalid format: {format_output}")
        console.print(f"Valid values: {', '.join(sorted(VALID_FORMATS))}")
        raise typer.Exit(code=1)

    # Parse --since if provided
    since_threshold: datetime | None = None
    if since:
        try:
            since_threshold = parse_duration(since)
        except ValueError as e:
            console.print(f"[red]Error:[/] {e}")
            raise typer.Exit(code=1) from None

    # Get statistics
    aggregator = StatsAggregator()
    stats = aggregator.get_global_stats(
        project_name=project,
        since=since_threshold,
        force_refresh=force,
    )

    # Output based on format
    if format_output == "json":
        _output_stats_json(stats)
    else:
        _show_global_stats(stats)


@global_app.command(name="dashboard")
def dashboard_command(
    refresh: int = typer.Option(
        30,
        "--refresh",
        "-r",
        help="Refresh interval in seconds",
        min=5,
        max=300,
    ),
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Filter to specific project initially",
    ),
    no_auto_refresh: bool = typer.Option(
        False,
        "--no-auto-refresh",
        help="Disable auto-refresh (use R to manually refresh)",
    ),
) -> None:
    """Launch the interactive TUI dashboard.

    Displays a real-time overview of ADW runs across all projects with
    statistics, active runs, and recent run history.

    Features:
    - Summary statistics (total runs, success rate, cost)
    - Active runs with elapsed time
    - Recent runs table with status indicators
    - Per-project breakdown

    Keyboard shortcuts:
    - Q / Esc: Quit dashboard
    - R: Force refresh
    - P: Pause/resume auto-refresh
    - Up/k: Move selection up
    - Down/j: Move selection down
    - Enter: View run details
    - 1/2/3: Switch views (Summary/Runs/Projects)

    Examples:
        adw global dashboard                    # Default 30s refresh
        adw global dashboard --refresh 60       # 60s refresh interval
        adw global dashboard --project my-api   # Filter to project
        adw global dashboard --no-auto-refresh  # Manual refresh only
    """
    from adw.cli.dashboard import run_dashboard

    try:
        run_dashboard(
            refresh_interval=refresh,
            project_filter=project,
            no_auto_refresh=no_auto_refresh,
        )
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        console.print("\n[dim]Dashboard closed[/]")
        raise typer.Exit(code=0) from None


# ============================================================================
# Clean Command
# ============================================================================

# Patterns that indicate temporary/test directories
TEMP_PATH_PATTERNS = (
    "/pytest-",
    "/tmp/",
    "/var/folders/",
    "/private/var/folders/",
    "/.worktrees/",
    "/test_",
)


def _is_temp_path(path: str) -> bool:
    """Check if path matches temporary/test directory patterns.

    Args:
        path: Project path to check.

    Returns:
        True if path appears to be a temporary directory.
    """
    return any(pattern in path for pattern in TEMP_PATH_PATTERNS)


def _path_exists(path: str) -> bool:
    """Check if path exists on filesystem.

    Args:
        path: Project path to check.

    Returns:
        True if path exists.
    """
    from pathlib import Path

    return Path(path).exists()


@global_app.command(name="clean")
def clean_command(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be removed without making changes",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Clean up stale and temporary entries from the global index.

    Removes entries for:
    - Projects that no longer exist on disk
    - Temporary directories (pytest, /tmp/, etc.)

    Examples:
        adw global clean              # Interactive cleanup
        adw global clean --dry-run    # Preview what would be removed
        adw global clean --force      # Skip confirmation
    """
    index_manager = IndexManager()
    registry_manager = ProjectRegistryManager()

    if not index_manager.index_path.exists():
        console.print("[yellow]No global index found. Nothing to clean.[/]")
        return

    # Read all entries
    entries = index_manager._read_all_entries()
    total_count = len(entries)

    if total_count == 0:
        console.print("[green]Global index is empty. Nothing to clean.[/]")
        return

    # Get registered project paths
    registered_projects = registry_manager.get_all()
    registered_paths = {p.path for p in registered_projects}

    # Categorize entries
    entries_to_keep: list[IndexEntry] = []
    removed_temp: list[IndexEntry] = []
    removed_missing: list[IndexEntry] = []
    removed_unregistered: list[IndexEntry] = []

    for entry in entries:
        path = entry.project_path

        # Check if it's a temp/test path
        if _is_temp_path(path):
            removed_temp.append(entry)
            continue

        # Check if path still exists
        if not _path_exists(path):
            removed_missing.append(entry)
            continue

        # Check if project is registered (only if we have registered projects)
        if registered_paths and path not in registered_paths:
            removed_unregistered.append(entry)
            continue

        entries_to_keep.append(entry)

    # Calculate totals
    total_removed = len(removed_temp) + len(removed_missing) + len(removed_unregistered)

    if total_removed == 0:
        console.print("[green]Global index is clean. No entries to remove.[/]")
        return

    # Show summary
    console.print(f"\n[bold]Index Cleanup Summary[/]")
    console.print(f"Total entries: {total_count:,}")
    console.print(f"Entries to keep: {len(entries_to_keep):,}")
    console.print(f"Entries to remove: {total_removed:,}")

    if removed_temp:
        console.print(f"  - Temporary/test paths: {len(removed_temp):,}")
    if removed_missing:
        console.print(f"  - Missing paths: {len(removed_missing):,}")
    if removed_unregistered:
        console.print(f"  - Unregistered projects: {len(removed_unregistered):,}")

    # Show samples of what will be removed
    if dry_run:
        console.print("\n[yellow]Dry run - showing samples of entries to remove:[/]")

        if removed_temp:
            console.print("\n[dim]Temporary/test paths (sample):[/]")
            for entry in removed_temp[:5]:
                console.print(f"  {entry.project_name}: {entry.project_path}")
            if len(removed_temp) > 5:
                console.print(f"  ... and {len(removed_temp) - 5} more")

        if removed_missing:
            console.print("\n[dim]Missing paths (sample):[/]")
            for entry in removed_missing[:5]:
                console.print(f"  {entry.project_name}: {entry.project_path}")
            if len(removed_missing) > 5:
                console.print(f"  ... and {len(removed_missing) - 5} more")

        if removed_unregistered:
            console.print("\n[dim]Unregistered projects (sample):[/]")
            for entry in removed_unregistered[:5]:
                console.print(f"  {entry.project_name}: {entry.project_path}")
            if len(removed_unregistered) > 5:
                console.print(f"  ... and {len(removed_unregistered) - 5} more")

        console.print("\n[yellow]Run without --dry-run to apply changes.[/]")
        return

    # Confirm unless --force
    if not force:
        console.print("")
        confirm = typer.confirm(
            f"Remove {total_removed:,} entries from the global index?"
        )
        if not confirm:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit(code=0)

    # Write cleaned entries
    index_manager._write_all_entries(entries_to_keep)

    console.print(
        f"\n[green]Cleaned {total_removed:,} entries from global index.[/]"
    )
    console.print(f"[dim]Remaining entries: {len(entries_to_keep):,}[/]")
