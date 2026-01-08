"""Integration tests for TaskManager factory creation flow.

Per ADR-001: Integration tests verify real component interactions.
"""

from adw.models.config import TaskManagerConfig
from adw.task_managers.base import TaskManager
from adw.task_managers.factory import TaskManagerFactory
from adw.task_managers.null import NullTaskManager


class TestTaskManagerIntegration:
    """Integration tests for TaskManager factory flow."""

    def test_factory_creates_null_manager_from_config(self) -> None:
        """Factory creates NullTaskManager from TaskManagerConfig defaults."""
        config = TaskManagerConfig()
        factory = TaskManagerFactory()

        manager = factory.create(task_type=config.type)

        assert isinstance(manager, NullTaskManager)
        assert isinstance(manager, TaskManager)
        assert manager.name == "none"

    def test_factory_respects_explicit_none_type(self) -> None:
        """Factory creates NullTaskManager when type explicitly set to 'none'."""
        config = TaskManagerConfig(type="none", team_key="RULE")
        factory = TaskManagerFactory()

        manager = factory.create(task_type=config.type)

        assert isinstance(manager, NullTaskManager)
        assert manager.name == "none"
        # NullTaskManager doesn't use team_key - it's for actual task managers
        assert manager.resolve_task_id("RULE-123") is None
