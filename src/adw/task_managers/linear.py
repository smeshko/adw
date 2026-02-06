"""LinearTaskManager implementation.

This module provides the Linear task manager for integrating ADW with
Linear issue tracking system.
"""

import logging
import os
import re
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
                suggestion="Copy .adw/.env.template to .adw/.env and add your key",
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
                suggestion="Copy .adw/.env.template to .adw/.env and add your ID",
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

        Raises:
            TaskError: If required fields are missing from the API response.
        """
        # Validate required fields exist
        issue_id = issue.get("id")
        identifier = issue.get("identifier")
        title = issue.get("title")

        if not issue_id or not identifier or not title:
            raise TaskError(
                code="TASK_INVALID_RESPONSE",
                message="Linear API response missing required fields "
                "(id, identifier, or title)",
                suggestion="Check if the Linear API schema has changed",
                task_id=identifier or "unknown",
                recoverable=False,
            )

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
            id=issue_id,
            identifier=identifier,
            title=title,
            description=issue.get("description"),
            status=status,
            priority=issue.get("priority") or None,
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
            task_id: The internal Linear issue UUID (from TaskInfo.id, NOT the
                identifier like RULE-123). Use the UUID from fetch_task().
            status: The ADW status to map to Linear state (e.g., "running").
            metadata: Optional additional metadata (currently unused).
        """
        # Map ADW phase/status to Linear state name if mapping exists,
        # otherwise use the status directly (already mapped by StatusSyncService)
        linear_state_name = self._config.state_mapping.get(status, status)

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
                logger.debug(
                    "Updated state to '%s'",
                    linear_state_name,
                    extra={"task_id": task_id},
                )
            else:
                logger.error(
                    "Failed to update state to '%s'",
                    linear_state_name,
                    extra={"task_id": task_id},
                )
        except Exception as e:
            logger.error(
                "Error updating state to '%s': %s",
                linear_state_name,
                str(e),
                extra={"task_id": task_id, "state": linear_state_name},
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
            logger.error(
                "Failed to fetch team workflow states: %s",
                str(e),
            )

    def close(self) -> None:
        """Close the underlying HTTP client.

        Should be called when the task manager is no longer needed
        to release resources.
        """
        self._client.close()

    def __enter__(self) -> "LinearTaskManager":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - close client."""
        self.close()

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
            The extracted task ID (uppercase) if found, None otherwise.
        """
        team_key = self._config.team_key
        if not team_key:
            return None

        if not input_str:
            return None

        # Build pattern: {team_key}-\d+ (case insensitive)
        pattern = rf"({re.escape(team_key)}-\d+)"
        match = re.search(pattern, input_str, re.IGNORECASE)

        if match:
            # Return normalized (uppercase) task ID
            return match.group(1).upper()

        return None

    def close_task(self, task_id: str) -> None:
        """Close a task by moving it to the Done state.

        This operation:
        1. Finds the "Done" state ID from the team workflow
        2. Updates the issue to the Done state
        3. Sets the completedAt timestamp

        Args:
            task_id: The internal Linear issue UUID (from TaskInfo.id).

        Raises:
            TaskError: If the task cannot be closed.
        """
        # Get done state ID (handles custom state mapping via config)
        done_state_id = self._get_done_state_id()
        if not done_state_id:
            raise TaskError(
                code="DONE_STATE_NOT_FOUND",
                message="Could not find 'Done' or 'Completed' state in workflow",
                suggestion="Verify your Linear team has a 'Done' workflow state, "
                "or configure state_mapping in project.yaml",
                task_id=task_id,
                recoverable=False,
            )

        # Update issue with done state and completedAt timestamp
        from datetime import UTC, datetime

        completed_at = datetime.now(UTC).isoformat()

        try:
            result = self._client.update_issue(
                task_id,
                {
                    "stateId": done_state_id,
                    "completedAt": completed_at,
                },
            )
            if result:
                logger.info(
                    "Closed issue",
                    extra={"task_id": task_id},
                )
            else:
                raise TaskError(
                    code="TASK_CLOSE_FAILED",
                    message=f"Failed to close Linear issue '{task_id}'",
                    suggestion="Check Linear API connectivity and permissions",
                    task_id=task_id,
                    recoverable=True,
                )
        except TaskError:
            raise
        except Exception as e:
            raise TaskError(
                code="TASK_CLOSE_ERROR",
                message=f"Error closing Linear issue '{task_id}': {e}",
                suggestion="Check Linear API connectivity and try again",
                task_id=task_id,
                recoverable=True,
            ) from e

    def _get_done_state_id(self) -> str | None:
        """Get the Done state ID for closing tasks.

        Checks state_mapping config first, then falls back to looking
        for 'Done' or 'Completed' states in the team workflow.

        Returns:
            The state ID for the done state, or None if not found.
        """
        # Check if there's a custom mapping for 'done' or 'completed' status
        done_state_name = self._config.state_mapping.get("done")
        if not done_state_name:
            done_state_name = self._config.state_mapping.get("completed")

        # If no mapping, use default state names
        if not done_state_name:
            # Try common done state names
            for name in ["Done", "Completed", "Complete", "Closed"]:
                state_id = self._get_state_id(name)
                if state_id:
                    return state_id
            return None

        return self._get_state_id(done_state_name)

    def is_pr_merged(self, pr_url: str) -> bool:
        """Check if a pull request has been merged.

        Note: Linear does not natively track PR merge status. This method
        returns False by default. PR merge detection is handled separately
        via GitHub API in the IssueCloser service.

        Args:
            pr_url: The full URL to the pull request.

        Returns:
            Always False - PR detection is handled by IssueCloser.
        """
        # Linear doesn't track PR merge status natively
        # This is handled by IssueCloser using GitHub API
        return False

    def add_label(self, task_id: str, label: str) -> None:
        """Add a label to a Linear issue.

        This is a non-blocking operation - errors are logged but do not
        raise exceptions to avoid failing the ADW run.

        Args:
            task_id: The internal Linear issue UUID (from TaskInfo.id).
            label: The label name to add (e.g., "adw:running").
        """
        try:
            self._client.add_label(task_id, label, self._team_id)
            logger.debug(
                "Added label '%s'",
                label,
                extra={"task_id": task_id},
            )
        except Exception as e:
            logger.error(
                "Failed to add label '%s': %s",
                label,
                str(e),
                extra={"task_id": task_id},
            )

    def remove_label(self, task_id: str, label: str) -> None:
        """Remove a label from a Linear issue.

        This is a non-blocking operation - errors are logged but do not
        raise exceptions to avoid failing the ADW run.

        Args:
            task_id: The internal Linear issue UUID (from TaskInfo.id).
            label: The label name to remove (e.g., "adw:running").
        """
        try:
            self._client.remove_label(task_id, label, self._team_id)
            logger.debug(
                "Removed label '%s'",
                label,
                extra={"task_id": task_id},
            )
        except Exception as e:
            logger.error(
                "Failed to remove label '%s': %s",
                label,
                str(e),
                extra={"task_id": task_id},
            )

    def post_comment(self, task_id: str, body: str) -> None:
        """Post a comment to a Linear issue.

        This is a non-blocking operation - errors are logged but do not
        raise exceptions to avoid failing the ADW run.

        Args:
            task_id: The internal Linear issue UUID (from TaskInfo.id).
            body: The comment body (supports markdown).
        """
        try:
            self._client.post_comment(task_id, body)
            logger.debug(
                "Posted sync comment",
                extra={"task_id": task_id},
            )
        except Exception as e:
            logger.error(
                "Failed to post comment: %s",
                str(e),
                extra={"task_id": task_id},
            )
