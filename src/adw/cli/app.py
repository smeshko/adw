"""Main Typer CLI application for ADW."""

from datetime import UTC, datetime

import typer
from rich.console import Console
from rich.panel import Panel
from ulid import ULID

console = Console()
app = typer.Typer(
    name="adw",
    help="Agentic Development Workflow SDK",
    add_completion=True,
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
) -> None:
    """Agentic Development Workflow SDK CLI."""
    if version:
        from adw import __version__

        console.print(f"adw version {__version__}")
        raise typer.Exit()


@app.command()
def run(
    feature_description: str = typer.Argument(
        ...,
        help="Description of the feature to implement",
        metavar="FEATURE_DESCRIPTION",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would happen without executing",
    ),
) -> None:
    """Start a new ADW run with the given feature description.

    Example:
        adw run "Add user authentication"
    """
    # Validate feature description is not empty
    if not feature_description.strip():
        console.print("[red]Error:[/] Feature description cannot be empty")
        raise typer.Exit(code=1)

    # Generate run ID
    run_id = str(ULID())
    started_at = datetime.now(UTC)

    # Truncate long feature descriptions for display
    max_len = 60
    feature_display = (
        f"{feature_description[:max_len]}..."
        if len(feature_description) > max_len
        else feature_description
    )

    timestamp = started_at.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Show run header (UX-12)
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Run ID:[/] {run_id}\n"
            f"[bold]Feature:[/] {feature_display}\n"
            f"[dim]Started:[/] {timestamp}",
            title="[bold blue]ADW Run[/]",
            border_style="blue",
        )
    )
    console.print()

    if dry_run:
        console.print("[yellow]Dry run mode - no execution[/]")
        return

    # TODO(Story 6.1 Task 6): Wire to Orchestrator
    console.print("[yellow]Full execution not implemented yet[/yellow]")
