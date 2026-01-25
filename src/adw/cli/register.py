"""Register command for ADW CLI.

This module provides the register command that allows users to register
the current project in the global ADW dashboard registry.

Examples:
    adw register                    # Register with directory name
    adw register --name "My API"    # Register with custom name
"""

from pathlib import Path

import typer
from rich.console import Console

from adw.core.project_registry import ProjectRegistryManager

console = Console()


def register(
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom display name for the project",
    ),
) -> None:
    """Register current project in global ADW dashboard.

    Adds the current project to the global project registry at ~/.adw/projects.yaml.
    This enables the project to appear in cross-project views like:
    - Global run list (adw runs --global)
    - Cross-project statistics (adw stats)
    - TUI dashboard project breakdown

    If the project is already registered, its name will be updated.

    Examples:
        adw register                    # Register with directory name
        adw register --name "My API"    # Register with custom name
    """
    project_path = Path.cwd()

    # Validate that this is an ADW project
    adw_dir = project_path / ".adw"
    if not adw_dir.exists():
        console.print(
            "[red]Error:[/] Current directory is not an ADW project.\n"
            "[dim]Suggestion:[/] Run 'adw init' first to initialize the project."
        )
        raise typer.Exit(code=1)

    # Check if already registered
    manager = ProjectRegistryManager()
    existing = manager.get_by_path(project_path)

    # Register or update
    project = manager.register(project_path, name=name)

    # Display result
    if existing:
        console.print(f"[green]✓[/] Project registration updated: {project.name}")
    else:
        console.print(f"[green]✓[/] Project registered: {project.name}")

    console.print(f"  [dim]Path:[/] {project.path}")
