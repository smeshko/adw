"""Logs CLI subcommands for state inspection and debugging.

This module provides CLI commands for inspecting run state, viewing snapshots,
and computing state diffs for debugging purposes.

Commands:
- logs snapshots <run_id>: List all available snapshots
- logs state <run_id>: Display current or specific snapshot state
- logs diff <run_id>: Show differences between two snapshots/phases
"""

from pathlib import Path

import typer
from rich.console import Console

from adw.exceptions import StateError

console = Console()

logs_app = typer.Typer(
    name="logs",
    help="View logs, state snapshots, and diffs for debugging",
    add_completion=False,
)


def _get_runs_dir() -> Path:
    """Get the runs directory path.

    Returns:
        Path to .adw/runs directory.

    Raises:
        typer.Exit: If .adw directory not found.
    """
    cwd = Path.cwd()
    adw_dir = cwd / ".adw"
    if not adw_dir.exists():
        console.print("[red]Error:[/] No .adw directory found")
        console.print("[dim]Suggestion:[/] Run 'adw init' first")
        raise typer.Exit(1)
    return adw_dir / "runs"


@logs_app.command(name="snapshots")
def snapshots(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to list snapshots for",
    ),
) -> None:
    """List all available snapshots for a run.

    Displays a table of snapshots with sequence number, timestamp, label,
    and trigger information.

    Examples:
        adw logs snapshots 01HQXK5P3Z7V8R2M4N6T9W1Y3C
    """
    # Implementation in Task 2
    console.print(f"[dim]Listing snapshots for run:[/] {run_id}")
    console.print("[yellow]Not yet implemented[/]")


@logs_app.command(name="state")
def state(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to show state for",
    ),
    snapshot: int | None = typer.Option(
        None,
        "--snapshot",
        "-s",
        help="Show state at specific snapshot sequence number",
    ),
    phase: str | None = typer.Option(
        None,
        "--phase",
        "-p",
        help="Show state at specific phase",
    ),
    at: str | None = typer.Option(
        None,
        "--at",
        help="Phase boundary: 'start' or 'end' (requires --phase)",
    ),
) -> None:
    """Display run state at current or specific snapshot.

    By default shows the current/final state. Use --snapshot to view
    a specific snapshot, or --phase with --at to view phase boundaries.

    Examples:
        adw logs state 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw logs state 01HQXK5P3Z7V8R2M4N6T9W1Y3C --snapshot 3
        adw logs state 01HQXK5P3Z7V8R2M4N6T9W1Y3C --phase plan --at end
    """
    # Implementation in Task 3
    console.print(f"[dim]Showing state for run:[/] {run_id}")
    console.print("[yellow]Not yet implemented[/]")


@logs_app.command(name="diff")
def diff(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to compute diff for",
    ),
    from_phase: str | None = typer.Option(
        None,
        "--from-phase",
        help="Source phase for diff",
    ),
    to_phase: str | None = typer.Option(
        None,
        "--to-phase",
        help="Target phase for diff",
    ),
    from_snapshot: int | None = typer.Option(
        None,
        "--from-snapshot",
        help="Source snapshot sequence number",
    ),
    to_snapshot: int | None = typer.Option(
        None,
        "--to-snapshot",
        help="Target snapshot sequence number",
    ),
) -> None:
    """Show differences between two snapshots or phases.

    Compare state at two points in a run's execution. Either use
    --from-phase/--to-phase for phase boundaries, or
    --from-snapshot/--to-snapshot for specific snapshots.

    Examples:
        adw logs diff 01HQXK5P3Z7V8R2M4N6T9W1Y3C --from-phase plan --to-phase build
        adw logs diff 01HQXK5P3Z7V8R2M4N6T9W1Y3C --from-snapshot 1 --to-snapshot 3
    """
    # Validate options
    phase_mode = from_phase is not None or to_phase is not None
    snapshot_mode = from_snapshot is not None or to_snapshot is not None

    if phase_mode and snapshot_mode:
        console.print("[red]Error:[/] Cannot mix phase and snapshot options")
        console.print(
            "[dim]Suggestion:[/] Use either --from-phase/--to-phase "
            "or --from-snapshot/--to-snapshot"
        )
        raise typer.Exit(1)

    if not phase_mode and not snapshot_mode:
        console.print("[red]Error:[/] Must specify comparison targets")
        console.print(
            "[dim]Suggestion:[/] Use --from-phase/--to-phase "
            "or --from-snapshot/--to-snapshot"
        )
        raise typer.Exit(1)

    # Implementation in Task 4
    console.print(f"[dim]Computing diff for run:[/] {run_id}")
    console.print("[yellow]Not yet implemented[/]")
