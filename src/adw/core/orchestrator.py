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
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from ulid import ULID

from adw.core.constants import PHASE_SEQUENCE
from adw.core.context_manager import ContextManager
from adw.core.index_manager import IndexManager
from adw.core.interruption import InterruptionHandler, ShutdownRequested
from adw.core.resume_manager import ResumeManager
from adw.core.run_directory import RunDirectoryManager
from adw.core.run_lookup import RunLookup
from adw.core.snapshot_manager import SnapshotManager
from adw.exceptions import ADWError, ConfigError, WorktreeError
from adw.hooks.git_branch import sanitize_branch_name
from adw.models import GitConfig, RunContext, TaskManagerConfig, WorktreeConfig
from adw.models.phase import PhaseResult
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
        # Use provided run_id or generate new one
        run_id = run_id or str(ULID())

        # Determine if we should use worktree for this run
        should_use_worktree = (
            use_worktree
            and self.worktree_config.enabled
            and self._worktree_manager is not None
        )

        # Create worktree if enabled (Story 10.1, ISS-025, ISS-032)
        worktree_path: Path | None = None
        branch_name: str | None = None
        if should_use_worktree:
            worktree_result = self._create_worktree_for_run(run_id, feature_description)
            # If worktree creation failed, update flag to reflect reality
            if worktree_result is None:
                should_use_worktree = False
                logger.warning(
                    "Worktree creation failed, running in current directory",
                    extra={"run_id": run_id},
                )
            else:
                worktree_path, branch_name = worktree_result

        # Create initial context (ISS-025: branch_name now populated)
        context = RunContext(
            run_id=run_id,
            feature_description=feature_description,
            current_phase=PHASE_SEQUENCE[0],
            started_at=datetime.now(UTC),
            status="running",
            worktree_path=worktree_path,
            use_worktree=should_use_worktree,
            branch_name=branch_name,
        )

        # Create run directory structure
        self.run_directory_manager.create(context)

        # Persist initial state before any phase execution (NFR6)
        self.context_manager.save(context)

        # Register run in global index (Story 7.0)
        self.index_manager.register_run(context, self._project_path)

        # Set running label (Story 12.7)
        if self._label_manager:
            self._label_manager.set_running()

        logger.info(
            "Starting run",
            extra={"run_id": run_id, "feature": feature_description},
        )

        # Track PR result at run scope for ship phase and completion summary (ISS-031)
        pr_result = None
        pr_creation_attempted = False

        try:
            with self.interruption_handler.protected_execution(context):
                for phase in PHASE_SEQUENCE:
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

                    # ISS-031: Skip ship phase if PR creation was attempted but failed
                    # Only skip if we actually tried to create a PR and it failed
                    # If PR creation wasn't attempted (no progress_display), run ship
                    if (
                        phase == "ship"
                        and pr_creation_attempted
                        and (pr_result is None or not pr_result.success)
                    ):
                        reason = pr_result.reason if pr_result else "PR creation failed"
                        logger.warning(
                            "Skipping ship phase - PR not available",
                            extra={
                                "phase": phase,
                                "run_id": context.run_id,
                                "reason": reason,
                            },
                        )
                        if self.progress_display:
                            self.progress_display.console.print(
                                f"[yellow]⚠[/yellow] Skipping ship phase: {reason}"
                            )
                        continue

                    context = self._execute_phase_with_transitions(context, phase)

                    # ISS-031: Create PR immediately after document phase (before ship)
                    # This ensures ship phase can validate and merge the PR
                    if phase == "document" and self.git_config.auto_create_pr:
                        # Only mark as attempted if we have the capability to create PRs
                        if self.progress_display:
                            pr_creation_attempted = True
                        pr_result = self._maybe_create_pr_after_document(context)

                        # Store PR URL in context for ship phase hooks (ISS-031)
                        if pr_result and pr_result.success and pr_result.pr_url:
                            context = context.model_copy(
                                update={"pr_url": pr_result.pr_url}
                            )
                            self.context_manager.save(context)

                # All phases complete
                context = context.model_copy(
                    update={
                        "status": "completed",
                        "completed_at": datetime.now(UTC),
                    }
                )
                self.context_manager.save(context)

                # Set completed label (Story 12.7)
                if self._label_manager:
                    self._label_manager.set_completed()

                # Update global index on completion (Story 7.0)
                self.index_manager.update_run(
                    context.run_id,
                    status="completed",
                    completed_at=context.completed_at,
                    phase_reached=context.current_phase,
                    phases_completed=list(context.phase_history),
                )

                # Note: PR creation moved to after document phase (ISS-031)
                # pr_result is already set from _maybe_create_pr_after_document()

                # Post run completion comment to task manager (Story 12.6)
                # Non-blocking: catch and log any errors, never fail the run
                if self._status_sync_service:
                    try:
                        self._status_sync_service.post_completion_comment(
                            context,
                            pr_url=pr_result.pr_url if pr_result else None,
                            summary="All phases completed successfully",
                        )
                    except Exception as comment_error:
                        logger.warning(
                            "Failed to post completion comment (non-blocking)",
                            extra={
                                "run_id": context.run_id,
                                "error": str(comment_error),
                            },
                        )

                # Attempt to close task if auto_close enabled (Story 12.8)
                # This must run regardless of progress_display
                self._maybe_close_task(
                    task_uuid=task_uuid,
                    pr_url=pr_result.pr_url if pr_result else None,
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

                    self.progress_display.show_pipeline_summary(
                        completed_phases=context.phase_history,
                        status="completed",
                        total_duration_ms=duration_ms,
                        total_tokens=total_tokens,
                        run_id=context.run_id,
                        pr_result=pr_result,
                    )

                # Preserve worktree for user inspection (ISS-020)
                # Worktrees are NEVER auto-deleted - only via explicit cleanup command
                self._show_worktree_preserved(context, outcome="success")

                logger.info("Run completed", extra={"run_id": run_id})

        except ShutdownRequested as e:
            # Graceful shutdown - state already saved by handler
            # Clear running label on interruption (Story 12.7)
            if self._label_manager:
                self._label_manager.set_failed()

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
            # Sync failure status with task manager (Story 12.3)
            # Use error's phase if available (more accurate), else fall back to context
            # Non-blocking: catch and log any sync errors, never fail the run
            failed_phase = getattr(e, "phase", None) or context.current_phase
            if self._status_sync_service:
                try:
                    self._status_sync_service.sync_run_failed(
                        context, failed_phase, str(e)
                    )
                except Exception as sync_error:
                    logger.warning(
                        "Status sync failed (non-blocking)",
                        extra={
                            "run_id": context.run_id,
                            "phase": failed_phase,
                            "error": str(sync_error),
                        },
                    )

                # Post failure comment to task manager (Story 12.6)
                try:
                    self._status_sync_service.post_failure_comment(
                        context, failed_phase, str(e)
                    )
                except Exception as comment_error:
                    logger.warning(
                        "Failed to post failure comment (non-blocking)",
                        extra={
                            "run_id": context.run_id,
                            "phase": failed_phase,
                            "error": str(comment_error),
                        },
                    )

            # Mark as failed and persist
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Set failed label (Story 12.7)
            if self._label_manager:
                self._label_manager.set_failed()

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

            # Preserve worktree for debugging (ISS-020)
            # Worktrees are NEVER auto-deleted - only via explicit cleanup command
            self._show_worktree_preserved(context, outcome="failure")

            logger.error(
                "Run failed",
                extra={
                    "run_id": run_id,
                    "phase": failed_phase,
                    "error_code": e.code,
                },
            )
            raise

        except Exception as e:
            # Sync failure status with task manager (Story 12.3)
            # Non-blocking: catch and log any sync errors, never fail the run
            if self._status_sync_service:
                try:
                    self._status_sync_service.sync_run_failed(
                        context, context.current_phase, str(e)
                    )
                except Exception as sync_error:
                    logger.warning(
                        "Status sync failed (non-blocking)",
                        extra={
                            "run_id": context.run_id,
                            "phase": context.current_phase,
                            "error": str(sync_error),
                        },
                    )

                # Post failure comment to task manager (Story 12.6)
                try:
                    self._status_sync_service.post_failure_comment(
                        context, context.current_phase, str(e)
                    )
                except Exception as comment_error:
                    logger.warning(
                        "Failed to post failure comment (non-blocking)",
                        extra={
                            "run_id": context.run_id,
                            "phase": context.current_phase,
                            "error": str(comment_error),
                        },
                    )

            # Catch-all for unexpected errors (RuntimeError, etc.)
            # Ensures run status is updated even for infrastructure errors
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Set failed label (Story 12.7)
            if self._label_manager:
                self._label_manager.set_failed()

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

            # Preserve worktree for debugging (ISS-020)
            # Worktrees are NEVER auto-deleted - only via explicit cleanup command
            self._show_worktree_preserved(context, outcome="failure")

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

        # Create worktree if enabled (ISS-025, ISS-032)
        worktree_path: Path | None = None
        branch_name: str | None = None
        if should_use_worktree:
            worktree_result = self._create_worktree_for_run(run_id, feature_description)
            # If worktree creation failed, update flag to reflect reality
            if worktree_result is None:
                should_use_worktree = False
                logger.warning(
                    "Worktree creation failed, running in current directory",
                    extra={"run_id": run_id},
                )
            else:
                worktree_path, branch_name = worktree_result

        # Create initial context (ISS-025, ISS-032: branch_name now populated)
        context = RunContext(
            run_id=run_id,
            feature_description=feature_description,
            current_phase=phase,
            started_at=datetime.now(UTC),
            status="running",
            worktree_path=worktree_path,
            use_worktree=should_use_worktree,
            branch_name=branch_name,
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

        # Set running label (Story 12.7)
        if self._label_manager:
            self._label_manager.set_running()

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

            # Set completed label (Story 12.7)
            if self._label_manager:
                self._label_manager.set_completed()

            logger.info(
                "Single-phase run completed",
                extra={"run_id": run_id, "phase": phase},
            )

            # Preserve worktree for single-phase runs (ISS-018, ISS-020)
            # User intent: single-phase = stop and inspect before deciding next steps
            if should_use_worktree and worktree_path is not None:
                # Show phase completion message before worktree info
                if self.progress_display:
                    self.progress_display.console.print(
                        f"[green]✓[/green] Phase '{phase}' complete"
                    )
                self._show_worktree_preserved(context, outcome="success")

        except ADWError as e:
            # Sync failure status with task manager (Story 12.3)
            # Non-blocking: catch and log any sync errors, never fail the run
            if self._status_sync_service:
                try:
                    self._status_sync_service.sync_run_failed(context, phase, str(e))
                except Exception as sync_error:
                    logger.warning(
                        "Status sync failed (non-blocking)",
                        extra={
                            "run_id": context.run_id,
                            "phase": phase,
                            "error": str(sync_error),
                        },
                    )

            # Mark as failed
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Set failed label (Story 12.7)
            if self._label_manager:
                self._label_manager.set_failed()

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

            # Preserve worktree for debugging (ISS-020)
            # Worktrees are NEVER auto-deleted - only via explicit cleanup command
            self._show_worktree_preserved(context, outcome="failure")
            raise

        except Exception as e:
            # Sync failure status with task manager (Story 12.3)
            # Non-blocking: catch and log any sync errors, never fail the run
            if self._status_sync_service:
                try:
                    self._status_sync_service.sync_run_failed(context, phase, str(e))
                except Exception as sync_error:
                    logger.warning(
                        "Status sync failed (non-blocking)",
                        extra={
                            "run_id": context.run_id,
                            "phase": phase,
                            "error": str(sync_error),
                        },
                    )

            # Catch-all for unexpected errors (RuntimeError, etc.)
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Set failed label (Story 12.7)
            if self._label_manager:
                self._label_manager.set_failed()

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

            # Preserve worktree for debugging (ISS-020)
            # Worktrees are NEVER auto-deleted - only via explicit cleanup command
            self._show_worktree_preserved(context, outcome="failure")
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
            # All phases completed but status not "completed" - use current
            resume_phase = context.current_phase

        # Prepare context for resume (clears interrupted state, sets running)
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

        # Set running label (Story 12.7)
        if self._label_manager:
            self._label_manager.set_running()

        # Find the index of the resume phase
        start_idx = PHASE_SEQUENCE.index(resume_phase)

        # Load artifacts from completed phases for context
        source_artifacts = self._load_artifacts_for_resume(context, resume_phase)

        # Track PR result at run scope for ship phase and completion summary (ISS-031)
        pr_result = None
        pr_creation_attempted = False

        try:
            with self.interruption_handler.protected_execution(context):
                for phase in PHASE_SEQUENCE[start_idx:]:
                    # Check for shutdown request between phases
                    self.interruption_handler.set_context(context)
                    self.interruption_handler.check_shutdown()

                    # Check if phase is enabled in command config (ISS-029)
                    if not self._phase_runner.is_phase_enabled(phase):
                        logger.info(
                            "Phase skipped (disabled in config)",
                            extra={"phase": phase, "run_id": context.run_id},
                        )
                        continue

                    # ISS-031: Skip ship phase if PR creation was attempted but failed
                    # Only skip if we actually tried to create a PR and it failed
                    # If PR creation wasn't attempted (no progress_display), run ship
                    if (
                        phase == "ship"
                        and pr_creation_attempted
                        and (pr_result is None or not pr_result.success)
                    ):
                        reason = pr_result.reason if pr_result else "PR creation failed"
                        logger.warning(
                            "Skipping ship phase - PR not available",
                            extra={
                                "phase": phase,
                                "run_id": context.run_id,
                                "reason": reason,
                            },
                        )
                        if self.progress_display:
                            self.progress_display.console.print(
                                f"[yellow]⚠[/yellow] Skipping ship phase: {reason}"
                            )
                        continue

                    # Use source artifacts only for the resume phase
                    # (subsequent phases will use artifacts from current run)
                    artifacts = source_artifacts if phase == resume_phase else None
                    context = self._execute_phase_with_transitions(
                        context, phase, artifacts_override=artifacts
                    )

                    # ISS-031: Create PR immediately after document phase (before ship)
                    # This ensures ship phase can validate and merge the PR
                    if phase == "document" and self.git_config.auto_create_pr:
                        # Only mark as attempted if we have the capability to create PRs
                        if self.progress_display:
                            pr_creation_attempted = True
                        pr_result = self._maybe_create_pr_after_document(context)

                        # Store PR URL in context for ship phase hooks (ISS-031)
                        if pr_result and pr_result.success and pr_result.pr_url:
                            context = context.model_copy(
                                update={"pr_url": pr_result.pr_url}
                            )
                            self.context_manager.save(context)

                # All phases complete
                context = context.model_copy(
                    update={
                        "status": "completed",
                        "completed_at": datetime.now(UTC),
                    }
                )
                self.context_manager.save(context)

                # Set completed label (Story 12.7)
                if self._label_manager:
                    self._label_manager.set_completed()

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

                    # Note: PR creation moved to after document phase (ISS-031)
                    # pr_result is already set from _maybe_create_pr_after_document()

                    self.progress_display.show_pipeline_summary(
                        completed_phases=context.phase_history,
                        status="completed",
                        total_duration_ms=duration_ms,
                        total_tokens=total_tokens,
                        run_id=context.run_id,
                        pr_result=pr_result,
                    )

                logger.info("Resume completed", extra={"run_id": run_id})

                # Preserve worktree for user inspection (ISS-020)
                # Worktrees are NEVER auto-deleted - only via explicit cleanup command
                self._show_worktree_preserved(context, outcome="success")

        except ShutdownRequested as e:
            # Graceful shutdown - state already saved by handler
            # Clear running label on interruption (Story 12.7)
            if self._label_manager:
                self._label_manager.set_failed()

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
            # Sync failure status with task manager (Story 12.3)
            # Non-blocking: catch and log any sync errors, never fail the run
            if self._status_sync_service:
                try:
                    self._status_sync_service.sync_run_failed(
                        context, context.current_phase, str(e)
                    )
                except Exception as sync_error:
                    logger.warning(
                        "Status sync failed (non-blocking)",
                        extra={
                            "run_id": context.run_id,
                            "phase": context.current_phase,
                            "error": str(sync_error),
                        },
                    )

            # Mark as failed and persist
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Set failed label (Story 12.7)
            if self._label_manager:
                self._label_manager.set_failed()

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

            # Preserve worktree for debugging (ISS-020)
            # Worktrees are NEVER auto-deleted - only via explicit cleanup command
            self._show_worktree_preserved(context, outcome="failure")
            raise

        except Exception as e:
            # Sync failure status with task manager (Story 12.3)
            # Non-blocking: catch and log any sync errors, never fail the run
            if self._status_sync_service:
                try:
                    self._status_sync_service.sync_run_failed(
                        context, context.current_phase, str(e)
                    )
                except Exception as sync_error:
                    logger.warning(
                        "Status sync failed (non-blocking)",
                        extra={
                            "run_id": context.run_id,
                            "phase": context.current_phase,
                            "error": str(sync_error),
                        },
                    )

            # Catch-all for unexpected errors (RuntimeError, etc.)
            context = context.model_copy(
                update={
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Set failed label (Story 12.7)
            if self._label_manager:
                self._label_manager.set_failed()

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

            # Preserve worktree for debugging (ISS-020)
            # Worktrees are NEVER auto-deleted - only via explicit cleanup command
            self._show_worktree_preserved(context, outcome="failure")
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

        # Set phase label (Story 12.7)
        if self._label_manager:
            self._label_manager.set_phase(phase)

        # Sync status with task manager (Story 12.3)
        # Non-blocking: catch and log any sync errors, never fail the phase
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

        logger.info(
            "Starting phase",
            extra={"phase": phase, "run_id": context.run_id},
        )

        try:
            # Execute phase with retry for recoverable errors
            result = self._execute_phase_with_retry(
                context, phase, artifacts_override=artifacts_override
            )

            # Post-phase snapshot
            self.snapshot_manager.create_post_phase_snapshot(context, phase, result)

            # Notify progress display of phase completion (Story 5.5)
            if self.progress_display:
                self.progress_display.on_phase_complete(phase, result)

            # Post phase completion comment to task manager (Story 12.6)
            # Non-blocking: catch and log any errors, never fail the phase
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

    def _maybe_create_pr_after_document(
        self,
        context: RunContext,
    ) -> "AutoPRResult | None":
        """Create PR after document phase completes (ISS-031).

        This method is called immediately after the document phase completes,
        before the ship phase runs. This ensures the ship phase can find and
        validate the PR for merging.

        This method is non-blocking - PR creation failures are logged but don't
        fail the run. If PR creation fails and ship phase is enabled, ship will
        fail gracefully in its pre.sh hook.

        Args:
            context: Current run context.

        Returns:
            AutoPRResult with outcome, or None if PR creation failed or
            progress_display is not available.
        """
        if not self.progress_display:
            logger.debug(
                "No progress_display available for PR creation",
                extra={"run_id": context.run_id},
            )
            return None

        logger.info(
            "Creating PR after document phase",
            extra={"run_id": context.run_id, "phase": "document"},
        )

        try:
            pr_result = self.progress_display.try_auto_create_pr(
                run_id=context.run_id,
                context=context,
                runs_dir=self.runs_dir,
                auto_create_pr_enabled=True,  # Already checked in caller
            )

            # PR creation failed - warn about potential ship phase failure
            if (
                pr_result
                and not pr_result.success
                and self._phase_runner.is_phase_enabled("ship")
            ):
                logger.warning(
                    "PR creation failed, ship phase may fail",
                    extra={
                        "run_id": context.run_id,
                        "reason": pr_result.reason,
                    },
                )

            return pr_result

        except Exception as e:
            # Non-blocking: log warning and continue
            logger.warning(
                "PR creation after document phase failed (non-blocking)",
                extra={
                    "run_id": context.run_id,
                    "error": str(e),
                },
            )
            return None

    def _maybe_close_task(
        self,
        task_uuid: str | None,
        pr_url: str | None,
    ) -> None:
        """Attempt to close task if auto_close is enabled (Story 12.8).

        This method is non-blocking - failures are logged but don't
        affect the run outcome.

        Args:
            task_uuid: Internal task UUID (from TaskInfo.id). If None, does nothing.
            pr_url: PR URL to check merge status. If None, closes without checking PR.
        """
        if not task_uuid:
            logger.debug("No task_uuid provided, skipping issue closing")
            return

        if not self.task_manager_config.auto_close:
            logger.debug("Auto-close disabled, skipping issue closing")
            return

        try:
            from adw.task_managers import TaskManagerFactory
            from adw.task_managers.closer import IssueCloser

            task_manager = TaskManagerFactory().create(
                task_type=self.task_manager_config.type,
                config=self.task_manager_config,
            )
            with IssueCloser(task_manager, self.task_manager_config) as closer:
                closed = closer.maybe_close(task_uuid, pr_url)
                if closed:
                    logger.info(
                        "Task closed after run completion",
                        extra={"task_uuid": task_uuid},
                    )
                else:
                    logger.debug(
                        "Task not closed (PR not merged or condition not met)",
                        extra={"task_uuid": task_uuid, "pr_url": pr_url},
                    )
        except Exception as e:
            # Non-blocking - log warning and continue
            logger.warning(
                "Failed to close task: %s. Close manually with: adw task close %s",
                e,
                task_uuid,
            )

    def _show_worktree_preserved(
        self, context: RunContext, outcome: str = "success"
    ) -> None:
        """Show worktree preservation message after run completion (ISS-020).

        Displays worktree location and cleanup instructions to the user.
        This method should be called after any run completion (success or failure)
        when a worktree was used.

        Args:
            context: Run context containing worktree information.
            outcome: Either "success" or "failure" for logging purposes.
        """
        if not (context.use_worktree and context.worktree_path):
            return

        log_message = (
            "Worktree preserved for user inspection"
            if outcome == "success"
            else "Worktree preserved for debugging"
        )
        logger.info(
            log_message,
            extra={
                "run_id": context.run_id,
                "worktree_path": str(context.worktree_path),
                "outcome": outcome,
                "reason": "user_control_policy",
            },
        )
        if self.progress_display:
            self.progress_display.console.print()
            self.progress_display.console.print(
                f"[blue]Worktree:[/blue] {context.worktree_path}"
            )
            self.progress_display.console.print(
                f"Run [yellow]adw cleanup {context.run_id}[/yellow] to remove"
            )
            self.progress_display.console.print()

    def _create_worktree_for_run(
        self, run_id: str, feature_description: str
    ) -> tuple[Path, str] | None:
        """Create a worktree for the given run.

        Creates a git worktree in the configured base directory for isolated
        execution of this run. Checks concurrent run limits before creation
        and registers the run after successful creation.

        When git integration is enabled, the worktree is created with a
        human-readable feature branch name (e.g., 'feature/add-auth') instead
        of the default 'adw/<run_id>' format. This allows the branch to be
        meaningful in git history and PRs.

        ISS-025: Branch creation failures are now fatal. If the worktree or
        branch cannot be created, this method raises WorktreeError instead
        of returning None, ensuring the run fails immediately.

        Args:
            run_id: ULID identifier for this run.
            feature_description: Human-readable feature description used to
                generate the branch name when git integration is enabled.

        Returns:
            Tuple of (worktree_path, branch_name) if successful, or None if
            worktree is not configured. Branch name format depends on git config.

        Raises:
            MaxConcurrentRunsError: If the maximum concurrent runs limit is reached.
            WorktreeError: If worktree or branch creation fails (ISS-025).
        """
        if self._worktree_manager is None:
            return None

        # Check concurrent run limit before creating worktree (Story 10.4)
        if self._concurrent_run_manager is not None:
            # This will raise MaxConcurrentRunsError if at limit
            self._concurrent_run_manager.check_can_start_or_raise()

        # Calculate feature branch name if git integration is enabled (ISS-032)
        # This creates a human-readable branch like 'feature/add-auth' instead
        # of the opaque 'adw/<run_id>' format
        feature_branch_name: str | None = None
        if self.git_config.enabled and feature_description:
            sanitized = sanitize_branch_name(feature_description)
            if sanitized:
                feature_branch_name = self.git_config.branch_prefix + sanitized

        try:
            worktree_path, branch_name = self._worktree_manager.create_worktree(
                run_id, branch_name=feature_branch_name
            )
            # Note: Worktree creation log is handled in WorktreeManager.create_worktree()
            # (ISS-035: Removed duplicate log message)

            # Register the run after successful worktree creation (Story 10.4)
            if self._concurrent_run_manager is not None:
                self._concurrent_run_manager.register_run(
                    run_id=run_id,
                    worktree_path=worktree_path,
                )

            return worktree_path, branch_name

        except WorktreeError:
            # ISS-025: Branch creation failures are fatal - propagate to caller
            # This ensures the run fails if we can't create the story branch
            raise

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
