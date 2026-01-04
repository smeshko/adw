"""Tests for SecurityError exception.

Verifies SecurityError includes all required fields for rich error
context including alternatives, override instructions, and severity.
"""


from adw.exceptions import ADWError


class TestSecurityError:
    """Tests for SecurityError exception."""

    def test_security_error_exists(self) -> None:
        """Test SecurityError can be imported."""
        from adw.exceptions import SecurityError

        assert issubclass(SecurityError, ADWError)

    def test_create_basic_security_error(self) -> None:
        """Test creating a basic SecurityError."""
        from adw.exceptions import SecurityError

        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Command blocked for safety",
            pattern_matched=r"rm\s+-rf",
            tool_name="Bash",
        )
        assert error.code == "DANGEROUS_COMMAND_BLOCKED"
        assert error.message == "Command blocked for safety"
        assert error.pattern_matched == r"rm\s+-rf"
        assert error.tool_name == "Bash"

    def test_security_error_with_alternatives(self) -> None:
        """Test SecurityError includes alternatives field."""
        from adw.exceptions import SecurityError

        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Command blocked",
            pattern_matched=r"rm\s+-rf",
            tool_name="Bash",
            alternatives=["Use specific paths", "Use trash command"],
        )
        assert error.alternatives == ["Use specific paths", "Use trash command"]

    def test_security_error_with_override_instruction(self) -> None:
        """Test SecurityError includes override_instruction field."""
        from adw.exceptions import SecurityError

        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Command blocked",
            pattern_matched=r"rm\s+-rf",
            tool_name="Bash",
            override_instruction="Use --allow-dangerous flag",
        )
        assert error.override_instruction == "Use --allow-dangerous flag"

    def test_security_error_with_severity(self) -> None:
        """Test SecurityError includes severity field."""
        from adw.exceptions import SecurityError

        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Command blocked",
            pattern_matched=r"rm\s+-rf",
            tool_name="Bash",
            severity="critical",
        )
        assert error.severity == "critical"

    def test_security_error_defaults(self) -> None:
        """Test SecurityError default values."""
        from adw.exceptions import SecurityError

        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Command blocked",
            pattern_matched=r"rm\s+-rf",
            tool_name="Bash",
        )
        # Check defaults
        assert error.alternatives == []
        assert error.override_instruction is None
        assert error.severity == "warning"
        assert error.recoverable is False

    def test_security_error_to_dict(self) -> None:
        """Test SecurityError serialization."""
        from adw.exceptions import SecurityError

        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Command blocked",
            pattern_matched=r"rm\s+-rf",
            tool_name="Bash",
            alternatives=["Use specific paths"],
            override_instruction="Use --allow-dangerous",
            severity="critical",
        )
        d = error.to_dict()

        assert d["code"] == "DANGEROUS_COMMAND_BLOCKED"
        assert d["pattern_matched"] == r"rm\s+-rf"
        assert d["tool_name"] == "Bash"
        assert d["alternatives"] == ["Use specific paths"]
        assert d["override_instruction"] == "Use --allow-dangerous"
        assert d["severity"] == "critical"

    def test_security_error_str_includes_alternatives(self) -> None:
        """Test SecurityError string representation includes alternatives."""
        from adw.exceptions import SecurityError

        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Command blocked",
            pattern_matched=r"rm\s+-rf",
            tool_name="Bash",
            alternatives=["Use specific paths"],
        )
        error_str = str(error)

        assert "DANGEROUS_COMMAND_BLOCKED" in error_str
        assert "Command blocked" in error_str

    def test_security_error_inherits_suggestion(self) -> None:
        """Test SecurityError inherits suggestion from ADWError."""
        from adw.exceptions import SecurityError

        error = SecurityError(
            code="DANGEROUS_COMMAND_BLOCKED",
            message="Command blocked",
            pattern_matched=r"rm\s+-rf",
            tool_name="Bash",
            suggestion="Consider using a safer alternative",
        )
        assert error.suggestion == "Consider using a safer alternative"
