"""Unit tests for ReviewValidator implementation.

Tests for the validator that uses LLM to perform code review
and converts findings to ValidationIssues.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from adw.models import RunContext
from adw.models.llm import LLMResult
from adw.validation.config import ValidationConfig
from adw.validation.models import IssueSeverity, ValidationIssue, ValidationSource
from adw.validation.validators.review_validator import ReviewValidator


@pytest.fixture
def mock_context() -> RunContext:
    """Create a mock RunContext for testing."""
    return RunContext(
        run_id="01HQ0000000000000000000000",
        feature_description="Test feature",
        current_phase="validation",
        phase_history=["plan", "build"],
        started_at=datetime.now(UTC),
        completed_at=None,
        status="running",
        artifacts={
            "build": ["build_output.md"],
        },
        phase_tokens={},
        worktree_path=None,
        use_worktree=False,
        branch_name=None,
    )


@pytest.fixture
def mock_executor() -> MagicMock:
    """Create a mock LLM executor."""
    return MagicMock()


class TestReviewValidator:
    """Test cases for ReviewValidator class."""

    def test_validate_no_issues(
        self, mock_context: RunContext, mock_executor: MagicMock
    ) -> None:
        """Returns empty list when review finds no issues."""
        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="## Code Review\n\nNo issues found. The code looks good!",
            tool_calls=[],
            tokens_used=100,
        )
        validator = ReviewValidator(executor=mock_executor)

        issues = validator.validate(mock_context)

        assert issues == []
        mock_executor.execute.assert_called_once()

    def test_validate_finds_issues(
        self, mock_context: RunContext, mock_executor: MagicMock
    ) -> None:
        """Parses LLM response and returns issues for findings."""
        review_response = """## Code Review

### Issues Found

**[HIGH] Missing error handling in auth.py:42**
The login function doesn't handle invalid credentials properly.

**[MEDIUM] Security: SQL injection risk in users.py:25**
User input is not sanitized before database query.

**[LOW] Code style: Inconsistent naming in utils.py**
Variable names don't follow project conventions.
"""
        mock_executor.execute.return_value = LLMResult(
            success=True,
            content=review_response,
            tool_calls=[],
            tokens_used=200,
        )
        validator = ReviewValidator(executor=mock_executor)

        issues = validator.validate(mock_context)

        assert len(issues) >= 2  # At least HIGH and MEDIUM issues
        assert all(i.source == ValidationSource.REVIEW for i in issues)
        severities = [i.severity for i in issues]
        # high maps to ERROR, medium maps to WARNING
        assert IssueSeverity.ERROR in severities or IssueSeverity.WARNING in severities

    def test_validate_with_custom_focus_areas(
        self, mock_context: RunContext, mock_executor: MagicMock
    ) -> None:
        """Uses custom focus areas in review prompt."""
        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="No issues found.",
            tool_calls=[],
            tokens_used=100,
        )
        config = ValidationConfig(
            review_focus=["performance", "memory_usage", "concurrency"]
        )
        validator = ReviewValidator(executor=mock_executor, config=config)

        validator.validate(mock_context)

        # Check that the prompt includes focus areas
        call_args = mock_executor.execute.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "performance" in prompt.lower() or mock_executor.execute.called

    def test_validate_llm_error_handling(
        self, mock_context: RunContext, mock_executor: MagicMock
    ) -> None:
        """Returns error issue when LLM execution fails."""
        mock_executor.execute.side_effect = RuntimeError("LLM unavailable")
        validator = ReviewValidator(executor=mock_executor)

        issues = validator.validate(mock_context)

        assert len(issues) == 1
        assert issues[0].source == ValidationSource.REVIEW
        assert "error" in issues[0].message.lower() or "failed" in issues[0].message.lower()
        # critical and high map to ERROR
        assert issues[0].severity == IssueSeverity.ERROR

    def test_name_property(self, mock_executor: MagicMock) -> None:
        """ReviewValidator returns correct name."""
        validator = ReviewValidator(executor=mock_executor)
        assert validator.name == "review"

    def test_validate_without_executor(self, mock_context: RunContext) -> None:
        """Returns error when no executor is provided."""
        validator = ReviewValidator(executor=None)

        issues = validator.validate(mock_context)

        assert len(issues) == 1
        assert issues[0].source == ValidationSource.REVIEW
        assert issues[0].severity == IssueSeverity.ERROR  # critical maps to ERROR
