"""Main Typer CLI application for ADW."""

from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from ulid import ULID

from adw.cli.bootstrap import create_orchestrator
from adw.cli.init import init as init_impl
from adw.cli.run_display import RunDisplay
from adw.commands.template import escape_feature_description
from adw.core.constants import PHASE_SEQUENCE
from adw.exceptions import ADWError, ConfigError

console = Console()
app = typer.Typer(
    name="adw",
    help="Agentic Development Workflow SDK",
    add_completion=True,
)


@app.command(name="init")
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
        help="Override detected language (python, javascript, go, rust, java, ruby, php)",
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
    try:
        init_impl(force=force, language=language)
    except ConfigError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1)


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
        metavar="FEATURE_DESCRIPTION",
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
    safe_feature = escape_feature_description(feature)
    _ = safe_feature  # Will be used when templates need the escaped version

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
                    f"[red]Error:[/] Phase '{phase}' requires artifacts from previous phases"
                )
                console.print(
                    "[dim]Suggestion:[/] Use --from-run <run_id> to specify source run"
                )
                raise typer.Exit(1)

            # Single phase execution (Story 5.4)
            context = orchestrator.run_single_phase(phase, feature, from_run)
            console.print(f"[green]✓[/] Single phase '{phase}' completed: {context.run_id}")
        else:
            # Full pipeline execution
            context = orchestrator.run(feature)
            console.print(f"[green]✓[/] Run completed: {context.run_id}")

    except ConfigError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1)
    except ADWError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1)
    except RuntimeError as e:
        # PhaseRunner not set - infrastructure not ready
        console.print(f"[red]Error:[/] {e}")
        console.print(
            "[dim]Suggestion:[/] Ensure phase commands are configured in .adw/commands/"
        )
        raise typer.Exit(1)


@app.command()
def abort(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to abort",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Abort without confirmation",
    ),
) -> None:
    """Abort a running execution.

    The run must be in 'running' status to be aborted.
    Use --force to skip the confirmation prompt.

    Examples:
        adw abort 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw abort 01HQXK5P3Z7V8R2M4N6T9W1Y3C --force
    """
    from adw.cli.abort import abort_command

    try:
        abort_command(run_id=run_id, force=force)
    except ConfigError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1)
