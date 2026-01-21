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
            phase: Phase name starting (plan, build, validate, document).
        """
        self._current_phase = phase
        color = self.PHASE_COLORS.get(phase, "white")

        # Calculate phase position
        try:
            phase_num = PHASE_SEQUENCE.index(phase) + 1
        except ValueError:
            phase_num = 0
        total_phases = len(PHASE_SEQUENCE)

        # Show overall progress bar
        self._show_progress_bar(current_phase=phase)

        self.console.print()
        self.console.print(
            Panel(
                f"[bold {color}]{phase.upper()}[/] Starting phase...",
                title=f"Phase {phase_num}/{total_phases}",
                border_style=color,
            )
        )

    def _show_progress_bar(self, current_phase: str | None = None) -> None:
        """Display the overall pipeline progress bar.

        Shows: [Plan] ✓ [Build] ► [Validate] · [Document]
        with percentage complete.

        Args:
            current_phase: Currently executing phase (shown with ►).
        """
        phase_status = []
        for phase in PHASE_SEQUENCE:
            color = self.PHASE_COLORS.get(phase, "white")
            if phase in self._completed_phases:
                phase_status.append(f"[green]✓[/] [{color}]{phase}[/]")
            elif phase == current_phase:
                phase_status.append(f"[yellow]►[/] [{color}]{phase}[/]")
            else:
                phase_status.append(f"[dim]· {phase}[/]")

        status_line = " → ".join(phase_status)

        # Calculate percentage
        completed = len(self._completed_phases)
        total = len(PHASE_SEQUENCE)
        percentage = (completed / total) * 100

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
        duration = f"{result.duration_ms / 1000:.1f}s" if result.duration_ms else "N/A"
        artifacts = len(result.artifacts)

        self.console.print(
            f"[bold green]✓[/] [{color}]{phase.upper()}[/] completed "
            f"[dim]({duration}, {artifacts} artifacts, {result.tokens_used} tokens)[/]"
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

        # Build phase status line
        phase_status = []
        for phase in PHASE_SEQUENCE:
            color = self.PHASE_COLORS.get(phase, "white")
            if phase in completed_phases:
                phase_status.append(f"[green]✓[/] [{color}]{phase}[/]")
            else:
                phase_status.append(f"[dim]· {phase}[/]")

        status_line = " → ".join(phase_status)

        # Format duration
        duration = f"{total_duration_ms / 1000:.1f}s"

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
            f"[bold]Tokens:[/] {total_tokens:,}",
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
        auto_create_pr_enabled: bool = True,
    ) -> AutoPRResult | None:
        """Attempt automatic PR creation after successful run.

        This method attempts to create a PR using the generated PR description.
        It handles all prerequisites checking and error handling gracefully.

        Args:
            run_id: ID of the completed run.
            context: RunContext with feature description.
            runs_dir: Path to runs directory.
            auto_create_pr_enabled: Whether auto-PR is enabled in config.

        Returns:
            AutoPRResult with outcome, or None if auto-PR is disabled.
        """
        if not auto_create_pr_enabled:
            return None

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
