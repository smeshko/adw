"""Bootstrap module for CLI dependency injection.

Creates and wires up all dependencies needed for CLI commands to execute
the ADW pipeline. This module provides factory functions that handle
the complexity of instantiating the orchestrator and its dependencies.
"""

from pathlib import Path

from rich.console import Console

from adw.cli.progress import ProgressDisplay
from adw.core import (
    ArtifactManager,
    ContextManager,
    InterruptionHandler,
    Orchestrator,
    RunDirectoryManager,
    SnapshotManager,
)
from adw.logging import LogManager
from adw.logging.console import ConsoleTransport
from adw.models.logging import Verbosity


def get_project_root() -> Path:
    """Find the project root directory.

    The project root is the current working directory.
    The .adw directory will be created there if it doesn't exist.

    Returns:
        Path to the project root directory.
    """
    return Path.cwd()


def get_runs_dir(project_root: Path | None = None) -> Path:
    """Get the runs directory, creating it if necessary.

    Args:
        project_root: Project root directory. If None, uses cwd.

    Returns:
        Path to the .adw/runs directory.
    """
    root = project_root or get_project_root()
    runs_dir = root / ".adw" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir


def create_log_manager(
    console: Console | None = None,
    verbosity: Verbosity = Verbosity.NORMAL,
) -> LogManager:
    """Create a LogManager configured for CLI use.

    Sets up console transport with the specified verbosity. Console output
    respects verbosity settings while file transports (when added) capture
    everything for debugging purposes.

    Args:
        console: Rich console for output. If None, creates a new one.
        verbosity: Verbosity level for console output (default: NORMAL)

    Returns:
        Configured LogManager ready for use.

    Example:
        >>> logger = create_log_manager(verbosity=Verbosity.VERBOSE)
        >>> logger.debug(LogCategory.PHASE, "Detailed info")
    """
    console = console or Console()
    log_manager = LogManager(verbosity=verbosity)

    # Add console transport with verbosity filtering
    console_transport = ConsoleTransport(
        file=console.file,
        force_tty=console.is_terminal,
        verbosity=verbosity,
    )
    log_manager.register(console_transport)

    return log_manager


def create_orchestrator(
    console: Console | None = None,
    *,
    with_progress: bool = True,
) -> Orchestrator:
    """Create a fully configured Orchestrator instance.

    Sets up all required dependencies:
    - ContextManager for state persistence
    - SnapshotManager for debugging snapshots
    - ArtifactManager for storing phase outputs
    - RunDirectoryManager for directory structure
    - InterruptionHandler for graceful shutdown
    - ProgressDisplay for CLI output (optional)

    Args:
        console: Rich console for output. If None, creates a new one.
        with_progress: Whether to include progress display.

    Returns:
        Configured Orchestrator ready for use.

    Example:
        >>> orchestrator = create_orchestrator()
        >>> context = orchestrator.run_single_phase("plan", "Add login")
    """
    project_root = get_project_root()
    runs_dir = get_runs_dir(project_root)

    # Create managers
    context_manager = ContextManager(runs_dir)
    snapshot_manager = SnapshotManager(runs_dir)
    artifact_manager = ArtifactManager(runs_dir)
    run_directory_manager = RunDirectoryManager(project_root)
    interruption_handler = InterruptionHandler(context_manager, snapshot_manager)

    # Progress display for CLI feedback
    progress_display = None
    if with_progress:
        console = console or Console()
        progress_display = ProgressDisplay(console)

    # Create orchestrator
    orchestrator = Orchestrator(
        runs_dir=runs_dir,
        context_manager=context_manager,
        snapshot_manager=snapshot_manager,
        artifact_manager=artifact_manager,
        run_directory_manager=run_directory_manager,
        interruption_handler=interruption_handler,
        progress_display=progress_display,
    )

    return orchestrator
