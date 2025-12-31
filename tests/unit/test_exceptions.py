"""Unit tests for ADW exception hierarchy."""

import pytest

from adw.exceptions import ADWError, ConfigError, HookError


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


class TestConfigError:
    """Tests for ConfigError exception."""

    def test_config_error_is_adw_error(self) -> None:
        """ConfigError inherits from ADWError."""
        error = ConfigError(
            code="CONFIG_NOT_FOUND",
            message="Config file not found",
        )
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_config_error_not_recoverable_by_default(self) -> None:
        """ConfigError is not recoverable by default."""
        error = ConfigError(
            code="CONFIG_NOT_FOUND",
            message="Config file not found",
        )
        assert error.recoverable is False

    def test_config_error_with_suggestion(self) -> None:
        """ConfigError accepts suggestion."""
        error = ConfigError(
            code="CONFIG_NOT_FOUND",
            message="Config file not found",
            suggestion="Create an adw.yaml file",
        )
        assert error.suggestion == "Create an adw.yaml file"
        assert "Suggestion:" in str(error)

    def test_config_error_common_codes(self) -> None:
        """ConfigError works with common error codes."""
        codes = ["CONFIG_NOT_FOUND", "INVALID_CONFIG", "COMMAND_NOT_FOUND"]
        for code in codes:
            error = ConfigError(code=code, message=f"Error with {code}")
            assert error.code == code

    def test_config_error_to_dict(self) -> None:
        """ConfigError serializes properly."""
        error = ConfigError(
            code="INVALID_CONFIG",
            message="Invalid configuration",
            suggestion="Check your adw.yaml",
        )
        d = error.to_dict()
        assert d["code"] == "INVALID_CONFIG"
        assert d["recoverable"] is False


class TestHookError:
    """Tests for HookError exception."""

    def test_hook_error_is_adw_error(self) -> None:
        """HookError inherits from ADWError."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_hook_error_has_phase_field(self) -> None:
        """HookError includes phase field."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert error.phase == "build"

    def test_hook_error_has_exit_code(self) -> None:
        """HookError includes exit_code field."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
            exit_code=1,
        )
        assert error.exit_code == 1

    def test_hook_error_exit_code_default_none(self) -> None:
        """HookError exit_code defaults to None."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert error.exit_code is None

    def test_hook_error_has_stdout_stderr(self) -> None:
        """HookError includes stdout and stderr fields."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
            stdout="output text",
            stderr="error text",
        )
        assert error.stdout == "output text"
        assert error.stderr == "error text"

    def test_hook_error_stdout_stderr_defaults(self) -> None:
        """HookError stdout and stderr default to empty string."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert error.stdout == ""
        assert error.stderr == ""

    def test_hook_error_not_recoverable_by_default(self) -> None:
        """HookError is not recoverable by default."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert error.recoverable is False

    def test_hook_error_common_codes(self) -> None:
        """HookError works with common error codes."""
        codes = ["HOOK_FAILED", "HOOK_TIMEOUT"]
        for code in codes:
            error = HookError(code=code, message=f"Error with {code}", phase="test")
            assert error.code == code

    def test_hook_error_to_dict_includes_extra_fields(self) -> None:
        """HookError to_dict includes phase, exit_code, stdout, stderr."""
        error = HookError(
            code="HOOK_FAILED",
            message="Failed",
            phase="build",
            exit_code=1,
            stdout="out",
            stderr="err",
        )
        d = error.to_dict()
        assert d["phase"] == "build"
        assert d["exit_code"] == 1
        assert d["stdout"] == "out"
        assert d["stderr"] == "err"
