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
        assert result["post_publish"] == []  # No post-publish hooks
        assert result["pr"]["merge_on_success"] is False
        assert result["pr"]["delete_branch_on_merge"] is True
        assert result["pr"]["merge_method"] == "squash"

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
            # Configure ship: Yes, Add hooks: Yes, Auto-merge: Yes, Delete branch: Yes
            if "Configure ship phase" in msg:
                return True
            if "Add post-publish hooks" in msg:
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
            if "Build command" in msg:
                return "npm run build"
            if "Publish command" in msg:
                return "npm publish"
            if "Hook command" in msg:
                # First call returns a hook, second returns empty to finish
                if prompt_calls.count(msg) == 1:
                    return "git push --tags"
                return ""
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
        assert result["commands"]["build"] == "npm run build"
        assert result["commands"]["publish"] == "npm publish"
        assert result["post_publish"] == ["git push --tags"]
        assert result["pr"]["merge_on_success"] is True
        assert result["pr"]["delete_branch_on_merge"] is True
        assert result["pr"]["merge_method"] == "squash"

    def test_commands_empty_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty command inputs result in no commands in config."""
        from adw.cli.wizard.ship import run_ship_step
        from adw.models.wizard import WizardState

        def mock_confirm(*args: Any, **kwargs: Any) -> bool:
            msg = str(args[0]) if args else ""
            # Enable configuration but decline post-publish hooks
            if "Configure ship phase" in msg:
                return True
            if "Add post-publish" in msg:
                return False
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
        assert result["post_publish"] == []

    def test_post_publish_hooks_loop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that post-publish hooks loop collects multiple entries."""
        from adw.cli.wizard.ship import run_ship_step
        from adw.models.wizard import WizardState

        hook_call_count = 0

        def mock_confirm(*args: Any, **kwargs: Any) -> bool:
            msg = str(args[0]) if args else ""
            if "Configure ship phase" in msg:
                return True
            return "Add post-publish" in msg  # All other options use defaults

        def mock_prompt(*args: Any, **kwargs: Any) -> str:
            nonlocal hook_call_count
            msg = str(args[0]) if args else ""
            if "Hook command" in msg:
                hook_call_count += 1
                if hook_call_count == 1:
                    return "git push --tags"
                if hook_call_count == 2:
                    return "echo 'deployed'"
                return ""  # Empty to finish
            return kwargs.get("default", "")

        monkeypatch.setattr("adw.cli.wizard.ship.Confirm.ask", mock_confirm)
        monkeypatch.setattr("adw.cli.wizard.ship.Prompt.ask", mock_prompt)

        state = WizardState()
        console = Console()
        result = run_ship_step(state, console)

        # Should have both hooks
        assert result["post_publish"] == ["git push --tags", "echo 'deployed'"]

    def test_pr_merge_strategies(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test all merge strategy values are accepted."""
        from adw.cli.wizard.ship import run_ship_step
        from adw.models.wizard import WizardState

        for strategy in ["squash", "merge", "rebase"]:

            def mock_confirm(*args: Any, **kwargs: Any) -> bool:
                msg = str(args[0]) if args else ""
                if "Configure ship phase" in msg:
                    return True
                if "Add post-publish" in msg:
                    return False
                return False

            def make_mock_prompt(strat: str):
                def mock_prompt(*args: Any, **kwargs: Any) -> str:
                    msg = str(args[0]) if args else ""
                    if "Merge strategy" in msg:
                        return strat
                    return kwargs.get("default", "")

                return mock_prompt

            monkeypatch.setattr("adw.cli.wizard.ship.Confirm.ask", mock_confirm)
            monkeypatch.setattr(
                "adw.cli.wizard.ship.Prompt.ask", make_mock_prompt(strategy)
            )

            state = WizardState()
            console = Console()
            result = run_ship_step(state, console)

            assert result["pr"]["merge_method"] == strategy


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
