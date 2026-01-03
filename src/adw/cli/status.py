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
from rich.panel import Panel

from adw.cli.bootstrap import get_runs_dir
from adw.cli.status_display import StatusDisplay, output_json
from adw.core.run_lookup import RunLookup
from adw.exceptions import ADWError, ConfigError, StateError

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
    try:
        context = _find_run(run_id)
    except ADWError as e:
        console.print(
            Panel(
                f"[red]Error:[/] {e.message}\n\n[dim]Suggestion:[/] {e.suggestion}",
                title=f"[red]{e.code}[/]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from None

    # Output format
    if json_output:
        output_json(context, console)
    else:
        display = StatusDisplay(console)
        display.show_status(context, verbose=verbose)


def _find_run(run_id: str | None):
    """Find the run to display status for.

    Args:
        run_id: Specific run ID, or None for most recent.

    Returns:
        RunContext of the found run.

    Raises:
        ConfigError: If run not found.
        StateError: If run context is corrupted.
        typer.Exit: If no runs exist (user-friendly exit).
    """
    from adw.models import RunContext

    runs_dir = get_runs_dir()
    lookup = RunLookup(runs_dir)

    if run_id:
        context = lookup.find_by_id(run_id)
        if not context:
            # Check if run directory exists but context is corrupted
            run_path = runs_dir / run_id
            if run_path.exists():
                # Directory exists but context couldn't be loaded - corrupted state
                raise StateError(
                    code="STATE_CORRUPTED",
                    message=f"Run {run_id} has corrupted state",
                    suggestion=(
                        f"Check snapshots in .adw/runs/{run_id}/snapshots/ "
                        "for recovery options"
                    ),
                    recoverable=False,
                )
            raise ConfigError(
                code="RUN_NOT_FOUND",
                message=f"Run {run_id} not found",
                suggestion="Use 'adw list' to see available runs",
                recoverable=False,
            )
        return context
    else:
        context = lookup.find_most_recent()
        if not context:
            console.print("[yellow]No runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
            raise typer.Exit()
        return context
