"""TaskManager Protocol definition.

This module defines the Protocol for task management backends, providing
a consistent interface for different task management systems (Linear,
Jira, GitHub Issues, etc.).
"""

from typing import Any, Protocol, runtime_checkable

from adw.models.task import TaskInfo


@runtime_checkable
class TaskManager(Protocol):
    """Protocol for task management backends.

    This Protocol defines the interface that all task managers must implement.
    Using Protocol-based abstraction enables:
    - Dependency injection for testing
    - Multiple task manager backend support
    - Structural subtyping (no explicit inheritance required)

    Example:
        >>> class MyTaskManager:
        ...     @property
        ...     def name(self) -> str:
        ...         return "my-task-manager"
        ...
        ...     def fetch_task(self, task_id: str) -> TaskInfo:
        ...         ...
        ...
        ...     def update_status(
        ...         self,
        ...         task_id: str,
        ...         status: str,
        ...         metadata: dict[str, Any] | None = None,
        ...     ) -> None:
        ...         ...
        ...
        ...     def resolve_task_id(self, input_str: str) -> str | None:
        ...         ...
        >>>
        >>> manager: TaskManager = MyTaskManager()  # Type checks!
    """

    @property
    def name(self) -> str:
        """Return the task manager type name.

        Returns:
            The name of the task manager (e.g., "linear", "jira", "none").
        """
        ...

    def fetch_task(self, task_id: str) -> TaskInfo:
        """Fetch task information from the external system.

        Args:
            task_id: The task identifier (e.g., "RULE-123", "PROJECT-456").

        Returns:
            TaskInfo with task details from the external system.

        Raises:
            TaskError: If the task cannot be fetched.
        """
        ...

    def update_status(
        self,
        task_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update task status in the external system.

        Args:
            task_id: The task identifier.
            status: The new status (mapped via config state_mapping).
            metadata: Optional additional metadata to include in the update.

        Raises:
            TaskError: If the status update fails.
        """
        ...

    def resolve_task_id(self, input_str: str) -> str | None:
        """Attempt to extract a task ID from an input string.

        This method tries to parse task IDs from various inputs:
        - Direct task IDs: "RULE-123"
        - Branch names: "feature/RULE-123-add-auth"
        - URLs: "https://linear.app/team/issue/RULE-123"
        - Feature descriptions: "Add auth for RULE-123"

        Args:
            input_str: The input string that may contain a task ID.

        Returns:
            The extracted task ID if found, None otherwise.
        """
        ...

    def add_label(self, task_id: str, label: str) -> None:
        """Add a label to a task.

        Args:
            task_id: The task identifier (internal ID, e.g., UUID).
            label: The label to add (e.g., "adw:running").

        Note:
            This operation should be non-blocking. Implementations should
            catch and log errors rather than raising exceptions.
        """
        ...

    def remove_label(self, task_id: str, label: str) -> None:
        """Remove a label from a task.

        Args:
            task_id: The task identifier (internal ID, e.g., UUID).
            label: The label to remove (e.g., "adw:running").

        Note:
            This operation should be non-blocking. Implementations should
            catch and log errors rather than raising exceptions.
        """
        ...
