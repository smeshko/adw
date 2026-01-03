"""Status command for ADW CLI.

This module provides the status command that allows users to check
the status of any run.

Examples:
    adw status                    # Most recent run
    adw status 01HQXK5P3Z...     # Specific run
    adw status --json             # JSON output
    adw status -v                 # Verbose output
"""

import typer
from rich.console import Console

from adw.cli.bootstrap import get_runs_dir
from adw.cli.status_display import StatusDisplay, output_json
from adw.core.run_lookup import RunLookup
from adw.exceptions import ConfigError

console = Console()


def status(
    run_id: str | None = typer.Argument(
        None,
        help="Run ID to check (defaults to most recent)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed information",
    ),
) -> None:
    """Show status of a run.

    If no run_id is provided, shows status of the most recent run.

    Examples:
        adw status                    # Most recent run
        adw status 01HQXK5P3Z...      # Specific run
        adw status --json             # JSON output
    """
    runs_dir = get_runs_dir()
    lookup = RunLookup(runs_dir)

    # Find the run
    if run_id:
        context = lookup.find_by_id(run_id)
        if not context:
            raise ConfigError(
                code="RUN_NOT_FOUND",
                message=f"Run {run_id} not found",
                suggestion="Use 'adw list' to see available runs",
                recoverable=False,
            )
    else:
        context = lookup.find_most_recent()
        if not context:
            console.print("[yellow]No runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
            raise typer.Exit()

    # Output format
    if json_output:
        output_json(context, console)
    else:
        display = StatusDisplay(console)
        display.show_status(context, verbose=verbose)
