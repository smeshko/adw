"""Task manager abstraction for external task management systems.

This package provides a pluggable abstraction for integrating with external
task management systems like Linear, Jira, or GitHub Issues.

Example:
    >>> from adw.task_managers import TaskManager, TaskManagerFactory
    >>> factory = TaskManagerFactory()
    >>> manager = factory.create(config)
    >>> task_info = manager.fetch_task("RULE-123")

    >>> from adw.task_managers import InputResolver, InputType, ResolvedInput
    >>> resolver = InputResolver(manager)
    >>> result = resolver.resolve("RULE-123")
    >>> result.type == InputType.TASK_ID
    True
"""

from adw.task_managers.base import TaskManager
from adw.task_managers.factory import TaskManagerFactory
from adw.task_managers.null import NullTaskManager
from adw.task_managers.resolver import InputResolver, InputType, ResolvedInput

__all__ = [
    "InputResolver",
    "InputType",
    "NullTaskManager",
    "ResolvedInput",
    "TaskManager",
    "TaskManagerFactory",
]
