"""Tests for the wizard flow controller.

This module tests the WizardFlowController class and WizardStep enum
that coordinate the interactive init wizard experience.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from adw.cli.wizard import StepHandler, WizardFlowController, WizardStep
from adw.models.wizard import WizardState


class TestWizardStep:
    """Tests for the WizardStep enum."""

    def test_step_values_exist(self) -> None:
        """Verify all expected wizard steps are defined."""
        expected_steps = [
            "basics",
            "git",
            "ports",
            "task_manager",
            "phases",
            "llm_retry",
            "security",
            "webhooks",
            "summary",
        ]
        actual_steps = [step.value for step in WizardStep]
        assert actual_steps == expected_steps

    def test_step_enum_members(self) -> None:
        """Verify enum member access works correctly."""
        assert WizardStep.BASICS.value == "basics"
        assert WizardStep.GIT.value == "git"
        assert WizardStep.SUMMARY.value == "summary"


class TestWizardFlowController:
    """Tests for the WizardFlowController class."""

    def test_init_creates_default_state(self) -> None:
        """Controller creates default state when none provided."""
        controller = WizardFlowController()
        assert controller.state is not None
        assert isinstance(controller.state, WizardState)
        assert controller.state.current_step == "basics"

    def test_init_accepts_existing_state(self) -> None:
        """Controller accepts existing state."""
        state = WizardState(current_step="git", completed_steps=["basics"])
        controller = WizardFlowController(state=state)
        assert controller.state is state
        assert controller.state.current_step == "git"

    def test_step_sequence_defined(self) -> None:
        """Controller has defined step sequence."""
        assert len(WizardFlowController.STEP_SEQUENCE) == 9
        assert WizardFlowController.STEP_SEQUENCE[0] == WizardStep.BASICS
        assert WizardFlowController.STEP_SEQUENCE[-1] == WizardStep.SUMMARY

    def test_get_current_step(self) -> None:
        """Get current step returns correct step."""
        controller = WizardFlowController()
        assert controller.get_current_step() == WizardStep.BASICS

    def test_get_current_step_at_end(self) -> None:
        """Get current step returns None when past end."""
        controller = WizardFlowController()
        controller.current_index = len(controller.steps)
        assert controller.get_current_step() is None

    def test_advance_moves_to_next_step(self) -> None:
        """Advance moves to next step and updates state."""
        controller = WizardFlowController()
        assert controller.advance() is True
        assert controller.current_index == 1
        assert controller.get_current_step() == WizardStep.GIT
        assert controller.state.current_step == "git"
        assert "basics" in controller.state.completed_steps

    def test_advance_at_end_returns_false(self) -> None:
        """Advance returns False when at end."""
        controller = WizardFlowController()
        controller.current_index = len(controller.steps) - 1
        assert controller.advance() is False

    def test_go_back_moves_to_previous_step(self) -> None:
        """Go back moves to previous step and updates state."""
        controller = WizardFlowController()
        controller.advance()  # Move to git
        controller.advance()  # Move to ports

        assert controller.go_back() is True
        assert controller.current_index == 1
        assert controller.get_current_step() == WizardStep.GIT
        assert controller.state.current_step == "git"

    def test_go_back_at_start_returns_false(self) -> None:
        """Go back returns False when at start."""
        controller = WizardFlowController()
        assert controller.go_back() is False

    def test_go_back_removes_step_from_completed(self) -> None:
        """Go back removes step from completed list."""
        controller = WizardFlowController()
        controller.advance()  # basics -> completed, current = git
        assert "basics" in controller.state.completed_steps

        # Manually add git to completed (simulating forward progress)
        controller.state.completed_steps.append("git")

        controller.go_back()  # git removed, current = basics
        assert "git" not in controller.state.completed_steps


class TestPackageExports:
    """Tests for wizard package exports."""

    def test_wizard_flow_controller_exported(self) -> None:
        """WizardFlowController is exported from package."""
        from adw.cli.wizard import WizardFlowController
        assert WizardFlowController is not None

    def test_wizard_step_exported(self) -> None:
        """WizardStep is exported from package."""
        from adw.cli.wizard import WizardStep
        assert WizardStep is not None

    def test_step_handler_exported(self) -> None:
        """StepHandler is exported from package."""
        from adw.cli.wizard import StepHandler
        assert StepHandler is not None

    def test_all_exports_defined(self) -> None:
        """__all__ contains expected exports."""
        from adw.cli import wizard
        assert "WizardFlowController" in wizard.__all__
        assert "WizardStep" in wizard.__all__
        assert "StepHandler" in wizard.__all__


class TestWizardFlowControllerRun:
    """Tests for WizardFlowController.run() method."""

    def test_run_without_handlers_uses_placeholders(self) -> None:
        """Run without handlers shows placeholders for each step."""
        controller = WizardFlowController()

        # Mock the prompt to always return "next" to complete wizard
        with patch.object(controller, "_prompt_navigation", return_value="next"):
            with patch.object(controller, "_show_welcome"):
                with patch.object(controller, "_show_step_header"):
                    with patch.object(controller, "_show_step_placeholder"):
                        with patch.object(controller, "_show_completion"):
                            result = controller.run()

        assert result is True
        assert controller.current_index == len(controller.steps)

    def test_run_cancel_returns_false(self) -> None:
        """Run returns False when cancelled."""
        controller = WizardFlowController()

        with patch.object(controller, "_prompt_navigation", return_value="cancel"):
            with patch.object(controller, "_show_welcome"):
                with patch.object(controller, "_show_step_header"):
                    with patch.object(controller, "_show_step_placeholder"):
                        result = controller.run()

        assert result is False
        assert controller.interrupted is True

    def test_run_back_navigation(self) -> None:
        """Run supports back navigation."""
        controller = WizardFlowController()

        # Sequence: next, next, back, next, cancel
        nav_sequence = ["next", "next", "back", "cancel"]
        nav_iter = iter(nav_sequence)

        with patch.object(controller, "_prompt_navigation", side_effect=lambda: next(nav_iter)):
            with patch.object(controller, "_show_welcome"):
                with patch.object(controller, "_show_step_header"):
                    with patch.object(controller, "_show_step_placeholder"):
                        controller.run()

        # Should be at index 1 (went to 2, back to 1, then cancelled)
        assert controller.current_index == 1

    def test_run_marks_steps_completed(self) -> None:
        """Run marks steps as completed when advancing."""
        controller = WizardFlowController()

        # Advance through 3 steps then cancel
        nav_sequence = ["next", "next", "next", "cancel"]
        nav_iter = iter(nav_sequence)

        with patch.object(controller, "_prompt_navigation", side_effect=lambda: next(nav_iter)):
            with patch.object(controller, "_show_welcome"):
                with patch.object(controller, "_show_step_header"):
                    with patch.object(controller, "_show_step_placeholder"):
                        controller.run()

        # First 3 steps should be completed
        assert "basics" in controller.state.completed_steps
        assert "git" in controller.state.completed_steps
        assert "ports" in controller.state.completed_steps

    def test_run_with_registered_handler(self) -> None:
        """Run calls registered handler for step."""
        controller = WizardFlowController()

        # Create mock handler
        mock_handler = MagicMock()
        mock_handler.execute.return_value = {"language": "python"}
        controller.register_step_handler(WizardStep.BASICS, mock_handler)

        # Run one step then cancel
        nav_sequence = ["next", "cancel"]
        nav_iter = iter(nav_sequence)

        with patch.object(controller, "_prompt_navigation", side_effect=lambda: next(nav_iter)):
            with patch.object(controller, "_show_welcome"):
                with patch.object(controller, "_show_step_header"):
                    controller.run()

        # Handler should have been called
        mock_handler.execute.assert_called_once()
        # Config should be stored
        assert controller.state.collected_config.get("basics") == {"language": "python"}


class TestWizardFlowControllerCancel:
    """Tests for cancel functionality."""

    def test_cancel_sets_interrupted(self) -> None:
        """Cancel sets interrupted flag."""
        controller = WizardFlowController()
        controller.cancel()
        assert controller.interrupted is True


class TestStepTitles:
    """Tests for step titles."""

    def test_all_steps_have_titles(self) -> None:
        """All wizard steps have titles defined."""
        for step in WizardStep:
            assert step in WizardFlowController.STEP_TITLES
