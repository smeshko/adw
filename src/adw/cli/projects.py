"""Projects command for ADW CLI.

This module provides the projects command that lists all registered projects
in the global ADW dashboard registry.

Examples:
    adw projects                 # List registered projects
    adw projects --discover      # Show projects from run history
    adw projects --json          # JSON output for scripting
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from adw.core.index_manager import IndexManager
from adw.core.project_registry import ProjectRegistryManager
from adw.models.registry import RegisteredProject

console = Console()


def projects(
    discover: bool = typer.Option(
        False,
        "--discover",
        "-d",
        help="Show projects discovered from run history (not registered)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format",
    ),
) -> None:
    """List registered projects.

    Shows all projects registered in the global ADW dashboard at ~/.adw/projects.yaml.
    Each project shows its name, path, run count, and registration date.

    Use --discover to show projects found in the run history that aren't registered.
    These can be added using 'adw register' in each project directory.

    Examples:
        adw projects                 # List registered projects
        adw projects --discover      # Show projects from run history
        adw projects --json          # JSON output for scripting
    """
    manager = ProjectRegistryManager()
    index_manager = IndexManager()

    if discover:
        # Show projects discovered from index (not necessarily registered)
        project_list = manager.discover_from_index()
        title = "Discovered Projects (from runs)"
    else:
        # Show registered projects
        project_list = manager.get_all()
        title = "Registered Projects"

    # Calculate run counts for each project
    project_data = []
    for project in project_list:
        runs = index_manager.get_recent_runs(
            limit=10000,  # High limit to count all
            project_path=Path(project.path),
        )
        project_data.append(
            {
                "name": project.name,
                "path": project.path,
                "registered_at": project.registered_at.isoformat(),
                "run_count": len(runs),
            }
        )

    # Output format
    if json_output:
        _output_json(project_data)
    else:
        _output_table(project_data, title, discover)


def _output_json(project_data: list[dict]) -> None:
    """Output projects as JSON."""
    output = {"projects": project_data}
    console.print(json.dumps(output, indent=2))


def _output_table(
    project_data: list[dict],
    title: str,
    is_discover: bool,
) -> None:
    """Output projects as a Rich table."""
    if not project_data:
        if is_discover:
            console.print("[yellow]No projects found in run history.[/]")
            console.print(
                "[dim]Run 'adw run' in a project to start tracking runs.[/]"
            )
        else:
            console.print("[yellow]No projects registered.[/]")
            console.print(
                "[dim]Run 'adw register' in a project directory to add it.[/]"
            )
        return

    # Create table
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Path", style="dim")
    table.add_column("Runs", justify="right", style="green")
    table.add_column("Since", style="dim")

    # Add rows
    for project in project_data:
        # Format "Since" as relative time
        since = _format_relative_time(project["registered_at"])
        table.add_row(
            project["name"],
            _truncate_path(project["path"]),
            str(project["run_count"]),
            since,
        )

    console.print(table)

    # Show tips for discover mode
    if is_discover:
        console.print()
        console.print(
            "[dim]Tip:[/] Run 'adw register' in a project directory to add it to the registry."
        )


def _format_relative_time(iso_timestamp: str) -> str:
    """Format a timestamp as relative time (e.g., '3d ago')."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        delta = now - dt

        if delta.days > 30:
            months = delta.days // 30
            return f"{months}mo ago"
        elif delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"
    except (ValueError, AttributeError):
        return "unknown"


def _truncate_path(path: str, max_length: int = 40) -> str:
    """Truncate a path for display, showing the end."""
    if len(path) <= max_length:
        return path
    return "..." + path[-(max_length - 3) :]
