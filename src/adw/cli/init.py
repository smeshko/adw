"""CLI init implementation for initializing ADW projects.

This module provides the init logic that creates the .adw/ directory
structure and generates project configuration based on auto-detection.
"""

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from adw.config.detector import ProjectTypeDetector
from adw.config.initializer import ProjectInitializer
from adw.exceptions import ConfigError

console = Console()


def init(
    force: bool = False,
    language: str | None = None,
) -> None:
    """Initialize ADW in the current directory.

    Creates .adw/ directory with project configuration.
    Auto-detects project type and sets appropriate defaults.

    Args:
        force: If True, overwrite existing configuration.
        language: Override detected language (python, javascript, etc.).

    Raises:
        ConfigError: If project is already initialized and force is False.
    """
    project_root = Path.cwd()
    adw_dir = project_root / ".adw"

    # Check if already initialized
    if adw_dir.exists() and not force:
        raise ConfigError(
            code="PROJECT_ALREADY_INITIALIZED",
            message="Project already initialized",
            suggestion="Use 'adw init --force' to reinitialize",
            recoverable=False,
        )

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
        project_type = language
    else:
        project_type = detected_type

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
