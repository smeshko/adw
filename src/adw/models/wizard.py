"""Wizard state model for tracking interactive init progress.

This module provides the WizardState model that tracks the wizard's
progress through configuration steps and collects user input.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field


class WizardState(BaseModel):
    """Tracks wizard progress and collected configuration.

    The WizardState model maintains the current position in the wizard,
    tracks completed steps, accumulates configuration as the user
    progresses through each step, and maintains navigation history
    for back/forward support.

    Attributes:
        current_step: The current wizard step identifier.
        completed_steps: List of step identifiers that have been completed.
        collected_config: Configuration values collected from each step.
        navigation_history: Ordered list of steps visited for back navigation.
        history_position: Current position in navigation history (-1 means at end).
    """

    current_step: str = Field(default="basics", description="Current wizard step")
    completed_steps: list[str] = Field(
        default_factory=list, description="List of completed step identifiers"
    )
    collected_config: dict[str, Any] = Field(
        default_factory=dict, description="Configuration collected from wizard steps"
    )
    navigation_history: list[str] = Field(
        default_factory=lambda: ["basics"],
        description="Ordered list of visited steps for navigation",
    )
    history_position: int = Field(
        default=0, description="Current position in navigation history"
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
            True if there is history to go back to.
        """
        return self.history_position > 0

    def can_go_forward(self) -> bool:
        """Check if navigation forward is possible.

        Returns:
            True if there are steps ahead in history (after going back).
        """
        return self.history_position < len(self.navigation_history) - 1

    def navigate_to(self, step: str) -> None:
        """Navigate to a new step, updating history.

        When navigating forward to a new step (not via back/forward),
        this truncates any forward history and appends the new step.

        Args:
            step: The step identifier to navigate to.
        """
        # If we're not at the end of history, truncate forward history
        if self.history_position < len(self.navigation_history) - 1:
            self.navigation_history = self.navigation_history[
                : self.history_position + 1
            ]

        # Add new step to history if different from current
        if not self.navigation_history or self.navigation_history[-1] != step:
            self.navigation_history.append(step)
            self.history_position = len(self.navigation_history) - 1

        self.current_step = step

    def go_back_in_history(self) -> str | None:
        """Move back one step in navigation history.

        Returns:
            The previous step identifier, or None if can't go back.
        """
        if not self.can_go_back():
            return None

        self.history_position -= 1
        self.current_step = self.navigation_history[self.history_position]
        return self.current_step

    def go_forward_in_history(self) -> str | None:
        """Move forward one step in navigation history.

        Returns:
            The next step identifier, or None if can't go forward.
        """
        if not self.can_go_forward():
            return None

        self.history_position += 1
        self.current_step = self.navigation_history[self.history_position]
        return self.current_step

    def update_config(self, step: str, config: dict[str, Any]) -> None:
        """Update collected configuration for a step.

        Args:
            step: The step identifier.
            config: Configuration values to store for this step.
        """
        self.collected_config[step] = config

    def get_step_config(self, step: str) -> dict[str, Any]:
        """Get collected configuration for a specific step.

        Args:
            step: The step identifier.

        Returns:
            Configuration dict for the step, or empty dict if none.
        """
        result = self.collected_config.get(step, {})
        return cast(dict[str, Any], result)
