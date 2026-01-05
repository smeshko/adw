"""Logs CLI subcommands for state inspection and debugging.

This module provides CLI commands for inspecting run state, viewing snapshots,
computing state diffs, and viewing tool execution history for debugging purposes.

Commands:
- logs snapshots <run_id>: List all available snapshots
- logs state <run_id>: Display current or specific snapshot state
- logs diff <run_id>: Show differences between two snapshots/phases
- logs tools <run_id>: Display tool execution history for a run
"""

import contextlib
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
from ulid import ULID

from adw.models.security import ToolCallLog
from adw.security.tool_logger import ToolLogger
from adw.utils.diff import json_diff

console = Console()


def _validate_ulid(run_id: str) -> bool:
    """Check if string is valid ULID format.

    Args:
        run_id: The run ID to validate.

    Returns:
        True if valid ULID format, False otherwise.
    """
    if not run_id or len(run_id) != 26:
        return False
    try:
        ULID.from_str(run_id)
        return True
    except (ValueError, TypeError):
        return False


def _find_similar_runs(runs_dir: Path, target: str) -> list[str]:
    """Find run IDs similar to target (prefix match).

    Args:
        runs_dir: Path to the runs directory.
        target: The target run ID to match against.

    Returns:
        List of similar run IDs.
    """
    if not runs_dir.exists():
        return []

    similar: list[str] = []
    # Only check prefix if target is at least 8 characters
    min_prefix_len = min(8, len(target))

    for run_path in runs_dir.iterdir():
        if run_path.is_dir() and not run_path.name.startswith("."):
            run_id = run_path.name
            # Prefix match (common copy/paste truncation)
            if (
                len(target) >= min_prefix_len
                and len(run_id) >= min_prefix_len
                and run_id[:min_prefix_len] == target[:min_prefix_len]
            ):
                similar.append(run_id)

    return similar


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


def _get_run_dir(run_id: str, *, debug: bool = False) -> Path:
    """Get the run directory path with improved error handling.

    Args:
        run_id: The run ID.
        debug: If True, show diagnostic information.

    Returns:
        Path to .adw/runs/<run_id> directory.

    Raises:
        typer.Exit: If run not found or invalid format.
    """
    runs_dir = _get_runs_dir()

    if debug:
        console.print(f"[dim]Searching in: {runs_dir}[/]")

    # Step 1: Validate ULID format
    if not _validate_ulid(run_id):
        console.print(f"[red]Error:[/] Invalid run ID format: {run_id}")
        console.print(
            "[dim]Run IDs are 26-character ULIDs (e.g., 01HQXK5P3Z7V8R2M4N6T9W1Y3C)[/]"
        )
        raise typer.Exit(1)

    run_dir = runs_dir / run_id

    # Step 2: Check if run directory exists
    if run_dir.exists():
        return run_dir

    # Step 3: Try fuzzy match for similar IDs
    similar_runs = _find_similar_runs(runs_dir, run_id)
    if similar_runs:
        console.print(f"[red]Error:[/] Run not found: {run_id}")
        console.print("[yellow]Did you mean one of these?[/]")
        for similar_id in similar_runs[:3]:
            console.print(f"  • {similar_id}")
        raise typer.Exit(1)

    # Step 4: Generic not found
    console.print(f"[red]Error:[/] Run not found: {run_id}")
    console.print("[dim]Suggestion:[/] Use 'adw list' to see available runs")
    raise typer.Exit(1)


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


def _find_phase_snapshot(run_id: str, phase: str, boundary: str) -> dict[str, Any]:
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

    console.print(f"[red]Error:[/] No {boundary} snapshot found for phase '{phase}'")
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

        # Format duration with tilde to indicate estimate
        # (Individual tool timing is distributed evenly from total duration)
        duration = f"~{entry.duration_ms}ms"

        # Format status
        status = "[red]✗ Blocked[/]" if entry.blocked else "[green]✓ Success[/]"

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
    console.print(f"  Total time:   ~{total_duration}ms")
    console.print("  [dim](Durations are estimates, evenly distributed)[/]")

    if top_tools and not blocked_only:
        most_used = ", ".join(f"{name} ({count})" for name, count in top_tools)
        console.print(f"  Most used:    {most_used}")


# =============================================================================
# Story 7.4: Log Viewing Commands
# =============================================================================


def _load_log_entries(run_dir: Path) -> list[dict[str, Any]]:
    """Load log entries from the structured log file.

    Args:
        run_dir: Path to the run directory.

    Returns:
        List of log entry dicts.
    """
    logs_file = run_dir / "logs" / "logs.jsonl"
    if not logs_file.exists():
        return []

    entries: list[dict[str, Any]] = []
    try:
        with open(logs_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except (json.JSONDecodeError, OSError):
        pass
    return entries


def _filter_log_entries(
    entries: list[dict[str, Any]],
    phase: str | None = None,
    level: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Filter log entries by phase, level, or category.

    Args:
        entries: List of log entry dicts.
        phase: Filter by phase name.
        level: Filter by log level (minimum level threshold).
        category: Filter by category.

    Returns:
        Filtered list of entries.
    """
    # Level ordering for filtering
    level_order = {"trace": 0, "debug": 1, "info": 2, "warn": 3, "error": 4, "fatal": 5}

    filtered = entries

    if phase:
        filtered = [
            e
            for e in filtered
            if e.get("context", {}).get("phase", "").lower() == phase.lower()
        ]

    if level:
        min_level = level_order.get(level.lower(), 0)
        filtered = [
            e
            for e in filtered
            if level_order.get(e.get("level", "info").lower(), 0) >= min_level
        ]

    if category:
        filtered = [
            e for e in filtered if e.get("category", "").lower() == category.lower()
        ]

    return filtered


def _display_log_entry(entry: dict[str, Any]) -> None:
    """Display a single log entry with formatting.

    Args:
        entry: Log entry dict.
    """
    timestamp = entry.get("timestamp", "")
    if "T" in timestamp:
        # Parse ISO format, extract time
        timestamp = timestamp.split("T")[1].split(".")[0]

    level = entry.get("level", "info").upper()
    category = entry.get("category", "")
    message = entry.get("message", "")
    context = entry.get("context", {})
    phase = context.get("phase", "")

    # Color coding by level
    level_colors = {
        "TRACE": "dim",
        "DEBUG": "dim",
        "INFO": "green",
        "WARN": "yellow",
        "ERROR": "red",
        "FATAL": "red bold",
    }
    level_style = level_colors.get(level, "")

    # Build display line
    parts = [f"[dim]{timestamp}[/]", f"[{level_style}]{level:5}[/]"]
    if category:
        parts.append(f"[cyan][{category}][/]")
    if phase:
        parts.append(f"[magenta]({phase})[/]")
    parts.append(message)

    console.print(" ".join(parts))


@logs_app.command(name="show")
def logs_show(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to show logs for",
    ),
    tail: int = typer.Option(
        50,
        "--tail",
        "-n",
        help="Last N entries to show",
    ),
    phase: str | None = typer.Option(
        None,
        "--phase",
        "-p",
        help="Filter by phase",
    ),
    level: str | None = typer.Option(
        None,
        "--level",
        "-l",
        help="Minimum log level (trace, debug, info, warn, error, fatal)",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Show diagnostic information about run lookup",
    ),
) -> None:
    """Display log entries from a run.

    Shows recent log entries with optional filtering by phase or level.

    Examples:
        adw logs show 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw logs show 01HQXK5P3Z7V8R2M4N6T9W1Y3C --tail 100
        adw logs show 01HQXK5P3Z7V8R2M4N6T9W1Y3C --phase build
        adw logs show 01HQXK5P3Z7V8R2M4N6T9W1Y3C --level error
        adw logs show 01HQXK5P3Z7V8R2M4N6T9W1Y3C --debug
    """
    run_dir = _get_run_dir(run_id, debug=debug)

    # Load log entries
    entries = _load_log_entries(run_dir)

    if not entries:
        console.print(f"[yellow]No log entries found for run:[/] {run_id}")
        return

    # Apply filters
    entries = _filter_log_entries(entries, phase=phase, level=level)

    if not entries:
        console.print("[yellow]No entries match the filters[/]")
        return

    # Apply tail limit
    if tail > 0 and len(entries) > tail:
        entries = entries[-tail:]

    # Display header
    console.print(f"\n[bold]Logs for run {run_id}[/]")
    console.print(f"[dim]Showing {len(entries)} entries[/]\n")

    # Display entries
    for entry in entries:
        _display_log_entry(entry)


@logs_app.command(name="follow")
def logs_follow(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to follow logs for",
    ),
    phase: str | None = typer.Option(
        None,
        "--phase",
        "-p",
        help="Filter by phase",
    ),
    interval: float = typer.Option(
        0.1,
        "--interval",
        "-i",
        help="Polling interval in seconds (default: 0.1)",
    ),
) -> None:
    """Stream new log entries in real-time.

    Watches for new log entries and displays them as they arrive.
    Press Ctrl+C to stop following.

    Examples:
        adw logs follow 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw logs follow 01HQXK5P3Z7V8R2M4N6T9W1Y3C --phase build
        adw logs follow 01HQXK5P3Z7V8R2M4N6T9W1Y3C --interval 0.5
    """
    import time

    run_dir = _get_run_dir(run_id)

    # Check if run is active
    context_file = run_dir / "context.json"
    if context_file.exists():
        try:
            context = json.loads(context_file.read_text())
            status = context.get("status", "")
            if status not in ("running", ""):
                console.print(f"[yellow]Run is not active (status: {status})[/]")
                console.print("[dim]Showing existing logs instead...[/]\n")
                # Fall back to show
                entries = _load_log_entries(run_dir)
                entries = _filter_log_entries(entries, phase=phase)
                for entry in entries:
                    _display_log_entry(entry)
                return
        except (json.JSONDecodeError, OSError):
            pass

    logs_file = run_dir / "logs" / "logs.jsonl"
    if not logs_file.exists():
        console.print(f"[yellow]No log file found for run:[/] {run_id}")
        return

    console.print(f"[bold]Following logs for run {run_id}[/]")
    console.print("[dim]Press Ctrl+C to stop[/]\n")

    # Track file position
    try:
        with open(logs_file) as f:
            # Go to end of file
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            # Apply phase filter
                            if phase:
                                entry_phase = entry.get("context", {}).get("phase", "")
                                if entry_phase.lower() != phase.lower():
                                    continue
                            _display_log_entry(entry)
                        except json.JSONDecodeError:
                            pass
                else:
                    # Check if run is still active
                    if context_file.exists():
                        try:
                            context = json.loads(context_file.read_text())
                            status = context.get("status", "")
                            if status not in ("running", ""):
                                console.print(
                                    f"\n[green]Run completed (status: {status})[/]"
                                )
                                break
                        except (json.JSONDecodeError, OSError):
                            pass
                    time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped following logs[/]")


@logs_app.command(name="search")
def logs_search(
    pattern: str = typer.Argument(
        ...,
        help="Pattern to search for (regex supported)",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run",
        "-r",
        help="Search in specific run (otherwise searches all runs)",
    ),
    category: str | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by category",
    ),
) -> None:
    """Search logs for matching entries.

    Searches log entries for pattern matches across runs.

    Examples:
        adw logs search "error" --run 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw logs search "phase.*failed" --category error
        adw logs search "timeout" --run 01HQXK5P3Z7V8R2M4N6T9W1Y3C
    """
    runs_dir = _get_runs_dir()

    # Compile regex pattern
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        console.print(f"[red]Error:[/] Invalid regex pattern: {e}")
        console.print("[dim]Examples of valid patterns:[/]")
        console.print("  [cyan]error[/]              - literal text match")
        console.print("  [cyan]error|warning[/]      - match either word")
        console.print("  [cyan]phase.*failed[/]      - 'phase' followed by 'failed'")
        console.print("  [cyan]\\[ERROR\\][/]          - literal brackets (escaped)")
        raise typer.Exit(1) from None

    # Determine which runs to search
    if run_id:
        run_dirs = [_get_run_dir(run_id)]
    else:
        if not runs_dir.exists():
            console.print("[yellow]No runs found[/]")
            return
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]

    matches: list[tuple[str, dict[str, Any]]] = []

    for run_dir in run_dirs:
        entries = _load_log_entries(run_dir)

        # Apply category filter
        if category:
            entries = _filter_log_entries(entries, category=category)

        # Search for pattern matches
        for entry in entries:
            message = entry.get("message", "")
            if regex.search(message):
                matches.append((run_dir.name, entry))

    if not matches:
        console.print("[yellow]No matches found[/]")
        return

    console.print(f"\n[bold]Found {len(matches)} match(es)[/]\n")

    current_run = None
    for run_name, entry in matches:
        if run_name != current_run:
            current_run = run_name
            console.print(f"\n[bold blue]Run: {run_name}[/]")
        _display_log_entry(entry)


def _load_llm_files(
    llm_dir: Path,
) -> list[tuple[int, str, dict[str, Any], dict[str, Any] | None]]:
    """Load LLM request/response pairs from directory.

    Args:
        llm_dir: Path to the llm/ directory.

    Returns:
        List of (sequence, phase, request, response) tuples.
    """
    if not llm_dir.exists():
        return []

    # Find all request files
    request_files = sorted(llm_dir.glob("*_request.json"))
    pairs: list[tuple[int, str, dict[str, Any], dict[str, Any] | None]] = []

    for req_file in request_files:
        # Parse filename: 001_plan_request.json -> seq=1, phase=plan
        match = re.match(r"(\d+)_(.+)_request\.json", req_file.name)
        if not match:
            continue

        seq = int(match.group(1))
        phase = match.group(2)

        # Load request
        try:
            request: dict[str, Any] = json.loads(req_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        # Try to load matching response
        resp_file = llm_dir / f"{seq:03d}_{phase}_response.json"
        response: dict[str, Any] | None = None
        if resp_file.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                response = json.loads(resp_file.read_text())

        pairs.append((seq, phase, request, response))

    return pairs


def _replay_token_streams(
    llm_dir: Path,
    pairs: list[tuple[int, str, dict[str, Any], dict[str, Any] | None]],
    phase_filter: str | None = None,
) -> None:
    """Replay token streams from JSONL files.

    Args:
        llm_dir: Path to the llm/ directory.
        pairs: List of (sequence, phase, request, response) tuples.
        phase_filter: Optional phase filter.
    """
    import time as time_module

    console.print("\n[bold]Token Stream Replay[/]")
    console.print("[dim]Press Ctrl+C to stop[/]\n")

    try:
        for seq, interaction_phase, _request, _response in pairs:
            # Find stream file
            stream_file = llm_dir / f"{seq:03d}_{interaction_phase}_stream.jsonl"
            if not stream_file.exists():
                msg = f"No stream file for interaction #{seq} ({interaction_phase})"
                console.print(f"[dim]{msg}[/]")
                continue

            console.print(
                f"\n[bold blue]═══ Replaying #{seq} ({interaction_phase}) ═══[/]\n"
            )

            # Read and replay tokens
            prev_time = 0
            try:
                with open(stream_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            event_type = event.get("type", "")
                            content = event.get("content", "")
                            event_time = event.get("t", 0)

                            # Simulate timing delay (scaled down for replay)
                            delay = (event_time - prev_time) / 1000.0  # ms to seconds
                            if delay > 0:
                                time_module.sleep(min(delay * 0.1, 0.05))  # Cap at 50ms
                            prev_time = event_time

                            if event_type == "token" and content:
                                console.print(content, end="")
                        except json.JSONDecodeError:
                            pass
                console.print("\n")  # Newline after stream
            except OSError as e:
                console.print(f"[red]Error reading stream:[/] {e}")

    except KeyboardInterrupt:
        console.print("\n[dim]Stream replay stopped[/]")


@logs_app.command(name="llm")
def logs_llm(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to view LLM interactions for",
    ),
    phase: str | None = typer.Option(
        None,
        "--phase",
        "-p",
        help="Filter by phase",
    ),
    request_only: bool = typer.Option(
        False,
        "--request-only",
        help="Show only requests (prompts)",
    ),
    response_only: bool = typer.Option(
        False,
        "--response-only",
        help="Show only responses",
    ),
    tools: bool = typer.Option(
        False,
        "--tools",
        help="Show only tool calls",
    ),
    stream: bool = typer.Option(
        False,
        "--stream",
        help="Replay token stream",
    ),
) -> None:
    """View LLM prompts and responses for a run.

    Shows the LLM interactions captured during the run, including
    prompts, responses, and tool calls.

    Examples:
        adw logs llm 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw logs llm 01HQXK5P3Z7V8R2M4N6T9W1Y3C --phase plan
        adw logs llm 01HQXK5P3Z7V8R2M4N6T9W1Y3C --request-only
        adw logs llm 01HQXK5P3Z7V8R2M4N6T9W1Y3C --tools
    """
    run_dir = _get_run_dir(run_id)
    llm_dir = run_dir / "llm"

    if not llm_dir.exists():
        console.print(f"[yellow]No LLM captures found for run:[/] {run_id}")
        return

    # Load LLM pairs
    pairs = _load_llm_files(llm_dir)

    if not pairs:
        console.print(f"[yellow]No LLM interactions found for run:[/] {run_id}")
        return

    # Filter by phase
    if phase:
        pairs = [
            (s, p, req, resp) for s, p, req, resp in pairs if p.lower() == phase.lower()
        ]

    if not pairs:
        console.print(f"[yellow]No LLM interactions found for phase:[/] {phase}")
        return

    # Handle stream mode - replay tokens from stream files
    if stream:
        _replay_token_streams(llm_dir, pairs, phase)
        return

    console.print(f"\n[bold]LLM Interactions for run {run_id}[/]")
    console.print(f"[dim]Found {len(pairs)} interaction(s)[/]\n")

    for seq, interaction_phase, request, response in pairs:
        console.print(
            f"\n[bold blue]═══ Interaction #{seq} ({interaction_phase}) ═══[/]"
        )

        # Show request
        if not response_only:
            prompt = request.get("prompt", "")
            params = request.get("params", {})
            timestamp = request.get("timestamp", "")

            console.print(f"\n[bold green]Request[/] [dim]({timestamp})[/]")
            if params:
                model = params.get("model", "unknown")
                console.print(f"[dim]Model: {model}[/]")

            # Truncate long prompts for display
            if len(prompt) > 500:
                console.print(
                    Panel(
                        prompt[:500]
                        + f"\n\n[dim]... (truncated, {len(prompt)} chars total)[/]",
                        title="Prompt",
                        border_style="green",
                    )
                )
            else:
                console.print(Panel(prompt, title="Prompt", border_style="green"))

        # Show response
        if not request_only and response:
            content = response.get("content", "")
            stats = response.get("stats", {})
            tool_calls = response.get("tool_calls", [])
            timestamp = response.get("timestamp", "")

            console.print(f"\n[bold cyan]Response[/] [dim]({timestamp})[/]")

            # Stats
            if stats:
                input_tokens = stats.get("input_tokens", 0)
                output_tokens = stats.get("output_tokens", 0)
                duration_ms = stats.get("duration_ms", 0)
                console.print(
                    f"[dim]Tokens: {input_tokens} in / {output_tokens} out | "
                    f"Duration: {duration_ms}ms[/]"
                )

            # Tool calls (show when tool_calls exist, or when --tools flag is set)
            if tool_calls:
                console.print("\n[bold yellow]Tool Calls:[/]")
                for tc in tool_calls:
                    tc_id = tc.get("id", "")
                    tc_name = tc.get("name", "")
                    tc_input = tc.get("input", {})
                    console.print(f"  [yellow]{tc_name}[/] [dim]({tc_id})[/]")
                    if tc_input:
                        input_str = json.dumps(tc_input, indent=2)
                        if len(input_str) > 200:
                            input_str = input_str[:200] + "\n..."
                        console.print(f"    [dim]{input_str}[/]")

            # Content (skip if tools-only mode)
            if not tools:
                if len(content) > 500:
                    truncated = content[:500]
                    suffix = f"\n\n[dim]... (truncated, {len(content)} total)[/]"
                    console.print(
                        Panel(
                            truncated + suffix,
                            title="Response Content",
                            border_style="cyan",
                        )
                    )
                else:
                    console.print(
                        Panel(content, title="Response Content", border_style="cyan")
                    )


@logs_app.command(name="export")
def logs_export(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to export",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (defaults to <run_id>_export.tar.gz)",
    ),
    format_type: str = typer.Option(
        "tar",
        "--format",
        "-f",
        help="Export format: tar (tar.gz), json, or html",
    ),
    limit: int = typer.Option(
        0,
        "--limit",
        "-l",
        help="Limit log entries in HTML export (0 = all)",
    ),
) -> None:
    """Create a shareable bundle of logs and state.

    Exports logs, LLM captures, snapshots, and context for debugging
    and sharing.

    Examples:
        adw logs export 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw logs export 01HQXK5P3Z7V8R2M4N6T9W1Y3C --output debug.tar.gz
        adw logs export 01HQXK5P3Z7V8R2M4N6T9W1Y3C --format json
        adw logs export 01HQXK5P3Z7V8R2M4N6T9W1Y3C --format html --limit 100
    """
    import shutil
    import tarfile
    import tempfile

    run_dir = _get_run_dir(run_id)

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        if format_type == "json":
            output_path = Path(f"{run_id}_export.json")
        elif format_type == "html":
            output_path = Path(f"{run_id}_export.html")
        else:
            output_path = Path(f"{run_id}_export.tar.gz")

    console.print(f"[bold]Exporting run {run_id}...[/]")

    if format_type == "json":
        # Export as single JSON file
        export_data: dict[str, Any] = {
            "run_id": run_id,
            "exported_at": datetime.now().isoformat(),
        }

        # Load context
        context_file = run_dir / "context.json"
        if context_file.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                export_data["context"] = json.loads(context_file.read_text())

        # Load logs
        export_data["logs"] = _load_log_entries(run_dir)

        # Load LLM interactions
        llm_pairs = _load_llm_files(run_dir / "llm")
        export_data["llm_interactions"] = [
            {"sequence": s, "phase": p, "request": req, "response": resp}
            for s, p, req, resp in llm_pairs
        ]

        # Load snapshots
        snapshots = _list_snapshots(run_id)
        export_data["snapshots"] = []
        for snap in snapshots:
            content = _load_snapshot_content(snap["path"])
            export_data["snapshots"].append(
                {
                    "sequence": snap["sequence"],
                    "label": snap["label"],
                    "content": content,
                }
            )

        output_path.write_text(json.dumps(export_data, indent=2, default=str))

    elif format_type == "html":
        # Export as HTML report
        html_content = _generate_html_report(run_id, run_dir, log_limit=limit)
        output_path.write_text(html_content)

    else:
        # Export as tar.gz
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / run_id
            shutil.copytree(run_dir, tmp_path)

            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(tmp_path, arcname=run_id)

    console.print(f"[green]✓[/] Exported to: {output_path}")
    console.print(f"[dim]Size: {output_path.stat().st_size / 1024:.1f} KB[/]")


def _generate_html_report(run_id: str, run_dir: Path, log_limit: int = 0) -> str:
    """Generate HTML report for a run.

    Args:
        run_id: The run ID.
        run_dir: Path to the run directory.
        log_limit: Maximum log entries to include (0 = all).

    Returns:
        HTML content string.
    """
    # Load data
    context: dict[str, Any] = {}
    context_file = run_dir / "context.json"
    if context_file.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            context = json.loads(context_file.read_text())

    logs = _load_log_entries(run_dir)
    llm_pairs = _load_llm_files(run_dir / "llm")

    # Apply limit if specified
    display_logs = logs[-log_limit:] if log_limit > 0 else logs

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ADW Run Export: {run_id}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }}
        .log-entry {{ font-family: monospace; font-size: 13px; padding: 4px 0; }}
        .log-entry.error {{ color: #d32f2f; }}
        .log-entry.warn {{ color: #f57c00; }}
        .log-entry.info {{ color: #388e3c; }}
        .log-entry.debug {{ color: #757575; }}
        pre {{ background: #f5f5f5; padding: 15px; overflow-x: auto; border-radius: 4px; }}
        .stats {{ color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>ADW Run Export</h1>
    <p><strong>Run ID:</strong> {run_id}</p>
    <p><strong>Feature:</strong> {context.get("feature_description", "N/A")}</p>
    <p><strong>Status:</strong> {context.get("status", "N/A")}</p>
    <p><strong>Exported:</strong> {datetime.now().isoformat()}</p>

    <div class="section">
        <h2>Logs ({len(display_logs)} of {len(logs)} entries)</h2>
"""

    for entry in display_logs:
        level = entry.get("level", "info").lower()
        message = entry.get("message", "")
        timestamp = entry.get("timestamp", "")[:19]
        html += f'        <div class="log-entry {level}">[{timestamp}] [{level.upper()}] {message}</div>\n'

    html += """    </div>

    <div class="section">
        <h2>LLM Interactions</h2>
"""

    for seq, phase, request, response in llm_pairs:
        prompt = request.get("prompt", "")[:500]
        content = (response or {}).get("content", "")[:500]
        stats = (response or {}).get("stats", {})

        html += f"""
        <h3>#{seq} - {phase}</h3>
        <p class="stats">Tokens: {stats.get("input_tokens", 0)} in / {stats.get("output_tokens", 0)} out</p>
        <h4>Prompt</h4>
        <pre>{prompt}{"..." if len(request.get("prompt", "")) > 500 else ""}</pre>
        <h4>Response</h4>
        <pre>{content}{"..." if len((response or {}).get("content", "")) > 500 else ""}</pre>
"""

    html += """    </div>
</body>
</html>
"""
    return html
