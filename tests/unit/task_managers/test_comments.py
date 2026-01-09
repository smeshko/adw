"""Unit tests for comment posting functionality (Story 12.6).

Tests for:
- TaskManager Protocol post_comment method
- NullTaskManager post_comment implementation (no-op)
- LinearTaskManager post_comment implementation
- CommentFormatter for formatting comments
"""

from unittest.mock import MagicMock, patch

import pytest

from adw.models.config import TaskManagerConfig
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


class TestLinearTaskManagerPostComment:
    """Tests for LinearTaskManager.post_comment."""

    @pytest.fixture
    def linear_manager(self, monkeypatch: pytest.MonkeyPatch) -> "LinearTaskManager":
        """Create LinearTaskManager with mocked environment."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test123")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid-123")

        from adw.task_managers.linear import LinearTaskManager

        config = TaskManagerConfig(type="linear", team_key="RULE")
        return LinearTaskManager(config)

    def test_post_comment_calls_client(
        self, linear_manager: "LinearTaskManager"
    ) -> None:
        """post_comment should call LinearClient.post_comment."""
        linear_manager._client.post_comment = MagicMock(return_value=True)

        linear_manager.post_comment("issue-uuid-123", "Test comment")

        linear_manager._client.post_comment.assert_called_once_with(
            "issue-uuid-123", "Test comment"
        )

    def test_post_comment_handles_api_error_gracefully(
        self, linear_manager: "LinearTaskManager"
    ) -> None:
        """post_comment should log warning but not raise on API error."""
        linear_manager._client.post_comment = MagicMock(
            side_effect=Exception("API Error")
        )

        # Should not raise
        linear_manager.post_comment("issue-uuid-123", "Test comment")

    def test_post_comment_with_markdown_body(
        self, linear_manager: "LinearTaskManager"
    ) -> None:
        """post_comment should support markdown in body."""
        linear_manager._client.post_comment = MagicMock(return_value=True)

        markdown_body = """**Phase Complete** ✓

Duration: 45.2s
Artifacts: 3
"""
        linear_manager.post_comment("issue-uuid-123", markdown_body)

        linear_manager._client.post_comment.assert_called_once_with(
            "issue-uuid-123", markdown_body
        )


class TestLinearClientPostComment:
    """Tests for LinearClient.post_comment."""

    def test_post_comment_sends_graphql_mutation(self) -> None:
        """post_comment should send commentCreate mutation."""
        from adw.task_managers.linear_client import LinearClient

        with patch.object(LinearClient, "_request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {"commentCreate": {"success": True, "comment": {"id": "c123"}}}
            }
            mock_request.return_value = mock_response

            client = LinearClient(api_key="test-api-key")
            result = client.post_comment("issue-uuid-123", "Test comment")

            assert result is True
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "commentCreate" in call_args[0][0]
            assert call_args[1]["variables"]["issueId"] == "issue-uuid-123"
            assert call_args[1]["variables"]["body"] == "Test comment"

    def test_post_comment_returns_false_on_failure(self) -> None:
        """post_comment should return False when mutation fails."""
        from adw.task_managers.linear_client import LinearClient

        with patch.object(LinearClient, "_request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {"commentCreate": {"success": False}}
            }
            mock_request.return_value = mock_response

            client = LinearClient(api_key="test-api-key")
            result = client.post_comment("issue-uuid-123", "Test comment")

            assert result is False
