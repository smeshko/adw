"""TaskManager factory for creating task manager instances.

This module provides a factory for creating task manager instances
based on configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from adw.exceptions import ConfigError
from adw.task_managers.base import TaskManager
from adw.task_managers.null import NullTaskManager

if TYPE_CHECKING:
    from adw.task_managers.linear import LinearTaskManager

# Registry of available task manager types
_AVAILABLE_TYPES = {"none", "linear"}


class TaskManagerFactory:
    """Factory for creating TaskManager instances.

    The factory uses a registry pattern to support multiple task manager
    implementations. New task managers can be added by registering them
    in the _AVAILABLE_TYPES set and implementing the corresponding branch
    in the create method.

    Linear imports are lazy to avoid httpx dependency when not using Linear.

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
                Supported values: "none", "linear".

        Returns:
            A TaskManager implementation.

        Raises:
            ConfigError: If the task_type is not recognized.
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
            return self._create_linear()

        # Should be unreachable
        raise ConfigError(
            code="TASK_MANAGER_NOT_IMPLEMENTED",
            message=f"Task manager type '{task_type}' is not implemented",
            suggestion="Use 'none' as a fallback",
            recoverable=False,
        )

    def _create_linear(self) -> "LinearTaskManager":
        """Create LinearTaskManager with lazy import.

        Lazy import avoids loading httpx when Linear is not used.

        Returns:
            A configured LinearTaskManager instance.
        """
        # Lazy import to avoid httpx dependency if not using Linear
        from adw.models.config import TaskManagerConfig
        from adw.task_managers.linear import LinearTaskManager

        # Create with default config - actual config comes from project.yaml
        # This factory is a simple creator; config is typically provided
        # by the orchestrator based on project settings
        config = TaskManagerConfig(type="linear")
        return LinearTaskManager(config)
