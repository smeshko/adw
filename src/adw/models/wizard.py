"""Wizard state model for tracking interactive init progress.

This module provides the WizardState model that tracks the wizard's
progress through configuration steps and collects user input.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WizardState(BaseModel):
    """Tracks wizard progress and collected configuration.

    The WizardState model maintains the current position in the wizard,
    tracks completed steps, and accumulates configuration as the user
    progresses through each step.

    Attributes:
        current_step: The current wizard step identifier.
        completed_steps: List of step identifiers that have been completed.
        collected_config: Configuration values collected from each step.
    """

    current_step: str = Field(default="basics", description="Current wizard step")
    completed_steps: list[str] = Field(
        default_factory=list, description="List of completed step identifiers"
    )
    collected_config: dict[str, Any] = Field(
        default_factory=dict, description="Configuration collected from wizard steps"
    )

    def mark_completed(self, step: str) -> None:
        """Mark a step as completed.

        Args:
            step: The step identifier to mark as completed.
        """
        if step not in self.completed_steps:
            self.completed_steps.append(step)

    def can_go_back(self) -> bool:
        """Check if navigation back is possible.

        Returns:
            True if there are completed steps to return to.
        """
        return len(self.completed_steps) > 0

    def can_go_forward(self) -> bool:
        """Check if navigation forward is possible.

        Returns:
            True if the current step is in completed steps.
        """
        return self.current_step in self.completed_steps
