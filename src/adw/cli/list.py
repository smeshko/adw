"""List runs CLI command.

This module provides the `list` command for viewing recent ADW runs.
Supports both project-local runs and global index queries.
"""

from pathlib import Path

import typer
from rich.console import Console

from adw.cli.list_display import ListDisplay
from adw.core.index_manager import IndexManager
from adw.core.run_lookup import RunLookup
from adw.models import RunContext
from adw.models.index import IndexEntry

console = Console()

# Valid status values for filtering
VALID_STATUSES = frozenset({"running", "completed", "failed", "interrupted", "aborted"})


def list_runs(
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of runs to display",
        min=1,
        max=100,
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (running, completed, failed, interrupted, aborted)",
    ),
    project: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Filter to runs from current project only (when inside a project)",
    ),
    global_view: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Show runs from all projects (global index)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format",
    ),
) -> None:
    """List recent runs.

    Displays recent ADW runs sorted by creation time (newest first).
    By default, shows the 10 most recent runs.

    When run inside a project directory (with .adw/runs/), shows local runs.
    When run outside a project, shows runs from the global index (~/.adw/index.jsonl).

    Use --global to show all runs across all projects.
    Use --project to filter global view to current project.

    Examples:
        adw list                       # List 10 most recent
        adw list --limit 20            # List 20 most recent
        adw list --status failed       # List only failed runs
        adw list --global              # List all runs from global index
        adw list --project             # Filter to current project
        adw list --json                # JSON output for scripting
    """
    # Validate status filter
    if status and status not in VALID_STATUSES:
        console.print(f"[red]Error:[/] Invalid status: {status}")
        console.print(f"Valid values: {', '.join(sorted(VALID_STATUSES))}")
        raise typer.Exit(code=1)

    # Determine data source: local runs or global index
    runs_dir = _get_runs_dir()
    use_global = global_view or (runs_dir is None and not project)

    if use_global:
        # Use global index
        _list_from_global_index(
            limit=limit,
            status=status,
            project_filter=project,
            json_output=json_output,
        )
    else:
        # Use local runs directory
        if runs_dir is None:
            console.print("[yellow]No runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
            console.print("Or use --global to view runs from all projects")
            return

        _list_from_local_runs(
            runs_dir=runs_dir,
            limit=limit,
            status=status,
            json_output=json_output,
        )


def _list_from_local_runs(
    runs_dir: Path,
    limit: int,
    status: str | None,
    json_output: bool,
) -> None:
    """List runs from local .adw/runs directory.

    Args:
        runs_dir: Path to .adw/runs directory.
        limit: Maximum number of runs to display.
        status: Optional status filter.
        json_output: Whether to output as JSON.
    """
    lookup = RunLookup(runs_dir=runs_dir)
    runs = lookup.list_runs(limit=limit, status=status)

    if not runs:
        if status:
            console.print(f"[yellow]No runs with status '{status}'[/]")
        else:
            console.print("[yellow]No runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
        return

    if json_output:
        _output_json_list(runs)
    else:
        display = ListDisplay(console)
        display.show_runs(runs)


def _list_from_global_index(
    limit: int,
    status: str | None,
    project_filter: bool,
    json_output: bool,
) -> None:
    """List runs from global index (~/.adw/index.jsonl).

    Args:
        limit: Maximum number of runs to display.
        status: Optional status filter.
        project_filter: If True, filter to current project path.
        json_output: Whether to output as JSON.
    """
    index_manager = IndexManager()

    # Determine project path filter
    project_path: Path | None = None
    if project_filter:
        project_path = Path.cwd()

    # Get entries from global index
    entries = index_manager.get_recent_runs(
        limit=limit,
        project_path=project_path,
        status=status,
    )

    if not entries:
        if status:
            console.print(f"[yellow]No runs with status '{status}'[/]")
        elif project_filter:
            console.print("[yellow]No runs found for current project[/]")
            console.print("Use 'adw list --global' to view all projects")
        else:
            console.print("[yellow]No runs found in global index[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
        return

    if json_output:
        _output_json_index_entries(entries)
    else:
        _display_index_entries(entries)


def _display_index_entries(entries: list[IndexEntry]) -> None:
    """Display index entries in Rich table format.

    Args:
        entries: List of IndexEntry objects to display.
    """
    from rich.table import Table

    table = Table(title="Recent Runs (Global Index)")
    table.add_column("Run ID", style="cyan", no_wrap=True)
    table.add_column("Project", style="green")
    table.add_column("Feature", max_width=40)
    table.add_column("Status", style="bold")
    table.add_column("Started", style="dim")
    table.add_column("Phase", style="yellow")

    for entry in entries:
        # Format status with color
        status_style = _get_status_style(entry.status)

        # Format started time
        if entry.started_at:
            started = entry.started_at.strftime("%Y-%m-%d %H:%M")
        else:
            started = "-"

        # Truncate run_id for display
        run_id_short = entry.run_id[:12] + "..."

        # Truncate feature description if too long
        feature = entry.feature_description
        if len(feature) > 40:
            feature = feature[:40] + "..."

        table.add_row(
            run_id_short,
            entry.project_name,
            feature,
            f"[{status_style}]{entry.status}[/{status_style}]",
            started,
            entry.phase_reached or "-",
        )

    console.print(table)


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


def _output_json_index_entries(entries: list[IndexEntry]) -> None:
    """Output index entries as JSON array.

    Args:
        entries: List of IndexEntry objects.
    """
    import json

    output = []
    for entry in entries:
        output.append(
            {
                "run_id": entry.run_id,
                "project_path": entry.project_path,
                "project_name": entry.project_name,
                "feature": entry.feature_description,
                "status": entry.status,
                "started_at": (
                    entry.started_at.isoformat() if entry.started_at else None
                ),
                "completed_at": entry.completed_at.isoformat()
                if entry.completed_at
                else None,
                "phase_reached": entry.phase_reached,
                "phases_completed": entry.phases_completed,
            }
        )

    console.print_json(json.dumps(output))


def _get_runs_dir() -> Path | None:
    """Get the runs directory path.

    Returns:
        Path to .adw/runs directory, or None if it doesn't exist.
    """
    cwd = Path.cwd()
    runs_dir = cwd / ".adw" / "runs"

    if not runs_dir.exists():
        return None

    return runs_dir


def _output_json_list(runs: list[RunContext]) -> None:
    """Output runs as JSON array.

    Args:
        runs: List of RunContext objects.
    """
    import json

    output = []
    for run in runs:
        output.append(
            {
                "run_id": run.run_id,
                "feature": run.feature_description,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat()
                if run.completed_at
                else None,
            }
        )

    console.print_json(json.dumps(output))
