"""Unit tests for SecurityInterceptor."""

import pytest

from adw.exceptions import SecurityError
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
        response = interceptor.check_tool_call(
            "Bash", {"command": "git push --force origin main"}
        )
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

    def test_block_pem_file(self) -> None:
        """Test that .pem files are blocked."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("Read", {"file_path": "server.pem"})
        assert response.result == SecurityCheckResult.BLOCKED


class TestAllowDangerous:
    """Tests for allow_dangerous mode."""

    def test_warning_instead_of_block(self) -> None:
        """Test that allow_dangerous issues warnings instead of blocking."""
        interceptor = SecurityInterceptor(allow_dangerous=True)
        response = interceptor.check_tool_call("Bash", {"command": "rm -rf /"})
        assert response.result == SecurityCheckResult.WARNING
        assert response.blocked_pattern is not None


class TestCaseInsensitiveToolNames:
    """Tests for case-insensitive tool name matching."""

    def test_bash_lowercase(self) -> None:
        """Test bash (lowercase) is handled."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("bash", {"command": "rm -rf /"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_bash_uppercase(self) -> None:
        """Test BASH (uppercase) is handled."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("BASH", {"command": "rm -rf /"})
        assert response.result == SecurityCheckResult.BLOCKED

    def test_read_lowercase(self) -> None:
        """Test read (lowercase) is handled."""
        interceptor = SecurityInterceptor()
        response = interceptor.check_tool_call("read", {"file_path": ".env"})
        assert response.result == SecurityCheckResult.BLOCKED


class TestValidateAndRaise:
    """Tests for validate_and_raise method."""

    def test_raises_security_error_when_blocked(self) -> None:
        """Test that validate_and_raise raises SecurityError."""
        interceptor = SecurityInterceptor(allow_dangerous=False)

        with pytest.raises(SecurityError) as exc_info:
            interceptor.validate_and_raise("Bash", {"command": "rm -rf /"})

        assert exc_info.value.code == "DANGEROUS_COMMAND_BLOCKED"
        assert exc_info.value.tool_name == "Bash"

    def test_does_not_raise_with_allow_dangerous(self) -> None:
        """Test that validate_and_raise doesn't raise with allow_dangerous."""
        interceptor = SecurityInterceptor(allow_dangerous=True)
        # Should not raise
        interceptor.validate_and_raise("Bash", {"command": "rm -rf /"})

    def test_does_not_raise_for_safe_command(self) -> None:
        """Test that validate_and_raise doesn't raise for safe commands."""
        interceptor = SecurityInterceptor(allow_dangerous=False)
        # Should not raise
        interceptor.validate_and_raise("Bash", {"command": "ls -la"})
