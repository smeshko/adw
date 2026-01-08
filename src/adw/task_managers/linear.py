"""LinearTaskManager implementation.

This module provides the Linear task manager for integrating ADW with
Linear issue tracking system.
"""

import logging
import os
from typing import Any

from adw.exceptions import ConfigError, TaskError
from adw.models.config import TaskManagerConfig
from adw.models.task import TaskInfo
from adw.task_managers.linear_client import LinearClient

logger = logging.getLogger(__name__)


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
        self._client = LinearClient(api_key=self._api_key)
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
        issue = self._client.fetch_issue(task_id)

        if issue is None:
            raise TaskError(
                code="TASK_NOT_FOUND",
                message=f"Task '{task_id}' not found in Linear",
                suggestion="Verify the task ID is correct",
                task_id=task_id,
                recoverable=False,
            )

        return self._map_issue_to_task_info(issue)

    def _map_issue_to_task_info(self, issue: dict[str, Any]) -> TaskInfo:
        """Map Linear issue response to TaskInfo model.

        Args:
            issue: Raw issue data from Linear API.

        Returns:
            TaskInfo with mapped fields.
        """
        # Extract labels from nested structure
        labels_data = issue.get("labels", {}) or {}
        labels_nodes = labels_data.get("nodes", []) or []
        labels = [label["name"] for label in labels_nodes if label and "name" in label]

        # Extract parent info if present
        parent = issue.get("parent")
        parent_id = parent.get("identifier") if parent else None
        parent_title = parent.get("title") if parent else None

        # Extract state name if present
        state = issue.get("state")
        status = state.get("name") if state else None

        # Extract assignee name if present
        assignee_data = issue.get("assignee")
        assignee = assignee_data.get("name") if assignee_data else None

        return TaskInfo(
            id=issue["id"],
            identifier=issue["identifier"],
            title=issue["title"],
            description=issue.get("description"),
            status=status,
            priority=issue.get("priority"),
            labels=labels,
            assignee=assignee,
            parent_id=parent_id,
            parent_title=parent_title,
        )

    def update_status(
        self,
        task_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update task status in Linear.

        This is a non-blocking operation - errors are logged but do not
        raise exceptions to avoid failing the ADW run.

        Args:
            task_id: The task identifier (internal UUID, not identifier like RULE-123).
            status: The ADW status to map to Linear state (e.g., "running", "completed").
            metadata: Optional additional metadata (currently unused).
        """
        # Map ADW status to Linear state name
        linear_state_name = self._config.state_mapping.get(status)
        if not linear_state_name:
            logger.warning(
                "No state mapping found for ADW status '%s'",
                status,
            )
            return

        # Get state ID from cache or fetch
        state_id = self._get_state_id(linear_state_name)
        if not state_id:
            logger.warning(
                "Linear state '%s' not found in team workflow states",
                linear_state_name,
            )
            return

        # Update issue
        try:
            result = self._client.update_issue(task_id, {"stateId": state_id})
            if result:
                logger.info(
                    "Updated Linear issue %s to state '%s'",
                    task_id,
                    linear_state_name,
                )
            else:
                logger.warning(
                    "Failed to update Linear issue %s to state '%s'",
                    task_id,
                    linear_state_name,
                )
        except Exception as e:
            logger.warning(
                "Error updating Linear issue %s: %s",
                task_id,
                str(e),
            )

    def _get_state_id(self, state_name: str) -> str | None:
        """Get Linear state ID by name, using cache.

        Args:
            state_name: The state name to look up.

        Returns:
            The state ID if found, None otherwise.
        """
        # Populate cache if empty
        if not self._state_cache:
            self._populate_state_cache()

        return self._state_cache.get(state_name)

    def _populate_state_cache(self) -> None:
        """Fetch and cache team workflow states."""
        try:
            states = self._client.get_team_states(self._team_id)
            for state in states:
                name = state.get("name")
                state_id = state.get("id")
                if name and state_id:
                    self._state_cache[name] = state_id
            logger.debug(
                "Cached %d workflow states for team %s",
                len(self._state_cache),
                self._team_id,
            )
        except Exception as e:
            logger.warning(
                "Failed to fetch team workflow states: %s",
                str(e),
            )

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
