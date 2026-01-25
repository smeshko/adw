"""Unregister command for ADW CLI.

This module provides the unregister command that allows users to remove
the current project from the global ADW dashboard registry.

Examples:
    adw unregister  # Remove current project from registry
"""

from pathlib import Path

import typer
from rich.console import Console

from adw.core.project_registry import ProjectRegistryManager

console = Console()


def unregister() -> None:
    """Unregister current project from global ADW dashboard.

    Removes the project from the global registry at ~/.adw/projects.yaml.
    The project will no longer appear in cross-project views.

    Examples:
        adw unregister  # Remove current project from registry
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

    # Attempt to unregister
    manager = ProjectRegistryManager()
    removed = manager.unregister(project_path)

    # Display result
    if removed:
        console.print(f"[green]✓[/] Project unregistered: {project_path.name}")
        console.print(f"  [dim]Path:[/] {project_path}")
    else:
        console.print(f"[yellow]![/] Project was not registered: {project_path.name}")
        console.print(
            "[dim]Tip:[/] Use 'adw register' to add this project to the registry."
        )
