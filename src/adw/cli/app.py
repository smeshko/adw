"""Main Typer CLI application for ADW."""

from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from ulid import ULID

from adw.cli.progress import ProgressDisplay
from adw.cli.run_display import RunDisplay
from adw.config.loader import ConfigLoader
from adw.core.artifact_manager import ArtifactManager
from adw.core.context_manager import ContextManager
from adw.core.interruption import ShutdownRequested
from adw.core.orchestrator import Orchestrator
from adw.core.run_directory import RunDirectoryManager
from adw.core.snapshot_manager import SnapshotManager
from adw.exceptions import ADWError

console = Console()
app = typer.Typer(
    name="adw",
    help="Agentic Development Workflow SDK",
    add_completion=True,
)


def _create_orchestrator(
    project_root: Path,
    console: Console,
    *,
    verbose: bool = False,
) -> Orchestrator:
    """Create and configure an Orchestrator with all required managers.

    This factory function wires together all the components needed
    for pipeline execution:
    - ContextManager for state persistence
    - SnapshotManager for debugging snapshots
    - ArtifactManager for phase artifact storage
    - RunDirectoryManager for directory structure
    - ProgressDisplay for user feedback

    Args:
        project_root: Root directory of the project.
        console: Rich Console for output.
        verbose: Enable verbose logging.

    Returns:
        Configured Orchestrator ready for execution.
    """
    runs_dir = project_root / ".adw" / "runs"

    # Create managers
    context_manager = ContextManager(runs_dir)
    snapshot_manager = SnapshotManager(runs_dir)
    artifact_manager = ArtifactManager(runs_dir)
    run_directory_manager = RunDirectoryManager(runs_dir)

    # Create progress display for user feedback
    progress_display = ProgressDisplay(console)

    # Create and configure orchestrator
    orchestrator = Orchestrator(
        runs_dir=runs_dir,
        context_manager=context_manager,
        snapshot_manager=snapshot_manager,
        artifact_manager=artifact_manager,
        run_directory_manager=run_directory_manager,
        progress_display=progress_display,
    )

    return orchestrator


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

    # Generate run ID and timestamp
    run_id = str(ULID())
    started_at = datetime.now(UTC)

    # Show run header using RunDisplay (UX-12)
    run_display = RunDisplay(console)
    run_display.show_run_header(
        run_id=run_id,
        feature=feature_description,
        started_at=started_at,
    )

    if dry_run:
        console.print("[yellow]Dry run mode - no execution[/]")
        return

    # Load project configuration
    project_root = Path.cwd()
    config_loader = ConfigLoader(project_root)

    try:
        config = config_loader.load()
        if verbose:
            console.print(f"[dim]Loaded config: {config.name} ({config.language})[/]")
    except ADWError as e:
        console.print(
            Panel(
                f"[red]Error:[/] {e.message}\n\n"
                f"[dim]Suggestion:[/] {e.suggestion}",
                title=f"[red]{e.code}[/]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from e

    # Create and run orchestrator
    try:
        orchestrator = _create_orchestrator(
            project_root,
            console,
            verbose=verbose,
        )

        # Note: PhaseRunner must be set before running
        # For now, we inform the user that full execution requires PhaseRunner setup
        # This will be completed when we have the actual LLM executor wired up
        console.print(
            "[yellow]Note:[/] Full pipeline execution requires LLM executor configuration."
        )
        console.print(
            "[dim]Run ID:[/] {run_id} | "
            "[dim]Config:[/] {config.name} | "
            "[dim]Language:[/] {config.language}".format(
                run_id=run_id,
                config=config,
            )
        )

    except ShutdownRequested as e:
        console.print(f"\n[yellow]Run interrupted at phase: {e.phase}[/]")
        console.print("[dim]State saved. Use 'adw resume' to continue.[/]")
        raise typer.Exit(code=130) from e  # 130 = 128 + SIGINT

    except ADWError as e:
        console.print(
            Panel(
                f"[red]Error:[/] {e.message}\n\n"
                f"[dim]Suggestion:[/] {e.suggestion}",
                title=f"[red]{e.code}[/]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from e
