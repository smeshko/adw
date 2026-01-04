"""Run display for ADW CLI.

This module provides the RunDisplay class that shows run information
using the Rich library, implementing UX-12 specification for run headers.
"""

from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.panel import Panel

__all__ = ["RunDisplay"]


class RunDisplay:
    """Display run information using Rich.

    Implements UX-12 specification for run header display:
    - Run ID (ULID)
    - Feature description (truncated if long)
    - Started timestamp

    Attributes:
        console: Rich Console instance for output.

    Example:
        >>> from rich.console import Console
        >>> from datetime import datetime, UTC
        >>> console = Console()
        >>> display = RunDisplay(console)
        >>> display.show_run_header(
        ...     run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        ...     feature="Add user authentication",
        ...     started_at=datetime.now(UTC),
        ... )
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the RunDisplay.

        Args:
            console: Rich Console instance for output. If None, creates a new one.
        """
        self.console = console or Console()

    def show_run_header(
        self,
        run_id: str,
        feature: str,
        started_at: datetime,
    ) -> None:
        """Display the run header panel.

        UX-12: Run header panel displays run ID, feature, started timestamp.

        Args:
            run_id: The ULID run identifier.
            feature: Feature description (will be truncated if long).
            started_at: When the run started.
        """
        # Truncate long feature descriptions
        max_len = 60
        feature_display = (
            f"{feature[:max_len]}..." if len(feature) > max_len else feature
        )

        timestamp = started_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        self.console.print()
        self.console.print(
            Panel(
                f"[bold cyan]Run ID:[/] {run_id}\n"
                f"[bold]Feature:[/] {feature_display}\n"
                f"[dim]Started:[/] {timestamp}",
                title="[bold blue]ADW Run[/]",
                border_style="blue",
            )
        )
        self.console.print()

    def show_resume_header(
        self,
        run_id: str,
        feature: str,
        completed_phases: list[str],
        resume_phase: str,
    ) -> None:
        """Display the resume header panel.

        Shows run resume information including completed phases and which
        phase will resume.

        Args:
            run_id: The ULID run identifier.
            feature: Feature description (will be truncated if long).
            completed_phases: List of phases that completed successfully.
            resume_phase: The phase that will resume/restart.

        Example:
            >>> display.show_resume_header(
            ...     run_id="01HQXK5P3Z...",
            ...     feature="Add user auth",
            ...     completed_phases=["plan"],
            ...     resume_phase="build",
            ... )
        """
        # Truncate long feature descriptions
        max_len = 60
        feature_display = (
            f"{feature[:max_len]}..." if len(feature) > max_len else feature
        )

        # Format completed phases with checkmarks
        completed_display = ""
        if completed_phases:
            phase_list = ", ".join(f"✓ {p}" for p in completed_phases)
            completed_display = f"\n[green]Completed:[/] {phase_list}"

        self.console.print()
        self.console.print(
            Panel(
                f"[bold cyan]Run ID:[/] {run_id}\n"
                f"[bold]Feature:[/] {feature_display}"
                f"{completed_display}\n"
                f"[yellow]Resuming from:[/] {resume_phase}",
                title="[bold yellow]Resuming Run[/]",
                border_style="yellow",
            )
        )
        self.console.print()
