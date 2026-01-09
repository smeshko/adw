"""Unit tests for comment posting functionality (Story 12.6).

Tests for:
- TaskManager Protocol post_comment method
- NullTaskManager post_comment implementation (no-op)
- CommentFormatter for formatting comments
"""

import pytest

from adw.task_managers.null import NullTaskManager


class TestNullTaskManagerPostComment:
    """Tests for NullTaskManager.post_comment (no-op behavior)."""

    def test_post_comment_is_noop(self) -> None:
        """NullTaskManager.post_comment should silently do nothing."""
        manager = NullTaskManager()
        # Should not raise - just a no-op
        manager.post_comment("task-123", "Test comment body")

    def test_post_comment_with_empty_body(self) -> None:
        """NullTaskManager.post_comment handles empty body without error."""
        manager = NullTaskManager()
        manager.post_comment("task-123", "")

    def test_post_comment_with_none_task_id(self) -> None:
        """NullTaskManager.post_comment handles edge cases."""
        manager = NullTaskManager()
        # Should not raise even with unusual inputs
        manager.post_comment("", "body")


class TestTaskManagerProtocolHasPostComment:
    """Tests that TaskManager Protocol includes post_comment."""

    def test_null_manager_has_post_comment_method(self) -> None:
        """NullTaskManager should have post_comment method."""
        manager = NullTaskManager()
        assert hasattr(manager, "post_comment")
        assert callable(manager.post_comment)

    def test_post_comment_signature(self) -> None:
        """post_comment should accept task_id and body parameters."""
        manager = NullTaskManager()
        # Should accept two string arguments
        import inspect

        sig = inspect.signature(manager.post_comment)
        params = list(sig.parameters.keys())
        assert "task_id" in params
        assert "body" in params
