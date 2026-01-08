"""LinearTaskManager implementation.

This module provides the Linear task manager for integrating ADW with
Linear issue tracking system.
"""

import os
from typing import Any

from adw.exceptions import ConfigError, TaskError
from adw.models.config import TaskManagerConfig
from adw.models.task import TaskInfo


class LinearTaskManager:
    """Task manager for Linear issue tracking integration.

    This implementation integrates ADW with Linear's GraphQL API to:
    - Fetch task information by identifier (e.g., RULE-123)
    - Update task status as ADW phases progress
    - Resolve task IDs from various input formats

    Required environment variables:
        LINEAR_API_KEY: Linear API key from settings
        LINEAR_TEAM_ID: Team UUID

    Example:
        >>> config = TaskManagerConfig(type="linear", team_key="RULE")
        >>> manager = LinearTaskManager(config)
        >>> task = manager.fetch_task("RULE-123")
        >>> task.title
        'Add user authentication'
    """

    def __init__(self, config: TaskManagerConfig) -> None:
        """Initialize LinearTaskManager with configuration.

        Args:
            config: Task manager configuration from project settings.

        Raises:
            ConfigError: If LINEAR_API_KEY or LINEAR_TEAM_ID is not set.
        """
        self._config = config
        self._api_key = self._get_api_key()
        self._team_id = self._get_team_id()
        self._state_cache: dict[str, str] = {}  # state_name -> state_id

    @property
    def name(self) -> str:
        """Return the task manager type name.

        Returns:
            'linear' to indicate Linear task manager.
        """
        return "linear"

    def _get_api_key(self) -> str:
        """Get LINEAR_API_KEY from environment.

        Returns:
            The Linear API key.

        Raises:
            ConfigError: If LINEAR_API_KEY is not set.
        """
        api_key = os.environ.get("LINEAR_API_KEY")
        if not api_key:
            raise ConfigError(
                code="MISSING_LINEAR_API_KEY",
                message="LINEAR_API_KEY environment variable is not set",
                suggestion="Add LINEAR_API_KEY to your .env file",
                recoverable=False,
            )
        return api_key

    def _get_team_id(self) -> str:
        """Get LINEAR_TEAM_ID from environment.

        Returns:
            The Linear team UUID.

        Raises:
            ConfigError: If LINEAR_TEAM_ID is not set.
        """
        team_id = os.environ.get("LINEAR_TEAM_ID")
        if not team_id:
            raise ConfigError(
                code="MISSING_LINEAR_TEAM_ID",
                message="LINEAR_TEAM_ID environment variable is not set",
                suggestion="Add LINEAR_TEAM_ID to your .env file",
                recoverable=False,
            )
        return team_id

    def fetch_task(self, task_id: str) -> TaskInfo:
        """Fetch task information from Linear by identifier.

        Args:
            task_id: The task identifier (e.g., RULE-123).

        Returns:
            TaskInfo with task details from Linear.

        Raises:
            TaskError: If the task cannot be fetched.
        """
        # TODO: Implement in Task 3
        raise NotImplementedError("fetch_task will be implemented in Task 3")

    def update_status(
        self,
        task_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update task status in Linear.

        Args:
            task_id: The task identifier.
            status: The new status (mapped via config state_mapping).
            metadata: Optional additional metadata to include in the update.

        Raises:
            TaskError: If the status update fails.
        """
        # TODO: Implement in Task 4
        pass  # Non-blocking - log and continue on failure

    def resolve_task_id(self, input_str: str) -> str | None:
        """Attempt to extract a task ID from an input string.

        This method tries to parse Linear task IDs from various inputs:
        - Direct task IDs: "RULE-123"
        - Branch names: "feature/RULE-123-add-auth"
        - URLs: "https://linear.app/team/issue/RULE-123"
        - Feature descriptions: "Add auth for RULE-123"

        Args:
            input_str: The input string that may contain a task ID.

        Returns:
            The extracted task ID if found, None otherwise.
        """
        # TODO: Implement in Task 5
        return None
