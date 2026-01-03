"""Abort command for stopping running executions.

This module provides the abort command that allows users to stop
a running execution gracefully from the CLI.
"""

import typer
from rich.console import Console
from rich.prompt import Confirm

from adw.cli.bootstrap import get_runs_dir
from adw.core import ContextManager, InterruptionHandler, SnapshotManager
from adw.exceptions import ConfigError, StateError

console = Console()


def abort_command(
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
    runs_dir = get_runs_dir()
    context_manager = ContextManager(runs_dir)
    snapshot_manager = SnapshotManager(runs_dir)

    # Load context for the run
    try:
        context = context_manager.load(run_id)
    except StateError as e:
        if e.code == "CONTEXT_NOT_FOUND":
            raise ConfigError(
                code="RUN_NOT_FOUND",
                message=f"Run {run_id} not found",
                suggestion="Use 'adw list' to see available runs",
                recoverable=False,
            ) from e
        raise

    # Validate run is active
    if context.status not in ("running",):
        raise ConfigError(
            code="RUN_NOT_ACTIVE",
            message=f"Run is not active (status: {context.status})",
            suggestion="Only running executions can be aborted",
            recoverable=False,
        )

    # Confirm abort unless --force
    if not force:
        if not Confirm.ask(f"Abort run {run_id}?", default=False):
            console.print("[green]Abort cancelled[/]")
            return

    # Perform abort using InterruptionHandler
    handler = InterruptionHandler(
        context_manager=context_manager,
        snapshot_manager=snapshot_manager,
        console=console,
    )
    handler.abort_gracefully(context, reason="cli_abort")
