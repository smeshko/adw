"""NullTaskManager implementation.

This module provides a no-op task manager used when no external
task management system is configured.
"""

from typing import Any

from adw.exceptions import TaskError
from adw.models.task import TaskInfo


class NullTaskManager:
    """No-op task manager for when no task management system is configured.

    This implementation is used when `task_manager: none` is set or when
    no task manager configuration is provided. All operations are no-ops
    except fetch_task which raises an error since there's no system to fetch from.

    Example:
        >>> manager = NullTaskManager()
        >>> manager.name
        'none'
        >>> manager.resolve_task_id("RULE-123")  # Returns None
        >>> manager.update_status("RULE-123", "Done")  # No-op
        >>> manager.fetch_task("RULE-123")  # Raises TaskError
    """

    @property
    def name(self) -> str:
        """Return the task manager type name.

        Returns:
            'none' to indicate no task manager is configured.
        """
        return "none"

    def fetch_task(self, task_id: str) -> TaskInfo:
        """Raise an error since no task manager is configured.

        Args:
            task_id: The task identifier.

        Raises:
            TaskError: Always raised with NO_TASK_MANAGER code.
        """
        raise TaskError(
            code="NO_TASK_MANAGER",
            message=f"Cannot fetch task '{task_id}': No task manager configured",
            suggestion="Configure a task manager in project.yaml",
            task_id=task_id,
            recoverable=False,
        )

    def update_status(
        self,
        task_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """No-op - silently ignores status updates.

        Args:
            task_id: The task identifier.
            status: The new status.
            metadata: Optional additional metadata (ignored).
        """
        # No-op - nothing to update
        pass

    def resolve_task_id(self, input_str: str) -> str | None:
        """Return None since no task manager is configured.

        Args:
            input_str: The input string that may contain a task ID.

        Returns:
            Always None - no task ID detection without a task manager.
        """
        return None
