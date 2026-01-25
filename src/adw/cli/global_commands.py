"""Global cross-project CLI commands.

This module provides the `global` command group for querying
runs across all projects using the global index.
"""

import re
from datetime import UTC, datetime, timedelta

import typer
from rich.console import Console

console = Console()

global_app = typer.Typer(
    name="global",
    help="Cross-project commands for viewing runs across all projects",
)


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


@global_app.command(name="list")
def list_runs(
    since: str | None = typer.Option(
        None,
        "--since",
        help="Filter by time (e.g., 7d, 24h, 2w, 30m)",
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
    # Validate --since if provided
    since_threshold: datetime | None = None
    if since:
        try:
            since_threshold = parse_duration(since)
        except ValueError as e:
            console.print(f"[red]Error:[/] {e}")
            raise typer.Exit(code=1) from None

    # Placeholder implementation - will be completed in Task 4
    _ = since_threshold  # Will be used in Task 4
    console.print("[yellow]Global list command - implementation pending[/]")
