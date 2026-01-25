"""Global cross-project CLI commands.

This module provides the `global` command group for querying
runs across all projects using the global index.
"""

import typer
from rich.console import Console

console = Console()

global_app = typer.Typer(
    name="global",
    help="Cross-project commands for viewing runs across all projects",
)


@global_app.command(name="list")
def list_runs() -> None:
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
    # Placeholder implementation - will be completed in Task 4
    console.print("[yellow]Global list command - implementation pending[/]")
