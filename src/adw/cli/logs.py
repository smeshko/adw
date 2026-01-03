"""Logs CLI subcommands for state inspection and debugging.

This module provides CLI commands for inspecting run state, viewing snapshots,
and computing state diffs for debugging purposes.

Commands:
- logs snapshots <run_id>: List all available snapshots
- logs state <run_id>: Display current or specific snapshot state
- logs diff <run_id>: Show differences between two snapshots/phases
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

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


def _get_run_dir(run_id: str) -> Path:
    """Get the run directory path.

    Args:
        run_id: The run ID.

    Returns:
        Path to .adw/runs/<run_id> directory.

    Raises:
        typer.Exit: If run not found.
    """
    runs_dir = _get_runs_dir()
    run_dir = runs_dir / run_id
    if not run_dir.exists():
        console.print(f"[red]Error:[/] Run not found: {run_id}")
        console.print("[dim]Suggestion:[/] Use 'adw list' to see available runs")
        raise typer.Exit(1)
    return run_dir


def _parse_snapshot_filename(filename: str) -> tuple[int, str] | None:
    """Parse snapshot filename to extract sequence and label.

    Args:
        filename: Snapshot filename (e.g., '001_pre_plan.json').

    Returns:
        Tuple of (sequence, label) or None if invalid format.
    """
    match = re.match(r"(\d+)_(.+)\.json", filename)
    if match:
        return int(match.group(1)), match.group(2)
    return None


def _load_snapshot_metadata(path: Path) -> dict[str, Any]:
    """Load snapshot and extract metadata.

    Args:
        path: Path to snapshot file.

    Returns:
        Dict with timestamp, label, and sequence.
    """
    try:
        content = json.loads(path.read_text())
        return {
            "timestamp": content.get("timestamp", ""),
            "label": content.get("label", ""),
            "sequence": content.get("sequence", 0),
        }
    except (json.JSONDecodeError, OSError):
        return {"timestamp": "", "label": "", "sequence": 0}


def _list_snapshots(run_id: str) -> list[dict[str, Any]]:
    """List all snapshots for a run.

    Args:
        run_id: The run ID.

    Returns:
        List of snapshot metadata sorted by sequence.
    """
    run_dir = _get_run_dir(run_id)
    snapshots_dir = run_dir / "snapshots"

    if not snapshots_dir.exists():
        return []

    snapshots: list[dict[str, Any]] = []
    for path in sorted(snapshots_dir.glob("*.json")):
        parsed = _parse_snapshot_filename(path.name)
        if parsed:
            sequence, label = parsed
            metadata = _load_snapshot_metadata(path)
            snapshots.append(
                {
                    "sequence": sequence,
                    "label": label,
                    "timestamp": metadata.get("timestamp", ""),
                    "path": path,
                }
            )

    return sorted(snapshots, key=lambda s: s["sequence"])


def _format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp for display.

    Args:
        timestamp: ISO format timestamp string.

    Returns:
        Formatted timestamp or original if parsing fails.
    """
    if not timestamp:
        return "-"
    try:
        # Parse ISO format
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return timestamp


def _extract_trigger_from_label(label: str) -> str:
    """Extract trigger type from snapshot label.

    Args:
        label: Snapshot label (e.g., 'pre_plan', 'post_build').

    Returns:
        Trigger type ('pre', 'post', or 'error').
    """
    if label.startswith("pre_"):
        return "pre"
    elif label.startswith("post_"):
        return "post"
    elif "error" in label.lower():
        return "error"
    elif "abort" in label.lower():
        return "abort"
    return "auto"


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
    snapshot_list = _list_snapshots(run_id)

    if not snapshot_list:
        console.print(f"[yellow]No snapshots found for run:[/] {run_id}")
        return

    # Create table
    table = Table(title=f"Snapshots for {run_id}")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Timestamp", style="dim")
    table.add_column("Label", style="green")
    table.add_column("Trigger", style="yellow")

    for snap in snapshot_list:
        trigger = _extract_trigger_from_label(snap["label"])
        table.add_row(
            str(snap["sequence"]),
            _format_timestamp(snap["timestamp"]),
            snap["label"],
            trigger,
        )

    console.print(table)


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
