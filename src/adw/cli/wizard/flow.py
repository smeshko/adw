"""Wizard flow controller for interactive init setup.

This module provides the WizardFlowController class that coordinates
the step-by-step wizard experience for project initialization.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


class WizardStep(Enum):
    """Enumeration of wizard steps in execution order."""

    BASICS = "basics"
    GIT = "git"
    PORTS = "ports"
    TASK_MANAGER = "task_manager"
    PHASES = "phases"
    LLM_RETRY = "llm_retry"
    SECURITY = "security"
    WEBHOOKS = "webhooks"
    SUMMARY = "summary"


class WizardFlowController:
    """Controls the wizard flow for interactive project initialization.

    The flow controller manages the sequence of wizard steps, handles
    navigation between steps, and coordinates state updates.

    Attributes:
        state: The current wizard state tracking progress and config.
        steps: Ordered list of wizard steps to execute.
        current_index: Index of the current step in the sequence.
    """

    STEP_SEQUENCE: list[WizardStep] = [
        WizardStep.BASICS,
        WizardStep.GIT,
        WizardStep.PORTS,
        WizardStep.TASK_MANAGER,
        WizardStep.PHASES,
        WizardStep.LLM_RETRY,
        WizardStep.SECURITY,
        WizardStep.WEBHOOKS,
        WizardStep.SUMMARY,
    ]

    def __init__(self, state: WizardState | None = None) -> None:
        """Initialize the flow controller.

        Args:
            state: Optional initial wizard state. If None, creates new state.
        """
        # Import here to avoid circular dependency at module level
        from adw.models.wizard import WizardState

        self.state = state if state is not None else WizardState()
        self.steps = self.STEP_SEQUENCE.copy()
        self.current_index = 0

    def run(self) -> None:
        """Execute the wizard flow sequentially.

        Runs through all wizard steps in order, updating state
        as each step completes.

        Note:
            Full implementation will be added in Task 4.
        """
        # Stub - full implementation in Task 4
        pass

    def get_current_step(self) -> WizardStep | None:
        """Get the current wizard step.

        Returns:
            The current WizardStep or None if wizard is complete.
        """
        if self.current_index >= len(self.steps):
            return None
        return self.steps[self.current_index]

    def advance(self) -> bool:
        """Advance to the next wizard step.

        Returns:
            True if advanced successfully, False if already at end.
        """
        if self.current_index >= len(self.steps) - 1:
            return False
        self.current_index += 1
        self.state.current_step = self.steps[self.current_index].value
        self.state.completed_steps.append(self.steps[self.current_index - 1].value)
        return True

    def go_back(self) -> bool:
        """Go back to the previous wizard step.

        Returns:
            True if went back successfully, False if already at start.
        """
        if self.current_index <= 0:
            return False
        self.current_index -= 1
        self.state.current_step = self.steps[self.current_index].value
        # Remove from completed if present
        prev_step = self.steps[self.current_index + 1].value
        if prev_step in self.state.completed_steps:
            self.state.completed_steps.remove(prev_step)
        return True
