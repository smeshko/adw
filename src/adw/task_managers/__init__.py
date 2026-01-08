"""Task manager abstraction for external task management systems.

This package provides a pluggable abstraction for integrating with external
task management systems like Linear, Jira, or GitHub Issues.

Example:
    >>> from adw.task_managers import TaskManager, TaskManagerFactory
    >>> factory = TaskManagerFactory()
    >>> manager = factory.create(task_type="linear")
    >>> task_info = manager.fetch_task("RULE-123")
"""

from adw.task_managers.base import TaskManager
from adw.task_managers.factory import TaskManagerFactory
from adw.task_managers.null import NullTaskManager

# LinearTaskManager is lazily imported to avoid httpx dependency
# when not using Linear. Use factory.create("linear") instead of direct import.

__all__ = [
    "NullTaskManager",
    "TaskManager",
    "TaskManagerFactory",
]
