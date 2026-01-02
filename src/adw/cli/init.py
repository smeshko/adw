"""CLI init command for initializing ADW projects.

This module provides the `adw init` command that creates the .adw/ directory
structure and generates project configuration based on auto-detection.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from adw.config.detector import ProjectTypeDetector
from adw.config.initializer import ProjectInitializer

console = Console()


def init(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration",
    ),
    language: str | None = typer.Option(
        None,
        "--language",
        "-l",
        help="Override detected language (python, javascript, go, rust, etc.)",
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Use a specific project template (future feature)",
        hidden=True,
    ),
) -> None:
    """Initialize ADW in the current directory.

    Creates .adw/ directory with project configuration.
    Auto-detects project type and sets appropriate defaults.

    Examples:
        adw init                    # Auto-detect and initialize
        adw init --force            # Reinitialize existing project
        adw init --language python  # Override detection
    """
    project_root = Path.cwd()
    adw_dir = project_root / ".adw"

    # Check if already initialized
    if adw_dir.exists() and not force:
        console.print(
            f"[red]Error:[/] Project already initialized\n"
            f"[dim]Suggestion: Use 'adw init --force' to reinitialize[/]"
        )
        raise typer.Exit(code=1)

    # Detect project type
    detector = ProjectTypeDetector()
    detected_type = detector.detect(project_root)

    # Override if specified
    project_type = language or detected_type

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
    config: dict,
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
            f"  2. Start your first run: adw run \"Add feature description\"",
            title="[blue]ADW Init[/]",
            border_style="green",
        )
    )
