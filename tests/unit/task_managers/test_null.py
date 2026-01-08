"""Tests for NullTaskManager implementation.

Per ADR-001: Tests focus on behavior, not mock verification.
"""

import pytest

from adw.exceptions import TaskError
from adw.task_managers.base import TaskManager
from adw.task_managers.null import NullTaskManager


class TestNullTaskManager:
    """Tests for NullTaskManager."""

    def test_implements_protocol(self) -> None:
        """NullTaskManager satisfies TaskManager protocol."""
        manager = NullTaskManager()
        assert isinstance(manager, TaskManager)

    def test_name_returns_none(self) -> None:
        """name property returns 'none'."""
        manager = NullTaskManager()
        assert manager.name == "none"

    def test_fetch_task_raises_error(self) -> None:
        """fetch_task raises TaskError with NO_TASK_MANAGER code."""
        manager = NullTaskManager()
        with pytest.raises(TaskError) as exc_info:
            manager.fetch_task("RULE-123")

        assert exc_info.value.code == "NO_TASK_MANAGER"
        assert "RULE-123" in exc_info.value.message
        assert exc_info.value.task_id == "RULE-123"

    def test_update_status_no_op(self) -> None:
        """update_status does nothing and doesn't raise."""
        manager = NullTaskManager()
        # Should not raise - this is a no-op
        manager.update_status("RULE-123", "In Progress")
        manager.update_status("RULE-456", "Done", {"key": "value"})

    def test_resolve_task_id_returns_none(self) -> None:
        """resolve_task_id always returns None."""
        manager = NullTaskManager()
        assert manager.resolve_task_id("RULE-123") is None
        assert manager.resolve_task_id("feature/RULE-123-add-auth") is None
        assert manager.resolve_task_id("anything") is None
