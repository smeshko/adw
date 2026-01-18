"""Tests for wizard security configuration step.

Tests the regex pattern validation, dangerous operations warning flow,
blocked patterns loops, and interactive prompt flow for security configuration.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from rich.console import Console

from adw.cli.wizard.security import (
    BUILTIN_BLOCKED_COMMANDS,
    BUILTIN_BLOCKED_ENV_FILES,
    SecurityStepHandler,
    run_security_step,
    validate_regex,
)
from adw.models.wizard import WizardState


class TestRegexValidation:
    """Tests for validate_regex function."""

    @pytest.mark.parametrize(
        "pattern,expected_valid",
        [
            (r"rm\s+-rf", True),
            (r"sudo\s+.*", True),
            (r"dd\s+if=.*\s+of=/dev/", True),
            (r"curl.*\|.*sh", True),
            (r"chmod\s+-R\s+777", True),
            (r"^simple$", True),
            (r"[a-z]+", True),
        ],
    )
    def test_valid_regex_patterns(self, pattern: str, expected_valid: bool) -> None:
        """Test validation of valid regex patterns."""
        is_valid, result = validate_regex(pattern)
        assert is_valid == expected_valid
        assert result == pattern

    @pytest.mark.parametrize(
        "pattern,expected_error_contains",
        [
            (r"[invalid", "invalid"),
            (r"*invalid", "invalid"),
            (r"(unclosed", "invalid"),
            (r"(?P<>bad)", "invalid"),
        ],
    )
    def test_invalid_regex_patterns(
        self, pattern: str, expected_error_contains: str
    ) -> None:
        """Test validation of invalid regex patterns."""
        is_valid, result = validate_regex(pattern)
        assert is_valid is False
        assert isinstance(result, str)
        assert expected_error_contains.lower() in result.lower()

    def test_empty_pattern_invalid(self) -> None:
        """Test that empty patterns are rejected."""
        is_valid, result = validate_regex("")
        assert is_valid is False
        assert "empty" in result.lower()

    def test_whitespace_only_pattern_invalid(self) -> None:
        """Test that whitespace-only patterns are rejected."""
        is_valid, result = validate_regex("   ")
        assert is_valid is False
        assert "empty" in result.lower()


class TestRunSecurityStepDefaults:
    """Tests for run_security_step when using defaults."""

    def test_decline_configuration_uses_defaults(self) -> None:
        """Test that declining security configuration uses default values."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.security.Confirm.ask", return_value=False):
            result = run_security_step(state, console)

        assert result["security_custom"] is False
        assert result["security_allow_dangerous"] is False
        assert result["security_blocked_commands"] == []
        assert result["security_blocked_env_files"] == []


class TestRunSecurityStepDangerousOperations:
    """Tests for dangerous operations configuration flow."""

    def test_dangerous_operations_declined(self) -> None:
        """Test when user declines dangerous operations."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.security.Confirm.ask") as mock_confirm,
        ):
            # Configure custom: Yes, Allow dangerous: No, Add blocked commands: No, Add blocked env: No
            mock_confirm.side_effect = [True, False, False, False]
            result = run_security_step(state, console)

        assert result["security_custom"] is True
        assert result["security_allow_dangerous"] is False

    def test_dangerous_operations_accepted_then_declined_confirm(self) -> None:
        """Test when user says yes to dangerous but no to confirmation."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.security.Confirm.ask") as mock_confirm,
        ):
            # Configure: Yes, Allow dangerous: Yes, Really sure: No, Add blocked: No, No
            mock_confirm.side_effect = [True, True, False, False, False]
            result = run_security_step(state, console)

        assert result["security_custom"] is True
        assert result["security_allow_dangerous"] is False

    def test_dangerous_operations_fully_confirmed(self) -> None:
        """Test when user confirms dangerous operations twice."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.security.Confirm.ask") as mock_confirm,
        ):
            # Configure: Yes, Allow dangerous: Yes, Really sure: Yes, Add blocked: No, No
            mock_confirm.side_effect = [True, True, True, False, False]
            result = run_security_step(state, console)

        assert result["security_custom"] is True
        assert result["security_allow_dangerous"] is True


class TestRunSecurityStepBlockedCommands:
    """Tests for blocked command patterns configuration."""

    def test_blocked_commands_single_pattern(self) -> None:
        """Test adding a single blocked command pattern."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.security.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.security.Prompt.ask") as mock_prompt,
        ):
            # Configure: Yes, Dangerous: No, Add blocked commands: Yes, Add env: No
            mock_confirm.side_effect = [True, False, True, False]
            # Pattern, then empty to finish
            mock_prompt.side_effect = [r"npm\s+publish", ""]
            result = run_security_step(state, console)

        assert result["security_blocked_commands"] == [r"npm\s+publish"]

    def test_blocked_commands_multiple_patterns(self) -> None:
        """Test adding multiple blocked command patterns."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.security.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.security.Prompt.ask") as mock_prompt,
        ):
            # Configure: Yes, Dangerous: No, Add blocked commands: Yes, Add env: No
            mock_confirm.side_effect = [True, False, True, False]
            # Multiple patterns, then empty to finish
            mock_prompt.side_effect = [r"npm\s+publish", r"docker\s+push", ""]
            result = run_security_step(state, console)

        assert result["security_blocked_commands"] == [
            r"npm\s+publish",
            r"docker\s+push",
        ]

    def test_blocked_commands_invalid_pattern_reprompts(self) -> None:
        """Test that invalid regex patterns trigger reprompt."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.security.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.security.Prompt.ask") as mock_prompt,
        ):
            # Configure: Yes, Dangerous: No, Add blocked commands: Yes, Add env: No
            mock_confirm.side_effect = [True, False, True, False]
            # Invalid pattern, valid pattern, empty to finish
            mock_prompt.side_effect = [r"[invalid", r"valid\s+pattern", ""]
            result = run_security_step(state, console)

        # Only valid pattern should be stored
        assert result["security_blocked_commands"] == [r"valid\s+pattern"]


class TestRunSecurityStepBlockedEnvFiles:
    """Tests for blocked env files configuration."""

    def test_blocked_env_files_single_pattern(self) -> None:
        """Test adding a single blocked env file pattern."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.security.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.security.Prompt.ask") as mock_prompt,
        ):
            # Configure: Yes, Dangerous: No, Add blocked commands: No, Add env: Yes
            mock_confirm.side_effect = [True, False, False, True]
            # Pattern, then empty to finish
            mock_prompt.side_effect = [".secrets", ""]
            result = run_security_step(state, console)

        assert result["security_blocked_env_files"] == [".secrets"]

    def test_blocked_env_files_multiple_patterns(self) -> None:
        """Test adding multiple blocked env file patterns."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.security.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.security.Prompt.ask") as mock_prompt,
        ):
            # Configure: Yes, Dangerous: No, Add blocked commands: No, Add env: Yes
            mock_confirm.side_effect = [True, False, False, True]
            # Multiple patterns, then empty to finish
            mock_prompt.side_effect = [".secrets", "config/*.json", ""]
            result = run_security_step(state, console)

        assert result["security_blocked_env_files"] == [".secrets", "config/*.json"]


class TestSecurityStepHandler:
    """Tests for SecurityStepHandler class."""

    def test_handler_execute_delegates_to_run_security_step(self) -> None:
        """Test handler execute method delegates correctly."""
        handler = SecurityStepHandler()
        state = WizardState()
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.security.Confirm.ask", return_value=False):
            result = handler.execute(state, console)

        assert result["security_custom"] is False
        assert result["security_allow_dangerous"] is False


class TestBuiltinDefaults:
    """Tests for builtin default values."""

    def test_builtin_blocked_commands_exist(self) -> None:
        """Test that builtin blocked commands are defined."""
        assert len(BUILTIN_BLOCKED_COMMANDS) > 0
        # Should include dangerous patterns
        patterns_str = " ".join(BUILTIN_BLOCKED_COMMANDS)
        assert "rm" in patterns_str

    def test_builtin_blocked_env_files_exist(self) -> None:
        """Test that builtin blocked env files are defined."""
        assert len(BUILTIN_BLOCKED_ENV_FILES) > 0
        # Should include common sensitive files
        assert ".env" in BUILTIN_BLOCKED_ENV_FILES


class TestStateIntegration:
    """Tests for integration with wizard state."""

    def test_config_stored_via_flow_controller_pattern(self) -> None:
        """Test that config can be stored using flow controller pattern."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.security.Confirm.ask", return_value=False):
            config = run_security_step(state, console)

        # Simulate what flow controller does
        state.update_config("security", config)
        state.mark_completed("security")

        # Verify storage
        stored = state.get_step_config("security")
        assert stored["security_custom"] is False
        assert "security" in state.completed_steps

    def test_full_flow_returns_complete_config(self) -> None:
        """Test that full flow returns all expected configuration keys."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.security.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.security.Prompt.ask") as mock_prompt,
        ):
            # Full custom configuration
            mock_confirm.side_effect = [True, True, True, True, True]
            mock_prompt.side_effect = [r"npm\s+publish", "", ".secrets", ""]
            result = run_security_step(state, console)

        # Verify all keys present
        assert "security_custom" in result
        assert "security_allow_dangerous" in result
        assert "security_blocked_commands" in result
        assert "security_blocked_env_files" in result

        # Verify values
        assert result["security_custom"] is True
        assert result["security_allow_dangerous"] is True
        assert result["security_blocked_commands"] == [r"npm\s+publish"]
        assert result["security_blocked_env_files"] == [".secrets"]
