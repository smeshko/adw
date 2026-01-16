"""LabelManager service for task label management.

This module provides a high-level service for managing task labels
based on run state, handling label prefix configuration, and
abstracting the label operations from the orchestrator.
"""

import logging

from adw.models.config import TaskManagerLabelsConfig
from adw.task_managers.base import TaskManager

logger = logging.getLogger(__name__)


class LabelManager:
    """Service for managing task labels based on run state.

    Provides high-level methods for setting labels at different run stages:
    - set_running(): When a run starts
    - set_phase(): When transitioning between phases
    - set_completed(): When a run completes successfully
    - set_failed(): When a run fails

    All operations are non-blocking - failures are logged but don't raise.

    Example:
        >>> manager = LabelManager(task_manager, config, task_id)
        >>> manager.set_running()  # Adds adw:running
        >>> manager.set_phase("build")  # Adds adw:phase:build
        >>> manager.set_completed()  # Removes running, adds completed
    """

    def __init__(
        self,
        task_manager: TaskManager,
        config: TaskManagerLabelsConfig,
        task_id: str,
    ) -> None:
        """Initialize LabelManager.

        Args:
            task_manager: The task manager for label operations.
            config: Label configuration (enabled, prefix).
            task_id: The task ID (internal UUID) to manage labels for.
        """
        self._task_manager = task_manager
        self._config = config
        self._task_id = task_id
        self._current_phase_label: str | None = None

    def _get_label(self, label_suffix: str) -> str:
        """Construct full label name with prefix.

        Args:
            label_suffix: The label suffix (e.g., "running", "phase:build").

        Returns:
            Full label name with prefix (e.g., "adw:running").
        """
        return f"{self._config.prefix}{label_suffix}"

    def _get_phase_label(self, phase_name: str) -> str:
        """Construct phase label name.

        Args:
            phase_name: The phase name (e.g., "build", "validate").

        Returns:
            Full phase label (e.g., "adw:phase:build").
        """
        return self._get_label(f"phase:{phase_name}")

    def set_running(self) -> None:
        """Set the running label when a run starts.

        Adds the running label (e.g., "adw:running") to indicate
        an ADW run is in progress.
        """
        if not self._config.enabled:
            return

        label = self._get_label("running")
        try:
            self._task_manager.add_label(self._task_id, label)
            logger.debug("Added label '%s' to task %s", label, self._task_id)
        except Exception as e:
            logger.warning(
                "Failed to add running label to task %s: %s",
                self._task_id,
                str(e),
            )

    def set_phase(self, phase_name: str) -> None:
        """Set the current phase label.

        Removes the previous phase label (if any) and adds the new phase label.
        Operations are isolated - failure to remove doesn't block adding new label.

        Args:
            phase_name: The phase name (e.g., "plan", "build", "validate").
        """
        if not self._config.enabled:
            return

        new_phase_label = self._get_phase_label(phase_name)

        # Remove previous phase label if exists (isolated try/except)
        if self._current_phase_label:
            try:
                self._task_manager.remove_label(
                    self._task_id, self._current_phase_label
                )
                logger.debug(
                    "Removed phase label '%s' from task %s",
                    self._current_phase_label,
                    self._task_id,
                )
            except Exception as e:
                logger.warning(
                    "Failed to remove phase label '%s' from task %s: %s",
                    self._current_phase_label,
                    self._task_id,
                    str(e),
                )

        # Add new phase label (isolated try/except)
        try:
            self._task_manager.add_label(self._task_id, new_phase_label)
            self._current_phase_label = new_phase_label
            logger.debug(
                "Added phase label '%s' to task %s",
                new_phase_label,
                self._task_id,
            )
        except Exception as e:
            logger.warning(
                "Failed to add phase label '%s' to task %s: %s",
                new_phase_label,
                self._task_id,
                str(e),
            )

    def set_completed(self) -> None:
        """Set labels when a run completes successfully.

        Removes the running label and current phase label (if any),
        then adds the completed label.
        Operations are isolated - failures don't block subsequent operations.
        """
        if not self._config.enabled:
            return

        running_label = self._get_label("running")
        completed_label = self._get_label("completed")

        # Remove running label (isolated try/except)
        try:
            self._task_manager.remove_label(self._task_id, running_label)
            logger.debug(
                "Removed label '%s' from task %s", running_label, self._task_id
            )
        except Exception as e:
            logger.warning(
                "Failed to remove running label from task %s: %s",
                self._task_id,
                str(e),
            )

        # Remove current phase label if exists (isolated try/except)
        if self._current_phase_label:
            try:
                self._task_manager.remove_label(
                    self._task_id, self._current_phase_label
                )
                logger.debug(
                    "Removed phase label '%s' from task %s",
                    self._current_phase_label,
                    self._task_id,
                )
                self._current_phase_label = None
            except Exception as e:
                logger.warning(
                    "Failed to remove phase label '%s' from task %s: %s",
                    self._current_phase_label,
                    self._task_id,
                    str(e),
                )

        # Add completed label (isolated try/except)
        try:
            self._task_manager.add_label(self._task_id, completed_label)
            logger.debug("Added label '%s' to task %s", completed_label, self._task_id)
        except Exception as e:
            logger.warning(
                "Failed to add completed label to task %s: %s",
                self._task_id,
                str(e),
            )

    def set_failed(self) -> None:
        """Set labels when a run fails.

        Removes the running label and adds the failed label.
        Note: The phase label is kept for debugging purposes.
        Operations are isolated - failures don't block subsequent operations.
        """
        if not self._config.enabled:
            return

        running_label = self._get_label("running")
        failed_label = self._get_label("failed")

        # Remove running label (isolated try/except)
        try:
            self._task_manager.remove_label(self._task_id, running_label)
            logger.debug(
                "Removed label '%s' from task %s", running_label, self._task_id
            )
        except Exception as e:
            logger.warning(
                "Failed to remove running label from task %s: %s",
                self._task_id,
                str(e),
            )

        # Note: Phase label is intentionally kept for debugging

        # Add failed label (isolated try/except)
        try:
            self._task_manager.add_label(self._task_id, failed_label)
            logger.debug("Added label '%s' to task %s", failed_label, self._task_id)
        except Exception as e:
            logger.warning(
                "Failed to add failed label to task %s: %s",
                self._task_id,
                str(e),
            )
