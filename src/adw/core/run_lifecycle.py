"""Run lifecycle management for ADW pipeline execution.

This module provides the RunLifecycle class that manages lifecycle concerns
for ADW pipeline runs. It consolidates duplicated lifecycle code from
Orchestrator's run(), run_single_phase(), and resume() methods.

Key responsibilities:
- Run context creation with worktree setup
- Run initialization (directory, persist, index, labels)
- Success completion handling
- Error handling (ADWError, Exception, ShutdownRequested)
- Pipeline summary display
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ulid import ULID

from adw.core.constants import PHASE_SEQUENCE
from adw.core.context_manager import ContextManager
from adw.core.index_manager import IndexManager
from adw.core.interruption import InterruptionHandler, ShutdownRequested
from adw.core.run_directory import RunDirectoryManager
from adw.exceptions import ADWError, WorktreeError
from adw.hooks.git_branch import sanitize_branch_name
from adw.models import GitConfig, RunContext, TaskManagerConfig, WorktreeConfig
from adw.models.task import TaskInfo
from adw.worktree import ConcurrentRunManager
from adw.worktree.manager import WorktreeManager

if TYPE_CHECKING:
    from adw.cli.pr import AutoPRResult
    from adw.cli.progress import ProgressDisplay
    from adw.task_managers.labels import LabelManager
    from adw.task_managers.sync import StatusSyncService

__all__ = ["RunLifecycle"]

logger = logging.getLogger(__name__)


class _PRResultFromContext:
    """Lightweight PR result for constructing from context fields.

    Avoids importing AutoPRResult from CLI layer into core.
    Duck-typed to match the interface used by ProgressDisplay.show_pipeline_summary().
    """

    __slots__ = ("success", "pr_url", "reason")

    def __init__(self, *, success: bool, pr_url: str, reason: str) -> None:
        self.success = success
        self.pr_url = pr_url
        self.reason = reason


class RunLifecycle:
    """Manages lifecycle concerns for ADW pipeline runs.

    Consolidates lifecycle management code previously duplicated across:
    - Orchestrator.run(): worktree setup, context creation, completion handling
    - Orchestrator.run_single_phase(): same lifecycle operations
    - Orchestrator.resume(): resume preparation, completion handling

    Uses constructor injection pattern per project conventions.

    Attributes:
        runs_dir: Path to the .adw/runs directory.
        project_path: Path to the project root.
        context_manager: Manager for persisting run context.
        run_directory_manager: Manager for run directory structure.
        index_manager: Manager for global workflow execution index.
        interruption_handler: Handler for graceful shutdown on Ctrl+C/SIGTERM.

    Example:
        >>> lifecycle = RunLifecycle(
        ...     runs_dir=Path(".adw/runs"),
        ...     project_path=Path("."),
        ...     context_manager=context_manager,
        ...     run_directory_manager=run_directory_manager,
        ...     index_manager=index_manager,
        ...     interruption_handler=interruption_handler,
        ... )
        >>> context = lifecycle.create_run_context(
        ...     feature_description="Add user auth",
        ...     use_worktree=True,
        ... )
    """

    def __init__(
        self,
        runs_dir: Path,
        project_path: Path,
        context_manager: ContextManager,
        run_directory_manager: RunDirectoryManager,
        index_manager: IndexManager,
        interruption_handler: InterruptionHandler,
        *,
        progress_display: ProgressDisplay | None = None,
        worktree_config: WorktreeConfig | None = None,
        git_config: GitConfig | None = None,
        task_manager_config: TaskManagerConfig | None = None,
        label_manager: LabelManager | None = None,
        status_sync_service: StatusSyncService | None = None,
        worktree_manager: WorktreeManager | None = None,
        concurrent_run_manager: ConcurrentRunManager | None = None,
        task_info: TaskInfo | None = None,
    ) -> None:
        """Initialize the RunLifecycle.

        Args:
            runs_dir: Path to the .adw/runs directory.
            project_path: Path to the project root.
            context_manager: Manager for persisting run context.
            run_directory_manager: Manager for run directory structure.
            index_manager: Manager for global workflow execution index.
            interruption_handler: Handler for graceful shutdown.
            progress_display: Display for phase progress (optional, Story 5.5).
            worktree_config: Worktree isolation config (optional, Story 10.1).
            git_config: Git configuration for auto-PR creation (optional, ISS-011).
            task_manager_config: Task manager configuration for auto-close (Story 12.8).
            label_manager: Manager for task labels (optional, Story 12.7).
            status_sync_service: Service for syncing status with task managers
                (optional, Story 12.3).
            worktree_manager: Manager for git worktrees (optional).
            concurrent_run_manager: Manager for tracking concurrent runs (optional).
            task_info: Task information from external task manager (optional, ISS-039).
                Used to populate RunContext.task_id and RunContext.task_info.
        """
        self.runs_dir = runs_dir
        self.project_path = project_path
        self.context_manager = context_manager
        self.run_directory_manager = run_directory_manager
        self.index_manager = index_manager
        self.interruption_handler = interruption_handler
        self.progress_display = progress_display
        self.worktree_config = worktree_config or WorktreeConfig()
        self.git_config = git_config or GitConfig()
        self.task_manager_config = task_manager_config or TaskManagerConfig()
        self._label_manager = label_manager
        self._status_sync_service = status_sync_service
        self._worktree_manager = worktree_manager
        self._concurrent_run_manager = concurrent_run_manager
        self._task_info = task_info

    def create_run_context(
        self,
        feature_description: str,
        *,
        run_id: str | None = None,
        use_worktree: bool = True,
        starting_phase: str | None = None,
    ) -> RunContext:
        """Create and initialize a new run context.

        This method handles:
        1. Generate run ID if not provided
        2. Create worktree for isolation (if enabled)
        3. Create initial context
        4. Create run directory structure
        5. Persist initial state
        6. Register run in global index
        7. Set running label

        Args:
            feature_description: Description of the feature to implement.
            run_id: Optional run ID. If not provided, a new ULID is generated.
            use_worktree: Whether to use worktree isolation for this run.
            starting_phase: Phase to start from (default: first in sequence).

        Returns:
            Initialized RunContext ready for execution.

        Raises:
            WorktreeError: If worktree creation fails (ISS-025).
            MaxConcurrentRunsError: If the maximum concurrent runs limit is reached.
        """
        run_id = run_id or str(ULID())
        starting_phase = starting_phase or PHASE_SEQUENCE[0]

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
            if worktree_result is None:
                should_use_worktree = False
                logger.warning(
                    "Worktree creation failed, running in current directory",
                    extra={"run_id": run_id},
                )
            else:
                worktree_path, branch_name = worktree_result

        # Create initial context (populate task_id, task_info, and task_manager)
        context = RunContext(
            run_id=run_id,
            feature_description=feature_description,
            current_phase=starting_phase,
            started_at=datetime.now(UTC),
            status="running",
            worktree_path=worktree_path,
            use_worktree=should_use_worktree,
            branch_name=branch_name,
            task_id=self._task_info.identifier if self._task_info else None,
            task_info=self._task_info,
            task_manager=self.task_manager_config.type
            if self.task_manager_config.type != "none"
            else None,
        )

        # Initialize run
        self._initialize_run(context)

        logger.info(
            "Starting run",
            extra={"run_id": run_id, "feature": feature_description},
        )

        return context

    def prepare_resume_context(self, context: RunContext) -> RunContext:
        """Prepare context for resumed execution.

        Sets the running label for the resumed run and backfills task_info
        if the lifecycle has it but the context doesn't (ISS-039).

        Args:
            context: The run context being resumed.

        Returns:
            The context, potentially updated with task_info if backfilled.
        """
        # Backfill task_info from lifecycle if context is missing it (ISS-039)
        # This handles runs created before ISS-039 that are resumed after
        if self._task_info and not context.task_info:
            context = context.model_copy(
                update={
                    "task_id": self._task_info.identifier,
                    "task_info": self._task_info,
                }
            )
            self.context_manager.save(context)
            logger.debug(
                "Backfilled task_info on resume",
                extra={
                    "run_id": context.run_id,
                    "task_id": self._task_info.identifier,
                },
            )

        if self._label_manager:
            self._label_manager.set_running()
        return context

    def finalize_success(
        self,
        context: RunContext,
        *,
        pr_result: AutoPRResult | None = None,
        task_uuid: str | None = None,
    ) -> RunContext:
        """Finalize a successful run.

        This method handles:
        1. Update status to "completed"
        2. Persist final state
        3. Set completed label
        4. Update global index
        5. Post completion comment
        6. Attempt to close task (if auto_close enabled)
        7. Show pipeline summary
        8. Show worktree preservation message

        Args:
            context: The run context to finalize.
            pr_result: Result of PR creation (optional).
            task_uuid: Internal task UUID for issue closing (optional).

        Returns:
            Updated context with completed status.
        """
        # Mark as completed
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

        # Post run completion comment to task manager (Story 12.6)
        self._post_completion_comment(context, pr_result)

        # Attempt to close task if auto_close enabled (Story 12.8)
        self._maybe_close_task(
            task_uuid=task_uuid,
            pr_url=pr_result.pr_url if pr_result else None,
        )

        # Show pipeline summary (Story 5.5)
        self._show_pipeline_summary(context, status="completed", pr_result=pr_result)

        # Preserve worktree for user inspection (ISS-020)
        self._show_worktree_preserved(context, outcome="success")

        logger.info("Run completed", extra={"run_id": context.run_id})

        return context

    def handle_adw_error(
        self,
        context: RunContext,
        error: ADWError,
    ) -> RunContext:
        """Handle an ADWError during run execution.

        This method handles:
        1. Sync failure status with task manager
        2. Post failure comment
        3. Update status to "failed"
        4. Set failed label
        5. Update global index
        6. Show pipeline summary
        7. Show worktree preservation message

        Args:
            context: The run context.
            error: The ADWError that occurred.

        Returns:
            Updated context with failed status.
        """
        failed_phase = getattr(error, "phase", None) or context.current_phase

        # Sync and comment
        self._sync_failure(context, failed_phase, error)
        self._post_failure_comment(context, failed_phase, error)

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

        # Show pipeline summary on failure (Story 5.5)
        self._show_pipeline_summary(context, status="failed", pr_result=None)

        # Preserve worktree for debugging (ISS-020)
        self._show_worktree_preserved(context, outcome="failure")

        logger.error(
            "Run failed",
            extra={
                "run_id": context.run_id,
                "phase": failed_phase,
                "error_code": error.code,
            },
        )

        return context

    def handle_exception(
        self,
        context: RunContext,
        error: Exception,
    ) -> RunContext:
        """Handle an unexpected exception during run execution.

        Same handling as handle_adw_error but for generic exceptions.

        Args:
            context: The run context.
            error: The exception that occurred.

        Returns:
            Updated context with failed status.
        """
        # Sync and comment
        self._sync_failure(context, context.current_phase, error)
        self._post_failure_comment(context, context.current_phase, error)

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

        # Show pipeline summary on failure (Story 5.5)
        self._show_pipeline_summary(context, status="failed", pr_result=None)

        # Preserve worktree for debugging (ISS-020)
        self._show_worktree_preserved(context, outcome="failure")

        logger.error(
            "Run failed with unexpected error",
            extra={
                "run_id": context.run_id,
                "phase": context.current_phase,
                "error": str(error),
            },
        )

        return context

    def handle_shutdown(
        self,
        context: RunContext,
        error: ShutdownRequested,
    ) -> RunContext:
        """Handle a shutdown request during run execution.

        This method handles:
        1. Set failed label (since run was interrupted)
        2. Update global index with interrupted status

        Note: State is already saved by the interruption handler.

        Args:
            context: The run context.
            error: The ShutdownRequested that occurred.

        Returns:
            The same context (state already saved by handler).
        """
        # Clear running label on interruption (Story 12.7)
        if self._label_manager:
            self._label_manager.set_failed()

        # Update global index on interruption (Story 7.0)
        self.index_manager.update_run(
            context.run_id,
            status="interrupted",
            phase_reached=error.phase,
            phases_completed=list(context.phase_history),
        )

        logger.info(
            "Run interrupted",
            extra={"run_id": context.run_id, "phase": error.phase},
        )

        return context

    # Private methods

    def _initialize_run(self, context: RunContext) -> None:
        """Initialize run directory, persist state, and register in index.

        Args:
            context: The run context to initialize.
        """
        # Create run directory structure
        self.run_directory_manager.create(context)

        # Persist initial state before any phase execution (NFR6)
        self.context_manager.save(context)

        # Register run in global index (Story 7.0)
        self.index_manager.register_run(context, self.project_path)

        # Set running label (Story 12.7)
        if self._label_manager:
            self._label_manager.set_running()

    def _create_worktree_for_run(
        self, run_id: str, feature_description: str
    ) -> tuple[Path, str] | None:
        """Create a worktree for the given run.

        Args:
            run_id: ULID identifier for this run.
            feature_description: Human-readable feature description.

        Returns:
            Tuple of (worktree_path, branch_name) if successful, or None.

        Raises:
            MaxConcurrentRunsError: If the maximum concurrent runs limit is reached.
            WorktreeError: If worktree or branch creation fails (ISS-025).
        """
        if self._worktree_manager is None:
            return None

        # Check concurrent run limit before creating worktree (Story 10.4)
        if self._concurrent_run_manager is not None:
            self._concurrent_run_manager.check_can_start_or_raise()

        # Calculate feature branch name if git integration is enabled (ISS-032)
        feature_branch_name: str | None = None
        if self.git_config.enabled and feature_description:
            sanitized = sanitize_branch_name(feature_description)
            if sanitized:
                feature_branch_name = self.git_config.branch_prefix + sanitized

        try:
            worktree_path, branch_name = self._worktree_manager.create_worktree(
                run_id, branch_name=feature_branch_name
            )

            # Register the run after successful worktree creation (Story 10.4)
            if self._concurrent_run_manager is not None:
                self._concurrent_run_manager.register_run(
                    run_id=run_id,
                    worktree_path=worktree_path,
                )

            return worktree_path, branch_name

        except WorktreeError:
            # ISS-025: Branch creation failures are fatal
            raise

    def _show_pipeline_summary(
        self,
        context: RunContext,
        status: str,
        pr_result: AutoPRResult | None,
    ) -> None:
        """Show pipeline summary via progress display.

        Args:
            context: The run context.
            status: Final status ("completed" or "failed").
            pr_result: Result of PR creation (optional).
        """
        if not self.progress_display:
            return

        total_tokens = sum(context.phase_tokens.values())
        duration_ms = 0
        if context.completed_at and context.started_at:
            duration_ms = int(
                (context.completed_at - context.started_at).total_seconds() * 1000
            )

        # Determine PR result for display (only for completed runs)
        # Type is AutoPRResult | _PRResultFromContext | None (duck-typed)
        effective_pr_result: Any = None
        if status == "completed":
            if pr_result is not None:
                effective_pr_result = pr_result
            elif context.pr_url:
                # Construct from context fields (Phase Extensions store PR info)
                # Use simple object with required attrs to avoid CLI import
                effective_pr_result = _PRResultFromContext(
                    success=True, pr_url=context.pr_url, reason=""
                )
            elif context.pr_creation_attempted and context.pr_creation_failed:
                effective_pr_result = _PRResultFromContext(
                    success=False,
                    pr_url="",
                    reason=context.pr_failure_reason or "Unknown error",
                )

        self.progress_display.show_pipeline_summary(
            completed_phases=context.phase_history,
            status=status,
            total_duration_ms=duration_ms,
            total_tokens=total_tokens,
            run_id=context.run_id,
            pr_result=effective_pr_result,
        )

    def _show_worktree_preserved(
        self, context: RunContext, outcome: str = "success"
    ) -> None:
        """Show worktree preservation message after run completion (ISS-020).

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

    def _sync_failure(
        self,
        context: RunContext,
        phase: str,
        error: Exception,
    ) -> None:
        """Sync failure status with task manager (non-blocking).

        Args:
            context: The run context.
            phase: The phase that failed.
            error: The error that occurred.
        """
        if not self._status_sync_service:
            return

        try:
            self._status_sync_service.sync_run_failed(context, phase, str(error))
        except Exception as sync_error:
            logger.warning(
                "Status sync failed (non-blocking)",
                extra={
                    "run_id": context.run_id,
                    "phase": phase,
                    "error": str(sync_error),
                },
            )

    def _post_failure_comment(
        self,
        context: RunContext,
        phase: str,
        error: Exception,
    ) -> None:
        """Post failure comment to task manager (non-blocking).

        Args:
            context: The run context.
            phase: The phase that failed.
            error: The error that occurred.
        """
        if not self._status_sync_service:
            return

        try:
            self._status_sync_service.post_failure_comment(context, phase, str(error))
        except Exception as comment_error:
            logger.warning(
                "Failed to post failure comment (non-blocking)",
                extra={
                    "run_id": context.run_id,
                    "phase": phase,
                    "error": str(comment_error),
                },
            )

    def _post_completion_comment(
        self,
        context: RunContext,
        pr_result: AutoPRResult | None,
    ) -> None:
        """Post completion comment to task manager (non-blocking).

        Args:
            context: The run context.
            pr_result: Result of PR creation (optional).
        """
        if not self._status_sync_service:
            return

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
