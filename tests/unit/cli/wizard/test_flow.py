"""Tests for the wizard flow controller.

This module tests the WizardFlowController class and WizardStep enum
that coordinate the interactive init wizard experience.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from adw.cli.wizard import StepHandler, WizardFlowController, WizardStep
from adw.models.wizard import WizardState


class TestWizardStep:
    """Tests for the WizardStep enum."""

    def test_step_values_exist(self) -> None:
        """Verify all expected wizard steps are defined."""
        expected_steps = [
            "basics",
            "global_registry",
            "git",
            "ports",
            "task_manager",
            "phases",
            "ship",
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
        assert len(WizardFlowController.STEP_SEQUENCE) == 11
        assert WizardFlowController.STEP_SEQUENCE[0] == WizardStep.BASICS
        assert WizardFlowController.STEP_SEQUENCE[1] == WizardStep.GLOBAL_REGISTRY
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
        assert controller.get_current_step() == WizardStep.GLOBAL_REGISTRY
        assert controller.state.current_step == "global_registry"
        assert "basics" in controller.state.completed_steps

    def test_advance_at_end_returns_false(self) -> None:
        """Advance returns False when at end."""
        controller = WizardFlowController()
        controller.current_index = len(controller.steps) - 1
        assert controller.advance() is False

    def test_go_back_moves_to_previous_step(self) -> None:
        """Go back moves to previous step and updates state."""
        controller = WizardFlowController()
        controller.advance()  # Move to global_registry
        controller.advance()  # Move to git

        assert controller.go_back() is True
        assert controller.current_index == 1
        assert controller.get_current_step() == WizardStep.GLOBAL_REGISTRY
        assert controller.state.current_step == "global_registry"

    def test_go_back_at_start_returns_false(self) -> None:
        """Go back returns False when at start."""
        controller = WizardFlowController()
        assert controller.go_back() is False

    def test_go_back_removes_current_step_from_completed(self) -> None:
        """Go back removes current step from completed list if it was completed.

        This covers the case where a step was completed, but the user
        goes back to re-edit it - it should no longer be marked complete.
        """
        controller = WizardFlowController()
        controller.advance()  # basics -> completed, current = global_registry
        assert "basics" in controller.state.completed_steps
        assert controller.state.current_step == "global_registry"

        # Manually mark global_registry as completed (simulates completing the step)
        controller.state.mark_completed("global_registry")
        assert "global_registry" in controller.state.completed_steps

        # Go back should remove global_registry from completed since we're revisiting
        controller.go_back()
        assert controller.state.current_step == "basics"
        # global_registry should be removed from completed (we're revisiting it)
        assert "global_registry" not in controller.state.completed_steps


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

        with (
            patch.object(controller, "_show_welcome"),
            patch.object(controller, "_show_step_header"),
            patch.object(controller, "_show_step_placeholder"),
            patch.object(controller, "_show_completion"),
        ):
            result = controller.run()

        assert result is True
        assert controller.current_index == len(controller.steps)

    def test_run_cancel_via_interrupt_returns_false(self) -> None:
        """Run returns False when interrupted via Ctrl+C."""
        controller = WizardFlowController()

        def interrupt_on_first_step(*args: object, **kwargs: object) -> None:
            controller.interrupted = True

        with (
            patch.object(controller, "_show_welcome"),
            patch.object(
                controller, "_show_step_header", side_effect=interrupt_on_first_step
            ),
        ):
            result = controller.run()

        assert result is False
        assert controller.interrupted is True

    def test_run_marks_steps_completed(self) -> None:
        """Run marks steps as completed when advancing."""
        controller = WizardFlowController()

        with (
            patch.object(controller, "_show_welcome"),
            patch.object(controller, "_show_step_header"),
            patch.object(controller, "_show_step_placeholder"),
            patch.object(controller, "_show_completion"),
        ):
            controller.run()

        # All steps should be completed
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

        with (
            patch.object(controller, "_show_welcome"),
            patch.object(controller, "_show_step_header"),
            patch.object(controller, "_show_step_placeholder"),
            patch.object(controller, "_show_completion"),
        ):
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


class TestInterruptHandler:
    """Tests for interrupt handler functionality."""

    def test_interrupt_handler_installed_during_run(self) -> None:
        """Interrupt handler is installed when run() starts."""
        import signal

        controller = WizardFlowController()
        original_handler = signal.getsignal(signal.SIGINT)

        with (
            patch.object(controller, "_show_welcome"),
            patch.object(controller, "_show_step_header"),
            patch.object(controller, "_show_step_placeholder"),
            patch.object(controller, "_show_completion"),
        ):
            controller.run()

        # Handler should be restored after run completes
        current_handler = signal.getsignal(signal.SIGINT)
        assert current_handler == original_handler

    def test_interrupt_flag_stops_wizard(self) -> None:
        """Setting interrupted flag stops the wizard."""
        controller = WizardFlowController()

        def interrupt_after_call(*args: object, **kwargs: object) -> None:
            controller.interrupted = True

        with (
            patch.object(controller, "_show_welcome"),
            patch.object(
                controller, "_show_step_header", side_effect=interrupt_after_call
            ),
        ):
            result = controller.run()

        assert result is False
        assert controller.interrupted is True
