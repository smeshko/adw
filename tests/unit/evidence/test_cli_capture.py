"""Tests for CLI evidence capture functionality.

Tests the CLICaptureStrategy class that executes commands and captures output.
"""

import subprocess
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from adw.evidence.cli_capture import CLICaptureStrategy
from adw.models.evidence import CommandConfig, CommandResult


class TestCLICaptureStrategy:
    """Tests for CLICaptureStrategy class."""

    def test_init_default(self) -> None:
        """CLICaptureStrategy should initialize with default shell."""
        strategy = CLICaptureStrategy()
        assert strategy.shell == "/bin/bash"

    def test_init_custom_shell(self) -> None:
        """CLICaptureStrategy should accept custom shell."""
        strategy = CLICaptureStrategy(shell="/bin/sh")
        assert strategy.shell == "/bin/sh"


class TestExecuteCommand:
    """Tests for execute_command method."""

    @patch("subprocess.run")
    def test_execute_successful_command(self, mock_run: MagicMock) -> None:
        """execute_command should capture successful command output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="adw version 1.0.0\n",
            stderr="",
        )

        strategy = CLICaptureStrategy()
        result = strategy.execute_command("adw --version", timeout=30)

        assert isinstance(result, CommandResult)
        assert result.command == "adw --version"
        assert result.exit_code == 0
        assert result.stdout == "adw version 1.0.0\n"
        assert result.stderr == ""
        assert result.success is True
        assert result.duration_seconds >= 0

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["shell"] is True
        assert call_kwargs["capture_output"] is True
        assert call_kwargs["text"] is True
        assert call_kwargs["timeout"] == 30

    @patch("subprocess.run")
    def test_execute_failed_command(self, mock_run: MagicMock) -> None:
        """execute_command should capture failed command output."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: command failed\n",
        )

        strategy = CLICaptureStrategy()
        result = strategy.execute_command("false", timeout=30)

        assert result.exit_code == 1
        assert result.stderr == "Error: command failed\n"
        assert result.success is False

    @patch("subprocess.run")
    def test_execute_command_with_stdout_and_stderr(
        self, mock_run: MagicMock
    ) -> None:
        """execute_command should capture both stdout and stderr."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output line 1\noutput line 2\n",
            stderr="warning: something\n",
        )

        strategy = CLICaptureStrategy()
        result = strategy.execute_command("some-cmd", timeout=30)

        assert result.stdout == "output line 1\noutput line 2\n"
        assert result.stderr == "warning: something\n"
        assert result.success is True

    @patch("subprocess.run")
    def test_execute_command_timeout(self, mock_run: MagicMock) -> None:
        """execute_command should handle timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 100", timeout=5)

        strategy = CLICaptureStrategy()
        result = strategy.execute_command("sleep 100", timeout=5)

        assert result.exit_code == -1
        assert result.success is False
        assert "timed out" in result.stderr.lower()
        assert result.duration_seconds >= 0

    @patch("subprocess.run")
    def test_execute_command_duration_tracked(self, mock_run: MagicMock) -> None:
        """execute_command should track duration."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ok",
            stderr="",
        )

        strategy = CLICaptureStrategy()
        result = strategy.execute_command("echo ok", timeout=30)

        # Duration should be a small positive number
        assert result.duration_seconds >= 0
        assert result.duration_seconds < 5  # Should be very fast for mocked call

    @patch("subprocess.run")
    def test_execute_command_executed_at_set(self, mock_run: MagicMock) -> None:
        """execute_command should set executed_at timestamp."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ok",
            stderr="",
        )

        before = datetime.now(timezone.utc)
        strategy = CLICaptureStrategy()
        result = strategy.execute_command("echo ok", timeout=30)
        after = datetime.now(timezone.utc)

        assert before <= result.executed_at <= after

    @patch("subprocess.run")
    def test_execute_command_nonzero_exit(self, mock_run: MagicMock) -> None:
        """execute_command should handle various non-zero exit codes."""
        for exit_code in [1, 2, 127, 255]:
            mock_run.return_value = MagicMock(
                returncode=exit_code,
                stdout="",
                stderr=f"exit {exit_code}",
            )

            strategy = CLICaptureStrategy()
            result = strategy.execute_command("failing-cmd", timeout=30)

            assert result.exit_code == exit_code
            assert result.success is False


class TestExecuteCommandConfig:
    """Tests for execute_command_config method."""

    @patch("subprocess.run")
    def test_execute_from_config(self, mock_run: MagicMock) -> None:
        """execute_command_config should use config values."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="version info",
            stderr="",
        )

        config = CommandConfig(name="version", cmd="adw --version", timeout=60)
        strategy = CLICaptureStrategy()
        result = strategy.execute_command_config(config)

        assert result.command == "adw --version"
        assert result.success is True

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["timeout"] == 60

    @patch("subprocess.run")
    def test_execute_from_config_uses_config_timeout(
        self, mock_run: MagicMock
    ) -> None:
        """execute_command_config should use timeout from config."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ok",
            stderr="",
        )

        config = CommandConfig(name="slow", cmd="sleep 1", timeout=120)
        strategy = CLICaptureStrategy()
        strategy.execute_command_config(config)

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["timeout"] == 120
