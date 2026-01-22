"""Logs CLI subcommands for state inspection and debugging.

This module provides CLI commands for inspecting run state and exporting logs.

Commands:
- logs follow <run_id>: Stream real-time LLM output from live.log
- logs state <run_id>: Display current or specific snapshot state
- logs export <run_id>: Create a shareable bundle of logs and state
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
from ulid import ULID

console = Console()

# Pattern to parse structured log lines with optional level prefix:
# Format 1: [timestamp] [CATEGORY] content
# Format 2: [timestamp] [LEVEL] [COMPONENT] content (prefer COMPONENT)
LOG_LINE_PATTERN = re.compile(
    r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[(\w+)\] (.*)$"
)
# Pattern to extract component from content that starts with [COMPONENT]
COMPONENT_PATTERN = re.compile(r"^\[(\w+)\] (.*)$")

# Panel border colors by log category
PANEL_COLORS: dict[str, str] = {
    "PHASE": "magenta",
    "LLM": "cyan",
    "TOOL": "yellow",
    "ERROR": "red",
    "INFO": "green",
    "WARN": "yellow",
}

# Color for LLM output content (distinct from LLM markers)
LLM_OUTPUT_COLOR = "orange3"

# ANSI escape code pattern for stripping colors
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text.

    Args:
        text: Text potentially containing ANSI codes.

    Returns:
        Clean text without ANSI codes.
    """
    return ANSI_PATTERN.sub("", text)


def _parse_log_line(line: str) -> tuple[str, str, str] | None:
    """Parse a structured log line into components.

    Strips ANSI codes before parsing to handle colored log output.
    Handles two formats:
    - [timestamp] [CATEGORY] content
    - [timestamp] [LEVEL] [COMPONENT] content (extracts COMPONENT as category)

    Args:
        line: A single log line (may contain ANSI codes).

    Returns:
        Tuple of (timestamp, category, content) if structured log line,
        None otherwise.
    """
    # Strip ANSI codes first so regex can match
    clean_line = _strip_ansi(line.strip())
    match = LOG_LINE_PATTERN.match(clean_line)
    if match:
        timestamp = match.group(1)
        category = match.group(2)
        content = match.group(3)

        # Check if content starts with [COMPONENT] - if so, use that as category
        # This handles format: [timestamp] [INFO] [PHASE] message
        component_match = COMPONENT_PATTERN.match(content)
        if component_match:
            component = component_match.group(1)
            # Only override if component is a known category (PHASE, LLM, TOOL, etc.)
            if component in PANEL_COLORS:
                category = component
                content = component_match.group(2)

        return timestamp, category, content
    return None


class LogRenderer:
    """Stateful renderer for log lines with LLM content accumulation."""

    def __init__(self) -> None:
        """Initialize the renderer state."""
        self.in_llm_stream = False
        self.llm_buffer: list[str] = []

    def _flush_llm_buffer(self) -> None:
        """Flush accumulated LLM content as a single panel."""
        if self.llm_buffer:
            content = "\n".join(self.llm_buffer)
            panel = Panel(
                content,
                title=f"[{LLM_OUTPUT_COLOR}]LLM Output[/]",
                border_style=LLM_OUTPUT_COLOR,
                padding=(0, 1),
            )
            console.print(panel)
            self.llm_buffer = []

    def render(self, line: str) -> None:
        """Render a log line, accumulating LLM content into single panels.

        Args:
            line: The log line to render.
        """
        parsed = _parse_log_line(line)

        if parsed:
            timestamp, category, content = parsed
            color = PANEL_COLORS.get(category, "dim")
            clean_content = _strip_ansi(content)

            # Detect LLM stream boundaries
            if category == "LLM":
                if "Token stream begins" in clean_content:
                    # Flush any pending LLM content first
                    self._flush_llm_buffer()
                    # Show the marker in a panel
                    panel = Panel(
                        clean_content,
                        title=f"[dim]{timestamp}[/] [{color}]{category}[/]",
                        border_style=color,
                        padding=(0, 1),
                    )
                    console.print(panel)
                    self.in_llm_stream = True
                    return

                if "Token stream ends" in clean_content:
                    # Flush accumulated LLM content as one panel
                    self._flush_llm_buffer()
                    # Show the end marker
                    panel = Panel(
                        clean_content,
                        title=f"[dim]{timestamp}[/] [{color}]{category}[/]",
                        border_style=color,
                        padding=(0, 1),
                    )
                    console.print(panel)
                    self.in_llm_stream = False
                    return

            # For TOOL calls during LLM stream, flush buffer first
            if self.in_llm_stream and category == "TOOL":
                self._flush_llm_buffer()

            # Regular structured log line - show in panel
            panel = Panel(
                clean_content,
                title=f"[dim]{timestamp}[/] [{color}]{category}[/]",
                border_style=color,
                padding=(0, 1),
            )
            console.print(panel)

        else:
            # Unstructured content (LLM streaming text or other)
            clean_line = _strip_ansi(line.rstrip())
            if not clean_line:
                # Empty line in LLM stream - add to buffer as blank
                if self.in_llm_stream:
                    self.llm_buffer.append("")
                return

            if self.in_llm_stream:
                # Accumulate LLM streaming content
                self.llm_buffer.append(clean_line)
            else:
                # Non-streaming unstructured content - show in dim panel
                panel = Panel(
                    clean_line,
                    border_style="dim",
                    padding=(0, 1),
                )
                console.print(panel)


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
    help="View logs and state for debugging",
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
        "[dim]Suggestion:[/] Use 'adw logs state --list-snapshots' to see available"
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


@logs_app.command(name="follow")
def logs_follow(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to follow logs for",
    ),
    interval: float = typer.Option(
        0.1,
        "--interval",
        "-i",
        help="Polling interval in seconds (default: 0.1)",
    ),
    replay: bool = typer.Option(
        False,
        "--replay",
        "-r",
        help="Replay entire log file from beginning (for completed runs)",
    ),
) -> None:
    """Stream LLM output in real-time from live.log.

    For running executions: follows new output as it's written.
    For completed runs: use --replay to see full output.

    Examples:
        adw logs follow 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw logs follow 01HQXK5P3Z7V8R2M4N6T9W1Y3C --replay
        adw logs follow 01HQXK5P3Z7V8R2M4N6T9W1Y3C --interval 0.5
    """
    import time

    run_dir = _get_run_dir(run_id)

    live_log = run_dir / "live.log"
    context_file = run_dir / "context.json"

    # Check run status
    run_status = ""
    if context_file.exists():
        try:
            context = json.loads(context_file.read_text())
            run_status = context.get("status", "")
        except (json.JSONDecodeError, OSError):
            pass

    # If run is not active and not replay mode, inform user
    if run_status not in ("running", "") and not replay:
        console.print(f"[yellow]Run is not active (status: {run_status})[/]")
        if live_log.exists():
            console.print("[dim]Use --replay to view the complete log[/]\n")
        return

    # Wait for live.log to appear if run is active
    wait_count = 0
    while not live_log.exists():
        if wait_count == 0:
            console.print("[dim]Waiting for live.log to appear...[/]")
        wait_count += 1
        if wait_count > 50:  # 5 seconds
            console.print(f"[yellow]No live.log found for run:[/] {run_id}")
            return
        time.sleep(0.1)

    console.print(f"[bold]Following live output for run {run_id}[/]")
    console.print("[dim]Press Ctrl+C to stop[/]\n")

    try:
        with open(live_log, encoding="utf-8") as f:
            # For replay mode or completed runs, start from beginning
            # For active runs, skip to end and follow
            if not replay and run_status in ("running", ""):
                f.seek(0, 2)  # Seek to end

            # Create renderer to track state and accumulate LLM content
            renderer = LogRenderer()

            while True:
                line = f.readline()
                if line:
                    # Render line with colored panels, accumulating LLM content
                    renderer.render(line)
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
        help="Limit log lines in HTML export (0 = all)",
    ),
) -> None:
    """Create a shareable bundle of logs and state.

    Exports live.log, snapshots, and context for debugging and sharing.

    Examples:
        adw logs export 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw logs export 01HQXK5P3Z7V8R2M4N6T9W1Y3C --output debug.tar.gz
        adw logs export 01HQXK5P3Z7V8R2M4N6T9W1Y3C --format json
        adw logs export 01HQXK5P3Z7V8R2M4N6T9W1Y3C --format html --limit 100
    """
    import html
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

        # Load live.log content
        live_log = run_dir / "live.log"
        if live_log.exists():
            export_data["live_log"] = live_log.read_text()
        else:
            export_data["live_log"] = ""

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
        context: dict[str, Any] = {}
        context_file = run_dir / "context.json"
        if context_file.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                context = json.loads(context_file.read_text())

        # Load live.log content
        live_log_content = ""
        live_log = run_dir / "live.log"
        if live_log.exists():
            live_log_content = live_log.read_text()

        # Apply limit if specified (limit to last N lines)
        log_lines = live_log_content.splitlines()
        total_lines = len(log_lines)
        if limit > 0:
            log_lines = log_lines[-limit:]

        # Build HTML
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>ADW Run Export: {run_id}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }}
        pre {{ background: #1e1e1e; color: #d4d4d4; padding: 15px; overflow-x: auto; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; }}
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
        <h2>Live Log ({len(log_lines)} of {total_lines} lines)</h2>
        <pre>{html.escape(chr(10).join(log_lines))}</pre>
    </div>
</body>
</html>
"""
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
