"""Tests for TaskManager Protocol definition.

Per ADR-001: Tests focus on Protocol compliance and required methods.
"""

from typing import Any

from adw.task_managers.base import TaskManager


class TestTaskManagerProtocol:
    """Tests for TaskManager Protocol."""

    def test_protocol_defines_required_methods(self) -> None:
        """Protocol requires fetch_task, update_status, resolve_task_id, close_task, is_pr_merged, add_label, remove_label."""
        # Check Protocol has the required methods
        assert hasattr(TaskManager, "fetch_task")
        assert hasattr(TaskManager, "update_status")
        assert hasattr(TaskManager, "resolve_task_id")
        assert hasattr(TaskManager, "close_task")
        assert hasattr(TaskManager, "is_pr_merged")
        assert hasattr(TaskManager, "add_label")
        assert hasattr(TaskManager, "remove_label")

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

            def close_task(self, task_id: str) -> None:
                pass

            def is_pr_merged(self, pr_url: str) -> bool:
                return False

            def add_label(self, task_id: str, label: str) -> None:
                pass

            def remove_label(self, task_id: str, label: str) -> None:
                pass

            def post_comment(self, task_id: str, body: str) -> None:
                pass

        # This should type-check as TaskManager
        manager: TaskManager = MinimalTaskManager()
        assert isinstance(manager, TaskManager)
        assert manager.name == "minimal"
