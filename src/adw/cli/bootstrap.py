"""Bootstrap module for CLI dependency injection.

Creates and wires up all dependencies needed for CLI commands to execute
the ADW pipeline. This module provides factory functions that handle
the complexity of instantiating the orchestrator and its dependencies.
"""

from pathlib import Path
from typing import TextIO, cast

from rich.console import Console

from adw.cli.progress import ProgressDisplay
from adw.commands.resolver import CommandResolver
from adw.commands.template import TemplateEngine
from adw.core import (
    ArtifactManager,
    ContextManager,
    InterruptionHandler,
    Orchestrator,
    RunDirectoryManager,
    SnapshotManager,
)
from adw.core.phase_runner import PhaseRunner
from adw.executors.claude_code import ClaudeCodeExecutor
from adw.hooks.runner import HookRunner
from adw.logging import LogManager
from adw.logging.console import ConsoleTransport
from adw.models.config import HookConfig, LLMConfig
from adw.models.logging import Verbosity
from adw.security import SecurityInterceptor, ToolLogger


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
        file=cast(TextIO, console.file),
        force_tty=console.is_terminal,
        verbosity=verbosity,
    )
    log_manager.register(console_transport)

    return log_manager


def create_orchestrator(
    console: Console | None = None,
    *,
    with_progress: bool = True,
    allow_dangerous: bool = False,
    run_id: str | None = None,
) -> Orchestrator:
    """Create a fully configured Orchestrator instance.

    Sets up all required dependencies:
    - ContextManager for state persistence
    - SnapshotManager for debugging snapshots
    - ArtifactManager for storing phase outputs
    - RunDirectoryManager for directory structure
    - InterruptionHandler for graceful shutdown
    - ProgressDisplay for CLI output (optional)
    - SecurityInterceptor for tool call validation
    - ToolLogger for tool call audit trail
    - PhaseRunner with CommandResolver, TemplateEngine, HookRunner, LLMExecutor

    Args:
        console: Rich console for output. If None, creates a new one.
        with_progress: Whether to include progress display.
        allow_dangerous: If True, log warnings instead of blocking dangerous operations.
        run_id: Optional run ID for tool logging. If None, tool logging is disabled.

    Returns:
        Configured Orchestrator ready for use.

    Example:
        >>> orchestrator = create_orchestrator()
        >>> context = orchestrator.run_single_phase("plan", "Add login")
    """
    project_root = get_project_root()
    runs_dir = get_runs_dir(project_root)
    console = console or Console()

    # Create managers
    context_manager = ContextManager(runs_dir)
    snapshot_manager = SnapshotManager(runs_dir)
    artifact_manager = ArtifactManager(runs_dir)
    run_directory_manager = RunDirectoryManager(project_root)
    interruption_handler = InterruptionHandler(context_manager, snapshot_manager)

    # Progress display for CLI feedback
    progress_display = None
    if with_progress:
        progress_display = ProgressDisplay(console)

    # Create PhaseRunner dependencies (Epic 2 & 3)
    command_resolver = CommandResolver(project_root=project_root)
    template_engine = TemplateEngine(project_root=project_root)
    hook_runner = HookRunner(config=HookConfig())

    # Create security components (Story 3.6)
    security_interceptor = SecurityInterceptor(allow_dangerous=allow_dangerous)
    tool_logger = None
    if run_id:
        tool_logger = ToolLogger(runs_dir / run_id)

    llm_executor = ClaudeCodeExecutor(
        config=LLMConfig(),
        console=console,
        security_interceptor=security_interceptor,
        tool_logger=tool_logger,
        allow_dangerous=allow_dangerous,
    )

    # Create PhaseRunner (Story 5.2)
    phase_runner = PhaseRunner(
        command_resolver=command_resolver,
        template_engine=template_engine,
        hook_runner=hook_runner,
        executor=llm_executor,
        artifact_manager=artifact_manager,
        progress_display=progress_display,
    )

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

    # Wire up the PhaseRunner
    orchestrator.set_phase_runner(phase_runner)

    return orchestrator
