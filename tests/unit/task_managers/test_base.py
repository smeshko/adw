"""Tests for TaskManager Protocol definition.

Per ADR-001: Tests focus on Protocol compliance and required methods.
"""

from typing import Any

import pytest

from adw.task_managers.base import TaskManager


class TestTaskManagerProtocol:
    """Tests for TaskManager Protocol."""

    def test_protocol_defines_required_methods(self) -> None:
        """Protocol requires fetch_task, update_status, resolve_task_id."""
        # Check Protocol has the required methods
        assert hasattr(TaskManager, "fetch_task")
        assert hasattr(TaskManager, "update_status")
        assert hasattr(TaskManager, "resolve_task_id")

    def test_protocol_defines_name_property(self) -> None:
        """Protocol requires name property."""
        assert hasattr(TaskManager, "name")

    def test_minimal_implementation_satisfies_protocol(self) -> None:
        """A minimal implementation satisfies the Protocol."""
        from adw.models.task import TaskInfo

        class MinimalTaskManager:
            """Minimal implementation for testing."""

            @property
            def name(self) -> str:
                return "minimal"

            def fetch_task(self, task_id: str) -> TaskInfo:
                return TaskInfo(
                    id=task_id,
                    identifier=task_id,
                    title="Test Task",
                )

            def update_status(
                self,
                task_id: str,
                status: str,
                metadata: dict[str, Any] | None = None,
            ) -> None:
                pass

            def resolve_task_id(self, input_str: str) -> str | None:
                return None

        # This should type-check as TaskManager
        manager: TaskManager = MinimalTaskManager()
        assert isinstance(manager, TaskManager)
        assert manager.name == "minimal"
