"""Logs CLI subcommands for state inspection and debugging.

This module provides CLI commands for inspecting run state, viewing snapshots,
computing state diffs, and viewing tool execution history for debugging purposes.

Commands:
- logs snapshots <run_id>: List all available snapshots
- logs state <run_id>: Display current or specific snapshot state
- logs diff <run_id>: Show differences between two snapshots/phases
- logs tools <run_id>: Display tool execution history for a run
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from adw.models.security import ToolCallLog
from adw.security.tool_logger import ToolLogger
from adw.utils.diff import json_diff

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


def _load_snapshot_content(path: Path) -> dict[str, Any]:
    """Load full snapshot content.

    Args:
        path: Path to snapshot file.

    Returns:
        Snapshot content as dict.

    Raises:
        typer.Exit: If snapshot cannot be loaded.
    """
    try:
        content: dict[str, Any] = json.loads(path.read_text())
        return content
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]Error:[/] Failed to load snapshot: {e}")
        raise typer.Exit(1) from None


def _load_context(run_id: str) -> dict[str, Any]:
    """Load current/final context for a run.

    Args:
        run_id: The run ID.

    Returns:
        Context content as dict.

    Raises:
        typer.Exit: If context cannot be loaded.
    """
    run_dir = _get_run_dir(run_id)
    context_path = run_dir / "context.json"

    if not context_path.exists():
        console.print(f"[red]Error:[/] No context.json found for run: {run_id}")
        raise typer.Exit(1)

    try:
        content: dict[str, Any] = json.loads(context_path.read_text())
        return content
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]Error:[/] Failed to load context: {e}")
        raise typer.Exit(1) from None


def _find_snapshot_by_sequence(run_id: str, sequence: int) -> dict[str, Any]:
    """Find snapshot by sequence number.

    Args:
        run_id: The run ID.
        sequence: Snapshot sequence number.

    Returns:
        Snapshot metadata including path.

    Raises:
        typer.Exit: If snapshot not found.
    """
    snapshots = _list_snapshots(run_id)
    for snap in snapshots:
        if snap["sequence"] == sequence:
            return snap

    console.print(f"[red]Error:[/] Snapshot {sequence} not found for run: {run_id}")
    console.print(
        "[dim]Suggestion:[/] Use 'adw logs snapshots' to see available snapshots"
    )
    raise typer.Exit(1)


def _find_phase_snapshot(
    run_id: str, phase: str, boundary: str
) -> dict[str, Any]:
    """Find snapshot at phase boundary.

    Args:
        run_id: The run ID.
        phase: Phase name.
        boundary: 'start' or 'end'.

    Returns:
        Snapshot metadata including path.

    Raises:
        typer.Exit: If snapshot not found.
    """
    # Map boundary to snapshot label prefix
    label_prefix = "pre_" if boundary == "start" else "post_"
    target_label = f"{label_prefix}{phase}"

    snapshots = _list_snapshots(run_id)
    for snap in snapshots:
        if snap["label"] == target_label:
            return snap

    console.print(
        f"[red]Error:[/] No {boundary} snapshot found for phase '{phase}'"
    )
    console.print(
        "[dim]Suggestion:[/] Use 'adw logs snapshots' to see available snapshots"
    )
    raise typer.Exit(1)


def _display_state(state: dict[str, Any], title: str) -> None:
    """Display state with JSON syntax highlighting.

    Args:
        state: State dict to display.
        title: Panel title.
    """
    json_str = json.dumps(state, indent=2, default=str)
    syntax = Syntax(json_str, "json", theme="monokai", word_wrap=True)
    console.print(Panel(syntax, title=title, border_style="blue"))


def _display_diff(
    changes: list[tuple[str, str, str]], from_label: str, to_label: str
) -> None:
    """Display diff with color coding.

    Args:
        changes: List of (type, path, value) tuples.
        from_label: Label for source state.
        to_label: Label for target state.
    """
    if not changes:
        console.print("[green]No differences found[/]")
        return

    console.print(f"\n[bold]Comparing:[/] {from_label} → {to_label}\n")

    for change_type, path, value in changes:
        if change_type == "+":
            console.print(f"[green]+ {path}:[/] {value}")
        elif change_type == "-":
            console.print(f"[red]- {path}:[/] {value}")
        elif change_type == "~":
            console.print(f"[yellow]~ {path}:[/] {value}")

    console.print(f"\n[dim]Total changes: {len(changes)}[/]")


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
    # Validate options
    if phase is not None and at is None:
        console.print("[red]Error:[/] --phase requires --at option")
        console.print("[dim]Suggestion:[/] Use --at 'start' or --at 'end'")
        raise typer.Exit(1)

    if at is not None and phase is None:
        console.print("[red]Error:[/] --at requires --phase option")
        raise typer.Exit(1)

    if at is not None and at not in ("start", "end"):
        console.print(f"[red]Error:[/] Invalid --at value: {at}")
        console.print("[dim]Suggestion:[/] Use 'start' or 'end'")
        raise typer.Exit(1)

    # Determine which state to show
    if snapshot is not None:
        # Show specific snapshot
        snap = _find_snapshot_by_sequence(run_id, snapshot)
        content = _load_snapshot_content(snap["path"])
        title = f"Snapshot #{snapshot} ({snap['label']})"
        # Display the context from snapshot
        state_data = content.get("context", content)
        _display_state(state_data, title)

    elif phase is not None and at is not None:
        # Show phase boundary snapshot
        snap = _find_phase_snapshot(run_id, phase, at)
        content = _load_snapshot_content(snap["path"])
        title = f"State at {phase} phase {at}"
        # Display the context from snapshot
        state_data = content.get("context", content)
        _display_state(state_data, title)

    else:
        # Show current/final context
        context = _load_context(run_id)
        title = f"Current State for {run_id}"
        _display_state(context, title)


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

    # Get source and target snapshots
    if snapshot_mode:
        # Snapshot-based comparison
        if from_snapshot is None or to_snapshot is None:
            console.print(
                "[red]Error:[/] Both --from-snapshot and --to-snapshot required"
            )
            raise typer.Exit(1)

        source_snap = _find_snapshot_by_sequence(run_id, from_snapshot)
        target_snap = _find_snapshot_by_sequence(run_id, to_snapshot)
        from_label = f"Snapshot #{from_snapshot} ({source_snap['label']})"
        to_label = f"Snapshot #{to_snapshot} ({target_snap['label']})"

    else:
        # Phase-based comparison
        if from_phase is None or to_phase is None:
            console.print("[red]Error:[/] Both --from-phase and --to-phase required")
            raise typer.Exit(1)

        # Use post_<phase> snapshots for phase comparison
        source_snap = _find_phase_snapshot(run_id, from_phase, "start")
        target_snap = _find_phase_snapshot(run_id, to_phase, "end")
        from_label = f"Phase {from_phase} start"
        to_label = f"Phase {to_phase} end"

    # Load snapshot content
    source_content = _load_snapshot_content(source_snap["path"])
    target_content = _load_snapshot_content(target_snap["path"])

    # Extract context from snapshots
    source_state = source_content.get("context", source_content)
    target_state = target_content.get("context", target_content)

    # Compute and display diff using utility
    diff_result = json_diff(source_state, target_state)
    changes = diff_result.to_changes_list()
    _display_diff(changes, from_label, to_label)


@logs_app.command("tools")
def logs_tools(
    run_id: str = typer.Argument(..., help="Run ID to view tool history for"),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show full arguments for each tool call",
    ),
    blocked_only: bool = typer.Option(
        False,
        "--blocked-only",
        help="Only show blocked tool calls",
    ),
) -> None:
    """Display tool execution history for a run.

    Shows a table of all tool calls made during the run, including:
    - Timestamp
    - Tool name
    - Duration
    - Status (success/blocked)

    Use --verbose to see full tool arguments.
    Use --blocked-only to filter to only blocked calls.
    """
    run_dir = _get_run_dir(run_id)

    # Load tool history using ToolLogger
    tool_logger = ToolLogger(run_dir)
    history = tool_logger.get_tool_history()

    if not history:
        console.print(f"\n[dim]No tool calls logged for run {run_id}[/]")
        return

    # Apply filters
    display_entries = history
    if blocked_only:
        display_entries = [e for e in history if e.blocked]
        if not display_entries:
            console.print(f"\n[dim]No blocked tool calls for run {run_id}[/]")
            return

    # Display header
    console.print(f"\n[bold]Tool Execution History for run {run_id}[/]\n")

    # Build table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Timestamp", style="dim")
    table.add_column("Tool")
    table.add_column("Duration", justify="right")
    table.add_column("Status")

    if verbose:
        table.add_column("Arguments", style="dim")

    for entry in display_entries:
        # Format timestamp (extract time portion)
        timestamp = entry.timestamp
        if "T" in timestamp:
            timestamp = timestamp.split("T")[1].split(".")[0]

        # Format duration
        duration = f"{entry.duration_ms}ms"

        # Format status
        if entry.blocked:
            status = "[red]✗ Blocked[/]"
        else:
            status = "[green]✓ Success[/]"

        # Build row
        if verbose:
            args_str = json.dumps(entry.arguments, indent=None)
            if len(args_str) > 60:
                args_str = args_str[:57] + "..."
            table.add_row(timestamp, entry.tool_name, duration, status, args_str)
        else:
            table.add_row(timestamp, entry.tool_name, duration, status)

    console.print(table)

    # Display summary
    _display_tool_summary(history, blocked_only)


def _display_tool_summary(
    history: list[ToolCallLog],
    blocked_only: bool = False,
) -> None:
    """Display summary statistics for tool calls.

    Args:
        history: List of all tool call log entries.
        blocked_only: Whether showing only blocked calls.
    """
    total_calls = len(history)
    blocked_calls = sum(1 for e in history if e.blocked)
    successful_calls = total_calls - blocked_calls
    total_duration = sum(e.duration_ms for e in history)

    # Count tool usage
    tool_counts: dict[str, int] = {}
    for entry in history:
        tool_counts[entry.tool_name] = tool_counts.get(entry.tool_name, 0) + 1

    # Sort by usage count
    sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
    top_tools = sorted_tools[:3] if len(sorted_tools) > 3 else sorted_tools

    console.print("\n[bold]Summary[/]")
    console.print(f"  Total calls:  {total_calls}")
    console.print(f"  Successful:   [green]{successful_calls}[/]")
    console.print(f"  Blocked:      [red]{blocked_calls}[/]")
    console.print(f"  Total time:   {total_duration}ms")

    if top_tools and not blocked_only:
        most_used = ", ".join(f"{name} ({count})" for name, count in top_tools)
        console.print(f"  Most used:    {most_used}")
