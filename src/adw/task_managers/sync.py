"""StatusSyncService for synchronizing run status with task managers.

This module provides the StatusSyncService class that handles synchronization
of ADW run status with external task management systems (Linear, Jira, etc.)
at phase transitions.

Story 12.3: Status Synchronization at Phase Transitions
Story 12.6: Post Status Update Comments
"""

import logging
from datetime import UTC, datetime
from typing import Any

from adw.models.config import TaskManagerConfig
from adw.models.context import RunContext
from adw.models.phase import PhaseResult
from adw.models.task import TaskInfo
from adw.task_managers.base import TaskManager
from adw.task_managers.comments import CommentFormatter

logger = logging.getLogger(__name__)

# Default phase-to-status mapping for Linear
DEFAULT_STATE_MAPPING: dict[str, str] = {
    "plan": "In Progress",
    "build": "In Progress",
    "validate": "In Review",
    "document": "In Review",
    "failed": "In Progress",
}


class StatusSyncService:
    """Service for synchronizing run status with task managers.

    This service handles automatic status updates to external task management
    systems (Linear, Jira, etc.) as ADW runs progress through phases. All
    sync operations are non-blocking - errors are logged but don't fail the run.

    Example:
        >>> from adw.task_managers.linear import LinearTaskManager
        >>> manager = LinearTaskManager(config)
        >>> sync_service = StatusSyncService(manager, config)
        >>> sync_service.sync_phase_start(context, "plan")
        >>> sync_service.sync_phase_transition(context, "plan", "build")
    """

    def __init__(
        self,
        task_manager: TaskManager,
        config: TaskManagerConfig,
        task_info: TaskInfo | None = None,
    ) -> None:
        """Initialize StatusSyncService.

        Args:
            task_manager: The task manager instance to use for status updates.
            config: Task manager configuration with state_mapping settings.
            task_info: Optional TaskInfo with internal UUID for API calls.
                task_info.id is used for Linear/Jira API calls.
                If not provided, falls back to context.task_info (for backwards compat).
        """
        self._task_manager = task_manager
        self._config = config
        self._task_info = task_info
        self._comment_formatter = CommentFormatter()

    def sync_phase_start(self, context: RunContext, phase: str) -> None:
        """Sync status when a phase starts.

        Updates the external task management system with the status mapped
        from the starting phase. Does nothing if no task_info is available.

        Args:
            context: The current run context with task information.
            phase: The phase that is starting (e.g., "plan", "build").
        """
        # Use stored task_info, fallback to context for backwards compatibility
        task_info = self._task_info or context.task_info
        if not task_info:
            return

        self._safe_update_status(
            task_info.id,
            phase,
            {
                "run_id": context.run_id,
                "phase": phase,
            },
        )

    def sync_phase_transition(
        self,
        context: RunContext,
        from_phase: str,
        to_phase: str,
    ) -> None:
        """Sync status on phase transition.

        Updates the external task management system with the status mapped
        from the target phase. Does nothing if no task_info is available.

        Args:
            context: The current run context with task information.
            from_phase: The phase that just completed.
            to_phase: The phase that is starting.
        """
        # Use stored task_info, fallback to context for backwards compatibility
        task_info = self._task_info or context.task_info
        if not task_info:
            return

        self._safe_update_status(
            task_info.id,
            to_phase,
            {
                "run_id": context.run_id,
                "from_phase": from_phase,
                "to_phase": to_phase,
            },
        )

    def sync_run_failed(
        self,
        context: RunContext,
        phase: str,
        error: str,
    ) -> None:
        """Sync status when run fails.

        Updates the external task management system with the "failed" status
        mapping. Does nothing if no task_info is available.

        Args:
            context: The current run context with task information.
            phase: The phase where the failure occurred.
            error: The error message describing the failure.
        """
        # Use stored task_info, fallback to context for backwards compatibility
        task_info = self._task_info or context.task_info
        if not task_info:
            return

        self._safe_update_status(
            task_info.id,
            "failed",
            {
                "run_id": context.run_id,
                "failed_phase": phase,
                "error": error,
            },
        )

    def sync_run_complete(
        self,
        context: RunContext,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Handle run completion.

        Note: This method intentionally does NOT update status or close issues.
        Issue closing is handled separately by Story 12.8 if auto_close=true.
        The run stays at the last phase status (typically "document" -> "In Review").

        Args:
            context: The current run context.
            success: Whether the run completed successfully.
            error: Optional error message if success=False.
        """
        # Intentionally no-op - closing is handled by Story 12.8
        pass

    def _safe_update_status(
        self,
        task_id: str,
        phase_or_state: str,
        metadata: dict[str, Any],
    ) -> None:
        """Update status, catching and logging any errors.

        This method is non-blocking - it catches all exceptions and logs
        warnings instead of raising. The ADW run continues regardless of
        sync status.

        Args:
            task_id: The internal task ID (e.g., Linear UUID).
            phase_or_state: The phase or state key to map to external status.
            metadata: Additional metadata for the update.
        """
        try:
            # Use config mapping, fall back to defaults, then to phase name
            mapping = self._config.state_mapping
            if not mapping:
                mapping = DEFAULT_STATE_MAPPING
            mapped_status = mapping.get(phase_or_state, phase_or_state)

            self._task_manager.update_status(task_id, mapped_status, metadata)
            # Note: Success logging handled by task_manager (e.g., LinearTaskManager)
            # to avoid duplicate logs
        except Exception as e:
            logger.warning(
                "Failed to sync status to task manager: %s (task_id=%s, phase=%s)",
                str(e),
                task_id,
                phase_or_state,
            )

    def post_run_started_comment(self, context: RunContext) -> None:
        """Post a comment when an ADW run starts.

        Posts a formatted comment to the task management system when a run
        begins. Does nothing if:
        - no task_info is available
        - sync_comments is False in config
        - comment_on_failure_only is True

        Args:
            context: The current run context with task and run information.
        """
        task_info = self._task_info or context.task_info
        if not task_info:
            return

        if not self._config.sync_comments:
            return

        if self._config.comment_on_failure_only:
            return

        # Import locally to avoid circular dependency between core and task_managers
        from adw.core.constants import PHASE_SEQUENCE

        assignee = task_info.assignee if hasattr(task_info, "assignee") else None

        comment = self._comment_formatter.format_run_started(
            run_id=context.run_id,
            branch_name=context.branch_name,
            phase_sequence=list(PHASE_SEQUENCE),
            assignee=assignee,
        )

        self._safe_post_comment(task_info.id, comment)

    def post_phase_comment(
        self,
        context: RunContext,
        phase: str,
        result: PhaseResult,
    ) -> None:
        """Post a comment about phase completion.

        Posts a formatted comment to the task management system when a phase
        completes. Does nothing if:
        - no task_info is available
        - sync_comments is False in config
        - comment_on_failure_only is True (success comments skipped)

        Args:
            context: The current run context with task information.
            phase: The phase that completed.
            result: The phase result with duration and artifacts.
        """
        # Use stored task_info, fallback to context for backwards compatibility
        task_info = self._task_info or context.task_info
        if not task_info:
            return

        # Check sync_comments config (Story 12.6)
        if not self._config.sync_comments:
            return

        # Check comment_on_failure_only config
        if self._config.comment_on_failure_only:
            return

        # Determine artifacts count (count files in artifacts if available)
        artifacts_count = 0
        artifact_names: list[str] | None = None
        if result.artifacts:
            artifacts_count = len(result.artifacts)
            artifact_names = result.artifacts

        # Calculate duration
        duration = result.duration_ms / 1000 if result.duration_ms else 0.0

        # Extract token and tool call metrics
        tokens_used = result.tokens_used
        tool_calls_count = len(result.tool_calls)

        comment = self._comment_formatter.format_phase_complete(
            phase=phase,
            duration=duration,
            artifacts=artifacts_count,
            artifact_names=artifact_names,
            tokens_used=tokens_used,
            tool_calls_count=tool_calls_count,
        )

        self._safe_post_comment(task_info.id, comment)

    def post_failure_comment(
        self,
        context: RunContext,
        phase: str,
        error: str,
    ) -> None:
        """Post a comment about phase failure.

        Posts a formatted comment to the task management system when a phase
        fails. Does nothing if:
        - no task_info is available
        - sync_comments is False in config

        Note: Failure comments are ALWAYS posted (not affected by
        comment_on_failure_only - that only skips success comments).

        Args:
            context: The current run context with task information.
            phase: The phase where the failure occurred.
            error: The error message.
        """
        # Use stored task_info, fallback to context for backwards compatibility
        task_info = self._task_info or context.task_info
        if not task_info:
            return

        # Check sync_comments config (Story 12.6)
        if not self._config.sync_comments:
            return

        # Import locally to avoid circular dependency
        from adw.core.constants import PHASE_SEQUENCE

        # Calculate duration from started_at to now
        duration: float | None = None
        if context.started_at:
            delta = datetime.now(UTC) - context.started_at.replace(tzinfo=UTC)
            duration = delta.total_seconds()

        comment = self._comment_formatter.format_phase_failed(
            phase=phase,
            error=error,
            run_id=context.run_id,
            duration=duration,
            phase_sequence=list(PHASE_SEQUENCE),
            completed_phases=list(context.phase_history),
            branch_name=context.branch_name,
            artifacts_by_phase=dict(context.artifacts) if context.artifacts else None,
        )

        self._safe_post_comment(task_info.id, comment)

    def post_completion_comment(
        self,
        context: RunContext,
        pr_url: str | None = None,
        summary: str = "All phases completed successfully",
    ) -> None:
        """Post a comment about run completion.

        Posts a formatted comment to the task management system when the run
        completes. Does nothing if:
        - no task_info is available
        - sync_comments is False in config
        - comment_on_failure_only is True (success comments skipped)

        Args:
            context: The current run context with task information.
            pr_url: The pull request URL if a PR was created.
            summary: A summary of the run outcome.
        """
        # Use stored task_info, fallback to context for backwards compatibility
        task_info = self._task_info or context.task_info
        if not task_info:
            return

        # Check sync_comments config (Story 12.6)
        if not self._config.sync_comments:
            return

        # Check comment_on_failure_only config
        if self._config.comment_on_failure_only:
            return

        # Import locally to avoid circular dependency
        from adw.core.constants import PHASE_SEQUENCE

        # Calculate duration from started_at to completed_at (or now)
        duration: float | None = None
        if context.started_at:
            end = context.completed_at or datetime.now(UTC)
            delta = end.replace(tzinfo=UTC) - context.started_at.replace(tzinfo=UTC)
            duration = delta.total_seconds()

        comment = self._comment_formatter.format_run_complete(
            run_id=context.run_id,
            pr_url=pr_url,
            summary=summary,
            duration=duration,
            phase_sequence=list(PHASE_SEQUENCE),
            completed_phases=list(context.phase_history),
            total_tokens=context.total_tokens,
            commit_count=len(context.commit_shas),
            artifacts_by_phase=dict(context.artifacts) if context.artifacts else None,
        )

        self._safe_post_comment(task_info.id, comment)

    def _safe_post_comment(self, task_id: str, body: str) -> None:
        """Post comment, catching and logging any errors.

        This method is non-blocking - it catches all exceptions and logs
        warnings instead of raising. The ADW run continues regardless of
        comment posting status.

        Args:
            task_id: The internal task ID (e.g., Linear UUID).
            body: The comment body to post.
        """
        try:
            self._task_manager.post_comment(task_id, body)
            # Note: Success logging handled by task_manager (e.g., LinearTaskManager)
            # to avoid duplicate logs
        except Exception as e:
            logger.warning(
                "Failed to post comment to task manager: %s (task_id=%s)",
                str(e),
                task_id,
            )
