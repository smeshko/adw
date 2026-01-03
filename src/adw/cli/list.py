"""List runs CLI command.

This module provides the `list` command for viewing recent ADW runs.
"""

from pathlib import Path

import typer
from rich.console import Console

from adw.cli.list_display import ListDisplay
from adw.core.run_lookup import RunLookup
from adw.models import RunContext

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
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format",
    ),
) -> None:
    """List recent runs.

    Displays recent ADW runs sorted by creation time (newest first).
    By default, shows the 10 most recent runs.

    Examples:
        adw list                       # List 10 most recent
        adw list --limit 20            # List 20 most recent
        adw list --status failed       # List only failed runs
        adw list --json                # JSON output for scripting
    """
    # Validate status filter
    if status and status not in VALID_STATUSES:
        console.print(f"[red]Error:[/] Invalid status: {status}")
        console.print(f"Valid values: {', '.join(sorted(VALID_STATUSES))}")
        raise typer.Exit(code=1)

    # Get runs directory
    runs_dir = _get_runs_dir()
    if runs_dir is None:
        console.print("[yellow]No runs found[/]")
        console.print("Use 'adw run \"feature\"' to start a new run")
        return

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
