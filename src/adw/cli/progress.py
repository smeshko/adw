"""Progress display for ADW pipeline execution.

This module provides the ProgressDisplay class that shows real-time progress
during pipeline execution using the Rich library.

Features:
- Phase headers with status indicators
- Real-time LLM progress with spinner
- Overall pipeline progress bar
- Error display with suggestions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from adw.core.constants import PHASE_SEQUENCE, PR_DESCRIPTION_ARTIFACT
from adw.format import format_duration, format_tokens, status_style
from adw.logging.console import set_active_live

if TYPE_CHECKING:
    from adw.exceptions import ADWError
    from adw.models import PhaseResult

__all__ = ["ProgressDisplay"]


class ProgressDisplay:
    """Display progress for ADW pipeline execution.

    Uses Rich library for formatted console output with:
    - Phase headers with status indicators
    - Real-time LLM progress with spinner
    - Overall pipeline progress bar

    Attributes:
        console: Rich Console instance for output.
        PHASE_COLORS: Mapping of phase names to Rich colors.

    Example:
        >>> from rich.console import Console
        >>> console = Console()
        >>> progress = ProgressDisplay(console)
        >>> progress.on_phase_start("plan")
        [PLAN] Starting phase...
    """

    PHASE_COLORS: dict[str, str] = {
        "plan": "blue",
        "build": "cyan",
        "validate": "magenta",
        "document": "green",
        "ship": "yellow",
    }

    def __init__(
        self,
        console: Console | None = None,
        enabled_phases: list[str] | None = None,
    ) -> None:
        """Initialize the ProgressDisplay.

        Args:
            console: Rich Console instance for output. If None, creates a new one.
            enabled_phases: List of enabled phase names for progress display.
                If None, defaults to all phases in PHASE_SEQUENCE.
                Use this to filter out disabled phases from progress bar.
        """
        self.console = console or Console()
        self._enabled_phases = enabled_phases or list(PHASE_SEQUENCE)
        self._current_phase: str | None = None
        self._live: Live | None = None
        self._progress: Progress | None = None
        self._task_id: TaskID | None = None
        self._completed_phases: list[str] = []
        self._total_tokens: int = 0
        self._start_time_ms: int = 0

    def on_phase_start(self, phase: str) -> None:
        """Display phase starting message.

        Args:
            phase: Phase name starting (plan, build, validate, document, ship).
        """
        self._current_phase = phase
        color = self.PHASE_COLORS.get(phase, "white")

        # Calculate phase position relative to enabled phases
        try:
            phase_num = self._enabled_phases.index(phase) + 1
        except ValueError:
            phase_num = 0
        total_phases = len(self._enabled_phases)

        self.console.print()
        self.console.print(
            Panel(
                f"[bold {color}]{phase.upper()}[/] Starting phase...",
                title=f"Phase {phase_num}/{total_phases}",
                border_style=color,
            )
        )

        # Show overall progress bar (after phase header)
        self._show_progress_bar(current_phase=phase)

    def _show_progress_bar(self, current_phase: str | None = None) -> None:
        """Display the overall pipeline progress bar.

        Shows: [Plan] ✓ [Build] ► [Validate] · [Document]
        with percentage complete based on enabled phases only.

        Args:
            current_phase: Currently executing phase (shown with ►).
        """
        phase_status = []
        for phase in self._enabled_phases:
            color = self.PHASE_COLORS.get(phase, "white")
            if phase in self._completed_phases:
                phase_status.append(f"[green]✓[/] [{color}]{phase}[/]")
            elif phase == current_phase:
                phase_status.append(f"[yellow]►[/] [{color}]{phase}[/]")
            else:
                phase_status.append(f"[dim]· {phase}[/]")

        status_line = " → ".join(phase_status)

        # Calculate percentage based on enabled phases only
        completed = len(self._completed_phases)
        total = len(self._enabled_phases)
        percentage = (completed / total) * 100 if total > 0 else 0

        self.console.print(f"{status_line}  [bold cyan]{percentage:.0f}%[/]")

    def on_llm_start(self) -> None:
        """Start LLM progress display with spinner."""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("·"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        )
        self._live = Live(self._progress, console=self.console, refresh_per_second=4)
        self._live.start()
        # Register Live display for spinner/log coordination
        set_active_live(self._live)
        self._task_id = self._progress.add_task(
            "LLM executing...",
            total=None,
        )

    def on_llm_progress(self, _tokens: int) -> None:
        """Update LLM progress display (no-op, token count removed from UI)."""

    def on_llm_complete(self) -> None:
        """Complete LLM progress display."""
        if self._live is not None:
            self._live.stop()
            # Clear Live display registration for spinner/log coordination
            set_active_live(None)
            self._live = None
        self._progress = None
        self._task_id = None

    def on_phase_complete(self, phase: str, result: PhaseResult) -> None:
        """Display phase completion.

        Args:
            phase: Phase that completed.
            result: Phase result with metrics.
        """
        # Track completed phase
        if phase not in self._completed_phases:
            self._completed_phases.append(phase)
        self._total_tokens += result.tokens_used

        color = self.PHASE_COLORS.get(phase, "white")
        formatted_duration = format_duration(
            result.duration_ms / 1000 if result.duration_ms is not None else None
        )
        artifacts = len(result.artifacts)

        # Build token display with input/output breakdown
        input_display = format_tokens(result.input_tokens)
        cached_total = (
            result.cache_creation_input_tokens + result.cache_read_input_tokens
        )
        if cached_total > 0:
            new_tokens = result.input_tokens - cached_total
            input_display += (
                f" ({format_tokens(max(0, new_tokens))} new, "
                f"{format_tokens(cached_total)} cached)"
            )
        output_display = format_tokens(result.output_tokens)

        self.console.print(
            f"[bold green]✓[/] [{color}]{phase.upper()}[/] completed "
            f"[dim]({formatted_duration}, {artifacts} artifacts, "
            f"in: {input_display}, out: {output_display})[/]"
        )

        # Show updated progress bar
        self._show_progress_bar()

    def on_phase_error(self, phase: str, error: ADWError) -> None:
        """Display phase error.

        Args:
            phase: Phase that failed.
            error: The error that occurred.
        """
        self.on_llm_complete()  # Stop any live display

        self.console.print()
        self.console.print(
            Panel(
                f"[bold red]Error:[/] {error.message}\n\n"
                f"[dim]Suggestion:[/] {error.suggestion}",
                title=f"[red]{phase.upper()} Failed[/]",
                border_style="red",
            )
        )

    def show_pipeline_summary(
        self,
        completed_phases: list[str],
        status: str,
        total_duration_ms: int,
        total_tokens: int,
        run_id: str | None = None,
        pr_url: str | None = None,
        pr_error: str | None = None,
    ) -> None:
        """Show pipeline summary at end of run.

        Args:
            completed_phases: List of completed phase names.
            status: Final run status.
            total_duration_ms: Total run duration in milliseconds.
            total_tokens: Total tokens used.
            run_id: Optional run ID for displaying artifact paths.
            pr_url: URL of the PR the run opened, if any.
            pr_error: Why opening the PR failed, if it did.
        """
        self.console.print()

        # Build phase status line using enabled phases only
        phase_status = []
        for phase in self._enabled_phases:
            color = self.PHASE_COLORS.get(phase, "white")
            if phase in completed_phases:
                phase_status.append(f"[green]✓[/] [{color}]{phase}[/]")
            else:
                phase_status.append(f"[dim]· {phase}[/]")

        status_line = " → ".join(phase_status)

        # Format duration
        duration = format_duration(
            total_duration_ms / 1000 if total_duration_ms is not None else None
        )

        status_color = status_style(status).color

        # Build content with optional PR description path
        content_lines = [
            status_line,
            "",
            f"[bold]Status:[/] [{status_color}]{status}[/]",
            f"[bold]Duration:[/] {duration}",
            f"[bold]Tokens:[/] {format_tokens(total_tokens)}",
        ]

        # Add PR info if document phase completed
        if run_id and "document" in completed_phases:
            content_lines.append("")

            if pr_url:
                content_lines.append(f"[bold]PR Created:[/] [green]{pr_url}[/]")
            else:
                pr_path = f".adw/runs/{run_id}/{PR_DESCRIPTION_ARTIFACT}"
                content_lines.append(f"[bold]PR Description:[/] [cyan]{pr_path}[/]")
                if pr_error:
                    content_lines.append(f"[dim]{escape(pr_error)}[/]")
                    content_lines.append(f"Run 'adw pr {run_id}' to retry")

        self.console.print(
            Panel(
                "\n".join(content_lines),
                title="Pipeline Summary",
                border_style=status_color,
            )
        )
