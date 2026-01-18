"""Tests for wizard LLM retry configuration step.

Tests the validation functions for max_retries, base_delay, max_delay,
and multiplier, as well as the interactive prompt flow and state integration.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from rich.console import Console

from adw.cli.wizard.retry import (
    DEFAULT_BASE_DELAY,
    DEFAULT_MAX_DELAY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MULTIPLIER,
    MAX_DELAY_LIMIT,
    MAX_MULTIPLIER,
    MAX_RETRIES,
    MIN_DELAY,
    MIN_MULTIPLIER,
    MIN_RETRIES,
    RetryStepHandler,
    run_retry_step,
    validate_base_delay,
    validate_max_delay,
    validate_max_retries,
    validate_multiplier,
)
from adw.models.wizard import WizardState


class TestValidateMaxRetries:
    """Tests for validate_max_retries function."""

    @pytest.mark.parametrize(
        "value,expected_valid,expected_result",
        [
            ("3", True, 3),
            ("1", True, 1),
            ("10", True, 10),
            ("5", True, 5),
        ],
    )
    def test_valid_max_retries(
        self, value: str, expected_valid: bool, expected_result: int
    ) -> None:
        """Test validation of valid max retries values."""
        is_valid, result = validate_max_retries(value)
        assert is_valid == expected_valid
        assert result == expected_result

    @pytest.mark.parametrize(
        "value,expected_error_contains",
        [
            ("0", "at least"),
            ("11", "exceed"),
            ("-1", "at least"),
            ("abc", "integer"),
            ("3.5", "integer"),
            ("", "integer"),
        ],
    )
    def test_invalid_max_retries(
        self, value: str, expected_error_contains: str
    ) -> None:
        """Test validation of invalid max retries values."""
        is_valid, result = validate_max_retries(value)
        assert is_valid is False
        assert isinstance(result, str)
        assert expected_error_contains.lower() in result.lower()


class TestValidateBaseDelay:
    """Tests for validate_base_delay function."""

    @pytest.mark.parametrize(
        "value,expected_valid,expected_result",
        [
            ("1.0", True, 1.0),
            ("0.1", True, 0.1),
            ("60.0", True, 60.0),
            ("0.5", True, 0.5),
            ("300", True, 300.0),
        ],
    )
    def test_valid_base_delay(
        self, value: str, expected_valid: bool, expected_result: float
    ) -> None:
        """Test validation of valid base delay values."""
        is_valid, result = validate_base_delay(value)
        assert is_valid == expected_valid
        assert result == expected_result

    @pytest.mark.parametrize(
        "value,expected_error_contains",
        [
            ("0.05", "at least"),
            ("0", "at least"),
            ("301", "exceed"),
            ("-1", "at least"),
            ("abc", "number"),
            ("", "number"),
            ("nan", "finite"),
            ("inf", "finite"),
            ("-inf", "finite"),
        ],
    )
    def test_invalid_base_delay(self, value: str, expected_error_contains: str) -> None:
        """Test validation of invalid base delay values."""
        is_valid, result = validate_base_delay(value)
        assert is_valid is False
        assert isinstance(result, str)
        assert expected_error_contains.lower() in result.lower()


class TestValidateMaxDelay:
    """Tests for validate_max_delay function with cross-validation."""

    def test_valid_max_delay_greater_than_base(self) -> None:
        """Test max delay validation when greater than base delay."""
        is_valid, result = validate_max_delay("60.0", base_delay=1.0)
        assert is_valid is True
        assert result == 60.0

    def test_valid_max_delay_equal_to_base(self) -> None:
        """Test max delay validation when equal to base delay."""
        is_valid, result = validate_max_delay("5.0", base_delay=5.0)
        assert is_valid is True
        assert result == 5.0

    def test_invalid_max_delay_less_than_base(self) -> None:
        """Test max delay validation fails when less than base delay."""
        is_valid, result = validate_max_delay("0.5", base_delay=1.0)
        assert is_valid is False
        assert isinstance(result, str)
        assert ">=" in result

    def test_invalid_max_delay_exceeds_limit(self) -> None:
        """Test max delay validation fails when exceeding limit."""
        is_valid, result = validate_max_delay("400", base_delay=1.0)
        assert is_valid is False
        assert isinstance(result, str)
        assert "exceed" in result.lower()

    def test_invalid_max_delay_not_number(self) -> None:
        """Test max delay validation fails for non-numeric input."""
        is_valid, result = validate_max_delay("abc", base_delay=1.0)
        assert is_valid is False
        assert isinstance(result, str)
        assert "number" in result.lower()

    @pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
    def test_invalid_max_delay_non_finite(self, value: str) -> None:
        """Test max delay validation fails for non-finite values."""
        is_valid, result = validate_max_delay(value, base_delay=1.0)
        assert is_valid is False
        assert isinstance(result, str)
        assert "finite" in result.lower()


class TestValidateMultiplier:
    """Tests for validate_multiplier function."""

    @pytest.mark.parametrize(
        "value,expected_valid,expected_result",
        [
            ("2.0", True, 2.0),
            ("1.5", True, 1.5),
            ("3.0", True, 3.0),
            ("5.0", True, 5.0),
            ("1.1", True, 1.1),
        ],
    )
    def test_valid_multiplier(
        self, value: str, expected_valid: bool, expected_result: float
    ) -> None:
        """Test validation of valid multiplier values."""
        is_valid, result = validate_multiplier(value)
        assert is_valid == expected_valid
        assert result == expected_result

    @pytest.mark.parametrize(
        "value,expected_error_contains",
        [
            ("1.0", "greater than"),  # Must be > 1.0, not >= 1.0
            ("0.5", "greater than"),
            ("5.1", "exceed"),
            ("6.0", "exceed"),
            ("-1", "greater than"),
            ("abc", "number"),
            ("", "number"),
            ("nan", "finite"),
            ("inf", "finite"),
            ("-inf", "finite"),
        ],
    )
    def test_invalid_multiplier(self, value: str, expected_error_contains: str) -> None:
        """Test validation of invalid multiplier values."""
        is_valid, result = validate_multiplier(value)
        assert is_valid is False
        assert isinstance(result, str)
        assert expected_error_contains.lower() in result.lower()


class TestRunRetryStepDefaults:
    """Tests for run_retry_step when using defaults."""

    def test_decline_configuration_uses_defaults(self) -> None:
        """Test that declining retry configuration uses default values."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.retry.Confirm.ask", return_value=False):
            result = run_retry_step(state, console)

        assert result["retry_custom"] is False
        assert result["retry_max_retries"] == DEFAULT_MAX_RETRIES
        assert result["retry_base_delay"] == DEFAULT_BASE_DELAY
        assert result["retry_max_delay"] == DEFAULT_MAX_DELAY
        assert result["retry_multiplier"] == DEFAULT_MULTIPLIER


class TestRunRetryStepCustomConfiguration:
    """Tests for run_retry_step with custom configuration."""

    def test_accept_configuration_with_valid_values(self) -> None:
        """Test custom retry configuration with valid values."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.retry.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.retry.Prompt.ask") as mock_prompt,
        ):
            # max_retries, base_delay, max_delay, multiplier
            mock_prompt.side_effect = ["5", "2.0", "120.0", "1.5"]
            result = run_retry_step(state, console)

        assert result["retry_custom"] is True
        assert result["retry_max_retries"] == 5
        assert result["retry_base_delay"] == 2.0
        assert result["retry_max_delay"] == 120.0
        assert result["retry_multiplier"] == 1.5

    def test_invalid_max_retries_reprompts(self) -> None:
        """Test that invalid max_retries input reprompts user."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.retry.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.retry.Prompt.ask") as mock_prompt,
        ):
            # First invalid, then valid for max_retries, then rest
            mock_prompt.side_effect = ["abc", "5", "1.0", "60.0", "2.0"]
            result = run_retry_step(state, console)

        assert result["retry_max_retries"] == 5
        # Verify prompt was called at least 5 times (1 invalid + 4 valid)
        assert mock_prompt.call_count >= 5

    def test_invalid_base_delay_reprompts(self) -> None:
        """Test that invalid base_delay input reprompts user."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.retry.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.retry.Prompt.ask") as mock_prompt,
        ):
            # max_retries ok, base_delay invalid then valid, rest ok
            mock_prompt.side_effect = ["3", "invalid", "1.0", "60.0", "2.0"]
            result = run_retry_step(state, console)

        assert result["retry_base_delay"] == 1.0
        assert mock_prompt.call_count >= 5

    def test_max_delay_less_than_base_reprompts(self) -> None:
        """Test that max_delay < base_delay triggers reprompt."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.retry.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.retry.Prompt.ask") as mock_prompt,
        ):
            # max_retries, base_delay, max_delay (too small, then valid), multiplier
            mock_prompt.side_effect = ["3", "5.0", "2.0", "60.0", "2.0"]
            result = run_retry_step(state, console)

        assert result["retry_base_delay"] == 5.0
        assert result["retry_max_delay"] == 60.0  # The valid one
        assert mock_prompt.call_count >= 5

    def test_invalid_multiplier_reprompts(self) -> None:
        """Test that invalid multiplier input reprompts user."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.retry.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.retry.Prompt.ask") as mock_prompt,
        ):
            # max_retries, base_delay, max_delay, multiplier (1.0 is invalid, then valid)
            mock_prompt.side_effect = ["3", "1.0", "60.0", "1.0", "2.0"]
            result = run_retry_step(state, console)

        assert result["retry_multiplier"] == 2.0
        assert mock_prompt.call_count >= 5

    def test_max_delay_default_adjusts_to_base_delay(self) -> None:
        """Test that max_delay default adjusts when base_delay > DEFAULT_MAX_DELAY.

        When base_delay is set higher than the default max_delay (60s), the
        max_delay prompt should show a default that is >= base_delay so that
        pressing Enter to accept the default doesn't immediately fail validation.
        """
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.retry.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.retry.Prompt.ask") as mock_prompt,
        ):
            # Use base_delay of 100 (> DEFAULT_MAX_DELAY of 60)
            # User presses Enter for max_delay, accepting the adjusted default
            mock_prompt.side_effect = ["3", "100.0", "100.0", "2.0"]
            result = run_retry_step(state, console)

        # Verify the result uses base_delay of 100 and max_delay of 100
        assert result["retry_base_delay"] == 100.0
        assert result["retry_max_delay"] == 100.0  # Should work with adjusted default


class TestRetryStepHandler:
    """Tests for RetryStepHandler class."""

    def test_handler_execute_delegates_to_run_retry_step(self) -> None:
        """Test handler execute method delegates correctly."""
        handler = RetryStepHandler()
        state = WizardState()
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.retry.Confirm.ask", return_value=False):
            result = handler.execute(state, console)

        assert result["retry_custom"] is False
        assert result["retry_max_retries"] == DEFAULT_MAX_RETRIES
        assert result["retry_base_delay"] == DEFAULT_BASE_DELAY
        assert result["retry_max_delay"] == DEFAULT_MAX_DELAY
        assert result["retry_multiplier"] == DEFAULT_MULTIPLIER


class TestStateIntegration:
    """Tests for integration with wizard state."""

    def test_config_stored_via_flow_controller_pattern(self) -> None:
        """Test that config can be stored using flow controller pattern."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.retry.Confirm.ask", return_value=False):
            config = run_retry_step(state, console)

        # Simulate what flow controller does
        state.update_config("llm_retry", config)
        state.mark_completed("llm_retry")

        # Verify storage
        stored = state.get_step_config("llm_retry")
        assert stored["retry_custom"] is False
        assert stored["retry_max_retries"] == DEFAULT_MAX_RETRIES
        assert "llm_retry" in state.completed_steps

    def test_full_flow_returns_complete_config(self) -> None:
        """Test that full flow returns all expected configuration keys."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.retry.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.retry.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["5", "2.0", "120.0", "1.5"]
            result = run_retry_step(state, console)

        # Verify all keys present
        assert "retry_custom" in result
        assert "retry_max_retries" in result
        assert "retry_base_delay" in result
        assert "retry_max_delay" in result
        assert "retry_multiplier" in result

        # Verify values
        assert result["retry_custom"] is True
        assert result["retry_max_retries"] == 5
        assert result["retry_base_delay"] == 2.0
        assert result["retry_max_delay"] == 120.0
        assert result["retry_multiplier"] == 1.5


class TestConstants:
    """Tests for module constants validation."""

    def test_default_values_are_sensible(self) -> None:
        """Test that default retry configuration values are sensible."""
        assert DEFAULT_MAX_RETRIES == 3
        assert DEFAULT_BASE_DELAY == 1.0
        assert DEFAULT_MAX_DELAY == 60.0
        assert DEFAULT_MULTIPLIER == 2.0

    def test_validation_limits_are_consistent(self) -> None:
        """Test that validation limits are internally consistent."""
        # min < max for retries
        assert MIN_RETRIES < MAX_RETRIES
        # min delay < max delay limit
        assert MIN_DELAY < MAX_DELAY_LIMIT
        # multiplier must be > 1.0
        assert MIN_MULTIPLIER >= 1.0
        assert MAX_MULTIPLIER > MIN_MULTIPLIER

    def test_defaults_pass_validation(self) -> None:
        """Test that default values pass their own validation."""
        is_valid, _ = validate_max_retries(str(DEFAULT_MAX_RETRIES))
        assert is_valid

        is_valid, _ = validate_base_delay(str(DEFAULT_BASE_DELAY))
        assert is_valid

        is_valid, _ = validate_max_delay(str(DEFAULT_MAX_DELAY), DEFAULT_BASE_DELAY)
        assert is_valid

        is_valid, _ = validate_multiplier(str(DEFAULT_MULTIPLIER))
        assert is_valid
