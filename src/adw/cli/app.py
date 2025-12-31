"""Main Typer CLI application for ADW."""

import typer
from rich.console import Console

console = Console()
app = typer.Typer(
    name="adw-final",
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
def run() -> None:
    """Run the agentic development workflow."""
    console.print("[yellow]Not implemented yet[/yellow]")
