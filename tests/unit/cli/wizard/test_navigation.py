"""Tests for wizard navigation helpers.

Tests the navigation signal detection and navigation-aware prompt wrappers.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from rich.console import Console

from adw.cli.wizard.navigation import (
    NavigationError,
    NavigationSignal,
    check_navigation,
    nav_confirm_ask,
    nav_prompt_ask,
)


class TestNavigationSignal:
    """Tests for NavigationSignal enum."""

    def test_signal_values(self) -> None:
        """Test that navigation signals have correct values."""
        assert NavigationSignal.BACK.value == "back"
        assert NavigationSignal.CANCEL.value == "cancel"


class TestCheckNavigation:
    """Tests for check_navigation function."""

    def test_back_lowercase(self) -> None:
        """Test 'b' is detected as back."""
        assert check_navigation("b") == NavigationSignal.BACK

    def test_back_uppercase(self) -> None:
        """Test 'B' is detected as back."""
        assert check_navigation("B") == NavigationSignal.BACK

    def test_cancel_lowercase(self) -> None:
        """Test 'c' is detected as cancel."""
        assert check_navigation("c") == NavigationSignal.CANCEL

    def test_cancel_uppercase(self) -> None:
        """Test 'C' is detected as cancel."""
        assert check_navigation("C") == NavigationSignal.CANCEL

    def test_back_with_whitespace(self) -> None:
        """Test 'b' with whitespace is detected."""
        assert check_navigation("  b  ") == NavigationSignal.BACK

    def test_cancel_with_whitespace(self) -> None:
        """Test 'c' with whitespace is detected."""
        assert check_navigation("  c  ") == NavigationSignal.CANCEL

    def test_regular_input_returns_none(self) -> None:
        """Test regular input returns None."""
        assert check_navigation("hello") is None
        assert check_navigation("yes") is None
        assert check_navigation("build") is None

    def test_empty_input_returns_none(self) -> None:
        """Test empty input returns None."""
        assert check_navigation("") is None

    def test_words_starting_with_b_not_navigation(self) -> None:
        """Test that words like 'build' don't trigger back."""
        assert check_navigation("build") is None
        assert check_navigation("back") is None

    def test_words_starting_with_c_not_navigation(self) -> None:
        """Test that words like 'create' don't trigger cancel."""
        assert check_navigation("cancel") is None
        assert check_navigation("create") is None


class TestNavigationError:
    """Tests for NavigationError exception."""

    def test_error_stores_signal(self) -> None:
        """Test that error stores the navigation signal."""
        error = NavigationError(NavigationSignal.BACK)
        assert error.signal == NavigationSignal.BACK

    def test_error_message(self) -> None:
        """Test error message format."""
        error = NavigationError(NavigationSignal.CANCEL)
        assert "cancel" in str(error)


class TestNavPromptAsk:
    """Tests for nav_prompt_ask function."""

    def test_returns_normal_input(self) -> None:
        """Test that normal input is returned."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.navigation.Prompt.ask", return_value="hello"):
            result = nav_prompt_ask("Question", console=console)

        assert result == "hello"

    def test_raises_on_back(self) -> None:
        """Test that 'b' raises NavigationError."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.navigation.Prompt.ask", return_value="b"):
            with pytest.raises(NavigationError) as exc_info:
                nav_prompt_ask("Question", console=console)

        assert exc_info.value.signal == NavigationSignal.BACK

    def test_raises_on_cancel(self) -> None:
        """Test that 'c' raises NavigationError."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.navigation.Prompt.ask", return_value="c"):
            with pytest.raises(NavigationError) as exc_info:
                nav_prompt_ask("Question", console=console)

        assert exc_info.value.signal == NavigationSignal.CANCEL

    def test_passes_default(self) -> None:
        """Test that default is passed to Prompt.ask."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.navigation.Prompt.ask", return_value="test") as mock:
            nav_prompt_ask("Question", console=console, default="default_value")
            mock.assert_called_once()
            assert mock.call_args.kwargs["default"] == "default_value"

    def test_passes_choices(self) -> None:
        """Test that choices are passed to Prompt.ask."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.navigation.Prompt.ask", return_value="opt1") as mock:
            nav_prompt_ask(
                "Question", console=console, choices=["opt1", "opt2"]
            )
            mock.assert_called_once()
            assert mock.call_args.kwargs["choices"] == ["opt1", "opt2"]


class TestNavConfirmAsk:
    """Tests for nav_confirm_ask function."""

    def test_returns_true(self) -> None:
        """Test that True is returned for yes."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.navigation.Confirm.ask", return_value=True):
            result = nav_confirm_ask("Question?", console=console)

        assert result is True

    def test_returns_false(self) -> None:
        """Test that False is returned for no."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.navigation.Confirm.ask", return_value=False):
            result = nav_confirm_ask("Question?", console=console)

        assert result is False

    def test_passes_default(self) -> None:
        """Test that default is passed to Confirm.ask."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.navigation.Confirm.ask", return_value=False) as mock:
            nav_confirm_ask("Question?", console=console, default=False)
            mock.assert_called_once()
            assert mock.call_args.kwargs["default"] is False
