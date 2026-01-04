"""Unit tests for SecurityInterceptor."""

import pytest

from adw.models.security import BlockedPattern, SecurityConfig, SecuritySeverity
from adw.security import SecurityCheckResult, SecurityInterceptor


class TestSecurityInterceptor:
    """Tests for SecurityInterceptor class."""

    def test_allow_safe_bash_command(self) -> None:
        """Test that safe bash commands are allowed."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Bash", {"command": "ls -la"})
        assert response.result == SecurityCheckResult.ALLOWED

    def test_block_rm_rf(self) -> None:
        """Test that rm -rf is blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Bash", {"command": "rm -rf /"})
        assert response.result == SecurityCheckResult.BLOCKED
        assert response.blocked_pattern is not None
        assert "rm" in response.blocked_pattern.lower() or "rm" in response.description.lower()

    def test_block_rm_rf_home(self) -> None:
        """Test that rm -rf ~ is blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Bash", {"command": "rm -rf ~"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_block_chmod_777(self) -> None:
        """Test that chmod 777 is blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Bash", {"command": "chmod 777 /etc/passwd"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_block_git_push_force(self) -> None:
        """Test that git push --force is blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Bash", {"command": "git push --force origin main"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_block_git_push_f(self) -> None:
        """Test that git push -f is blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Bash", {"command": "git push -f origin main"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_allow_regular_git_push(self) -> None:
        """Test that regular git push is allowed."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Bash", {"command": "git push origin main"})
        assert response.result == SecurityCheckResult.ALLOWED


class TestFileAccessBlocking:
    """Tests for file access blocking."""

    def test_block_env_file(self) -> None:
        """Test that .env file access is blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Read", {"file_path": ".env"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_block_adw_env_file(self) -> None:
        """Test that .adw.env file access is blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Read", {"file_path": ".adw.env"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_allow_env_example(self) -> None:
        """Test that .env.example is allowed."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Read", {"file_path": ".env.example"})
        assert response.result == SecurityCheckResult.ALLOWED

    def test_allow_env_sample(self) -> None:
        """Test that .env.sample is allowed."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Read", {"file_path": ".env.sample"})
        assert response.result == SecurityCheckResult.ALLOWED

    def test_allow_env_template(self) -> None:
        """Test that .env.template is allowed."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Read", {"file_path": ".env.template"})
        assert response.result == SecurityCheckResult.ALLOWED

    def test_block_pem_file(self) -> None:
        """Test that .pem files are blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Read", {"file_path": "server.pem"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_block_ssh_key(self) -> None:
        """Test that SSH keys are blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Read", {"file_path": "~/.ssh/id_rsa"})
        assert response.result == SecurityCheckResult.BLOCKED


class TestAllowDangerous:
    """Tests for allow_dangerous mode."""

    def test_warning_instead_of_block(self) -> None:
        """Test that allow_dangerous issues warnings instead of blocking."""
        interceptor = SecurityInterceptor(allow_dangerous=True)
        response = interceptor.check_tool_call("Bash", {"command": "rm -rf /"})
        assert response.result == SecurityCheckResult.WARNING
        assert response.blocked_pattern is not None

    def test_warning_from_config(self) -> None:
        """Test that allow_dangerous can come from config."""
        config = SecurityConfig(allow_dangerous=True)
        interceptor = SecurityInterceptor(config=config)
        response = interceptor.check_tool_call("Bash", {"command": "rm -rf /"})
        assert response.result == SecurityCheckResult.WARNING


class TestCustomPatterns:
    """Tests for custom pattern configuration."""

    def test_custom_pattern_blocks(self) -> None:
        """Test that custom patterns are applied."""
        config = SecurityConfig(
            blocked_patterns=[
                BlockedPattern(
                    pattern=r"my-secret-command",
                    description="Custom blocked command",
                    severity=SecuritySeverity.HIGH,
                )
            ]
        )
        interceptor = SecurityInterceptor(config=config)
        response = interceptor.check_tool_call("Bash", {"command": "my-secret-command --arg"})
        assert response.result == SecurityCheckResult.BLOCKED
        assert response.description == "Custom blocked command"

    def test_invalid_regex_pattern_skipped(self) -> None:
        """Test that invalid regex patterns are skipped with warning."""
        config = SecurityConfig(
            blocked_patterns=[
                BlockedPattern(
                    pattern=r"[invalid(regex",  # Invalid regex
                    description="This should be skipped",
                    severity=SecuritySeverity.HIGH,
                ),
                BlockedPattern(
                    pattern=r"valid-pattern",
                    description="This should work",
                    severity=SecuritySeverity.HIGH,
                ),
            ]
        )
        # Should not raise, invalid pattern is skipped
        interceptor = SecurityInterceptor(config=config)
        # Valid pattern should still work
        response = interceptor.check_tool_call("Bash", {"command": "valid-pattern"})
        assert response.result == SecurityCheckResult.BLOCKED
        assert response.description == "This should work"

    def test_custom_pattern_on_non_shell_tool(self) -> None:
        """Test custom patterns are checked against all tool arguments."""
        config = SecurityConfig(
            blocked_patterns=[
                BlockedPattern(
                    pattern=r"secret-value",
                    description="Contains secret",
                    severity=SecuritySeverity.HIGH,
                )
            ]
        )
        interceptor = SecurityInterceptor(config=config)
        # Custom patterns check all string arguments for unknown tools
        response = interceptor.check_tool_call("CustomTool", {"data": "secret-value-here"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_is_blocked_convenience_method(self) -> None:
        """Test the is_blocked convenience method."""
        interceptor = SecurityInterceptor()

        is_blocked, pattern = interceptor.is_blocked("rm -rf /")
        assert is_blocked is True
        assert pattern is not None

        is_blocked, pattern = interceptor.is_blocked("ls -la")
        assert is_blocked is False
        assert pattern is None


class TestCaseInsensitiveToolNames:
    """Tests for case-insensitive tool name matching."""

    def test_bash_lowercase(self) -> None:
        """Test bash (lowercase) is handled."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("bash", {"command": "rm -rf /"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_bash_mixedcase(self) -> None:
        """Test BASH (uppercase) is handled."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("BASH", {"command": "rm -rf /"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_read_lowercase(self) -> None:
        """Test read (lowercase) is handled."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("read", {"file_path": ".env"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_write_uppercase(self) -> None:
        """Test WRITE (uppercase) is handled."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("WRITE", {"file_path": ".env"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_edit_mixedcase(self) -> None:
        """Test Edit (mixed case) is handled."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("eDiT", {"file_path": ".env"})
        assert response.result == SecurityCheckResult.BLOCKED
