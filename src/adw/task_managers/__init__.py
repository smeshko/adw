"""Task manager abstraction for external task management systems.

This package provides a pluggable abstraction for integrating with external
task management systems like Linear, Jira, or GitHub Issues.

Example:
    >>> from adw.task_managers import TaskManager, TaskManagerFactory
    >>> factory = TaskManagerFactory()
    >>> manager = factory.create(config)
    >>> task_info = manager.fetch_task("RULE-123")
"""

from adw.task_managers.base import TaskManager
from adw.task_managers.null import NullTaskManager

__all__ = [
    "NullTaskManager",
    "TaskManager",
]
