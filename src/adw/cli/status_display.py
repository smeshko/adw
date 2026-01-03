"""Status display for ADW CLI.

This module provides the StatusDisplay class that shows run status
using the Rich library, implementing run status display with color coding.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adw.core.constants import PHASE_SEQUENCE
from adw.models import RunContext

__all__ = ["StatusDisplay", "output_json"]


class StatusDisplay:
    """Display run status using Rich.

    Implements status display with color coding:
    - Green: completed
    - Red: failed
    - Yellow: running
    - Orange: interrupted

    Attributes:
        console: Rich Console instance for output.

    Example:
        >>> from rich.console import Console
        >>> console = Console()
        >>> display = StatusDisplay(console)
        >>> display.show_status(context)
    """

    STATUS_COLORS = {
        "running": "yellow",
        "completed": "green",
        "failed": "red",
        "interrupted": "orange1",
        "aborted": "red",
    }

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the StatusDisplay.

        Args:
            console: Rich Console instance for output. If None, creates a new one.
        """
        self.console = console or Console()

    def show_status(
        self,
        context: RunContext,
        *,
        verbose: bool = False,
    ) -> None:
        """Display run status.

        Args:
            context: The run context to display.
            verbose: Show detailed information.
        """
        status_color = self.STATUS_COLORS.get(context.status, "white")

        # Truncate long feature descriptions
        feature = context.feature_description
        if len(feature) > 60:
            feature = f"{feature[:57]}..."

        # Calculate duration
        duration = self._format_duration(context)

        # Build status table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="bold")
        table.add_column("Value")

        table.add_row("Run ID", context.run_id)
        table.add_row("Feature", feature)
        table.add_row("Status", f"[{status_color}]{context.status}[/]")
        table.add_row("Phase", context.current_phase or "—")
        table.add_row("Started", self._format_timestamp(context.started_at))

        if context.completed_at:
            table.add_row("Completed", self._format_timestamp(context.completed_at))

        table.add_row("Duration", duration)

        if verbose:
            table.add_row("Phases", self._format_phases(context))
            table.add_row("Tokens", f"{context.total_tokens:,}")
            table.add_row("Artifacts", str(self._count_artifacts(context)))

        # Wrap in panel
        self.console.print()
        self.console.print(
            Panel(table, title="Run Status", border_style=status_color)
        )

        # Show failure details (UX-3)
        if context.status == "failed":
            self._show_failure_details(context)

    def _show_failure_details(self, context: RunContext) -> None:
        """Show failure details with resume hint.

        UX-3: Failed status includes error message, suggestion, resume command.
        """
        self.console.print()
        self.console.print(
            Panel(
                f"[red]Phase Failed:[/] {context.current_phase}\n\n"
                f"[dim]To resume this run:[/]\n"
                f"  adw resume {context.run_id}",
                title="[red]Recovery[/]",
                border_style="red",
            )
        )

    def _format_duration(self, context: RunContext) -> str:
        """Format run duration in human-readable form."""
        if context.completed_at and context.started_at:
            delta = context.completed_at - context.started_at
            total_seconds = int(delta.total_seconds())
        elif context.started_at:
            delta = datetime.now(UTC) - context.started_at
            total_seconds = int(delta.total_seconds())
        else:
            return "—"

        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"

    def _format_timestamp(self, dt: datetime | None) -> str:
        """Format timestamp for display."""
        if not dt:
            return "—"
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    def _format_phases(self, context: RunContext) -> str:
        """Format phase progress line."""
        parts = []
        for phase in PHASE_SEQUENCE:
            if phase in context.phase_history:
                parts.append(f"[green]✓ {phase}[/]")
            elif phase == context.current_phase:
                parts.append(f"[yellow]► {phase}[/]")
            else:
                parts.append(f"[dim]· {phase}[/]")
        return " → ".join(parts)

    def _count_artifacts(self, context: RunContext) -> int:
        """Count total artifacts across all phases."""
        total = 0
        for artifacts in context.artifacts.values():
            total += len(artifacts)
        return total


def output_json(context: RunContext, console: Console | None = None) -> None:
    """Output run status as JSON.

    Args:
        context: The run context to output.
        console: Rich Console for output. If None, creates a new one.
    """
    console = console or Console()

    # Calculate additional fields
    duration_ms = 0
    if context.completed_at and context.started_at:
        duration_ms = int(
            (context.completed_at - context.started_at).total_seconds() * 1000
        )

    # Count artifacts
    artifact_count = sum(len(artifacts) for artifacts in context.artifacts.values())

    data = {
        "run_id": context.run_id,
        "feature_description": context.feature_description,
        "status": context.status,
        "current_phase": context.current_phase,
        "completed_phases": context.phase_history,
        "started_at": context.started_at.isoformat() if context.started_at else None,
        "completed_at": (
            context.completed_at.isoformat() if context.completed_at else None
        ),
        "duration_ms": duration_ms,
        "tokens_used": context.total_tokens,
        "phase_tokens": context.phase_tokens,
        "artifact_count": artifact_count,
    }

    console.print_json(data=data)
