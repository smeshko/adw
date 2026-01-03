"""Unit tests for security patterns."""

import pytest

from adw.security.patterns import (
    is_allowed_env_file,
    match_file_pattern,
    match_shell_pattern,
)


class TestShellPatterns:
    """Tests for shell command pattern matching."""

    def test_match_rm_rf_root(self) -> None:
        """Test matching rm -rf /."""
        result = match_shell_pattern("rm -rf /")
        assert result is not None
        pattern, description = result
        assert "rm" in pattern.lower()

    def test_match_rm_rf_home(self) -> None:
        """Test matching rm -rf ~."""
        result = match_shell_pattern("rm -rf ~")
        assert result is not None

    def test_match_rm_rf_current(self) -> None:
        """Test matching rm -rf ."""
        result = match_shell_pattern("rm -rf .")
        assert result is not None

    def test_no_match_safe_rm(self) -> None:
        """Test that rm without -rf is allowed."""
        result = match_shell_pattern("rm file.txt")
        assert result is None

    def test_match_chmod_777(self) -> None:
        """Test matching chmod 777."""
        result = match_shell_pattern("chmod 777 /var/www")
        assert result is not None

    def test_no_match_chmod_755(self) -> None:
        """Test that chmod 755 is allowed."""
        result = match_shell_pattern("chmod 755 script.sh")
        assert result is None

    def test_match_git_push_force(self) -> None:
        """Test matching git push --force."""
        result = match_shell_pattern("git push --force origin main")
        assert result is not None

    def test_match_git_push_f(self) -> None:
        """Test matching git push -f."""
        result = match_shell_pattern("git push -f origin main")
        assert result is not None


class TestFilePatterns:
    """Tests for file path pattern matching."""

    def test_match_env_file(self) -> None:
        """Test matching .env file."""
        result = match_file_pattern(".env")
        assert result is not None
        pattern, description = result
        assert "env" in pattern.lower()

    def test_match_adw_env_file(self) -> None:
        """Test matching .adw.env file."""
        result = match_file_pattern(".adw.env")
        assert result is not None

    def test_match_env_in_path(self) -> None:
        """Test matching .env in subdirectory."""
        result = match_file_pattern("config/.env")
        assert result is not None

    def test_no_match_env_example(self) -> None:
        """Test that .env.example is not matched."""
        result = match_file_pattern(".env.example")
        assert result is None

    def test_no_match_env_sample(self) -> None:
        """Test that .env.sample is not matched."""
        result = match_file_pattern(".env.sample")
        assert result is None

    def test_match_pem_file(self) -> None:
        """Test matching .pem file."""
        result = match_file_pattern("server.pem")
        assert result is not None

    def test_match_key_file(self) -> None:
        """Test matching .key file."""
        result = match_file_pattern("private.key")
        assert result is not None

    def test_match_ssh_key(self) -> None:
        """Test matching SSH key."""
        result = match_file_pattern("/home/user/.ssh/id_rsa")
        assert result is not None


class TestAllowedEnvFiles:
    """Tests for allowed env file checking."""

    def test_env_example_allowed(self) -> None:
        """Test that .env.example is allowed."""
        assert is_allowed_env_file(".env.example") is True

    def test_env_sample_allowed(self) -> None:
        """Test that .env.sample is allowed."""
        assert is_allowed_env_file(".env.sample") is True

    def test_env_template_allowed(self) -> None:
        """Test that .env.template is allowed."""
        assert is_allowed_env_file(".env.template") is True

    def test_env_not_allowed(self) -> None:
        """Test that .env is not allowed."""
        assert is_allowed_env_file(".env") is False

    def test_regular_file_not_allowed(self) -> None:
        """Test that regular files are not in allowed list."""
        assert is_allowed_env_file("config.yaml") is False
