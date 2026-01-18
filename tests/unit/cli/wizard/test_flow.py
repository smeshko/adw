"""Tests for the wizard flow controller.

This module tests the WizardFlowController class and WizardStep enum
that coordinate the interactive init wizard experience.
"""

from __future__ import annotations

import pytest

from adw.cli.wizard import WizardFlowController, WizardStep
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

    def test_all_exports_defined(self) -> None:
        """__all__ contains expected exports."""
        from adw.cli import wizard
        assert "WizardFlowController" in wizard.__all__
        assert "WizardStep" in wizard.__all__
