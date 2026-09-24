"""Bootstrap module for CLI dependency injection.

Creates and wires up all dependencies needed for CLI commands to execute
the ADW pipeline. This module provides factory functions that handle
the complexity of instantiating the orchestrator and its dependencies.
"""

import os
from pathlib import Path

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
from adw.core.constants import PHASE_SEQUENCE, project_runs_dir
from adw.core.extensions import create_default_registry
from adw.core.phase_runner import PhaseRunner
from adw.exceptions import ConfigError
from adw.executors.base import LLMExecutor
from adw.executors.claude_code import ClaudeCodeExecutor
from adw.hooks.runner import HookRunner
from adw.logging.live_stream import LiveStreamHandler
from adw.models.config import (
    GitConfig,
    HookConfig,
    LLMConfig,
    TaskManagerConfig,
    WorktreeConfig,
)
from adw.models.task import TaskInfo
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
    runs_dir = project_runs_dir(root)
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir


def create_orchestrator(
    console: Console | None = None,
    *,
    with_progress: bool = True,
    live_stream: LiveStreamHandler | None = None,
    task_manager: TaskManager | None = None,
    task_info: TaskInfo | None = None,
) -> Orchestrator:
    """Create a fully configured Orchestrator instance.

    Sets up all required dependencies:
    - ContextManager for state persistence
    - SnapshotManager for debugging snapshots
    - ArtifactManager for storing phase outputs
    - RunDirectoryManager for directory structure
    - InterruptionHandler for graceful shutdown
    - ProgressDisplay for CLI output (optional)
    - PhaseRunner with CommandResolver, TemplateEngine, HookRunner, LLMExecutor
    - LabelManager for task label operations (optional)

    Args:
        console: Rich console for output. If None, creates a new one.
        with_progress: Whether to include progress display.
        live_stream: The run's live.log handler from setup_logging. The
            executor writes the LLM stream through it, so live.log has one
            writer.
        task_manager: Optional task manager for label/sync operations.
        task_info: Optional TaskInfo with internal UUID for label operations.
            task_info.id is used for Linear API calls (not the identifier).

    Returns:
        Configured Orchestrator ready for use.

    Example:
        >>> orchestrator = create_orchestrator()
        >>> context = orchestrator.run_single_phase("plan", "Add login")
    """
    project_root = get_project_root()
    runs_dir = get_runs_dir(project_root)
    console = console or Console()

    # Load project configuration for worktree, git, task manager, and LLM settings
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

    llm_config = config.llm if config else LLMConfig()

    # Create managers
    context_manager = ContextManager(runs_dir)
    snapshot_manager = SnapshotManager(runs_dir)
    artifact_manager = ArtifactManager(runs_dir)
    run_directory_manager = RunDirectoryManager(project_root)
    interruption_handler = InterruptionHandler(context_manager, snapshot_manager)

    # Create PhaseRunner dependencies
    command_resolver = CommandResolver(project_root=project_root)
    template_engine = TemplateEngine(project_root=project_root)
    hook_runner = HookRunner(config=config.hooks if config else HookConfig())

    # Use MockExecutor in test mode to avoid hitting real Claude API
    # Set ADW_MOCK_EXECUTOR=1 to enable mock mode (used by tests)
    # Neither executor retries: the orchestrator retries the whole phase
    llm_executor: LLMExecutor
    if os.environ.get("ADW_MOCK_EXECUTOR"):
        from adw.executors.mock import MockExecutor

        llm_executor = MockExecutor()
    else:
        llm_executor = ClaudeCodeExecutor(
            config=llm_config,
            live_stream=live_stream,
        )

    # Create extension registry with built-in extensions (Phase Extensions)
    # This registers BuildExtension (diff capture), DocumentExtension (PR creation),
    # and ShipExtension (skip logic and hook env vars)
    # NOTE: Must be created BEFORE PhaseRunner so extensions are available for
    # artifact capture during phase execution
    extension_registry = create_default_registry(
        git_config,
        runs_dir,
        project_root=project_root,
        build_command=config.build_command if config else None,
    )

    # Create PhaseRunner first (without progress_display)
    # so we can compute enabled phases using is_phase_enabled()
    phase_runner = PhaseRunner(
        command_resolver=command_resolver,
        template_engine=template_engine,
        hook_runner=hook_runner,
        executor=llm_executor,
        artifact_manager=artifact_manager,
        progress_display=None,
        project_config=config,
        extension_registry=extension_registry,
        git_config=git_config,
    )

    # Progress display for CLI feedback (filter to enabled phases)
    progress_display = None
    if with_progress:
        # Compute enabled phases using PhaseRunner's is_phase_enabled()
        # This checks both command config and project config for each phase
        enabled_phases = [p for p in PHASE_SEQUENCE if phase_runner.is_phase_enabled(p)]
        progress_display = ProgressDisplay(console, enabled_phases=enabled_phases)
        # Update PhaseRunner with the progress display
        phase_runner.progress_display = progress_display

    # Create StatusSyncService if task manager is provided
    # Pass task_info so methods use stored value instead of context
    # Default task_manager_config if not set (e.g., config has task_manager: null)
    status_sync_service: StatusSyncService | None = None
    if task_manager is not None:
        effective_config = task_manager_config or TaskManagerConfig()
        status_sync_service = StatusSyncService(
            task_manager, effective_config, task_info=task_info
        )

    # Create LabelManager if task manager and task_info are provided
    # CRITICAL: LabelManager must receive task_info.id (internal UUID)
    # The Linear API requires internal UUID for all label operations
    label_manager: LabelManager | None = None
    if task_manager is not None and task_info is not None and config is not None:
        labels_config = config.task_manager.labels if config.task_manager else None
        if labels_config and labels_config.enabled:
            label_manager = LabelManager(task_manager, labels_config, task_info.id)

    # Create orchestrator (pass task_info to populate RunContext)
    orchestrator = Orchestrator(
        runs_dir=runs_dir,
        context_manager=context_manager,
        snapshot_manager=snapshot_manager,
        artifact_manager=artifact_manager,
        run_directory_manager=run_directory_manager,
        phase_runner=phase_runner,
        interruption_handler=interruption_handler,
        progress_display=progress_display,
        retry_config=llm_config.retry,
        worktree_config=worktree_config,
        git_config=git_config,
        task_manager_config=task_manager_config,
        label_manager=label_manager,
        status_sync_service=status_sync_service,
        extension_registry=extension_registry,
        task_info=task_info,
    )

    return orchestrator
