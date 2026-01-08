"""Tests for TaskManagerFactory.

Per ADR-001: Tests focus on factory behavior, not trivial checks.
"""

import pytest

from adw.exceptions import ConfigError
from adw.task_managers.base import TaskManager
from adw.task_managers.factory import TaskManagerFactory
from adw.task_managers.null import NullTaskManager


class TestTaskManagerFactory:
    """Tests for TaskManagerFactory."""

    def test_create_none_returns_null_manager(self) -> None:
        """Creating with type='none' returns NullTaskManager."""
        factory = TaskManagerFactory()
        manager = factory.create(task_type="none")

        assert isinstance(manager, NullTaskManager)
        assert isinstance(manager, TaskManager)
        assert manager.name == "none"

    def test_create_default_returns_null_manager(self) -> None:
        """Creating with no type specified returns NullTaskManager."""
        factory = TaskManagerFactory()
        manager = factory.create()

        assert isinstance(manager, NullTaskManager)

    def test_create_unknown_raises_config_error(self) -> None:
        """Unknown task_manager type raises ConfigError."""
        factory = TaskManagerFactory()

        with pytest.raises(ConfigError) as exc_info:
            factory.create(task_type="unknown")

        assert exc_info.value.code == "INVALID_TASK_MANAGER"
        assert "unknown" in exc_info.value.message

    def test_error_includes_available_options(self) -> None:
        """ConfigError message includes available task manager types."""
        factory = TaskManagerFactory()

        with pytest.raises(ConfigError) as exc_info:
            factory.create(task_type="invalid")

        error_str = str(exc_info.value)
        assert "none" in error_str.lower()
        assert "linear" in error_str.lower()

    def test_create_linear_returns_linear_manager(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Creating with type='linear' returns LinearTaskManager."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")

        factory = TaskManagerFactory()
        manager = factory.create(task_type="linear")

        assert manager.name == "linear"
        assert isinstance(manager, TaskManager)
