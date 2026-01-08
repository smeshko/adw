"""TaskManager factory for creating task manager instances.

This module provides a factory for creating task manager instances
based on configuration.
"""

from adw.exceptions import ConfigError
from adw.task_managers.base import TaskManager
from adw.task_managers.null import NullTaskManager

# Registry of available task manager types
# "linear" is registered but not yet implemented (Story 12.2)
_AVAILABLE_TYPES = {"none", "linear"}


class TaskManagerFactory:
    """Factory for creating TaskManager instances.

    The factory uses a registry pattern to support multiple task manager
    implementations. New task managers can be added by registering them
    in the _AVAILABLE_TYPES set and implementing the corresponding branch
    in the create method.

    Example:
        >>> factory = TaskManagerFactory()
        >>> manager = factory.create(task_type="none")
        >>> manager.name
        'none'
    """

    def create(self, task_type: str = "none") -> TaskManager:
        """Create a TaskManager instance based on the specified type.

        Args:
            task_type: The type of task manager to create. Defaults to "none".
                Supported values: "none", "linear" (not yet implemented).

        Returns:
            A TaskManager implementation.

        Raises:
            ConfigError: If the task_type is not recognized or not implemented.
        """
        if task_type not in _AVAILABLE_TYPES:
            available = ", ".join(sorted(_AVAILABLE_TYPES))
            raise ConfigError(
                code="INVALID_TASK_MANAGER",
                message=f"Unknown task manager type: '{task_type}'",
                suggestion=f"Available types: {available}",
                recoverable=False,
            )

        if task_type == "none":
            return NullTaskManager()

        if task_type == "linear":
            # Linear implementation coming in Story 12.2
            raise ConfigError(
                code="TASK_MANAGER_NOT_IMPLEMENTED",
                message="Linear task manager is not yet implemented",
                suggestion="Use 'none' or wait for Story 12.2",
                recoverable=False,
            )

        # Should not reach here, but satisfy type checker
        raise ConfigError(
            code="INVALID_TASK_MANAGER",
            message=f"Unknown task manager type: '{task_type}'",
            suggestion=f"Available types: {', '.join(sorted(_AVAILABLE_TYPES))}",
            recoverable=False,
        )
