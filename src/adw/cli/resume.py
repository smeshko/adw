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
from adw.core import ContextManager, ResumeManager
from adw.core.run_lookup import RunLookup
from adw.exceptions import ADWError
from adw.models.logging import Verbosity

console = Console()
logger = logging.getLogger(__name__)


def _create_resume_manager() -> ResumeManager:
    """Create a ResumeManager with required dependencies.

    Returns:
        Configured ResumeManager instance.
    """
    runs_dir = get_runs_dir()
    return ResumeManager(
        runs_dir=runs_dir,
        run_lookup=RunLookup(runs_dir),
        context_manager=ContextManager(runs_dir),
    )


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

    # Use ResumeManager to find and validate run
    resume_manager = _create_resume_manager()

    try:
        resume_info = resume_manager.find_run_to_resume(
            run_id=run_id,
            from_phase=from_phase,
        )
    except ADWError as e:
        console.print(
            Panel(
                f"[red]Error:[/] {e.message}\n\n[dim]Suggestion:[/] {e.suggestion}",
                title=f"[red]{e.code}[/]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from None

    # Check if resume info is valid
    if not resume_info.is_valid:
        # Use error metadata for consistent ADW error UX
        error_title = f"[red]{resume_info.error_code}[/]" if resume_info.error_code else "[red]Cannot Resume[/]"
        error_body = f"[red]Error:[/] {resume_info.validation_error}"
        if resume_info.error_suggestion:
            error_body += f"\n\n[dim]Suggestion:[/] {resume_info.error_suggestion}"
        console.print(
            Panel(
                error_body,
                title=error_title,
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from None

    context = resume_info.context
    resume_phase = resume_info.resume_phase

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
        completed_phases=list(context.phase_history),
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
