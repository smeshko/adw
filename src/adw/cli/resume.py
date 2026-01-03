"""Resume command for ADW CLI.

This module provides the resume command that allows users to continue
runs that failed or were interrupted.

Examples:
    adw resume                    # Resume most recent incomplete run
    adw resume 01HQXK5P3Z...     # Resume specific run
    adw resume --from-phase build # Restart from specific phase
"""

import logging

import typer
from rich.console import Console
from rich.panel import Panel

from adw.cli.bootstrap import create_log_manager, create_orchestrator, get_runs_dir
from adw.cli.run_display import RunDisplay
from adw.cli.validators import validate_phase
from adw.core.run_lookup import RunLookup
from adw.exceptions import ADWError, ConfigError, StateError
from adw.models import RunContext
from adw.models.logging import Verbosity

console = Console()
logger = logging.getLogger(__name__)


def resume(
    ctx: typer.Context,
    run_id: str | None = typer.Argument(
        None,
        help="Run ID to resume (defaults to most recent incomplete)",
    ),
    from_phase: str | None = typer.Option(
        None,
        "--from-phase",
        help="Phase to resume from (overrides saved state)",
        callback=validate_phase,
    ),
) -> None:
    """Resume a failed or interrupted run.

    If no run_id is provided, resumes the most recent incomplete run.

    Examples:
        adw resume                    # Resume most recent
        adw resume 01HQXK5P3Z...     # Resume specific run
        adw resume --from-phase build # Restart from build phase
    """
    # Get verbosity from context (Story 7.2)
    verbosity = Verbosity.NORMAL
    if ctx.obj:
        verbosity = ctx.obj.get("verbosity", Verbosity.NORMAL)

    # Enable debug logging for VERBOSE/TRACE levels
    if verbosity in (Verbosity.VERBOSE, Verbosity.TRACE):
        logging.basicConfig(level=logging.DEBUG, format="%(name)s - %(message)s")
        logger.debug("Verbose mode enabled")

    try:
        context = _find_run_to_resume(run_id)
    except ADWError as e:
        console.print(
            Panel(
                f"[red]Error:[/] {e.message}\n\n[dim]Suggestion:[/] {e.suggestion}",
                title=f"[red]{e.code}[/]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from None

    # Determine resume phase
    resume_phase = from_phase or context.current_phase
    logger.debug(
        "Resume phase: %s (from_phase=%s, context.current_phase=%s)",
        resume_phase,
        from_phase,
        context.current_phase,
    )

    # Show resume header (Story 6.2 Task 6)
    run_display = RunDisplay(console)
    run_display.show_resume_header(
        run_id=context.run_id,
        feature=context.feature_description,
        completed_phases=context.phase_history,
        resume_phase=resume_phase,
    )

    try:
        logger.debug("Creating orchestrator and starting resume")

        # Create log manager with verbosity (Story 7.2)
        log_manager = create_log_manager(console, verbosity=verbosity)
        _ = log_manager  # Log manager created, integration with orchestrator pending

        orchestrator = create_orchestrator(console)
        result = orchestrator.resume(context.run_id, from_phase=from_phase)
        console.print(f"[green]Run completed:[/] {result.run_id}")
    except ADWError as e:
        console.print(
            Panel(
                f"[red]Error:[/] {e.message}\n\n[dim]Suggestion:[/] {e.suggestion}",
                title=f"[red]{e.code}[/]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from None


def _find_run_to_resume(run_id: str | None) -> RunContext:
    """Find the run to resume.

    Args:
        run_id: Specific run ID to resume, or None for most recent incomplete.

    Returns:
        RunContext of the run to resume.

    Raises:
        ConfigError: If run not found or already completed.
        StateError: If run context is corrupted.
        typer.Exit: If no incomplete runs found (user-friendly exit).
    """
    runs_dir = get_runs_dir()
    lookup = RunLookup(runs_dir)

    if run_id:
        context = lookup.find_by_id(run_id)
        if not context:
            # Check if run directory exists but context is corrupted (AC4)
            run_path = runs_dir / run_id
            if run_path.exists():
                # Directory exists but context couldn't be loaded - corrupted state
                raise StateError(
                    code="STATE_CORRUPTED",
                    message=f"Run {run_id} has corrupted state",
                    suggestion=(
                        f"Check snapshots in .adw/runs/{run_id}/snapshots/ "
                        "for recovery options"
                    ),
                    recoverable=False,
                )
            raise ConfigError(
                code="RUN_NOT_FOUND",
                message=f"Run {run_id} not found",
                suggestion="Use 'adw list' to see available runs",
                recoverable=False,
            )
    else:
        logger.debug("No run_id provided, finding most recent incomplete run")
        context = lookup.find_most_recent_incomplete()
        if not context:
            console.print("[yellow]No incomplete runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
            raise typer.Exit()
        logger.debug(
            "Found incomplete run: %s (status=%s)", context.run_id, context.status
        )

    # Validate resumable
    if context.status == "completed":
        raise ConfigError(
            code="RUN_COMPLETED",
            message="Run already completed",
            suggestion="Start a new run with 'adw run'",
            recoverable=False,
        )

    return context
