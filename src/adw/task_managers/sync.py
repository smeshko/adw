"""StatusSyncService for synchronizing run status with task managers.

This module provides the StatusSyncService class that handles synchronization
of ADW run status with external task management systems (Linear, Jira, etc.)
at phase transitions.

Story 12.3: Status Synchronization at Phase Transitions
"""

import logging
from typing import Any

from adw.models.config import TaskManagerConfig
from adw.models.context import RunContext
from adw.task_managers.base import TaskManager

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
    ) -> None:
        """Initialize StatusSyncService.

        Args:
            task_manager: The task manager instance to use for status updates.
            config: Task manager configuration with state_mapping settings.
        """
        self._task_manager = task_manager
        self._config = config

    def sync_phase_start(self, context: RunContext, phase: str) -> None:
        """Sync status when a phase starts.

        Updates the external task management system with the status mapped
        from the starting phase. Does nothing if context has no task_id.

        Args:
            context: The current run context with task information.
            phase: The phase that is starting (e.g., "plan", "build").
        """
        if not context.task_id or not context.task_info:
            return

        self._safe_update_status(
            context.task_info.id,
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
        from the target phase. Does nothing if context has no task_id.

        Args:
            context: The current run context with task information.
            from_phase: The phase that just completed.
            to_phase: The phase that is starting.
        """
        if not context.task_id or not context.task_info:
            return

        self._safe_update_status(
            context.task_info.id,
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
        mapping. Does nothing if context has no task_id.

        Args:
            context: The current run context with task information.
            phase: The phase where the failure occurred.
            error: The error message describing the failure.
        """
        if not context.task_id or not context.task_info:
            return

        self._safe_update_status(
            context.task_info.id,
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

            logger.info(
                "Status synced to task manager",
                extra={
                    "task_id": task_id,
                    "status": mapped_status,
                    "phase": phase_or_state,
                },
            )
        except Exception as e:
            logger.warning(
                "Failed to sync status to task manager: %s (task_id=%s, phase=%s)",
                str(e),
                task_id,
                phase_or_state,
            )
