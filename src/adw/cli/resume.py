"""Resume command for ADW CLI.

This module provides the resume command that allows users to continue
runs that failed or were interrupted.

Examples:
    adw resume                    # Resume most recent incomplete run
    adw resume 01HQXK5P3Z...     # Resume specific run
    adw resume --from-phase build # Restart from specific phase
"""

import typer
from rich.console import Console
from rich.panel import Panel

from adw.cli.bootstrap import create_orchestrator, get_runs_dir
from adw.cli.run_display import RunDisplay
from adw.core.constants import PHASE_SEQUENCE
from adw.core.run_lookup import RunLookup
from adw.exceptions import ADWError, ConfigError

console = Console()


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
        msg = f"Invalid phase: {value}. Valid phases: {valid_phases}"
        raise typer.BadParameter(msg)
    return value


def resume(
    run_id: str | None = typer.Argument(
        None,
        help="Run ID to resume (defaults to most recent incomplete)",
    ),
    from_phase: str | None = typer.Option(
        None,
        "--from-phase",
        help="Phase to resume from (overrides saved state)",
        callback=_validate_phase,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """Resume a failed or interrupted run.

    If no run_id is provided, resumes the most recent incomplete run.

    Examples:
        adw resume                    # Resume most recent
        adw resume 01HQXK5P3Z...     # Resume specific run
        adw resume --from-phase build # Restart from build phase
    """
    runs_dir = get_runs_dir()
    lookup = RunLookup(runs_dir)

    # Find the run to resume
    if run_id:
        context = lookup.find_by_id(run_id)
        if not context:
            raise ConfigError(
                code="RUN_NOT_FOUND",
                message=f"Run {run_id} not found",
                suggestion="Use 'adw list' to see available runs",
                recoverable=False,
            )
    else:
        context = lookup.find_most_recent_incomplete()
        if not context:
            console.print("[yellow]No incomplete runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
            raise typer.Exit()

    # Validate resumable
    if context.status == "completed":
        raise ConfigError(
            code="RUN_COMPLETED",
            message="Run already completed",
            suggestion="Start a new run with 'adw run'",
            recoverable=False,
        )

    # Determine resume phase
    resume_phase = from_phase or context.current_phase

    # Show resume header (Story 6.2 Task 6)
    run_display = RunDisplay(console)
    run_display.show_resume_header(
        run_id=context.run_id,
        feature=context.feature_description,
        completed_phases=context.phase_history,
        resume_phase=resume_phase,
    )

    try:
        orchestrator = create_orchestrator(console)
        result = orchestrator.resume(context.run_id, from_phase=from_phase)
        console.print(f"[green]Run completed:[/] {result.run_id}")
    except ADWError as e:
        console.print(
            Panel(
                f"[red]Error:[/] {e.message}\n\n"
                f"[dim]Suggestion:[/] {e.suggestion}",
                title=f"[red]{e.code}[/]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from None
