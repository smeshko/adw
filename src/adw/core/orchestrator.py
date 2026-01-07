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
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from ulid import ULID

from adw.core.constants import PHASE_SEQUENCE
from adw.core.context_manager import ContextManager
from adw.core.index_manager import IndexManager
from adw.core.interruption import InterruptionHandler, ShutdownRequested
from adw.core.run_directory import RunDirectoryManager
from adw.core.snapshot_manager import SnapshotManager
from adw.evidence import (
    HTTPX_AVAILABLE,
    APICaptureStrategy,
    CLIEvidenceGatherer,
    EvidenceSummary,
    WebCaptureStrategy,
    capture_configured_screens,
    check_android_emulator_available,
    check_ios_simulator_available,
    detect_platform,
    generate_evidence_manifest,
    get_evidence_strategy,
    load_evidence_config,
    load_routes_from_config,
    optimize_evidence,
)
from adw.evidence import (
    generate_summary as generate_api_summary,
)
from adw.exceptions import ADWError, ConfigError
from adw.models import GitConfig, RunContext, WorktreeConfig
from adw.models.evidence import (
    APIEvidenceResult,
    EvidenceStrategy,
    MobileDeviceType,
    PlatformType,
)
from adw.models.phase import PhaseResult
from adw.worktree import ConcurrentRunManager
from adw.worktree.manager import WorktreeManager

if TYPE_CHECKING:
    from adw.cli.progress import ProgressDisplay
    from adw.core.artifact_manager import ArtifactManager


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
    ) -> RunContext:
        """Execute the full pipeline for a feature.

        This method orchestrates the complete execution flow:
        1. Generate a new run ID (ULID) if not provided
        2. Create worktree for isolation (if enabled)
        3. Create initial context and run directory
        4. Execute each phase in sequence with interruption checking
        5. Handle errors, retries, and graceful shutdown
        6. Clean up worktree on success, preserve on failure
        7. Mark run as completed, failed, or interrupted

        Args:
            feature_description: Description of the feature to implement.
            run_id: Optional run ID. If not provided, a new ULID is generated.
            use_worktree: Whether to use worktree isolation for this run.
                Defaults to True. Set to False to run in current directory.

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
        # Use provided run_id or generate new one
        run_id = run_id or str(ULID())

        # Determine if we should use worktree for this run
        should_use_worktree = (
            use_worktree
            and self.worktree_config.enabled
            and self._worktree_manager is not None
        )

        # Create worktree if enabled (Story 10.1)
        worktree_path: Path | None = None
        if should_use_worktree:
            worktree_path = self._create_worktree_for_run(run_id)
            # If worktree creation failed, update flag to reflect reality
            if worktree_path is None:
                should_use_worktree = False
                logger.warning(
                    "Worktree creation failed, running in current directory",
                    extra={"run_id": run_id},
                )

        # Create initial context
        context = RunContext(
            run_id=run_id,
            feature_description=feature_description,
            current_phase=PHASE_SEQUENCE[0],
            started_at=datetime.now(UTC),
            status="running",
            worktree_path=worktree_path,
            use_worktree=should_use_worktree,
        )

        # Create run directory structure
        self.run_directory_manager.create(context)

        # Persist initial state before any phase execution (NFR6)
        self.context_manager.save(context)

        # Register run in global index (Story 7.0)
        self.index_manager.register_run(context, self._project_path)

        logger.info(
            "Starting run",
            extra={"run_id": run_id, "feature": feature_description},
        )

        try:
            with self.interruption_handler.protected_execution(context):
                for phase in PHASE_SEQUENCE:
                    # Check for shutdown request between phases (NFR7)
                    self.interruption_handler.set_context(context)
                    self.interruption_handler.check_shutdown()

                    context = self._execute_phase_with_transitions(context, phase)

                # All phases complete
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

                # Show pipeline summary (Story 5.5)
                if self.progress_display:
                    total_tokens = sum(context.phase_tokens.values())
                    duration_ms = 0
                    if context.completed_at and context.started_at:
                        duration_ms = int(
                            (context.completed_at - context.started_at).total_seconds()
                            * 1000
                        )

                    # Attempt auto-PR creation if enabled (Story ISS-011)
                    pr_result = self.progress_display.try_auto_create_pr(
                        run_id=context.run_id,
                        context=context,
                        runs_dir=self.runs_dir,
                        auto_create_pr_enabled=self.git_config.auto_create_pr,
                    )

                    self.progress_display.show_pipeline_summary(
                        completed_phases=context.phase_history,
                        status="completed",
                        total_duration_ms=duration_ms,
                        total_tokens=total_tokens,
                        run_id=context.run_id,
                        pr_result=pr_result,
                    )

                # Clean up worktree on successful completion (Story 10.1)
                if context.use_worktree and context.worktree_path:
                    self._cleanup_worktree(context.run_id, preserve=False)

                logger.info("Run completed", extra={"run_id": run_id})

        except ShutdownRequested as e:
            # Graceful shutdown - state already saved by handler
            # Update global index on interruption (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="interrupted",
                phase_reached=e.phase,
                phases_completed=list(context.phase_history),
            )
            logger.info(
                "Run interrupted",
                extra={"run_id": run_id, "phase": e.phase},
            )
            raise

        except ADWError as e:
            # Mark as failed and persist
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Update global index on failure (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="failed",
                completed_at=context.completed_at,
                phase_reached=context.current_phase,
                phases_completed=list(context.phase_history),
            )

            # Show pipeline summary on failure (Story 5.5)
            if self.progress_display:
                total_tokens = sum(context.phase_tokens.values())
                duration_ms = 0
                if context.completed_at and context.started_at:
                    duration_ms = int(
                        (context.completed_at - context.started_at).total_seconds()
                        * 1000
                    )
                self.progress_display.show_pipeline_summary(
                    completed_phases=context.phase_history,
                    status="failed",
                    total_duration_ms=duration_ms,
                    total_tokens=total_tokens,
                    run_id=context.run_id,
                )

            # Handle worktree on failure (Story 10.1)
            if context.use_worktree and context.worktree_path:
                self._cleanup_worktree(
                    context.run_id,
                    preserve=self.worktree_config.preserve_on_failure,
                )

            logger.error(
                "Run failed",
                extra={
                    "run_id": run_id,
                    "phase": getattr(e, "phase", None),
                    "error_code": e.code,
                },
            )
            raise

        except Exception as e:
            # Catch-all for unexpected errors (RuntimeError, etc.)
            # Ensures run status is updated even for infrastructure errors
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Update global index on failure (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="failed",
                completed_at=context.completed_at,
                phase_reached=context.current_phase,
                phases_completed=list(context.phase_history),
            )

            # Show pipeline summary on failure (Story 5.5)
            if self.progress_display:
                total_tokens = sum(context.phase_tokens.values())
                duration_ms = 0
                if context.completed_at and context.started_at:
                    duration_ms = int(
                        (context.completed_at - context.started_at).total_seconds()
                        * 1000
                    )
                self.progress_display.show_pipeline_summary(
                    completed_phases=context.phase_history,
                    status="failed",
                    total_duration_ms=duration_ms,
                    total_tokens=total_tokens,
                    run_id=context.run_id,
                )

            # Handle worktree on failure (Story 10.1)
            if context.use_worktree and context.worktree_path:
                self._cleanup_worktree(
                    context.run_id,
                    preserve=self.worktree_config.preserve_on_failure,
                )

            logger.error(
                "Run failed with unexpected error",
                extra={
                    "run_id": run_id,
                    "phase": context.current_phase,
                    "error": str(e),
                },
            )
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
        # Use provided run_id or generate new one
        run_id = run_id or str(ULID())

        # Determine if we should use worktree for this run (Story 10.1)
        should_use_worktree = (
            use_worktree
            and self.worktree_config.enabled
            and self._worktree_manager is not None
        )

        # Create worktree if enabled
        worktree_path: Path | None = None
        if should_use_worktree:
            worktree_path = self._create_worktree_for_run(run_id)
            # If worktree creation failed, update flag to reflect reality
            if worktree_path is None:
                should_use_worktree = False
                logger.warning(
                    "Worktree creation failed, running in current directory",
                    extra={"run_id": run_id},
                )

        # Create initial context
        context = RunContext(
            run_id=run_id,
            feature_description=feature_description,
            current_phase=phase,
            started_at=datetime.now(UTC),
            status="running",
            worktree_path=worktree_path,
            use_worktree=should_use_worktree,
        )

        # Create run directory structure
        self.run_directory_manager.create(context)

        # Persist initial state
        self.context_manager.save(context)

        # Register run in global index (Story 7.0)
        self.index_manager.register_run(context, self._project_path)

        logger.info(
            "Starting single-phase run",
            extra={
                "run_id": run_id,
                "phase": phase,
                "from_run": from_run_id,
            },
        )

        # Load artifacts from source run if specified
        source_artifacts: dict[str, dict[str, str]] | None = None
        if from_run_id:
            source_artifacts = self._load_artifacts_from_source(from_run_id, phase)

            # Validate required artifacts exist
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

            logger.info(
                "Single-phase run completed",
                extra={"run_id": run_id, "phase": phase},
            )

            # Preserve worktree for single-phase runs (ISS-018)
            # User intent: single-phase = stop and inspect before deciding next steps
            if should_use_worktree and worktree_path is not None:
                logger.info(
                    "Worktree preserved for inspection",
                    extra={
                        "run_id": run_id,
                        "worktree_path": str(worktree_path),
                        "phase": phase,
                        "reason": "single_phase_execution",
                    },
                )
                # Display worktree preservation message if progress display available
                if self.progress_display:
                    self.progress_display.console.print()
                    self.progress_display.console.print(
                        f"[green]✓[/green] Phase '{phase}' complete"
                    )
                    self.progress_display.console.print(
                        f"[blue]Worktree:[/blue] {worktree_path}"
                    )
                    self.progress_display.console.print(
                        f"Run [yellow]adw cleanup {run_id}[/yellow] when done"
                    )
                    self.progress_display.console.print()

        except ADWError as e:
            # Mark as failed
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Update global index on failure (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="failed",
                completed_at=context.completed_at,
                phase_reached=context.current_phase,
                phases_completed=list(context.phase_history),
            )

            logger.error(
                "Single-phase run failed",
                extra={
                    "run_id": run_id,
                    "phase": phase,
                    "error_code": e.code,
                },
            )

            # Cleanup or preserve worktree based on config (Story 10.1)
            if should_use_worktree and worktree_path is not None:
                self._cleanup_worktree(
                    run_id,
                    preserve=self.worktree_config.preserve_on_failure,
                )
            raise

        except Exception as e:
            # Catch-all for unexpected errors (RuntimeError, etc.)
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Update global index on failure (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="failed",
                completed_at=context.completed_at,
                phase_reached=context.current_phase,
                phases_completed=list(context.phase_history),
            )

            logger.error(
                "Single-phase run failed with unexpected error",
                extra={
                    "run_id": run_id,
                    "phase": phase,
                    "error": str(e),
                },
            )

            # Cleanup or preserve worktree based on config (Story 10.1)
            if should_use_worktree and worktree_path is not None:
                self._cleanup_worktree(
                    run_id,
                    preserve=self.worktree_config.preserve_on_failure,
                )
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

        # Validate run can be resumed
        if context.status == "completed":
            raise ConfigError(
                code="RUN_COMPLETED",
                message="Run already completed",
                suggestion="Start a new run with 'adw run'",
                recoverable=False,
            )

        # Determine resume phase
        resume_phase = from_phase or context.current_phase
        if resume_phase not in PHASE_SEQUENCE:
            valid_phases = ", ".join(PHASE_SEQUENCE)
            raise ConfigError(
                code="INVALID_PHASE",
                message=f"Unknown phase: {resume_phase}",
                suggestion=f"Valid phases: {valid_phases}",
                recoverable=False,
            )

        # Update status to running
        context = context.model_copy(update={"status": "running"})
        self.context_manager.save(context)

        logger.info(
            "Resuming run",
            extra={
                "run_id": run_id,
                "from_phase": resume_phase,
                "completed_phases": context.phase_history,
            },
        )

        # Find the index of the resume phase
        start_idx = PHASE_SEQUENCE.index(resume_phase)

        # Load artifacts from completed phases for context
        source_artifacts = self._load_artifacts_for_resume(context, resume_phase)

        try:
            with self.interruption_handler.protected_execution(context):
                for phase in PHASE_SEQUENCE[start_idx:]:
                    # Check for shutdown request between phases
                    self.interruption_handler.set_context(context)
                    self.interruption_handler.check_shutdown()

                    # Use source artifacts only for the resume phase
                    # (subsequent phases will use artifacts from current run)
                    artifacts = source_artifacts if phase == resume_phase else None
                    context = self._execute_phase_with_transitions(
                        context, phase, artifacts_override=artifacts
                    )

                # All phases complete
                context = context.model_copy(
                    update={
                        "status": "completed",
                        "completed_at": datetime.now(UTC),
                    }
                )
                self.context_manager.save(context)

                # Update global index on resume completion (Story 7.0)
                self.index_manager.update_run(
                    context.run_id,
                    status="completed",
                    completed_at=context.completed_at,
                    phase_reached=context.current_phase,
                    phases_completed=list(context.phase_history),
                )

                # Show pipeline summary (Story 5.5)
                if self.progress_display:
                    total_tokens = sum(context.phase_tokens.values())
                    duration_ms = 0
                    if context.completed_at and context.started_at:
                        duration_ms = int(
                            (context.completed_at - context.started_at).total_seconds()
                            * 1000
                        )

                    # Attempt auto-PR creation if enabled (Story ISS-011)
                    pr_result = self.progress_display.try_auto_create_pr(
                        run_id=context.run_id,
                        context=context,
                        runs_dir=self.runs_dir,
                        auto_create_pr_enabled=self.git_config.auto_create_pr,
                    )

                    self.progress_display.show_pipeline_summary(
                        completed_phases=context.phase_history,
                        status="completed",
                        total_duration_ms=duration_ms,
                        total_tokens=total_tokens,
                        run_id=context.run_id,
                        pr_result=pr_result,
                    )

                logger.info("Resume completed", extra={"run_id": run_id})

                # Clean up worktree on successful resume (Story 10.1)
                if context.use_worktree and context.worktree_path is not None:
                    self._cleanup_worktree(context.run_id, preserve=False)

        except ShutdownRequested as e:
            # Graceful shutdown - state already saved by handler
            # Update global index on resume interruption (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="interrupted",
                phase_reached=e.phase,
                phases_completed=list(context.phase_history),
            )
            logger.info(
                "Resume interrupted",
                extra={"run_id": run_id, "phase": e.phase},
            )
            raise

        except ADWError as e:
            # Mark as failed and persist
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Update global index on resume failure (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="failed",
                completed_at=context.completed_at,
                phase_reached=context.current_phase,
                phases_completed=list(context.phase_history),
            )

            # Show pipeline summary on failure (Story 5.5)
            if self.progress_display:
                total_tokens = sum(context.phase_tokens.values())
                duration_ms = 0
                if context.completed_at and context.started_at:
                    duration_ms = int(
                        (context.completed_at - context.started_at).total_seconds()
                        * 1000
                    )
                self.progress_display.show_pipeline_summary(
                    completed_phases=context.phase_history,
                    status="failed",
                    total_duration_ms=duration_ms,
                    total_tokens=total_tokens,
                    run_id=context.run_id,
                )

            logger.error(
                "Resume failed",
                extra={
                    "run_id": run_id,
                    "phase": getattr(e, "phase", None),
                    "error_code": e.code,
                },
            )

            # Cleanup or preserve worktree based on config (Story 10.1)
            if context.use_worktree and context.worktree_path is not None:
                self._cleanup_worktree(
                    context.run_id,
                    preserve=self.worktree_config.preserve_on_failure,
                )
            raise

        except Exception as e:
            # Catch-all for unexpected errors (RuntimeError, etc.)
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Update global index on failure (Story 7.0)
            self.index_manager.update_run(
                context.run_id,
                status="failed",
                completed_at=context.completed_at,
                phase_reached=context.current_phase,
                phases_completed=list(context.phase_history),
            )

            # Show pipeline summary on failure (Story 5.5)
            if self.progress_display:
                total_tokens = sum(context.phase_tokens.values())
                duration_ms = 0
                if context.completed_at and context.started_at:
                    duration_ms = int(
                        (context.completed_at - context.started_at).total_seconds()
                        * 1000
                    )
                self.progress_display.show_pipeline_summary(
                    completed_phases=context.phase_history,
                    status="failed",
                    total_duration_ms=duration_ms,
                    total_tokens=total_tokens,
                    run_id=context.run_id,
                )

            logger.error(
                "Resume failed with unexpected error",
                extra={
                    "run_id": run_id,
                    "phase": context.current_phase,
                    "error": str(e),
                },
            )

            # Cleanup or preserve worktree based on config (Story 10.1)
            if context.use_worktree and context.worktree_path is not None:
                self._cleanup_worktree(
                    context.run_id,
                    preserve=self.worktree_config.preserve_on_failure,
                )
            raise

        return context

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

        # Load artifacts from phases that completed before the resume phase
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

        # Only load artifacts from phases before target
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
            # List artifacts for this phase from source run
            phase_artifacts = self.artifact_manager.list_artifacts(source_run_id, phase)

            if phase_artifacts:
                phase_map: dict[str, str] = {}
                for artifact_info in phase_artifacts:
                    artifact_name = artifact_info.get("name", "")
                    if artifact_name:
                        # Strip extension for template access
                        name_without_ext = artifact_name.rsplit(".", 1)[0]
                        content = self.artifact_manager.get(
                            source_run_id, phase, artifact_name
                        )
                        if content:
                            # Ensure content is a string for template access
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
        # Determine required phases (all phases before target)
        try:
            target_idx = PHASE_SEQUENCE.index(phase)
        except ValueError:
            return  # Unknown phase - skip validation

        required_phases = PHASE_SEQUENCE[:target_idx]

        if not required_phases:
            return  # plan phase has no requirements

        # Check each required phase has artifacts
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

        logger.info(
            "Starting phase",
            extra={"phase": phase, "run_id": context.run_id},
        )

        # Detect platform at validate phase startup (Story 8.1, ISS-019)
        if phase == "validate":
            context = self._detect_and_store_platform(context)

        try:
            # Execute phase with retry for recoverable errors
            result = self._execute_phase_with_retry(
                context, phase, artifacts_override=artifacts_override
            )

            # Gather evidence after validate phase LLM execution (ISS-010, ISS-019)
            if phase == "validate":
                self._gather_evidence(context)

            # Run evidence optimization after validate phase (Story 8.6, ISS-019)
            if phase == "validate":
                self._optimize_evidence(context)

            # Post-phase snapshot
            self.snapshot_manager.create_post_phase_snapshot(context, phase, result)

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

            transition_time_ms = (time.monotonic() - transition_start) * 1000
            logger.info(
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
            # Notify progress display of phase error (Story 5.5)
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
        # Note: _phase_runner is a required constructor argument, so this should
        # never be None. This check is a defensive guard against improper usage.
        assert self._phase_runner is not None, "PhaseRunner cannot be None"

        last_error: ADWError | None = None

        for attempt in range(self.max_retries):
            try:
                # Delegate to PhaseRunner (Story 5.2)
                return self._phase_runner.run(
                    phase, context, artifacts_override=artifacts_override
                )

            except ADWError as e:
                # Note: Only ADWError subclasses are retried. Other exceptions
                # (IOError, etc.) bubble up immediately as they indicate
                # infrastructure issues that retrying won't resolve.
                last_error = e

                if not e.recoverable:
                    logger.error(
                        "Non-recoverable error",
                        extra={"phase": phase, "error_code": e.code},
                    )
                    raise

                if attempt < self.max_retries - 1:
                    delay = 2**attempt  # 1, 2, 4 seconds
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

        # Retries exhausted
        logger.error(
            "Retries exhausted",
            extra={"phase": phase, "attempts": self.max_retries},
        )
        if last_error is not None:
            raise last_error
        raise RuntimeError("Unexpected state: no error captured but retries exhausted")

    def _detect_and_store_platform(self, context: RunContext) -> RunContext:
        """Detect platform type and store in RunContext (Story 8.1).

        Runs platform detection at the start of the validate phase to determine
        which evidence gathering strategy to use. The detected platform is
        stored in the context for downstream use.

        Args:
            context: Current run context.

        Returns:
            Updated context with detected platform stored.
        """
        detection_result = detect_platform(self._project_path)

        logger.info(
            "Platform detected for evidence gathering",
            extra={
                "platform": detection_result.platform.value,
                "confidence": detection_result.confidence.value,
                "source": detection_result.source,
                "markers": detection_result.markers,
            },
        )

        # Store detected platform in context for downstream use
        # Map PlatformType enum to string value for context storage
        platform_value = detection_result.platform.value

        # Handle UNKNOWN platform with default to CLI
        if detection_result.platform == PlatformType.UNKNOWN:
            platform_value = "cli"
            logger.warning(
                "Platform unknown, defaulting to CLI",
                extra={"run_id": context.run_id},
            )

        context = context.model_copy(update={"platform": platform_value})
        self.context_manager.save(context)

        return context

    def _gather_evidence(
        self, context: RunContext
    ) -> list[EvidenceSummary]:
        """Gather evidence based on detected platform type (Story ISS-010, ISS-019).

        This method is called after the LLM validate phase completes and before
        evidence optimization. It gathers platform-appropriate evidence:
        - CLI: Command outputs captured
        - WEB: Browser screenshots via Playwright
        - MOBILE: Simulator/emulator screenshots
        - BACKEND: API request/response pairs (if configured)

        Evidence is stored in .adw/runs/<run_id>/evidence/ and a manifest
        is generated.

        Args:
            context: Current run context with platform detected.

        Returns:
            List of EvidenceSummary objects from gathered evidence.
        """
        # Get platform from context (set by _detect_and_store_platform)
        platform_str = context.platform or "cli"
        try:
            platform = PlatformType(platform_str)
        except ValueError:
            platform = PlatformType.CLI
            logger.warning(
                "Invalid platform value, defaulting to CLI",
                extra={"run_id": context.run_id, "platform": platform_str},
            )

        # Determine evidence strategy
        strategy = get_evidence_strategy(platform)

        # Set up evidence directory
        run_dir = self.runs_dir / context.run_id
        evidence_dir = run_dir / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        summaries: list[EvidenceSummary] = []

        logger.info(
            "Starting evidence gathering",
            extra={
                "run_id": context.run_id,
                "platform": platform.value,
                "strategy": strategy.value,
            },
        )

        try:
            if strategy == EvidenceStrategy.TERMINAL_OUTPUT:
                # CLI evidence gathering
                cli_evidence_dir = evidence_dir / "cli"
                cli_evidence_dir.mkdir(parents=True, exist_ok=True)

                gatherer = CLIEvidenceGatherer(
                    project_root=self._project_path,
                    evidence_dir=cli_evidence_dir,
                )

                if gatherer.should_gather(platform):
                    summary = gatherer.gather()
                    summaries.append(summary)
                    logger.info(
                        "CLI evidence gathered",
                        extra={
                            "run_id": context.run_id,
                            "total_commands": summary.total_commands,
                            "passed": summary.passed,
                            "failed": summary.failed,
                        },
                    )

            elif strategy == EvidenceStrategy.SCREENSHOT:
                if platform == PlatformType.WEB:
                    # Web screenshot capture
                    web_evidence_dir = evidence_dir / "screenshots"
                    web_evidence_dir.mkdir(parents=True, exist_ok=True)

                    # Load routes from config
                    config_result = load_routes_from_config(self._project_path)
                    if config_result:
                        routes, base_url, viewports = config_result
                        capture = WebCaptureStrategy(
                            output_dir=web_evidence_dir,
                            base_url=base_url,
                            viewports=viewports,
                        )

                        if capture.is_available:
                            results = []
                            for route in routes:
                                all_viewports = capture.capture_route_all_viewports(
                                    route
                                )
                                results.extend(all_viewports)

                            # Create summary from results
                            from adw.models.evidence import WebEvidenceSummary

                            web_summary = WebEvidenceSummary(
                                base_url=base_url,
                                total_screenshots=len(results),
                                successful=sum(1 for r in results if r.success),
                                failed=sum(1 for r in results if not r.success),
                                results=results,
                            )
                            summaries.append(web_summary)
                            logger.info(
                                "Web evidence gathered",
                                extra={
                                    "run_id": context.run_id,
                                    "total_screenshots": web_summary.total_screenshots,
                                    "successful": web_summary.successful,
                                },
                            )
                        else:
                            logger.warning(
                                "Playwright not available, skipping web screenshots",
                                extra={
                                    "run_id": context.run_id,
                                    "reason": capture.unavailable_reason,
                                },
                            )
                    else:
                        logger.debug(
                            "No web routes configured, skipping web evidence",
                            extra={"run_id": context.run_id},
                        )

                elif platform == PlatformType.MOBILE:
                    # Mobile screenshot capture
                    mobile_evidence_dir = evidence_dir / "mobile"
                    mobile_evidence_dir.mkdir(parents=True, exist_ok=True)

                    # Detect available device
                    device_type = None
                    if check_ios_simulator_available():
                        device_type = MobileDeviceType.IOS
                    elif check_android_emulator_available():
                        device_type = MobileDeviceType.ANDROID

                    if device_type:
                        mobile_summary = capture_configured_screens(
                            project_root=self._project_path,
                            output_dir=mobile_evidence_dir,
                            device_type=device_type,
                        )
                        summaries.append(mobile_summary)
                        logger.info(
                            "Mobile evidence gathered",
                            extra={
                                "run_id": context.run_id,
                                "device_type": device_type.value,
                                "total_screenshots": mobile_summary.total_screenshots,
                                "successful": mobile_summary.successful,
                            },
                        )
                    else:
                        logger.warning(
                            "No mobile device available, skipping mobile screenshots",
                            extra={"run_id": context.run_id},
                        )

            elif strategy == EvidenceStrategy.API_CAPTURE:
                # API capture for BACKEND projects
                if not HTTPX_AVAILABLE or APICaptureStrategy is None:
                    logger.warning(
                        "httpx not available, skipping API evidence capture",
                        extra={"run_id": context.run_id},
                    )
                else:
                    api_evidence_dir = evidence_dir / "api"
                    api_evidence_dir.mkdir(parents=True, exist_ok=True)

                    # Load API endpoints from project config
                    api_config = load_evidence_config(self._project_path)
                    if api_config and api_config.endpoints:
                        api_capture = APICaptureStrategy(
                            base_url=api_config.base_url,
                            auth=api_config.auth,
                        )

                        # Capture all configured endpoints
                        api_results: list[APIEvidenceResult] = []
                        for endpoint in api_config.endpoints:
                            api_result = api_capture.call_endpoint(endpoint)
                            api_results.append(api_result)

                            # Write individual result to file
                            result_path = (
                                api_evidence_dir / f"{endpoint.name}.json"
                            )
                            result_path.write_text(api_result.model_dump_json(indent=2))

                        # Generate and store summary
                        api_summary = generate_api_summary(
                            base_url=api_config.base_url,
                            results=api_results,
                        )
                        summaries.append(api_summary)

                        logger.info(
                            "API evidence gathered",
                            extra={
                                "run_id": context.run_id,
                                "total_endpoints": api_summary.total_endpoints,
                                "successful": api_summary.successful,
                                "failed": api_summary.failed,
                            },
                        )
                    else:
                        logger.debug(
                            "No API endpoints configured, skipping API evidence",
                            extra={"run_id": context.run_id},
                        )

            # Generate evidence manifest if any evidence was gathered
            if summaries:
                plan_path = run_dir / "artifacts" / "plan" / "plan_output.md"
                manifest = generate_evidence_manifest(
                    run_id=context.run_id,
                    platform=platform.value,
                    evidence_directory=evidence_dir,
                    summaries=summaries,
                    plan_path=plan_path if plan_path.exists() else None,
                )
                logger.info(
                    "Evidence manifest generated",
                    extra={
                        "run_id": context.run_id,
                        "total_items": manifest.total_items,
                        "passed": manifest.passed,
                        "failed": manifest.failed,
                    },
                )

                # Copy evidence to validate artifacts for Document phase (ISS-019)
                validate_evidence_dir = (
                    run_dir / "artifacts" / "validate" / "evidence"
                )
                validate_evidence_dir.parent.mkdir(parents=True, exist_ok=True)
                if validate_evidence_dir.exists():
                    shutil.rmtree(validate_evidence_dir)
                shutil.copytree(evidence_dir, validate_evidence_dir)
                logger.info(
                    "Evidence copied to validate artifacts",
                    extra={
                        "run_id": context.run_id,
                        "source": str(evidence_dir),
                        "dest": str(validate_evidence_dir),
                    },
                )
            else:
                logger.debug(
                    "No evidence gathered, skipping manifest generation",
                    extra={"run_id": context.run_id},
                )

        except Exception as e:
            # Evidence gathering failures should NOT fail the run
            logger.warning(
                "Evidence gathering failed",
                extra={"run_id": context.run_id, "error": str(e)},
            )

        return summaries

    def _optimize_evidence(self, context: RunContext) -> None:
        """Optimize evidence files after validate phase completes (Story 8.6, ISS-019).

        Runs evidence optimization on the evidence directory to:
        - Compress images to reduce size
        - Truncate large text files
        - Minify JSON files

        The optimization report is saved to the evidence directory.

        Args:
            context: Current run context with run_id.
        """
        # Construct evidence directory path
        run_dir = self.runs_dir / context.run_id
        evidence_dir = run_dir / "evidence"

        # Only optimize if evidence directory exists
        if not evidence_dir.exists():
            logger.debug(
                "No evidence directory found, skipping optimization",
                extra={"run_id": context.run_id},
            )
            return

        try:
            report = optimize_evidence(
                run_id=context.run_id,
                evidence_directory=evidence_dir,
                project_root=self._project_path,
            )

            logger.info(
                "Evidence optimization completed",
                extra={
                    "run_id": context.run_id,
                    "files_optimized": report.files_optimized,
                    "total_files": report.total_files,
                    "savings_bytes": report.total_savings_bytes,
                    "savings_percent": report.total_savings_percent,
                },
            )

        except Exception as e:
            # Log but don't fail the phase if optimization fails
            logger.warning(
                "Evidence optimization failed",
                extra={"run_id": context.run_id, "error": str(e)},
            )

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
        # Load context
        context = self.context_manager.load(run_id)

        # Check if already aborted
        if context.status == "aborted":
            raise ConfigError(
                code="RUN_ALREADY_ABORTED",
                message=f"Run {run_id} is already aborted",
                suggestion="Run was previously aborted",
                recoverable=False,
            )

        # Validate run is active
        if context.status != "running":
            raise ConfigError(
                code="RUN_NOT_ACTIVE",
                message=f"Run is not active (status: {context.status})",
                suggestion="Only running executions can be aborted",
                recoverable=False,
            )

        # Abort gracefully using InterruptionHandler
        updated_context = self.interruption_handler.abort_gracefully(
            context, reason=reason
        )

        # Preserve worktree on abort for debugging (Story 10.1)
        if context.use_worktree and context.worktree_path:
            # Always preserve on abort - user may want to debug
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

    def _create_worktree_for_run(self, run_id: str) -> Path | None:
        """Create a worktree for the given run.

        Creates a git worktree in the configured base directory for isolated
        execution of this run. Checks concurrent run limits before creation
        and registers the run after successful creation.

        Args:
            run_id: ULID identifier for this run.

        Returns:
            Path to the created worktree, or None if creation failed.

        Raises:
            MaxConcurrentRunsError: If the maximum concurrent runs limit is reached.
        """
        if self._worktree_manager is None:
            return None

        # Check concurrent run limit before creating worktree (Story 10.4)
        if self._concurrent_run_manager is not None:
            # This will raise MaxConcurrentRunsError if at limit
            self._concurrent_run_manager.check_can_start_or_raise()

        try:
            worktree_path = self._worktree_manager.create_worktree(run_id)
            logger.info(
                "Created worktree for run",
                extra={
                    "run_id": run_id,
                    "worktree_path": str(worktree_path),
                },
            )

            # Register the run after successful worktree creation (Story 10.4)
            if self._concurrent_run_manager is not None:
                self._concurrent_run_manager.register_run(
                    run_id=run_id,
                    worktree_path=worktree_path,
                )

            return worktree_path

        except Exception as e:
            # Log but don't fail the run - fall back to running in current directory
            logger.warning(
                "Failed to create worktree, running in current directory",
                extra={
                    "run_id": run_id,
                    "error": str(e),
                },
            )
            return None

    def _cleanup_worktree(self, run_id: str, *, preserve: bool = False) -> None:
        """Clean up or preserve the worktree for a run.

        Always unregisters the run from concurrent run tracking (Story 10.4)
        regardless of whether the worktree is preserved or removed.

        Args:
            run_id: ULID identifier for this run.
            preserve: If True, log but don't remove the worktree.
        """
        # Always unregister the run from concurrent tracking (Story 10.4)
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
                preserve=True,  # Preserve artifacts to main project before removal
            )
            # Log successful cleanup with path and force indication (ISS-008)
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
            # Log but don't fail - worktree cleanup is not critical
            logger.warning(
                "Failed to cleanup worktree",
                extra={
                    "run_id": run_id,
                    "worktree_path": str(worktree_path),
                    "error": str(e),
                },
            )
