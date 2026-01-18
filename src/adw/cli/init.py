"""CLI init implementation for initializing ADW projects.

This module provides the init logic that creates the .adw/ directory
structure and generates project configuration based on auto-detection.
Supports both minimal setup and interactive wizard modes.
"""

from __future__ import annotations

import signal
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from adw.config.detector import ProjectTypeDetector
from adw.config.initializer import ProjectInitializer

console = Console()

# Global flag to track if setup was interrupted
_interrupted = False


def _interrupt_handler(signum: int, frame: Any) -> None:
    """Signal handler for Ctrl+C interrupt.

    Args:
        signum: Signal number (SIGINT).
        frame: Current stack frame.
    """
    global _interrupted
    _interrupted = True
    console.print()
    console.print("[yellow]Setup cancelled. No files created.[/]")
    raise SystemExit(0)


@contextmanager
def _setup_interrupt_handler() -> Generator[None]:
    """Context manager to install and restore interrupt handler.

    Yields:
        None, while interrupt handler is active.
    """
    global _interrupted
    _interrupted = False

    # Save original handler
    original_handler = signal.signal(signal.SIGINT, _interrupt_handler)

    try:
        yield
    finally:
        # Restore original handler
        signal.signal(signal.SIGINT, original_handler)


def init(
    force: bool = False,
    language: str | None = None,
    wizard: bool = False,
    no_interactive: bool = False,
) -> None:
    """Initialize ADW in the current directory.

    Creates .adw/ directory with project configuration.
    Auto-detects project type and sets appropriate defaults.

    Args:
        force: If True, overwrite existing configuration.
        language: Override detected language (python, javascript, etc.).
        wizard: If True, force wizard mode without prompting.
        no_interactive: If True, force minimal mode without prompting.

    Raises:
        ConfigError: If project is already initialized and force is False.
    """
    # Install interrupt handler for clean Ctrl+C handling
    with _setup_interrupt_handler():
        project_root = Path.cwd()
        adw_dir = project_root / ".adw"

        # Check if already initialized and handle overwrite confirmation
        if adw_dir.exists() and not force:
            # Show warning panel for existing configuration
            console.print()
            console.print(
                Panel(
                    "[yellow]Existing configuration found.[/]\n"
                    "This will overwrite all settings.",
                    title="[yellow]Warning[/]",
                    border_style="yellow",
                )
            )

            # In non-interactive mode, refuse to overwrite without --force
            if no_interactive:
                console.print(
                    "[red]Error:[/] Cannot overwrite existing configuration "
                    "in non-interactive mode without --force."
                )
                console.print(
                    "[dim]Use --force to overwrite existing configuration.[/]"
                )
                raise SystemExit(1)

            # Require explicit confirmation to proceed
            if not Confirm.ask(
                "Do you want to overwrite the existing configuration?",
                default=False,
            ):
                console.print("[dim]Setup cancelled. No changes made.[/]")
                return

        # Determine setup mode
        use_wizard = _determine_setup_mode(wizard, no_interactive)

        if use_wizard:
            # Enter wizard flow
            _run_wizard_setup(project_root)
        else:
            # Minimal setup path
            _run_minimal_setup(project_root, language, force, no_interactive)


def _determine_setup_mode(wizard: bool, no_interactive: bool) -> bool:
    """Determine whether to use wizard or minimal setup.

    Args:
        wizard: If True, force wizard mode.
        no_interactive: If True, force minimal mode.

    Returns:
        True if wizard mode should be used, False for minimal.
    """
    if wizard:
        return True
    if no_interactive:
        return False

    # Prompt user for choice
    console.print()
    return Confirm.ask("Would you like guided setup?", default=True)


def _run_wizard_setup(project_root: Path) -> None:
    """Run the interactive wizard setup.

    Args:
        project_root: Root directory of the project.

    Note:
        Full implementation will be added in Task 4.
        For now, this is a stub that displays a message.
    """
    from adw.cli.wizard import BasicsStepHandler, WizardFlowController, WizardStep
    from adw.models.wizard import WizardState

    console.print()
    console.print("[bold blue]Starting guided setup wizard...[/]")
    console.print()

    # Create controller and state
    state = WizardState()
    controller = WizardFlowController(state=state)

    # Register step handlers
    controller.register_step_handler(
        WizardStep.BASICS, BasicsStepHandler(project_root=project_root)
    )

    # Run the wizard flow
    completed = controller.run()

    if not completed:
        # Wizard was cancelled - exit without success message
        return

    console.print("[dim]Wizard flow will be implemented in subsequent stories.[/]")


def _run_minimal_setup(
    project_root: Path,
    language: str | None,
    force: bool,
    no_interactive: bool = False,
) -> None:
    """Run minimal setup with auto-detection.

    Args:
        project_root: Root directory of the project.
        language: Override detected language.
        force: Whether to overwrite existing config.
        no_interactive: If True, skip confirmation prompts.
    """
    adw_dir = project_root / ".adw"

    # Detect project type
    detector = ProjectTypeDetector()
    detected_type = detector.detect(project_root)

    # Validate and apply language override
    if language:
        valid_languages = set(detector.DEFAULTS.keys()) - {"unknown"}
        if language not in valid_languages:
            console.print(
                f"[yellow]Warning:[/] Unknown language '{language}'. "
                f"Valid options: {', '.join(sorted(valid_languages))}"
            )
            console.print("[dim]Proceeding with 'unknown' defaults.[/]")
            project_type = "unknown"  # Use unknown, not the invalid value
        else:
            project_type = language
    else:
        project_type = detected_type

        # Prompt for confirmation of detected language if interactive
        if not no_interactive:
            console.print()
            console.print(f"[bold]Detected project type:[/] {project_type}")
            if not Confirm.ask(
                f"Use detected language '{project_type}'?",
                default=True,
            ):
                # Let user override
                from rich.prompt import Prompt

                valid_languages = set(detector.DEFAULTS.keys()) - {"unknown"}
                choices_str = ", ".join(sorted(valid_languages))
                console.print(f"[dim]Available: {choices_str}[/]")
                project_type = Prompt.ask(
                    "Enter language",
                    default=project_type,
                )

    # Initialize
    initializer = ProjectInitializer(project_root)
    config = initializer.initialize(
        project_type=project_type,
        force=force,
    )

    # Show summary
    _show_init_summary(project_type, config, adw_dir)


def _show_init_summary(
    project_type: str,
    config: dict[str, Any],
    adw_dir: Path,
) -> None:
    """Display initialization summary.

    Args:
        project_type: Detected or specified project type.
        config: Generated configuration dictionary.
        adw_dir: Path to the .adw/ directory.
    """
    test_cmd = config.get("test_command") or "not configured"

    console.print()
    console.print(
        Panel(
            f"[bold green]Project initialized![/]\n\n"
            f"[bold]Detected:[/] {project_type}\n"
            f"[bold]Language:[/] {config.get('language', 'unknown')}\n"
            f"[bold]Test Command:[/] {test_cmd}\n\n"
            f"[dim]Config:[/] {adw_dir / 'project.yaml'}\n\n"
            f"[bold]Next steps:[/]\n"
            f"  1. Review configuration: {adw_dir / 'project.yaml'}\n"
            f'  2. Start your first run: adw run "Add feature description"',
            title="[blue]ADW Init[/]",
            border_style="green",
        )
    )
