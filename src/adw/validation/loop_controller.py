"""ValidationLoopController for managing validation loop execution.

This module provides the ValidationLoopController class that manages:
- Iteration counting and limits
- Stall detection for progress tracking
- Exit condition evaluation
- Auto-defer logic for remaining issues

Story 11.5: Iteration Limits and Exit Conditions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adw.validation.config import ValidationConfig

logger = logging.getLogger(__name__)


class ExitReason(str, Enum):
    """Reason why the validation loop exited.

    Attributes:
        ALL_RESOLVED: All issues were resolved, dismissed, or deferred.
        MAX_ITERATIONS: Maximum iteration limit was reached.
        STALL_DETECTED: No progress detected for consecutive iterations.
        USER_CANCELLED: User explicitly cancelled the loop.
    """

    ALL_RESOLVED = "ALL_RESOLVED"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    STALL_DETECTED = "STALL_DETECTED"
    USER_CANCELLED = "USER_CANCELLED"


@dataclass
class LoopState:
    """State tracking for the validation loop.

    Tracks iteration progress, issue counts, and stall detection data.

    Attributes:
        current_iteration: Current iteration number (0 = not started).
        total_issues_found: Total issues discovered across all iterations.
        issues_resolved: Number of issues successfully fixed.
        issues_dismissed: Number of issues triaged as dismiss.
        issues_deferred: Number of issues deferred for later.
        issues_remaining: Number of issues still needing fixes.
        stall_count: Consecutive iterations with no progress.
        last_progress_iteration: Last iteration where progress was made.
        previous_issue_fingerprints: Fingerprints from previous iteration.
    """

    current_iteration: int = 0
    total_issues_found: int = 0
    issues_resolved: int = 0
    issues_dismissed: int = 0
    issues_deferred: int = 0
    issues_remaining: int = 0
    stall_count: int = 0
    last_progress_iteration: int = 0
    previous_issue_fingerprints: set[str] = field(default_factory=set)


class ValidationLoopController:
    """Controller for managing the validation loop execution.

    The controller tracks iteration state, detects stalls, evaluates
    exit conditions, and handles auto-deferral of remaining issues
    when the loop must exit.

    Attributes:
        config: ValidationConfig with loop limits.
        state: Current LoopState tracking iteration progress.

    Example:
        >>> controller = ValidationLoopController(config)
        >>> while True:
        ...     iteration = controller.start_iteration()
        ...     # Run validators, triage, fix...
        ...     should_exit, reason = controller.should_exit()
        ...     if should_exit:
        ...         break
    """

    def __init__(self, config: ValidationConfig) -> None:
        """Initialize the loop controller.

        Args:
            config: ValidationConfig containing loop limits.
        """
        self.config = config
        self.state = LoopState()

    def start_iteration(self) -> int:
        """Start a new iteration and return the iteration number.

        Increments the iteration counter and returns the new value.
        Call this at the start of each validation loop iteration.

        Returns:
            The new iteration number (1-indexed).
        """
        self.state.current_iteration += 1
        logger.debug(
            "Starting iteration %d/%d",
            self.state.current_iteration,
            self.config.max_iterations,
        )
        return self.state.current_iteration


__all__ = ["ExitReason", "LoopState", "ValidationLoopController"]
