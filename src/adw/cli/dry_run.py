"""Dry-run display for ADW CLI.

This module provides the DryRunDisplay class that shows a preview of
what would happen during a run execution, without actually executing
any phases or modifying state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adw.core.constants import PHASE_SEQUENCE

if TYPE_CHECKING:
    from adw.models import ProjectConfig

__all__ = ["DryRunDisplay"]


class DryRunDisplay:
    """Display dry-run preview using Rich.

    Shows what would happen during a run execution:
    - Phases that would execute (full pipeline or single phase)
    - Pre/post hooks for each phase
    - Project configuration
    - Artifacts that would be loaded (with --from-run)

    Attributes:
        console: Rich Console instance for output.

    Example:
        >>> from rich.console import Console
        >>> console = Console()
        >>> display = DryRunDisplay(console)
        >>> display.show_execution_preview(
        ...     feature="Add user authentication",
        ...     phase=None,  # Full pipeline
        ...     from_run=None,
        ... )
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the DryRunDisplay.

        Args:
            console: Rich Console instance for output. If None, creates a new one.
        """
        self.console = console or Console()

    def show_execution_preview(
        self,
        feature: str,
        phase: str | None = None,
        from_run: str | None = None,
        config: ProjectConfig | None = None,
    ) -> None:
        """Display the execution preview.

        Shows what would happen during execution without actually
        running any phases.

        Args:
            feature: Feature description for the run.
            phase: Single phase to execute, or None for full pipeline.
            from_run: Source run ID for artifact loading, or None.
            config: Project configuration for hook display, or None.
        """
        # Determine phases to show
        if phase:
            phases_to_show = [phase]
            mode = f"Single Phase: {phase}"
        else:
            phases_to_show = list(PHASE_SEQUENCE)
            mode = "Full Pipeline"

        # Show header panel
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Feature:[/] {feature}\n"
                f"[bold]Mode:[/] {mode}\n"
                f"[dim]Run ID:[/] (would be generated)",
                title="[bold blue]Dry Run Preview[/]",
                border_style="blue",
            )
        )

        # Show phases table with hooks from config
        self._show_phases_table(phases_to_show, config)

        # Show configuration display if config provided
        if config:
            self._show_config_table(config)

        # Show artifact info if --from-run specified
        if from_run:
            self._show_artifact_preview(from_run, phase)

        # Show dry-run notice
        self.console.print()
        self.console.print(
            "[yellow]Dry run mode - no execution will occur[/]"
        )
        self.console.print()

    def _show_phases_table(
        self,
        phases: list[str],
        config: ProjectConfig | None = None,
    ) -> None:
        """Display table of phases that would execute.

        Args:
            phases: List of phase names to show.
            config: Project configuration for hook display, or None.
        """
        self.console.print()

        table = Table(title="Phases to Execute")
        table.add_column("Phase", style="cyan")
        table.add_column("Pre-Hook", style="dim")
        table.add_column("Post-Hook", style="dim")

        for phase_name in phases:
            pre_hook = "—"
            post_hook = "—"

            # Get hooks from config if available
            if config and phase_name in config.phases:
                phase_config = config.phases[phase_name]
                if phase_config.pre_hook:
                    pre_hook = phase_config.pre_hook
                if phase_config.post_hook:
                    post_hook = phase_config.post_hook

            table.add_row(phase_name, pre_hook, post_hook)

        self.console.print(table)

    def _show_config_table(self, config: ProjectConfig) -> None:
        """Display table of project configuration.

        Args:
            config: Project configuration to display.
        """
        self.console.print()

        table = Table(title="Project Configuration")
        table.add_column("Setting", style="bold")
        table.add_column("Value")

        # Core project settings
        table.add_row("Name", config.name)
        table.add_row("Language", config.language)
        if config.framework:
            table.add_row("Framework", config.framework)
        table.add_row("Platform", config.platform)

        # Commands
        if config.test_command:
            table.add_row("Test Command", config.test_command)
        if config.build_command:
            table.add_row("Build Command", config.build_command)

        # LLM settings
        table.add_row("LLM Path", config.llm.path)
        table.add_row("LLM Timeout", f"{config.llm.timeout_seconds}s")

        # Git integration
        git_status = "enabled" if config.git.enabled else "disabled"
        table.add_row("Git Integration", git_status)

        self.console.print(table)

    def _show_artifact_preview(
        self,
        from_run: str,
        target_phase: str | None,
    ) -> None:
        """Display preview of artifacts from source run.

        Args:
            from_run: Source run ID to load artifacts from.
            target_phase: Target phase (None for full pipeline).
        """
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Source Run:[/] {from_run}\n"
                f"[dim]Artifacts would be loaded from this run[/]",
                title="[bold cyan]Artifact Source[/]",
                border_style="cyan",
            )
        )
