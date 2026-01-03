"""Main Typer CLI application for ADW."""

from datetime import UTC, datetime

import typer
from rich.console import Console
from ulid import ULID

from adw.cli.bootstrap import create_log_manager, create_orchestrator
from adw.cli.init import init as init_impl
from adw.cli.list import list_runs
from adw.cli.logs import logs_app
from adw.cli.resume import resume as resume_command
from adw.cli.run_display import RunDisplay
from adw.cli.status import status as status_command
from adw.cli.validators import validate_phase
from adw.commands.template import escape_feature_description
from adw.exceptions import ADWError, ConfigError
from adw.models.logging import Verbosity

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
        help="Override detected language (python, javascript, go, rust, etc.)",
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
        raise typer.Exit(1) from None


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Show errors only (minimal output)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed output including debug info"
    ),
    trace: bool = typer.Option(
        False, "--trace", help="Show all output including trace-level debugging"
    ),
) -> None:
    """Agentic Development Workflow SDK CLI."""
    # Handle mutual exclusivity of verbosity flags
    verbosity_flags = sum([quiet, verbose, trace])
    if verbosity_flags > 1:
        console.print(
            "[red]Error:[/] Verbosity flags are mutually exclusive. "
            "Use only one of: --quiet, --verbose, --trace"
        )
        raise typer.Exit(1)

    # Determine verbosity level
    if quiet:
        verbosity = Verbosity.QUIET
    elif trace:
        verbosity = Verbosity.TRACE
    elif verbose:
        verbosity = Verbosity.VERBOSE
    else:
        verbosity = Verbosity.NORMAL

    # Store verbosity in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbosity"] = verbosity

    if version:
        from adw import __version__

        console.print(f"adw version {__version__}")
        raise typer.Exit()


@app.command()
def run(
    ctx: typer.Context,
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

    # Get verbosity from context (Story 7.2)
    verbosity = Verbosity.NORMAL
    if ctx.obj:
        verbosity = ctx.obj.get("verbosity", Verbosity.NORMAL)

    # Create log manager with verbosity (Story 7.2)
    # Note: LogManager will be integrated with orchestrator in future stories
    log_manager = create_log_manager(console, verbosity=verbosity)
    _ = log_manager  # Log manager created, integration with orchestrator pending

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
        console.print("[dim]Suggestion:[/] Ensure phase commands are in .adw/commands/")
        raise typer.Exit(1) from None


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
        raise typer.Exit(1) from None


# Register the resume command (Story 6.2)
app.command()(resume_command)

# Register the status command (Story 6.3)
app.command()(status_command)

# Register the list command (Story 6.4)
# Note: We use name="list" since list_runs avoids Python keyword conflict
app.command(name="list")(list_runs)

# Register the logs subapp (Story 7.5)
app.add_typer(logs_app, name="logs")
