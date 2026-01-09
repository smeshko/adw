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


class TestCommentFormatter:
    """Tests for CommentFormatter."""

    def test_format_phase_complete_returns_markdown(self) -> None:
        """format_phase_complete should return markdown string."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_phase_complete(
            phase="plan", duration=45.2, artifacts=3
        )

        assert "plan" in result.lower()
        assert "45.2" in result or "45.20" in result
        assert "3" in result
        # Should be markdown
        assert "**" in result or "#" in result

    def test_format_phase_complete_shows_duration_formatted(self) -> None:
        """format_phase_complete should format duration nicely."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_phase_complete(
            phase="build", duration=125.7, artifacts=5
        )

        # Duration should be formatted (could be seconds or minutes)
        assert "125" in result or "2m" in result

    def test_format_phase_failed_includes_error(self) -> None:
        """format_phase_failed should include error message."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_phase_failed(
            phase="build",
            error="Build failed: missing dependency",
            run_id="01ABC123",
        )

        assert "build" in result.lower()
        assert "missing dependency" in result.lower() or "Build failed" in result
        assert "01ABC123" in result

    def test_format_run_complete_with_pr_url(self) -> None:
        """format_run_complete should include PR URL when provided."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_run_complete(
            run_id="01ABC123",
            pr_url="https://github.com/org/repo/pull/42",
            summary="All phases completed successfully",
        )

        assert "01ABC123" in result
        assert "https://github.com/org/repo/pull/42" in result
        assert "completed" in result.lower() or "success" in result.lower()

    def test_format_run_complete_without_pr_url(self) -> None:
        """format_run_complete should work without PR URL."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_run_complete(
            run_id="01ABC123",
            pr_url=None,
            summary="Run completed",
        )

        assert "01ABC123" in result
        assert "completed" in result.lower() or "Run" in result
