"""Main Typer CLI application for ADW."""

import typer
from rich.console import Console

from adw.core.constants import PHASE_SEQUENCE

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


def _validate_phase(value: str | None) -> str | None:
    """Validate that phase is one of PHASE_SEQUENCE.

    Args:
        value: Phase name to validate, or None.

    Returns:
        The validated phase name, or None if not provided.

    Raises:
        typer.BadParameter: If phase is not a valid phase name.
    """
    if value is None:
        return None
    if value not in PHASE_SEQUENCE:
        valid_phases = ", ".join(PHASE_SEQUENCE)
        raise typer.BadParameter(f"Invalid phase: {value}. Valid phases: {valid_phases}")
    return value


@app.command()
def run(
    feature: str = typer.Argument(
        ...,
        help="Feature description to implement",
    ),
    phase: str | None = typer.Option(
        None,
        "--phase",
        "-p",
        help=f"Execute single phase only ({', '.join(PHASE_SEQUENCE)})",
        callback=_validate_phase,
    ),
    from_run: str | None = typer.Option(
        None,
        "--from-run",
        "-f",
        help="Load artifacts from this run ID (required for phases after plan)",
    ),
) -> None:
    """Run the agentic development workflow.

    Execute the full pipeline or a single phase.

    Examples:
        # Full pipeline
        adw run "Add user authentication"

        # Single phase (plan doesn't need --from-run)
        adw run --phase plan "Add login"

        # Single phase with artifacts from previous run
        adw run --phase build --from-run 01HQXK5P3Z7V "Add login"
    """
    if phase:
        # Validate --from-run requirement for non-plan phases
        if phase != "plan" and from_run is None:
            console.print(
                f"[red]Error:[/] Phase '{phase}' requires artifacts from previous phases"
            )
            console.print(
                "[dim]Suggestion:[/] Use --from-run <run_id> to specify source run"
            )
            raise typer.Exit(1)

        # Single phase execution (to be implemented in Story 5.4)
        console.print(f"[bold blue]Single phase mode:[/] {phase}")
        console.print(f"[dim]Feature:[/] {feature}")
        if from_run:
            console.print(f"[dim]From run:[/] {from_run}")
        console.print("[yellow]Single phase execution not yet implemented[/yellow]")
    else:
        # Full pipeline execution (to be implemented)
        console.print(f"[dim]Feature:[/] {feature}")
        console.print("[yellow]Full pipeline not yet implemented[/yellow]")
