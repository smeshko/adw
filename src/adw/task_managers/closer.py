"""IssueCloser service for automated task completion.

This module provides the IssueCloser service which manages the workflow
of closing tasks when PRs are merged, based on project configuration.
"""

import logging

from adw.models.config import TaskManagerConfig
from adw.task_managers.base import TaskManager
from adw.task_managers.github_client import GitHubClient

logger = logging.getLogger(__name__)


class IssueCloser:
    """Service for managing issue closing based on PR merge status.

    This service encapsulates the logic for closing tasks when:
    1. auto_close is enabled in configuration
    2. The associated PR has been merged (or no PR URL is provided)

    If the PR is not merged, the task remains open but can optionally
    have a "pr-ready" label added to indicate it's ready for merge.

    Example:
        >>> closer = IssueCloser(task_manager, config)
        >>> closed = closer.maybe_close("task-uuid", "https://github.com/o/r/pull/1")
        >>> closed
        True
    """

    def __init__(
        self,
        task_manager: TaskManager,
        config: TaskManagerConfig,
        github_client: GitHubClient | None = None,
    ) -> None:
        """Initialize IssueCloser with dependencies.

        Args:
            task_manager: The task manager for closing tasks.
            config: Task manager configuration with auto_close setting.
            github_client: Optional GitHub client for PR merge detection.
                If not provided, a default client will be created.
        """
        self._task_manager = task_manager
        self._config = config
        self._github_client = github_client or GitHubClient()

    def maybe_close(self, task_id: str, pr_url: str | None = None) -> bool:
        """Close task if conditions are met.

        This method checks:
        1. If auto_close is enabled in configuration
        2. If the PR is merged (when pr_url is provided)

        If conditions are met, the task is closed. If not:
        - With auto_close disabled: returns False, does nothing
        - With PR not merged: logs info, optionally adds pr-ready label

        Args:
            task_id: The internal task UUID (from TaskInfo.id).
            pr_url: Optional PR URL to check merge status. If not provided,
                the task is closed without checking PR status.

        Returns:
            True if the task was closed, False otherwise.
        """
        # Check if auto_close is enabled
        if not self._config.auto_close:
            logger.debug("Auto-close disabled, skipping close for task %s", task_id)
            return False

        # Check PR merge status if URL provided
        if pr_url:
            is_merged = self._github_client.is_pr_merged(pr_url)

            if not is_merged:
                logger.info(
                    "PR not merged, task remains open: %s (PR: %s)",
                    task_id,
                    pr_url,
                )
                self._add_pr_ready_label(task_id)
                return False

        # Close the task
        return self._safe_close_task(task_id)

    def _safe_close_task(self, task_id: str) -> bool:
        """Close task with error handling.

        Args:
            task_id: The task UUID to close.

        Returns:
            True if closed successfully, False otherwise.
        """
        try:
            self._task_manager.close_task(task_id)
            logger.info("Task closed: %s", task_id)
            return True
        except Exception as e:
            logger.warning(
                "Failed to close task %s: %s. "
                "Close manually with: adw task close %s",
                task_id,
                e,
                task_id,
            )
            return False

    def _add_pr_ready_label(self, task_id: str) -> None:
        """Add pr-ready label to task (placeholder for LabelManager integration).

        This method is a placeholder for when LabelManager (Story 12.7) is
        integrated. Currently it only logs the intent.

        Args:
            task_id: The task UUID to label.
        """
        # Check if labels are enabled
        if not self._config.labels.enabled:
            return

        label_name = f"{self._config.labels.prefix}pr-ready"
        logger.info(
            "Would add label '%s' to task %s (LabelManager not yet integrated)",
            label_name,
            task_id,
        )
        # TODO: Integrate with LabelManager from Story 12.7
        # Once LabelManager is available:
        # try:
        #     self._label_manager.add_label(task_id, label_name)
        # except Exception as e:
        #     logger.warning("Failed to add pr-ready label: %s", e)

    def close(self) -> None:
        """Close the underlying GitHub client."""
        self._github_client.close()

    def __enter__(self) -> "IssueCloser":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - close resources."""
        self.close()
