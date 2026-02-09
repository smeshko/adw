"""Unit tests for ship wizard step."""

from __future__ import annotations

from typing import Any

import pytest
from rich.console import Console


class TestRunShipStep:
    """Tests for run_ship_step function."""

    def test_skip_returns_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ship step returns defaults when user skips configuration."""
        from adw.cli.wizard.ship import run_ship_step
        from adw.models.wizard import WizardState

        # Mock Confirm.ask to return False (skip)
        monkeypatch.setattr("adw.cli.wizard.ship.Confirm.ask", lambda *a, **kw: False)

        state = WizardState()
        console = Console()
        result = run_ship_step(state, console)

        # Verify defaults
        assert result["enabled"] is True  # Ship is enabled by default
        assert result["commands"] == {}  # No commands configured

    def test_full_config_all_options(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ship step with all options configured."""
        from adw.cli.wizard.ship import run_ship_step
        from adw.models.wizard import WizardState

        # Track which prompts we're answering
        confirm_calls: list[str] = []
        prompt_calls: list[str] = []

        def mock_confirm(*args: Any, **kwargs: Any) -> bool:
            msg = str(args[0]) if args else str(kwargs.get("prompt", ""))
            confirm_calls.append(msg)
            # Configure ship: Yes, Auto-merge: Yes, Delete branch: Yes
            if "Configure ship phase" in msg:
                return True
            if "Auto-merge" in msg:
                return True
            if "Delete branch" in msg:
                return True
            return True

        def mock_prompt(*args: Any, **kwargs: Any) -> str:
            msg = str(args[0]) if args else str(kwargs.get("prompt", ""))
            prompt_calls.append(msg)
            # Return appropriate values based on prompt
            if "Version bump" in msg:
                return "npm version patch"
            if "Publish command" in msg:
                return "npm publish"
            if "Merge strategy" in msg:
                return "squash"
            return kwargs.get("default", "")

        monkeypatch.setattr("adw.cli.wizard.ship.Confirm.ask", mock_confirm)
        monkeypatch.setattr("adw.cli.wizard.ship.Prompt.ask", mock_prompt)

        state = WizardState()
        console = Console()
        result = run_ship_step(state, console)

        # Verify full configuration
        assert result["enabled"] is True
        assert result["commands"]["version_bump"] == "npm version patch"
        assert result["commands"]["publish"] == "npm publish"

    def test_commands_empty_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty command inputs result in no commands in config."""
        from adw.cli.wizard.ship import run_ship_step
        from adw.models.wizard import WizardState

        def mock_confirm(*args: Any, **kwargs: Any) -> bool:
            msg = str(args[0]) if args else ""
            # Enable configuration
            if "Configure ship phase" in msg:
                return True
            return False  # All PR options use defaults (No for merge)

        def mock_prompt(*args: Any, **kwargs: Any) -> str:
            # Return empty for all commands
            return kwargs.get("default", "")

        monkeypatch.setattr("adw.cli.wizard.ship.Confirm.ask", mock_confirm)
        monkeypatch.setattr("adw.cli.wizard.ship.Prompt.ask", mock_prompt)

        state = WizardState()
        console = Console()
        result = run_ship_step(state, console)

        # Empty commands should not be included
        assert result["commands"] == {}


class TestShipStepHandler:
    """Tests for ShipStepHandler class."""

    def test_handler_execute_delegates_to_run_ship_step(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that handler.execute() delegates to run_ship_step."""
        from adw.cli.wizard.ship import ShipStepHandler
        from adw.models.wizard import WizardState

        # Mock run_ship_step
        expected_result = {"enabled": True, "commands": {}}
        monkeypatch.setattr(
            "adw.cli.wizard.ship.run_ship_step", lambda *a, **kw: expected_result
        )

        handler = ShipStepHandler()
        state = WizardState()
        console = Console()
        result = handler.execute(state, console)

        assert result == expected_result


class TestPackageExports:
    """Tests for package exports."""

    def test_ship_step_handler_exported(self) -> None:
        """Test that ShipStepHandler is exported from wizard package."""
        from adw.cli.wizard import ShipStepHandler

        assert ShipStepHandler is not None

    def test_run_ship_step_exported(self) -> None:
        """Test that run_ship_step is exported from wizard package."""
        from adw.cli.wizard import run_ship_step

        assert run_ship_step is not None
