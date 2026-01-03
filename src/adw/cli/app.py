"""Main Typer CLI application for ADW."""

from datetime import UTC, datetime

import typer
from rich.console import Console
from ulid import ULID

from adw.cli.bootstrap import create_orchestrator
from adw.cli.resume import resume as resume_command
from adw.cli.run_display import RunDisplay
from adw.cli.validators import validate_phase
from adw.commands.template import escape_feature_description
from adw.exceptions import ADWError, ConfigError

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
    feature: str = typer.Argument(
        ...,
        help="Feature description to implement",
        metavar="FEATURE_DESCRIPTION",
    ),
    phase: str | None = typer.Option(
        None,
        "--phase",
        "-p",
        help="Execute single phase only (plan, build, verify, validate, document)",
        callback=validate_phase,
    ),
    from_run: str | None = typer.Option(
        None,
        "--from-run",
        "-f",
        help="Load artifacts from this run ID (required for phases after plan)",
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
    """Run the agentic development workflow.

    Execute the full pipeline or a single phase.

    Examples:
        # Full pipeline
        adw run "Add user authentication"

        # Single phase (plan doesn't need --from-run)
        adw run --phase plan "Add login"

        # Single phase with artifacts from previous run
        adw run --phase build --from-run 01HQXK5P3Z7V "Add login"

        # Dry run to see what would happen
        adw run "Add login" --dry-run
    """
    # Validate feature description is not empty (Story 6.1)
    if not feature.strip():
        console.print("[red]Error:[/] Feature description cannot be empty")
        raise typer.Exit(code=1)

    # Escape special characters for template safety (Story 6.1 Task 5)
    # Note: safe_feature will be used when templates need the escaped version
    _ = escape_feature_description(feature)

    # Generate run ID and timestamp (Story 6.1)
    run_id = str(ULID())
    started_at = datetime.now(UTC)

    # Show run header using RunDisplay (UX-12, Story 6.1)
    run_display = RunDisplay(console)
    run_display.show_run_header(
        run_id=run_id,
        feature=feature,
        started_at=started_at,
    )

    if dry_run:
        console.print("[yellow]Dry run mode - no execution[/]")
        return

    try:
        orchestrator = create_orchestrator(console)

        if phase:
            # Validate --from-run requirement for non-plan phases (Story 5.4)
            if phase != "plan" and from_run is None:
                console.print(
                    f"[red]Error:[/] Phase '{phase}' requires artifacts "
                    "from previous phases"
                )
                console.print(
                    "[dim]Suggestion:[/] Use --from-run <run_id> to specify source run"
                )
                raise typer.Exit(1)

            # Single phase execution (Story 5.4)
            context = orchestrator.run_single_phase(phase, feature, from_run)
            console.print(
                f"[green]✓[/] Single phase '{phase}' completed: {context.run_id}"
            )
        else:
            # Full pipeline execution
            context = orchestrator.run(feature)
            console.print(f"[green]✓[/] Run completed: {context.run_id}")

    except ConfigError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1) from None
    except ADWError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1) from None
    except RuntimeError as e:
        # PhaseRunner not set - infrastructure not ready
        console.print(f"[red]Error:[/] {e}")
        console.print(
            "[dim]Suggestion:[/] Ensure phase commands are in .adw/commands/"
        )
        raise typer.Exit(1) from None


# Register the resume command (Story 6.2)
app.command()(resume_command)
