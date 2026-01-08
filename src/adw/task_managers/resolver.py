"""Input resolver for task ID vs feature string detection.

This module provides automatic detection of whether user input is a task ID
(e.g., "RULE-123") or a literal feature description (e.g., "Add user auth").
"""

import logging
from dataclasses import dataclass
from enum import Enum

from adw.task_managers.base import TaskManager

logger = logging.getLogger(__name__)


class InputType(Enum):
    """Type of resolved input."""

    TASK_ID = "task_id"
    FEATURE_STRING = "feature_string"


@dataclass
class ResolvedInput:
    """Result of input resolution.

    Attributes:
        type: Whether input was resolved as TASK_ID or FEATURE_STRING.
        value: The resolved value (task ID or feature string).
        task_id: The extracted task ID (only set if type is TASK_ID).
        original: The original input string, preserved exactly.
    """

    type: InputType
    value: str
    task_id: str | None = None
    original: str = ""


class InputResolver:
    """Resolve user input to either a task ID or feature string.

    This class delegates pattern detection to the configured TaskManager,
    which knows its own ID patterns (e.g., Linear's "TEAM-123" format).

    Example:
        >>> from adw.task_managers import TaskManagerFactory
        >>> factory = TaskManagerFactory()
        >>> manager = factory.create(config)
        >>> resolver = InputResolver(manager)
        >>> result = resolver.resolve("RULE-123")
        >>> result.type
        <InputType.TASK_ID: 'task_id'>
    """

    def __init__(self, task_manager: TaskManager) -> None:
        """Initialize resolver with a task manager.

        Args:
            task_manager: The task manager to use for ID pattern detection.
        """
        self._task_manager = task_manager

    def resolve(
        self,
        input_str: str,
        *,
        force_task_id: bool = False,
        force_feature: bool = False,
    ) -> ResolvedInput:
        """Resolve input string to either task ID or feature string.

        Args:
            input_str: The user-provided input to resolve.
            force_task_id: If True, require input to be a valid task ID.
            force_feature: If True, treat input as feature string (skip resolution).

        Returns:
            ResolvedInput with the resolution result.

        Raises:
            ValueError: If force_task_id=True and input doesn't match pattern.
        """
        if force_feature:
            logger.info(
                "Input treated as feature (--no-task-manager)",
                extra={"input": input_str},
            )
            return ResolvedInput(
                type=InputType.FEATURE_STRING,
                value=input_str,
                original=input_str,
            )

        task_id = self._task_manager.resolve_task_id(input_str)

        if task_id:
            logger.info(
                "Input resolved as task ID",
                extra={"input": input_str, "task_id": task_id},
            )
            return ResolvedInput(
                type=InputType.TASK_ID,
                value=task_id,
                task_id=task_id,
                original=input_str,
            )

        if force_task_id:
            msg = f"Input '{input_str}' does not match task ID pattern"
            raise ValueError(msg)

        logger.info(
            "Input treated as feature string",
            extra={"input": input_str},
        )
        return ResolvedInput(
            type=InputType.FEATURE_STRING,
            value=input_str,
            original=input_str,
        )
