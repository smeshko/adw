# Test Reduction Notes:
# Following ADR-001, these tests focus on:
#   - The returned dict (API contract)
# NOT testing:
#   - Interactive prompt behavior (requires user input)
#   - Default values (visible in code)
#   - Import verification

"""Tests for global registry wizard step."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from adw.cli.wizard.global_registry import (
    run_global_registry_step,
)


@pytest.fixture
def console() -> Console:
    """Create a console for testing."""
    return Console(force_terminal=True, no_color=True)


class TestRunGlobalRegistryStep:
    """Tests for run_global_registry_step() function."""

    def test_returns_enabled_true_when_user_accepts(self, console: Console) -> None:
        """Returns enabled=True when user confirms registration."""
        with (
            patch("adw.cli.wizard.global_registry.Confirm.ask", return_value=True),
            patch(
                "adw.cli.wizard.global_registry.Prompt.ask",
                return_value="my-project",
            ),
        ):
            result = run_global_registry_step(console)

        assert result["global_registry_enabled"] is True
        assert result["global_registry_name"] == "my-project"

    def test_returns_enabled_false_when_user_declines(self, console: Console) -> None:
        """Returns enabled=False when user declines registration."""
        with patch("adw.cli.wizard.global_registry.Confirm.ask", return_value=False):
            result = run_global_registry_step(console)

        assert result["global_registry_enabled"] is False
        assert result["global_registry_name"] is None

    def test_uses_directory_name_as_default(self, console: Console) -> None:
        """Uses project directory name as default display name."""
        with (
            patch("adw.cli.wizard.global_registry.Confirm.ask", return_value=True),
            patch(
                "adw.cli.wizard.global_registry.Prompt.ask",
                return_value="custom-name",
            ) as mock_prompt,
            patch("adw.cli.wizard.global_registry.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/Users/dev/my-project")
            run_global_registry_step(console)

        # Verify Prompt.ask was called with default
        assert mock_prompt.called
        call_kwargs = mock_prompt.call_args
        # Default should be the directory name
        assert "my-project" in str(call_kwargs)

    def test_returns_dict_with_expected_keys(self, console: Console) -> None:
        """Returns dict with global_registry_enabled and global_registry_name."""
        with (
            patch("adw.cli.wizard.global_registry.Confirm.ask", return_value=True),
            patch(
                "adw.cli.wizard.global_registry.Prompt.ask",
                return_value="test",
            ),
        ):
            result = run_global_registry_step(console)

        assert "global_registry_enabled" in result
        assert "global_registry_name" in result
