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

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from adw.core.constants import PHASE_SEQUENCE, PR_DESCRIPTION_ARTIFACT
from adw.logging.console import set_active_live

if TYPE_CHECKING:
    from adw.cli.pr import AutoPRResult
    from adw.exceptions import ADWError
    from adw.models import PhaseResult, RunContext

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
        STATUS_ICONS: Mapping of status names to display icons.

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

    STATUS_ICONS: dict[str, str] = {
        "pending": "·",
        "running": "►",
        "completed": "✓",
        "failed": "✗",
        "aborted": "⊘",
        "interrupted": "⏸",
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
            TextColumn("[cyan]Tokens: {task.fields[tokens]}"),
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
            tokens=0,
        )

    def on_llm_progress(self, tokens: int) -> None:
        """Update LLM progress display.

        Args:
            tokens: Current token count.
        """
        if self._progress is not None and self._task_id is not None:
            self._progress.update(self._task_id, tokens=tokens)

    def on_llm_complete(self) -> None:
        """Complete LLM progress display."""
        if self._live is not None:
            self._live.stop()
            # Clear Live display registration for spinner/log coordination
            set_active_live(None)
            self._live = None
        self._progress = None
        self._task_id = None

    @staticmethod
    def _format_duration(duration_ms: int | None) -> str:
        """Format duration for display.

        Returns '13m44s' for >= 60s, '45.2s' for < 60s, 'N/A' for None.
        """
        if duration_ms is None:
            return "N/A"
        total_seconds = duration_ms / 1000
        if total_seconds >= 60:
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            return f"{minutes}m{seconds:02d}s"
        return f"{total_seconds:.1f}s"

    @staticmethod
    def _format_tokens(count: int) -> str:
        """Format token count with K/M abbreviation."""
        if count >= 1_000_000:
            value = count / 1_000_000
            return f"{value:.1f}M" if value != int(value) else f"{int(value)}M"
        if count >= 1_000:
            value = count / 1_000
            return f"{value:.0f}K" if value >= 10 else f"{value:.1f}K"
        return str(count)

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
        formatted_duration = self._format_duration(result.duration_ms)
        artifacts = len(result.artifacts)

        # Build token display with input/output breakdown
        input_display = self._format_tokens(result.input_tokens)
        cached_total = (
            result.cache_creation_input_tokens + result.cache_read_input_tokens
        )
        if cached_total > 0:
            new_tokens = result.input_tokens - cached_total
            input_display += (
                f" ({self._format_tokens(max(0, new_tokens))} new, "
                f"{self._format_tokens(cached_total)} cached)"
            )
        output_display = self._format_tokens(result.output_tokens)

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
        pr_result: AutoPRResult | None = None,
    ) -> None:
        """Show pipeline summary at end of run.

        Args:
            completed_phases: List of completed phase names.
            status: Final run status.
            total_duration_ms: Total run duration in milliseconds.
            total_tokens: Total tokens used.
            run_id: Optional run ID for displaying artifact paths.
            pr_result: Optional result of automatic PR creation attempt (Story ISS-011).
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
        duration = self._format_duration(total_duration_ms)

        # Status color: green for completed, orange for aborted, red for failed
        if status == "completed":
            status_color = "green"
        elif status == "aborted":
            status_color = "dark_orange"  # Distinct orange for aborted status
        elif status == "interrupted":
            status_color = "cyan"
        else:
            status_color = "red"

        # Build content with optional PR description path (Story 9.4)
        content_lines = [
            status_line,
            "",
            f"[bold]Status:[/] [{status_color}]{status}[/]",
            f"[bold]Duration:[/] {duration}",
            f"[bold]Tokens:[/] {self._format_tokens(total_tokens)}",
        ]

        # Add PR info if document phase completed (Story 9.4, enhanced by ISS-011)
        if run_id and "document" in completed_phases:
            content_lines.append("")

            if pr_result and pr_result.success:
                # PR was created successfully
                content_lines.append(
                    f"[bold]PR Created:[/] [green]{pr_result.pr_url}[/]"
                )
            elif pr_result and not pr_result.success:
                # PR creation was attempted but failed/skipped
                pr_path = f".adw/runs/{run_id}/{PR_DESCRIPTION_ARTIFACT}"
                content_lines.append(f"[bold]PR Description:[/] [cyan]{pr_path}[/]")

                # Add contextual hint based on failure reason
                if "remote" in pr_result.reason.lower():
                    content_lines.append(
                        "[dim]ℹ No git remote - push to create PR manually[/]"
                    )
                elif "installed" in pr_result.reason.lower():
                    content_lines.append(
                        "[dim]ℹ Install GitHub CLI (gh) for automatic PR creation[/]"
                    )
                elif "authenticated" in pr_result.reason.lower():
                    content_lines.append(
                        "[dim]ℹ Run 'gh auth login' to enable auto PR creation[/]"
                    )
                else:
                    # Generic hint for other failures
                    content_lines.append(
                        f"[dim]ℹ Run 'adw pr {run_id}' to create PR manually[/]"
                    )
            else:
                # No PR result provided (backward compatibility)
                pr_path = f".adw/runs/{run_id}/{PR_DESCRIPTION_ARTIFACT}"
                content_lines.append(f"[bold]PR Description:[/] [cyan]{pr_path}[/]")

        self.console.print(
            Panel(
                "\n".join(content_lines),
                title="Pipeline Summary",
                border_style=status_color,
            )
        )

    def try_auto_create_pr(
        self,
        run_id: str,
        context: RunContext,
        runs_dir: Path,
    ) -> AutoPRResult | None:
        """Attempt automatic PR creation after successful run.

        This method attempts to create a PR using the generated PR description.
        It handles all prerequisites checking and error handling gracefully.

        Args:
            run_id: ID of the completed run.
            context: RunContext with feature description.
            runs_dir: Path to runs directory.

        Returns:
            AutoPRResult with outcome, or None on failure.
        """
        # Import here to avoid circular imports
        from adw.cli.pr import AutoPRResult, auto_create_pr

        try:
            result = auto_create_pr(run_id, context, runs_dir)

            if result.success:
                self.console.print(
                    f"[bold green]✓[/] PR created: [cyan]{result.pr_url}[/]"
                )
            else:
                self.console.print(f"[dim]ℹ Auto-PR skipped: {result.reason}[/]")

            return result

        except Exception as e:
            # Don't fail the run if PR creation fails
            self.console.print(f"[dim]ℹ Auto-PR failed: {e}[/]")
            return AutoPRResult(
                success=False,
                reason=str(e),
                suggestion="Run 'adw pr' manually",
            )
