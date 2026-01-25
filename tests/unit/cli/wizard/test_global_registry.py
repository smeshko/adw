# Test Reduction Notes:
# Following ADR-001, these tests focus on:
#   - State return structure (API contract)
#   - Handler execution (business logic)
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
    GlobalRegistryStepHandler,
    run_global_registry_step,
)
from adw.models.wizard import WizardState


@pytest.fixture
def mock_state() -> WizardState:
    """Create a mock wizard state."""
    return WizardState(
        current_step="global_registry",
        completed_steps=["basics"],
        collected_config={
            "basics": {
                "project_name": "my-project",
                "project_root": "/Users/dev/my-project",
            }
        },
    )


@pytest.fixture
def console() -> Console:
    """Create a console for testing."""
    return Console(force_terminal=True, no_color=True)


class TestGlobalRegistryStepHandler:
    """Tests for GlobalRegistryStepHandler class."""

    def test_handler_executes_step(
        self, mock_state: WizardState, console: Console
    ) -> None:
        """Handler.execute() calls run_global_registry_step and returns result."""
        handler = GlobalRegistryStepHandler()

        with patch(
            "adw.cli.wizard.global_registry.run_global_registry_step"
        ) as mock_run:
            mock_run.return_value = {
                "global_registry_enabled": True,
                "global_registry_name": "my-project",
            }
            result = handler.execute(mock_state, console)

        assert result == {
            "global_registry_enabled": True,
            "global_registry_name": "my-project",
        }
        mock_run.assert_called_once_with(mock_state, console)


class TestRunGlobalRegistryStep:
    """Tests for run_global_registry_step() function."""

    def test_returns_enabled_true_when_user_accepts(
        self, mock_state: WizardState, console: Console
    ) -> None:
        """Returns enabled=True when user confirms registration."""
        with (
            patch("adw.cli.wizard.global_registry.Confirm.ask", return_value=True),
            patch(
                "adw.cli.wizard.global_registry.Prompt.ask",
                return_value="my-project",
            ),
        ):
            result = run_global_registry_step(mock_state, console)

        assert result["global_registry_enabled"] is True
        assert result["global_registry_name"] == "my-project"

    def test_returns_enabled_false_when_user_declines(
        self, mock_state: WizardState, console: Console
    ) -> None:
        """Returns enabled=False when user declines registration."""
        with patch("adw.cli.wizard.global_registry.Confirm.ask", return_value=False):
            result = run_global_registry_step(mock_state, console)

        assert result["global_registry_enabled"] is False
        assert result["global_registry_name"] is None

    def test_uses_directory_name_as_default(
        self, mock_state: WizardState, console: Console
    ) -> None:
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
            run_global_registry_step(mock_state, console)

        # Verify Prompt.ask was called with default
        assert mock_prompt.called
        call_kwargs = mock_prompt.call_args
        # Default should be the directory name
        assert "my-project" in str(call_kwargs)

    def test_returns_dict_with_expected_keys(
        self, mock_state: WizardState, console: Console
    ) -> None:
        """Returns dict with global_registry_enabled and global_registry_name."""
        with (
            patch("adw.cli.wizard.global_registry.Confirm.ask", return_value=True),
            patch(
                "adw.cli.wizard.global_registry.Prompt.ask",
                return_value="test",
            ),
        ):
            result = run_global_registry_step(mock_state, console)

        assert "global_registry_enabled" in result
        assert "global_registry_name" in result
