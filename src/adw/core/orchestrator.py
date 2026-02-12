"""Main orchestrator for ADW pipeline execution.

This module provides the Orchestrator class that coordinates phase execution
in the fixed order: Plan → Build → Validate → Document.

Key responsibilities:
- Phase sequencing and transitions
- State persistence at boundaries
- Error handling and retry logic
- Snapshot creation for debugging
"""

import logging
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from adw.core.constants import PHASE_SEQUENCE
from adw.core.context_manager import ContextManager
from adw.core.extensions import ExtensionRegistry
from adw.core.index_manager import IndexManager
from adw.core.interruption import InterruptionHandler, ShutdownRequested
from adw.core.resume_manager import ResumeManager
from adw.core.run_directory import RunDirectoryManager
from adw.core.run_lifecycle import RunLifecycle
from adw.core.run_lookup import RunLookup
from adw.core.snapshot_manager import SnapshotManager
from adw.exceptions import ADWError, ConfigError
from adw.models import GitConfig, RunContext, TaskManagerConfig, WorktreeConfig
from adw.models.phase import PhaseResult
from adw.models.task import TaskInfo
from adw.worktree import ConcurrentRunManager
from adw.worktree.manager import WorktreeManager

if TYPE_CHECKING:
    from adw.cli.pr import AutoPRResult
    from adw.cli.progress import ProgressDisplay
    from adw.core.artifact_manager import ArtifactManager
    from adw.task_managers.labels import LabelManager
    from adw.task_managers.sync import StatusSyncService


class PhaseRunnerProtocol(Protocol):
    """Protocol defining the interface for phase runners.

    This allows the Orchestrator to work with any class that implements
    the run() method, without requiring a specific PhaseRunner class.
    """

    def run(
        self,
        phase: str,
        context: RunContext,
        *,
        artifacts_override: dict[str, dict[str, str]] | None = None,
    ) -> PhaseResult:
        """Execute a single phase.

        Args:
            phase: Phase name to execute.
            context: Current run context.
            artifacts_override: Pre-loaded artifacts to use instead of loading
                from the current run.

        Returns:
            PhaseResult from the execution.
        """
        ...

    def is_phase_enabled(self, phase: str) -> bool:
        """Check if a phase is enabled in its command config.

        Args:
            phase: Phase name to check.

        Returns:
            True if the phase is enabled (default), False if disabled.
        """
        ...


__all__ = ["Orchestrator", "PhaseRunnerProtocol"]

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator for ADW pipeline execution.

    Coordinates phase execution in fixed order:
    Plan → Build → Validate → Document

    Handles:
    - Phase sequencing and transitions
    - State persistence at boundaries
    - Error handling and retry logic
    - Snapshot creation for debugging

    Attributes:
        runs_dir: Path to the .adw/runs directory.
        context_manager: Manager for persisting run context.
        snapshot_manager: Manager for creating state snapshots.
        artifact_manager: Manager for storing phase artifacts.
        run_directory_manager: Manager for run directory structure.
        phase_runner: Runner for executing individual phases.
        interruption_handler: Handler for graceful shutdown on Ctrl+C/SIGTERM.
        index_manager: Manager for global workflow execution index.
        max_retries: Maximum retry attempts for recoverable errors.

    Example:
        >>> from pathlib import Path
        >>> orchestrator = Orchestrator(
        ...     runs_dir=Path("/my/project/.adw/runs"),
        ...     context_manager=context_manager,
        ...     snapshot_manager=snapshot_manager,
        ...     artifact_manager=artifact_manager,
        ...     run_directory_manager=run_directory_manager,
        ...     phase_runner=phase_runner,
        ... )
        >>> context = orchestrator.run("Add user authentication")
    """

    def __init__(
        self,
        runs_dir: Path,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
        artifact_manager: "ArtifactManager",
        run_directory_manager: RunDirectoryManager,
        phase_runner: PhaseRunnerProtocol,
        interruption_handler: InterruptionHandler | None = None,
        index_manager: IndexManager | None = None,
        *,
        progress_display: "ProgressDisplay | None" = None,
        max_retries: int = 3,
        worktree_config: WorktreeConfig | None = None,
        git_config: GitConfig | None = None,
        task_manager_config: TaskManagerConfig | None = None,
        label_manager: "LabelManager | None" = None,
        status_sync_service: "StatusSyncService | None" = None,
        resume_manager: ResumeManager | None = None,
        run_lifecycle: RunLifecycle | None = None,
        extension_registry: ExtensionRegistry | None = None,
        task_info: TaskInfo | None = None,
    ) -> None:
        """Initialize the Orchestrator.

        Args:
            runs_dir: Path to the .adw/runs directory.
            context_manager: Manager for persisting run context.
            snapshot_manager: Manager for creating state snapshots.
            artifact_manager: Manager for storing phase artifacts.
            run_directory_manager: Manager for run directory structure.
            phase_runner: Runner for executing individual phases.
            interruption_handler: Handler for graceful shutdown (optional).
            index_manager: Manager for global execution index (optional).
            progress_display: Display for phase progress (optional, Story 5.5).
            max_retries: Maximum retry attempts for recoverable errors (default: 3).
            worktree_config: Worktree isolation config (optional, Story 10.1).
            git_config: Git configuration for auto-PR creation (optional, ISS-011).
            task_manager_config: Task manager configuration for auto-close (Story 12.8).
            label_manager: Manager for task labels (optional, Story 12.7).
            status_sync_service: Service for syncing status with task managers
                (optional, Story 12.3). When provided, sync calls are made at
                phase transitions.
            resume_manager: Manager for resume operations (optional, Story ISS-014).
                When provided, delegates resume validation and phase determination.
            run_lifecycle: Manager for run lifecycle operations (optional).
                When provided, delegates context creation, completion,
                and error handling.
            extension_registry: Registry for phase extensions (optional).
                If None, creates an empty registry (no extensions).
            task_info: Task information from external task manager (optional, ISS-039).
                Passed to RunLifecycle to populate RunContext.task_id and task_info.
        """
        self.runs_dir = runs_dir
        # Derive project path from runs_dir (runs_dir is typically .adw/runs)
        self._project_path = runs_dir.parent.parent
        self.context_manager = context_manager
        self.snapshot_manager = snapshot_manager
        self.artifact_manager = artifact_manager
        self.run_directory_manager = run_directory_manager
        self._phase_runner = phase_runner
        self.interruption_handler = interruption_handler or InterruptionHandler(
            context_manager, snapshot_manager
        )
        self.index_manager = index_manager or IndexManager()
        self.progress_display = progress_display
        self.max_retries = max_retries

        # Git config for auto-PR (Story ISS-011)
        self.git_config = git_config or GitConfig()

        # Task manager config for auto-close (Story 12.8)
        self.task_manager_config = task_manager_config or TaskManagerConfig()

        # Label manager for task label operations (Story 12.7)
        self._label_manager = label_manager

        # Status sync service for task manager integration (Story 12.3)
        self._status_sync_service = status_sync_service

        # Resume manager for centralized resume operations (Story ISS-014)
        # Lazy initialization: create on first use if not provided
        self._resume_manager = resume_manager

        # Extension registry for phase-specific behavior (Phase Extensions)
        self._extension_registry = extension_registry or ExtensionRegistry()

        # Worktree isolation (Story 10.1)
        self.worktree_config = worktree_config or WorktreeConfig()
        self._worktree_manager: WorktreeManager | None = None
        self._concurrent_run_manager: ConcurrentRunManager | None = None
        if self.worktree_config.enabled:
            self._worktree_manager = WorktreeManager(
                project_root=self._project_path,
                base_dir=self.worktree_config.base_dir,
            )
            # Concurrent run tracking (Story 10.4)
            self._concurrent_run_manager = ConcurrentRunManager(
                project_root=self._project_path,
                max_concurrent=self.worktree_config.max_concurrent,
                base_dir=self.worktree_config.base_dir,
            )

        # Run lifecycle manager (Story ISS-XXX)
        # Create default if not provided
        self._lifecycle = run_lifecycle or RunLifecycle(
            runs_dir=runs_dir,
            project_path=self._project_path,
            context_manager=context_manager,
            run_directory_manager=run_directory_manager,
            index_manager=self.index_manager,
            interruption_handler=self.interruption_handler,
            progress_display=progress_display,
            worktree_config=self.worktree_config,
            git_config=self.git_config,
            task_manager_config=self.task_manager_config,
            label_manager=label_manager,
            status_sync_service=status_sync_service,
            worktree_manager=self._worktree_manager,
            concurrent_run_manager=self._concurrent_run_manager,
            task_info=task_info,  # ISS-039: Pass task_info to populate RunContext
        )

    @property
    def resume_manager(self) -> ResumeManager:
        """Get the resume manager, creating it lazily if needed.

        Returns:
            ResumeManager instance for resume operations.
        """
        if self._resume_manager is None:
            self._resume_manager = ResumeManager(
                runs_dir=self.runs_dir,
                run_lookup=RunLookup(self.runs_dir),
                context_manager=self.context_manager,
            )
        return self._resume_manager

    def get_next_phase(self, current_phase: str) -> str | None:
        """Get the next phase in the sequence.

        Args:
            current_phase: Current phase name.

        Returns:
            Next phase name, or None if current is the last phase.

        Example:
            >>> orchestrator.get_next_phase("plan")
            "build"
            >>> orchestrator.get_next_phase("document")
            None
        """
        try:
            idx = PHASE_SEQUENCE.index(current_phase)
            if idx < len(PHASE_SEQUENCE) - 1:
                return PHASE_SEQUENCE[idx + 1]
            return None
        except ValueError:
            return None

    def run(
        self,
        feature_description: str,
        run_id: str | None = None,
        *,
        use_worktree: bool = True,
        task_uuid: str | None = None,
    ) -> RunContext:
        """Execute the full pipeline for a feature.

        This method orchestrates the complete execution flow:
        1. Generate a new run ID (ULID) if not provided
        2. Create worktree for isolation (if enabled)
        3. Create initial context and run directory
        4. Execute each phase in sequence with interruption checking
        5. Handle errors, retries, and graceful shutdown
        6. Preserve worktree for user inspection (ISS-020: use 'adw cleanup' to remove)
        7. Mark run as completed, failed, or interrupted
        8. Attempt to close task if auto_close enabled (Story 12.8)

        Args:
            feature_description: Description of the feature to implement.
            run_id: Optional run ID. If not provided, a new ULID is generated.
            use_worktree: Whether to use worktree isolation for this run.
                Defaults to True. Set to False to run in current directory.
            task_uuid: Internal task UUID (from TaskInfo.id) for issue closing.
                If provided and auto_close is enabled, task will be closed when
                PR is merged (Story 12.8).

        Returns:
            Final RunContext with status and artifacts.

        Raises:
            ADWError: If a non-recoverable error occurs.
            ShutdownRequested: If graceful shutdown is requested (Ctrl+C/SIGTERM).

        Example:
            >>> context = orchestrator.run("Add user authentication")
            >>> print(context.status)  # "completed" or "failed"
            >>> # Run without worktree isolation
            >>> context = orchestrator.run("Quick fix", use_worktree=False)
        """
        # Create run context via lifecycle
        context = self._lifecycle.create_run_context(
            feature_description,
            run_id=run_id,
            use_worktree=use_worktree,
        )

        try:
            with self.interruption_handler.protected_execution(context):
                context, pr_result = self._execute_phases(context, PHASE_SEQUENCE)
                context = self._lifecycle.finalize_success(
                    context, pr_result=pr_result, task_uuid=task_uuid
                )

        except ShutdownRequested as e:
            self._lifecycle.handle_shutdown(context, e)
            raise

        except ADWError as e:
            self._lifecycle.handle_adw_error(context, e)
            raise

        except Exception as e:
            self._lifecycle.handle_exception(context, e)
            raise

        return context

    def run_single_phase(
        self,
        phase: str,
        feature_description: str,
        from_run_id: str | None = None,
        run_id: str | None = None,
        *,
        use_worktree: bool = True,
    ) -> RunContext:
        """Execute a single phase in isolation.

        Creates a new run ID for this execution (or uses provided one) and
        executes only the specified phase. For phases after "plan", artifacts
        from a source run may be needed.

        Args:
            phase: Phase to execute (must be in PHASE_SEQUENCE).
            feature_description: Description of the feature to implement.
            from_run_id: Source run ID for loading artifacts (optional for plan).
            run_id: Optional run ID. If not provided, a new ULID is generated.
            use_worktree: Whether to use worktree isolation for this run.
                Defaults to True. Set to False to run in current directory.

        Returns:
            RunContext for this single-phase execution.

        Raises:
            ADWError: If phase execution fails.

        Example:
            >>> context = orchestrator.run_single_phase("plan", "Add login")
            >>> context = orchestrator.run_single_phase(
            ...     "build", "Add login", from_run_id="01HQTEST123"
            ... )
            >>> # Run without worktree isolation
            >>> context = orchestrator.run_single_phase(
            ...     "plan", "Quick fix", use_worktree=False
            ... )
        """
        # Create run context via lifecycle
        context = self._lifecycle.create_run_context(
            feature_description,
            run_id=run_id,
            use_worktree=use_worktree,
            starting_phase=phase,
        )

        logger.info(
            "Starting single-phase run",
            extra={
                "run_id": context.run_id,
                "phase": phase,
                "from_run": from_run_id,
            },
        )

        # Load artifacts from source run if specified
        source_artifacts: dict[str, dict[str, str]] | None = None
        if from_run_id:
            source_artifacts = self._load_artifacts_from_source(from_run_id, phase)
            self._validate_required_artifacts(phase, source_artifacts, from_run_id)

        try:
            # Execute only the specified phase with source artifacts
            context = self._execute_phase_with_transitions(
                context, phase, artifacts_override=source_artifacts
            )

            # Mark as completed
            context = context.model_copy(
                update={
                    "status": "completed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Update global index on completion (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="completed",
                completed_at=context.completed_at,
                phase_reached=context.current_phase,
                phases_completed=list(context.phase_history),
            )

            # Set completed label (Story 12.7)
            if self._label_manager:
                self._label_manager.set_completed()

            logger.info(
                "Single-phase run completed",
                extra={"run_id": context.run_id, "phase": phase},
            )

            # Preserve worktree for single-phase runs (ISS-018, ISS-020)
            if context.use_worktree and context.worktree_path is not None:
                if self.progress_display:
                    self.progress_display.console.print(
                        f"[green]✓[/green] Phase '{phase}' complete"
                    )
                self._lifecycle._show_worktree_preserved(context, outcome="success")

        except ADWError as e:
            self._lifecycle.handle_adw_error(context, e)
            raise

        except Exception as e:
            self._lifecycle.handle_exception(context, e)
            raise

        return context

    def resume(
        self,
        run_id: str,
        *,
        from_phase: str | None = None,
    ) -> RunContext:
        """Resume a failed or interrupted run.

        Loads the existing run context and continues execution from the
        specified phase (or the current_phase if not specified).

        Args:
            run_id: ID of the run to resume.
            from_phase: Phase to resume from (optional override).

        Returns:
            Final RunContext after completion.

        Raises:
            ConfigError: If run cannot be resumed (completed or invalid phase).
            StateError: If run state is corrupted.
            ADWError: If phase execution fails.

        Example:
            >>> context = orchestrator.resume("01HQXK5P3Z...")
            >>> context = orchestrator.resume("01HQXK5P3Z...", from_phase="build")
        """
        # Load existing context
        context = self.context_manager.load(run_id)

        # Use ResumeManager for validation and phase determination (Story ISS-014)
        self.resume_manager.validate_resumable(context, from_phase=from_phase)

        # Determine resume phase using ResumeManager
        resume_phase = from_phase or self.resume_manager.get_resume_phase(context)
        if resume_phase is None:
            resume_phase = context.current_phase

        # Prepare context for resume
        context = self.resume_manager.prepare_for_resume(context, from_phase=from_phase)
        self.context_manager.save(context)

        logger.info(
            "Resuming run",
            extra={
                "run_id": run_id,
                "from_phase": resume_phase,
                "completed_phases": context.phase_history,
            },
        )

        # Set running label via lifecycle
        context = self._lifecycle.prepare_resume_context(context)

        # Find the index of the resume phase
        start_idx = PHASE_SEQUENCE.index(resume_phase)
        phases_to_run = PHASE_SEQUENCE[start_idx:]

        # Load artifacts from completed phases for context
        source_artifacts = self._load_artifacts_for_resume(context, resume_phase)

        try:
            with self.interruption_handler.protected_execution(context):
                context, pr_result = self._execute_phases(
                    context,
                    phases_to_run,
                    start_artifacts=source_artifacts,
                    resume_phase=resume_phase,
                )
                context = self._lifecycle.finalize_success(context, pr_result=pr_result)

        except ShutdownRequested as e:
            self._lifecycle.handle_shutdown(context, e)
            raise

        except ADWError as e:
            self._lifecycle.handle_adw_error(context, e)
            raise

        except Exception as e:
            self._lifecycle.handle_exception(context, e)
            raise

        return context

    def continue_from_run(
        self,
        phase: str,
        source_run_id: str,
        feature_description: str | None = None,
    ) -> RunContext:
        """Continue from a previous run, reusing its environment.

        Loads the existing run context (worktree, branch, run directory)
        from source_run_id and executes the specified phase within that
        same environment. Unlike run_single_phase(), this does NOT create
        a new run — it reuses the source run's context entirely.

        Args:
            phase: Phase to execute (must be in PHASE_SEQUENCE).
            source_run_id: Run ID to continue from.
            feature_description: Optional override for the feature description.
                If None, uses the source run's feature_description.

        Returns:
            Updated RunContext after phase execution.

        Raises:
            ConfigError: If source run not found or worktree missing.
            ADWError: If phase execution fails.

        Example:
            >>> context = orchestrator.continue_from_run("document", "01HQXK5P3Z...")
            >>> context = orchestrator.continue_from_run(
            ...     "build", "01HQXK5P3Z...", "Override feature"
            ... )
        """
        # Load existing context
        context = self.context_manager.load(source_run_id)

        # Validate worktree still exists if the run used worktrees
        if (
            context.use_worktree
            and context.worktree_path
            and not context.worktree_path.exists()
        ):
            raise ConfigError(
                code="WORKTREE_MISSING",
                message=(
                    f"Worktree for run '{source_run_id}' no longer exists "
                    f"at {context.worktree_path}"
                ),
                suggestion=(
                    "The worktree may have been cleaned up. "
                    "Run a fresh 'adw run' instead."
                ),
                recoverable=False,
            )

        # Override feature description if provided
        if feature_description:
            context = context.model_copy(
                update={"feature_description": feature_description}
            )

        # Prepare context for continuation
        context = context.model_copy(
            update={
                "status": "running",
                "current_phase": phase,
            }
        )
        self.context_manager.save(context)

        logger.info(
            "Continuing from run",
            extra={
                "run_id": source_run_id,
                "phase": phase,
                "feature": context.feature_description,
                "worktree_path": str(context.worktree_path),
            },
        )

        # Load artifacts from the run's own previous phases
        source_artifacts = self._load_artifacts_from_source(source_run_id, phase)
        self._validate_required_artifacts(phase, source_artifacts, source_run_id)

        try:
            # Execute only the specified phase with source artifacts
            context = self._execute_phase_with_transitions(
                context, phase, artifacts_override=source_artifacts
            )

            # Mark as completed
            context = context.model_copy(
                update={
                    "status": "completed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Update global index on completion (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="completed",
                completed_at=context.completed_at,
                phase_reached=context.current_phase,
                phases_completed=list(context.phase_history),
            )

            # Set completed label (Story 12.7)
            if self._label_manager:
                self._label_manager.set_completed()

            logger.info(
                "Continue-from-run completed",
                extra={"run_id": context.run_id, "phase": phase},
            )

            # Preserve worktree for single-phase runs (ISS-018, ISS-020)
            if context.use_worktree and context.worktree_path is not None:
                if self.progress_display:
                    self.progress_display.console.print(
                        f"[green]✓[/green] Phase '{phase}' complete"
                    )
                self._lifecycle._show_worktree_preserved(context, outcome="success")

        except ADWError as e:
            self._lifecycle.handle_adw_error(context, e)
            raise

        except Exception as e:
            self._lifecycle.handle_exception(context, e)
            raise

        return context

    def _execute_phases(
        self,
        context: RunContext,
        phases: Sequence[str],
        *,
        start_artifacts: dict[str, dict[str, str]] | None = None,
        resume_phase: str | None = None,
    ) -> tuple[RunContext, "AutoPRResult | None"]:
        """Execute phases with PR creation logic.

        This method handles the common phase execution loop used by
        run() and resume().

        Args:
            context: Current run context.
            phases: List of phases to execute.
            start_artifacts: Pre-loaded artifacts for the first phase (for resume).
            resume_phase: The phase being resumed from (for artifact handling).

        Returns:
            Tuple of (updated context, PR result or None).
            Note: PR result is now tracked in context via DocumentExtension,
            so this always returns None for pr_result (Phase Extensions).
        """
        for phase in phases:
            # Check for shutdown request between phases (NFR7)
            self.interruption_handler.set_context(context)
            self.interruption_handler.check_shutdown()

            # Check if phase is enabled in command config (ISS-029)
            if not self._phase_runner.is_phase_enabled(phase):
                logger.info(
                    "Phase skipped (disabled in config)",
                    extra={"phase": phase, "run_id": context.run_id},
                )
                continue

            # Check if extensions want to skip this phase (Phase Extensions)
            should_skip, skip_reason = self._extension_registry.should_skip_phase(
                phase, context
            )
            if should_skip:
                logger.info(
                    "Phase skipped (extension requested)",
                    extra={
                        "phase": phase,
                        "run_id": context.run_id,
                        "reason": skip_reason,
                    },
                )
                if self.progress_display:
                    self.progress_display.console.print(
                        f"[yellow]⚠[/yellow] Skipping {phase} phase: {skip_reason}"
                    )
                continue

            # Note: ISS-031 ship phase skip logic is now handled by ShipExtension

            # Use source artifacts only for the resume phase
            artifacts = None
            if start_artifacts and phase == resume_phase:
                artifacts = start_artifacts

            context = self._execute_phase_with_transitions(
                context, phase, artifacts_override=artifacts
            )

            # Note: ISS-031 PR creation now handled by DocumentExtension

        # PR result is now tracked in context via DocumentExtension
        return context, None

    def _load_artifacts_for_resume(
        self,
        context: RunContext,
        resume_phase: str,
    ) -> dict[str, dict[str, str]] | None:
        """Load artifacts from completed phases for resume.

        Loads artifacts from phases that have already completed in this run.
        These artifacts are made available to the resumed phase for template
        rendering.

        Args:
            context: Current run context with phase history.
            resume_phase: Phase about to resume.

        Returns:
            Nested dict: {phase: {artifact_name: content}}, or None if no
            artifacts needed.

        Example:
            >>> artifacts = orch._load_artifacts_for_resume(ctx, "build")
            >>> plan_content = artifacts["plan"]["plan"]
        """
        if not context.phase_history:
            return None

        return self._load_artifacts_from_source(context.run_id, resume_phase)

    def _load_artifacts_from_source(
        self,
        source_run_id: str,
        target_phase: str,
    ) -> dict[str, dict[str, str]]:
        """Load artifacts from a source run for single-phase execution.

        Loads all artifacts from phases that would have executed before the
        target phase. These artifacts are used for template rendering in
        single-phase execution mode.

        Args:
            source_run_id: Run ID to load artifacts from.
            target_phase: Phase about to execute (artifacts from earlier phases).

        Returns:
            Nested dict: {phase: {artifact_name: content}}

        Example:
            >>> artifacts = orch._load_artifacts_from_source("01HQ...", "build")
            >>> plan_content = artifacts["plan"]["plan"]
        """
        artifacts_map: dict[str, dict[str, str]] = {}

        try:
            target_idx = PHASE_SEQUENCE.index(target_phase)
        except ValueError:
            logger.warning(
                "Unknown phase for artifact loading",
                extra={"phase": target_phase, "source_run": source_run_id},
            )
            return artifacts_map

        previous_phases = PHASE_SEQUENCE[:target_idx]

        for phase in previous_phases:
            phase_artifacts = self.artifact_manager.list_artifacts(source_run_id, phase)

            if phase_artifacts:
                phase_map: dict[str, str] = {}
                for artifact_info in phase_artifacts:
                    artifact_name = artifact_info.get("name", "")
                    if artifact_name:
                        name_without_ext = artifact_name.rsplit(".", 1)[0]
                        content = self.artifact_manager.get(
                            source_run_id, phase, artifact_name
                        )
                        if content:
                            if isinstance(content, bytes):
                                content = content.decode("utf-8")
                            phase_map[name_without_ext] = content

                if phase_map:
                    artifacts_map[phase] = phase_map

        logger.info(
            "Loaded artifacts from source run",
            extra={
                "source_run": source_run_id,
                "target_phase": target_phase,
                "phases_loaded": list(artifacts_map.keys()),
            },
        )

        return artifacts_map

    def _validate_required_artifacts(
        self,
        phase: str,
        artifacts: dict[str, dict[str, str]],
        source_run_id: str,
    ) -> None:
        """Validate that required artifacts exist for the phase.

        Each phase after "plan" requires artifacts from all previous phases.
        Raises ConfigError if any required artifacts are missing.

        Args:
            phase: Phase about to execute.
            artifacts: Loaded artifacts from source run.
            source_run_id: Source run ID (for error messages).

        Raises:
            ConfigError: If required artifacts are missing.
        """
        try:
            target_idx = PHASE_SEQUENCE.index(phase)
        except ValueError:
            return

        required_phases = PHASE_SEQUENCE[:target_idx]

        if not required_phases:
            return

        missing_phases = [p for p in required_phases if p not in artifacts]

        if missing_phases:
            missing_str = ", ".join(missing_phases)
            raise ConfigError(
                code="MISSING_ARTIFACTS",
                message=(
                    f"Phase '{phase}' requires artifacts from: {missing_str}. "
                    f"Source run '{source_run_id}' is missing these artifacts."
                ),
                suggestion=(
                    f"Ensure the source run completed the following phases: "
                    f"{missing_str}"
                ),
            )

        logger.debug(
            "Validated required artifacts",
            extra={
                "phase": phase,
                "required_phases": required_phases,
                "found_phases": list(artifacts.keys()),
            },
        )

    def _execute_phase_with_transitions(
        self,
        context: RunContext,
        phase: str,
        *,
        artifacts_override: dict[str, dict[str, str]] | None = None,
    ) -> RunContext:
        """Execute a single phase with proper transitions.

        Flow:
        1. Update current_phase and persist
        2. Create pre-phase snapshot
        3. Notify progress display of phase start
        4. Execute phase (with retries if recoverable)
        5. Create post-phase snapshot
        6. Notify progress display of completion/error
        7. Update phase_history and persist

        Must complete transitions within 1 second (NFR2).

        Args:
            context: Current run context.
            phase: Phase to execute.
            artifacts_override: Pre-loaded artifacts to use instead of loading
                from the current run. Used for single-phase execution.

        Returns:
            Updated context after phase completion.

        Raises:
            ADWError: If phase fails with non-recoverable error.
        """
        transition_start = time.monotonic()

        # Update current phase
        context = context.model_copy(update={"current_phase": phase})
        self.context_manager.save(context)

        # Pre-phase snapshot
        self.snapshot_manager.create_pre_phase_snapshot(context, phase)

        # Notify progress display of phase start (Story 5.5)
        if self.progress_display:
            self.progress_display.on_phase_start(phase)

        # Set phase label (Story 12.7)
        if self._label_manager:
            self._label_manager.set_phase(phase)

        # Sync status with task manager (Story 12.3)
        if self._status_sync_service:
            try:
                self._status_sync_service.sync_phase_start(context, phase)
            except Exception as sync_error:
                logger.warning(
                    "Status sync failed (non-blocking)",
                    extra={
                        "run_id": context.run_id,
                        "phase": phase,
                        "error": str(sync_error),
                    },
                )

        try:
            # Execute phase with retry for recoverable errors
            result = self._execute_phase_with_retry(
                context, phase, artifacts_override=artifacts_override
            )

            # Post-phase snapshot
            self.snapshot_manager.create_post_phase_snapshot(context, phase, result)

            # Post phase completion comment to task manager (Story 12.6)
            # Note: Sync before displaying completion so logs appear in order
            if self._status_sync_service:
                try:
                    self._status_sync_service.post_phase_comment(context, phase, result)
                except Exception as comment_error:
                    logger.warning(
                        "Failed to post phase comment (non-blocking)",
                        extra={
                            "run_id": context.run_id,
                            "phase": phase,
                            "error": str(comment_error),
                        },
                    )

            # Notify progress display of phase completion (Story 5.5)
            if self.progress_display:
                self.progress_display.on_phase_complete(phase, result)

            # Update context with phase completion
            context = context.model_copy(
                update={
                    "phase_history": [*context.phase_history, phase],
                    "phase_tokens": {**context.phase_tokens, phase: result.tokens_used},
                }
            )
            self.context_manager.save(context)

            # Update global index on phase transition (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                phase_reached=phase,
                phases_completed=list(context.phase_history),
            )

            # Call extension on_complete hooks (Phase Extensions)
            context = self._extension_registry.call_on_complete(phase, context, result)
            self.context_manager.save(context)

            transition_time_ms = (time.monotonic() - transition_start) * 1000
            logger.debug(
                "Phase completed",
                extra={"phase": phase, "duration_ms": transition_time_ms},
            )

            if transition_time_ms > 1000:
                logger.debug(
                    "Transition exceeded 1s",
                    extra={"phase": phase, "duration_ms": transition_time_ms},
                )

            return context

        except ADWError as e:
            if self.progress_display:
                self.progress_display.on_phase_error(phase, e)
            raise

    def _execute_phase_with_retry(
        self,
        context: RunContext,
        phase: str,
        *,
        artifacts_override: dict[str, dict[str, str]] | None = None,
    ) -> PhaseResult:
        """Execute a phase with retry logic for recoverable errors.

        Implements exponential backoff: 1s, 2s, 4s between retries.

        Args:
            context: Current run context.
            phase: Phase to execute.
            artifacts_override: Pre-loaded artifacts to use instead of loading
                from the current run. Used for single-phase execution.

        Returns:
            PhaseResult from successful execution.

        Raises:
            ADWError: If error is non-recoverable or retries exhausted.
        """
        assert self._phase_runner is not None, "PhaseRunner cannot be None"

        last_error: ADWError | None = None

        for attempt in range(self.max_retries):
            try:
                return self._phase_runner.run(
                    phase, context, artifacts_override=artifacts_override
                )

            except ADWError as e:
                last_error = e

                if self.progress_display:
                    self.progress_display.on_llm_complete()

                if not e.recoverable:
                    logger.error(
                        "Non-recoverable error",
                        extra={"phase": phase, "error_code": e.code},
                    )
                    raise

                if attempt < self.max_retries - 1:
                    delay = 2**attempt
                    logger.warning(
                        "Retrying phase",
                        extra={
                            "phase": phase,
                            "attempt": attempt + 1,
                            "max_attempts": self.max_retries,
                            "delay": delay,
                        },
                    )
                    time.sleep(delay)

        logger.error(
            "Retries exhausted",
            extra={"phase": phase, "attempts": self.max_retries},
        )
        if last_error is not None:
            raise last_error
        raise RuntimeError("Unexpected state: no error captured but retries exhausted")

    def abort(self, run_id: str, reason: str = "remote_abort") -> RunContext:
        """Abort a running execution.

        Loads the context for the specified run, validates it's in "running"
        status, and then aborts it gracefully using the InterruptionHandler.

        Args:
            run_id: ID of the run to abort.
            reason: Reason for abort (e.g., "remote_abort", "cli_abort").

        Returns:
            Updated RunContext with aborted status.

        Raises:
            ConfigError: If run is not found or not active.
        """
        context = self.context_manager.load(run_id)

        if context.status == "aborted":
            raise ConfigError(
                code="RUN_ALREADY_ABORTED",
                message=f"Run {run_id} is already aborted",
                suggestion="Run was previously aborted",
                recoverable=False,
            )

        if context.status != "running":
            raise ConfigError(
                code="RUN_NOT_ACTIVE",
                message=f"Run is not active (status: {context.status})",
                suggestion="Only running executions can be aborted",
                recoverable=False,
            )

        updated_context = self.interruption_handler.abort_gracefully(
            context, reason=reason
        )

        if context.use_worktree and context.worktree_path:
            logger.info(
                "Preserving worktree for debugging after abort",
                extra={
                    "run_id": run_id,
                    "worktree_path": str(context.worktree_path),
                },
            )

        logger.info(
            "Run aborted",
            extra={"run_id": run_id, "reason": reason},
        )

        return updated_context

    # Note: _maybe_create_pr_after_document removed - now handled by DocumentExtension

    # Keep these methods for backwards compatibility and cleanup command
    def _cleanup_worktree(self, run_id: str, *, preserve: bool = False) -> None:
        """Clean up or preserve the worktree for a run.

        Always unregisters the run from concurrent run tracking (Story 10.4)
        regardless of whether the worktree is preserved or removed.

        Args:
            run_id: ULID identifier for this run.
            preserve: If True, log but don't remove the worktree.
        """
        if self._concurrent_run_manager is not None:
            self._concurrent_run_manager.unregister_run(run_id)

        if self._worktree_manager is None:
            return

        if preserve:
            worktree_path = self._worktree_manager.worktree_base_path / run_id
            logger.info(
                "Preserving worktree for debugging",
                extra={
                    "run_id": run_id,
                    "worktree_path": str(worktree_path),
                },
            )
            return

        worktree_path = self._worktree_manager.worktree_base_path / run_id

        try:
            self._worktree_manager.remove_worktree(
                run_id,
                force=True,
                delete_branch=self.worktree_config.cleanup_branch_on_remove,
                preserve=True,
            )
            logger.info(
                "Cleaned up worktree (force=True, uncommitted changes discarded)",
                extra={
                    "run_id": run_id,
                    "worktree_path": str(worktree_path),
                    "forced": True,
                    "delete_branch": self.worktree_config.cleanup_branch_on_remove,
                },
            )

        except Exception as e:
            logger.warning(
                "Failed to cleanup worktree",
                extra={
                    "run_id": run_id,
                    "worktree_path": str(worktree_path),
                    "error": str(e),
                },
            )
