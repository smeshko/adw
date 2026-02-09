"""Unit tests for comment posting functionality (Story 12.6).

Tests for:
- TaskManager Protocol post_comment method
- NullTaskManager post_comment implementation (no-op)
- LinearTaskManager post_comment implementation
- CommentFormatter for formatting comments
"""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from adw.models.config import TaskManagerConfig
from adw.task_managers.null import NullTaskManager

if TYPE_CHECKING:
    from adw.task_managers.linear import LinearTaskManager


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
        assert "45s" in result or "45" in result
        assert "3" in result
        # Should be markdown
        assert "**" in result or "#" in result

    def test_format_phase_complete_shows_duration_formatted(self) -> None:
        """format_phase_complete should format duration as human-friendly."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_phase_complete(
            phase="build", duration=125.7, artifacts=5
        )

        # Duration should be formatted as minutes
        assert "2m 5s" in result

    def test_format_phase_complete_with_enriched_data(self) -> None:
        """format_phase_complete includes artifact names and token metrics."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_phase_complete(
            phase="build",
            duration=60.0,
            artifacts=2,
            artifact_names=["src/main.py", "tests/test_main.py"],
            tokens_used=15000,
            tool_calls_count=42,
        )

        assert "`src/main.py`" in result
        assert "`tests/test_main.py`" in result
        assert "15,000" in result
        assert "42" in result

    def test_format_phase_complete_backward_compatible(self) -> None:
        """format_phase_complete works without new keyword args."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        # Old-style call with only positional args
        result = formatter.format_phase_complete("plan", 30.0, 2)

        assert "plan" in result.lower()
        assert "30s" in result
        assert "2" in result

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

    def test_format_phase_failed_with_enriched_data(self) -> None:
        """format_phase_failed includes timeline, duration, artifacts, branch."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_phase_failed(
            phase="build",
            error="Compilation error",
            run_id="01ABC123",
            duration=138.5,
            phase_sequence=["plan", "build", "validate", "document", "ship"],
            completed_phases=["plan"],
            branch_name="adw/feature-auth",
            artifacts_by_phase={"plan": ["plan.md", "spec.md"]},
        )

        # Timeline
        assert "plan ✓" in result
        assert "build ✗" in result
        assert "validate ⊘" in result
        # Duration
        assert "2m 18s" in result
        # Branch
        assert "`adw/feature-auth`" in result
        # Artifacts before failure
        assert "`plan.md`" in result
        assert "`spec.md`" in result
        # Branch preservation note
        assert "preserved for debugging" in result

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

    def test_format_run_complete_with_enriched_data(self) -> None:
        """format_run_complete includes timeline, duration, tokens, commits, artifacts."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_run_complete(
            run_id="01ABC123",
            pr_url="https://github.com/org/repo/pull/99",
            summary="All phases completed",
            duration=300.0,
            phase_sequence=["plan", "build", "validate", "document", "ship"],
            completed_phases=["plan", "build", "validate", "document", "ship"],
            total_tokens=50000,
            commit_count=5,
            artifacts_by_phase={
                "plan": ["plan.md"],
                "build": ["src/app.py"],
                "document": ["README.md"],
            },
        )

        # Timeline - all completed
        assert "plan ✓" in result
        assert "ship ✓" in result
        # Duration
        assert "5m 0s" in result
        # Tokens
        assert "50,000" in result
        # Commits
        assert "5" in result
        # Artifacts
        assert "`plan.md`" in result
        assert "`src/app.py`" in result
        assert "`README.md`" in result


class TestFormatDuration:
    """Tests for CommentFormatter._format_duration helper."""

    def test_seconds_only(self) -> None:
        """Formats short durations as seconds."""
        from adw.task_managers.comments import CommentFormatter

        assert CommentFormatter._format_duration(28.0) == "28s"

    def test_minutes_and_seconds(self) -> None:
        """Formats longer durations as minutes and seconds."""
        from adw.task_managers.comments import CommentFormatter

        assert CommentFormatter._format_duration(138.0) == "2m 18s"

    def test_zero_seconds(self) -> None:
        """Formats zero duration."""
        from adw.task_managers.comments import CommentFormatter

        assert CommentFormatter._format_duration(0.0) == "0s"

    def test_negative_treated_as_zero(self) -> None:
        """Negative durations are clamped to zero."""
        from adw.task_managers.comments import CommentFormatter

        assert CommentFormatter._format_duration(-5.0) == "0s"

    def test_exact_minute(self) -> None:
        """Exact minute boundary."""
        from adw.task_managers.comments import CommentFormatter

        assert CommentFormatter._format_duration(60.0) == "1m 0s"

    def test_fractional_seconds_truncated(self) -> None:
        """Fractional seconds are truncated."""
        from adw.task_managers.comments import CommentFormatter

        assert CommentFormatter._format_duration(45.9) == "45s"


class TestFormatPhaseTimeline:
    """Tests for CommentFormatter._format_phase_timeline helper."""

    def test_all_completed(self) -> None:
        """All phases completed shows all checkmarks."""
        from adw.task_managers.comments import CommentFormatter

        seq = ["plan", "build", "validate"]
        result = CommentFormatter._format_phase_timeline(seq, seq)
        assert result == "plan ✓ → build ✓ → validate ✓"

    def test_failure_mid_pipeline(self) -> None:
        """Failure in the middle marks failed and skipped."""
        from adw.task_managers.comments import CommentFormatter

        seq = ["plan", "build", "validate", "document", "ship"]
        completed = ["plan"]
        result = CommentFormatter._format_phase_timeline(
            seq, completed, failed_phase="build"
        )
        assert result == "plan ✓ → build ✗ → validate ⊘ → document ⊘ → ship ⊘"

    def test_no_phases_completed(self) -> None:
        """No phases completed, first phase failed."""
        from adw.task_managers.comments import CommentFormatter

        seq = ["plan", "build"]
        result = CommentFormatter._format_phase_timeline(seq, [], failed_phase="plan")
        assert result == "plan ✗ → build ⊘"

    def test_no_failure(self) -> None:
        """Partial completion without failure (e.g., successful run that skipped ship)."""
        from adw.task_managers.comments import CommentFormatter

        seq = ["plan", "build", "validate"]
        completed = ["plan", "build"]
        result = CommentFormatter._format_phase_timeline(seq, completed)
        assert result == "plan ✓ → build ✓ → validate ⊘"


class TestFormatRunStarted:
    """Tests for CommentFormatter.format_run_started."""

    def test_basic_run_started(self) -> None:
        """Basic run started with just run_id."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_run_started("01RUN123")

        assert "▶ ADW Run Started" in result
        assert "`01RUN123`" in result

    def test_run_started_with_all_fields(self) -> None:
        """Run started with all optional fields."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_run_started(
            "01RUN123",
            branch_name="adw/feature-auth",
            phase_sequence=["plan", "build", "validate", "document", "ship"],
            assignee="developer@example.com",
        )

        assert "`01RUN123`" in result
        assert "`adw/feature-auth`" in result
        assert "plan → build → validate → document → ship" in result
        assert "developer@example.com" in result

    def test_run_started_without_optional_fields(self) -> None:
        """Run started omits rows for None fields."""
        from adw.task_managers.comments import CommentFormatter

        formatter = CommentFormatter()
        result = formatter.format_run_started("01RUN123")

        assert "Branch" not in result
        assert "Pipeline" not in result
        assert "Triggered by" not in result
