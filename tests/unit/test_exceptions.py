"""Unit tests for ADW exception hierarchy."""

import pytest

from adw.exceptions import ADWError


class TestADWErrorBase:
    """Tests for ADWError base class."""

    def test_adw_error_required_attributes(self) -> None:
        """ADWError has required attributes."""
        error = ADWError(
            code="TEST_ERROR",
            message="Test message",
            suggestion="Try again",
            recoverable=True,
        )
        assert error.code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.suggestion == "Try again"
        assert error.recoverable is True

    def test_adw_error_default_values(self) -> None:
        """ADWError has sensible defaults."""
        error = ADWError(
            code="TEST_ERROR",
            message="Test message",
        )
        assert error.suggestion is None
        assert error.recoverable is False

    def test_adw_error_str_format_with_suggestion(self) -> None:
        """ADWError formats nicely with suggestion for display."""
        error = ADWError(
            code="TEST_ERROR",
            message="Something failed",
            suggestion="Check logs",
        )
        formatted = str(error)
        assert "[TEST_ERROR]" in formatted
        assert "Something failed" in formatted
        assert "Suggestion: Check logs" in formatted

    def test_adw_error_str_format_without_suggestion(self) -> None:
        """ADWError formats correctly without suggestion."""
        error = ADWError(
            code="TEST_ERROR",
            message="Something failed",
        )
        formatted = str(error)
        assert "[TEST_ERROR]" in formatted
        assert "Something failed" in formatted
        assert "Suggestion:" not in formatted

    def test_adw_error_to_dict(self) -> None:
        """ADWError serializes to dict for structured logging."""
        error = ADWError(
            code="TEST",
            message="Test",
            suggestion="Fix it",
            recoverable=True,
        )
        d = error.to_dict()
        assert d["code"] == "TEST"
        assert d["message"] == "Test"
        assert d["suggestion"] == "Fix it"
        assert d["recoverable"] is True

    def test_adw_error_to_dict_without_suggestion(self) -> None:
        """ADWError to_dict includes None for missing suggestion."""
        error = ADWError(
            code="TEST",
            message="Test",
        )
        d = error.to_dict()
        assert d["suggestion"] is None
        assert d["recoverable"] is False

    def test_adw_error_is_exception(self) -> None:
        """ADWError is a proper Exception subclass."""
        error = ADWError(
            code="TEST_ERROR",
            message="Test message",
        )
        assert isinstance(error, Exception)

    def test_adw_error_can_be_raised(self) -> None:
        """ADWError can be raised and caught."""
        with pytest.raises(ADWError) as exc_info:
            raise ADWError(
                code="RAISED_ERROR",
                message="This was raised",
            )
        assert exc_info.value.code == "RAISED_ERROR"
        assert exc_info.value.message == "This was raised"
