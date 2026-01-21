"""Bootstrap module for CLI dependency injection.

Creates and wires up all dependencies needed for CLI commands to execute
the ADW pipeline. This module provides factory functions that handle
the complexity of instantiating the orchestrator and its dependencies.
"""

import logging
import os
from pathlib import Path
from typing import TextIO, cast

from rich.console import Console

from adw.cli.progress import ProgressDisplay
from adw.commands.resolver import CommandResolver
from adw.commands.template import TemplateEngine
from adw.config.loader import ConfigLoader
from adw.core import (
    ArtifactManager,
    ContextManager,
    InterruptionHandler,
    Orchestrator,
    RunDirectoryManager,
    SnapshotManager,
)
from adw.core.constants import PHASE_SEQUENCE
from adw.core.phase_runner import PhaseRunner
from adw.exceptions import ConfigError
from adw.executors.base import LLMExecutor
from adw.executors.claude_code import ClaudeCodeExecutor
from adw.hooks.runner import HookRunner
from adw.logging import LLMCaptureManager, LogManager, LogManagerHandler
from adw.logging.console import ConsoleTransport
from adw.logging.file import RawFileTransport, StructuredFileTransport
from adw.models.config import (
    GitConfig,
    HookConfig,
    LLMConfig,
    TaskManagerConfig,
    WorktreeConfig,
)
from adw.models.logging import VERBOSITY_LEVEL_MAP, LogLevel, Verbosity
from adw.security import SecurityInterceptor, ToolLogger
from adw.task_managers.base import TaskManager
from adw.task_managers.labels import LabelManager
from adw.task_managers.sync import StatusSyncService


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
    run_dir: Path | None = None,
) -> LogManager:
    """Create a LogManager configured for CLI use.

    Sets up console transport with the specified verbosity. When run_dir is
    provided, also sets up file transports for persistent logging.

    IMPORTANT: This function also wires up Python's standard logging to flow
    through the LogManager, so calls to logging.getLogger().info() will write
    to logs.jsonl (Story ISS-006 fix).

    Args:
        console: Rich console for output. If None, creates a new one.
        verbosity: Verbosity level for console output (default: NORMAL)
        run_dir: Optional run directory for file logging. If provided,
                 creates logs/logs.jsonl and logs/raw.log in the run directory.

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

    # Add file transports when run_dir is provided
    # Note: File transports create directories lazily on first write,
    # so we don't mkdir here to avoid conflicts with RunDirectoryManager
    if run_dir:
        logs_dir = run_dir / "logs"

        # Structured JSON Lines for programmatic access
        jsonl_transport = StructuredFileTransport(logs_dir / "logs.jsonl")
        log_manager.register(jsonl_transport)

        # Human-readable raw log
        raw_transport = RawFileTransport(logs_dir / "raw.log")
        log_manager.register(raw_transport)

    # Wire Python's standard logging to flow through LogManager (ISS-006 fix)
    # This ensures all logging.getLogger(__name__).info() calls in ADW modules
    # are captured in logs.jsonl for debugging via `adw logs show`
    handler = LogManagerHandler(log_manager)

    # Set handler level based on verbosity - file transports log everything,
    # but we filter at the handler level based on CLI verbosity
    log_level = VERBOSITY_LEVEL_MAP.get(verbosity, LogLevel.INFO)
    python_level_map = {
        LogLevel.TRACE: logging.DEBUG,  # Python has no TRACE, use DEBUG
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARN: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
        LogLevel.FATAL: logging.CRITICAL,
    }
    handler.setLevel(python_level_map.get(log_level, logging.INFO))

    # Attach to root logger to capture all ADW module logs
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    # Ensure root logger level allows messages through
    # (handlers filter further, but root must let them through first)
    if root_logger.level == logging.NOTSET or root_logger.level > logging.DEBUG:
        root_logger.setLevel(logging.DEBUG)

    return log_manager


def create_orchestrator(
    console: Console | None = None,
    *,
    with_progress: bool = True,
    allow_dangerous: bool = False,
    run_id: str | None = None,
    show_llm_output: bool = False,
    task_manager: TaskManager | None = None,
    task_id: str | None = None,
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
    - LabelManager for task label operations (optional, Story 12.7)

    Args:
        console: Rich console for output. If None, creates a new one.
        with_progress: Whether to include progress display.
        allow_dangerous: If True, log warnings instead of blocking dangerous operations.
        run_id: Optional run ID for tool logging. If None, tool logging is disabled.
        show_llm_output: If True, stream LLM output to terminal (Story UX-FIX-ISS-001).
        task_manager: Optional task manager for label operations (Story 12.7).
        task_id: Optional task ID (internal UUID) for label operations (Story 12.7).

    Returns:
        Configured Orchestrator ready for use.

    Example:
        >>> orchestrator = create_orchestrator()
        >>> context = orchestrator.run_single_phase("plan", "Add login")
    """
    project_root = get_project_root()
    runs_dir = get_runs_dir(project_root)
    console = console or Console()

    # Load project configuration for worktree, git, and task manager settings
    # (Story 10.1, ISS-011, Story 12.7, Story 12.8)
    worktree_config: WorktreeConfig | None = None
    git_config: GitConfig | None = None
    task_manager_config: TaskManagerConfig | None = None
    config = None  # May be needed for task manager labels
    try:
        config = ConfigLoader(project_root).load()
        worktree_config = config.worktree
        git_config = config.git
        task_manager_config = config.task_manager
    except ConfigError:
        # No config file or invalid config - use defaults
        worktree_config = WorktreeConfig()
        git_config = GitConfig()
        task_manager_config = TaskManagerConfig()

    # Create managers
    context_manager = ContextManager(runs_dir)
    snapshot_manager = SnapshotManager(runs_dir)
    artifact_manager = ArtifactManager(runs_dir)
    run_directory_manager = RunDirectoryManager(project_root)
    interruption_handler = InterruptionHandler(context_manager, snapshot_manager)

    # Create PhaseRunner dependencies (Epic 2 & 3)
    command_resolver = CommandResolver(project_root=project_root)
    template_engine = TemplateEngine(project_root=project_root)
    hook_runner = HookRunner(config=HookConfig())

    # Create security components (Story 3.6)
    security_interceptor = SecurityInterceptor(allow_dangerous=allow_dangerous)
    tool_logger = None
    llm_capture = None
    if run_id:
        run_dir = runs_dir / run_id
        tool_logger = ToolLogger(run_dir)
        # Create LLM capture manager for debugging (ISS-003 fix)
        llm_capture = LLMCaptureManager(run_dir / "llm")

    # Use MockExecutor in test mode to avoid hitting real Claude API
    # Set ADW_MOCK_EXECUTOR=1 to enable mock mode (used by tests)
    llm_executor: LLMExecutor
    if os.environ.get("ADW_MOCK_EXECUTOR"):
        from adw.executors.mock import MockExecutor

        llm_executor = MockExecutor()
    else:
        llm_executor = ClaudeCodeExecutor(
            config=LLMConfig(),
            console=console,
            security_interceptor=security_interceptor,
            tool_logger=tool_logger,
            allow_dangerous=allow_dangerous,
            show_llm_output=show_llm_output,
            llm_capture=llm_capture,
        )

    # Create PhaseRunner first (without progress_display) (Story 5.2)
    # so we can compute enabled phases using is_phase_enabled()
    phase_runner = PhaseRunner(
        command_resolver=command_resolver,
        template_engine=template_engine,
        hook_runner=hook_runner,
        executor=llm_executor,
        artifact_manager=artifact_manager,
        progress_display=None,
    )

    # Progress display for CLI feedback (ISS-036: filter to enabled phases)
    progress_display = None
    if with_progress:
        # Compute enabled phases using PhaseRunner's is_phase_enabled()
        # This checks both command config and project config for each phase
        enabled_phases = [p for p in PHASE_SEQUENCE if phase_runner.is_phase_enabled(p)]
        progress_display = ProgressDisplay(console, enabled_phases=enabled_phases)
        # Update PhaseRunner with the progress display
        phase_runner.progress_display = progress_display

    # Create StatusSyncService if task manager is configured (Story 12.3, ISS-033)
    status_sync_service: StatusSyncService | None = None
    if task_manager is not None and config is not None and config.task_manager:
        status_sync_service = StatusSyncService(task_manager, config.task_manager)

    # Create LabelManager if task manager and task ID are provided (Story 12.7)
    label_manager: LabelManager | None = None
    if task_manager is not None and task_id is not None and config is not None:
        labels_config = config.task_manager.labels if config.task_manager else None
        if labels_config and labels_config.enabled:
            label_manager = LabelManager(task_manager, labels_config, task_id)

    # Create orchestrator
    orchestrator = Orchestrator(
        runs_dir=runs_dir,
        context_manager=context_manager,
        snapshot_manager=snapshot_manager,
        artifact_manager=artifact_manager,
        run_directory_manager=run_directory_manager,
        phase_runner=phase_runner,
        interruption_handler=interruption_handler,
        progress_display=progress_display,
        worktree_config=worktree_config,
        git_config=git_config,
        task_manager_config=task_manager_config,
        label_manager=label_manager,
        status_sync_service=status_sync_service,
    )

    return orchestrator
