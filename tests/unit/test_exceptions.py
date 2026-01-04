"""Unit tests for ADW exception hierarchy."""

import pytest

from adw.exceptions import SecurityError


class TestSecurityError:
    """Tests for SecurityError exception."""

    def test_create_security_error(self) -> None:
        """Test creating a security error with all fields."""
        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Tool call blocked: rm -rf / matches dangerous pattern",
            pattern_matched=r"rm\s+-rf",
            tool_name="Bash",
            suggestion="Use --allow-dangerous flag to override",
        )
        assert error.code == "DANGEROUS_COMMAND_BLOCKED"
        assert "rm -rf" in error.message
        assert error.pattern_matched == r"rm\s+-rf"
        assert error.tool_name == "Bash"
        assert error.suggestion is not None
        assert error.recoverable is False

    def test_security_error_minimal(self) -> None:
        """Test creating a security error with minimal fields."""
        error = SecurityError(
            code="SECURITY_POLICY_VIOLATION",
            message="Security policy violated",
        )
        assert error.code == "SECURITY_POLICY_VIOLATION"
        assert error.pattern_matched is None
        assert error.tool_name is None

    def test_security_error_to_dict(self) -> None:
        """Test serializing security error to dict."""
        error = SecurityError(
            code="SENSITIVE_FILE_BLOCKED",
            message="Cannot read .env file",
            pattern_matched=r"^\.env$",
            tool_name="Read",
            suggestion="Use .env.example instead",
        )
        data = error.to_dict()
        assert data["code"] == "SENSITIVE_FILE_BLOCKED"
        assert data["message"] == "Cannot read .env file"
        assert data["pattern_matched"] == r"^\.env$"
        assert data["tool_name"] == "Read"
        assert data["suggestion"] == "Use .env.example instead"
        assert data["recoverable"] is False

    def test_security_error_str_format(self) -> None:
        """Test string formatting of security error."""
        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Command blocked",
            suggestion="Override with --allow-dangerous",
        )
        error_str = str(error)
        assert "[DANGEROUS_COMMAND_BLOCKED]" in error_str
        assert "Command blocked" in error_str
        assert "Override with --allow-dangerous" in error_str

    def test_security_error_is_exception(self) -> None:
        """Test that SecurityError can be raised and caught."""
        with pytest.raises(SecurityError) as exc_info:
            raise SecurityError(
                code="TEST_ERROR",
                message="Test security error",
                tool_name="Test",
            )
        assert exc_info.value.code == "TEST_ERROR"
        assert exc_info.value.tool_name == "Test"
