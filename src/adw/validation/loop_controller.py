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
    from adw.validation.models import ValidationIssue

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

    def should_exit(self) -> tuple[bool, ExitReason | None]:
        """Check if the validation loop should exit.

        Evaluates exit conditions in priority order:
        1. Max iterations reached
        2. All issues resolved/dismissed/deferred (no remaining)
        3. Stall threshold exceeded

        Returns:
            Tuple of (should_exit, reason). If should_exit is False,
            reason will be None.
        """
        # Check max iterations first (highest priority)
        if self.state.current_iteration >= self.config.max_iterations:
            logger.info(
                "Max iterations reached: %d/%d",
                self.state.current_iteration,
                self.config.max_iterations,
            )
            return True, ExitReason.MAX_ITERATIONS

        # Check if all issues are resolved/dismissed/deferred
        if self.state.issues_remaining == 0:
            logger.info("All issues resolved, dismissed, or deferred")
            return True, ExitReason.ALL_RESOLVED

        # Check stall threshold
        if self.state.stall_count >= self.config.stall_threshold:
            logger.info(
                "Stall detected: %d consecutive iterations without progress",
                self.state.stall_count,
            )
            return True, ExitReason.STALL_DETECTED

        return False, None

    def check_progress(self, issues: list[ValidationIssue]) -> bool:
        """Check if progress was made since the last iteration.

        Compares issue fingerprints to detect if the state has changed.
        Progress is determined by changes to FIX-triaged issues only.

        If the same issues remain in the same state (same fingerprints),
        this is considered a stall and the stall counter is incremented.
        If progress is made, the stall counter is reset to 0.

        Args:
            issues: Current list of validation issues.

        Returns:
            True if progress was made, False if stalled.
        """
        current_fingerprints = self._compute_fingerprints(issues)

        if current_fingerprints == self.state.previous_issue_fingerprints:
            # No change - stall detected
            self.state.stall_count += 1
            logger.debug(
                "Stall detected (count: %d): fingerprints unchanged",
                self.state.stall_count,
            )
            return False
        else:
            # Progress made - reset stall counter
            self.state.stall_count = 0
            self.state.last_progress_iteration = self.state.current_iteration
            self.state.previous_issue_fingerprints = current_fingerprints
            logger.debug(
                "Progress made at iteration %d",
                self.state.current_iteration,
            )
            return True

    def _compute_fingerprints(
        self,
        issues: list[ValidationIssue],
    ) -> set[str]:
        """Compute fingerprints for stall detection.

        Only FIX-triaged issues are included in the fingerprint.
        The fingerprint includes the issue ID, triage decision, and
        fix attempt count to detect meaningful state changes.

        Args:
            issues: List of validation issues.

        Returns:
            Set of fingerprint strings for FIX issues.
        """
        return {
            f"{issue.id}:{issue.triage_decision}:{issue.fix_attempt_count}"
            for issue in issues
            if issue.triage_decision == "FIX"
        }

    def update_counts(self, issues: list[ValidationIssue]) -> None:
        """Update issue counts in state from current issues.

        Counts issues by their status and updates the state:
        - resolved: Issues with last_fix_result == RESOLVED
        - dismissed: Issues with triage_decision == DISMISS
        - deferred: Issues with triage_decision == DEFER
        - remaining: Issues with triage_decision == FIX

        Also updates total_issues_found.

        Args:
            issues: Current list of validation issues.
        """
        # Import here to avoid circular import
        from adw.validation.models import FixResult

        self.state.total_issues_found = len(issues)

        self.state.issues_resolved = sum(
            1 for i in issues if i.last_fix_result == FixResult.RESOLVED
        )
        self.state.issues_dismissed = sum(
            1 for i in issues if i.triage_decision == "DISMISS"
        )
        self.state.issues_deferred = sum(
            1 for i in issues if i.triage_decision == "DEFER"
        )
        self.state.issues_remaining = sum(
            1 for i in issues if i.triage_decision == "FIX"
        )

        logger.debug(
            "Updated counts: %d resolved, %d dismissed, %d deferred, %d remaining",
            self.state.issues_resolved,
            self.state.issues_dismissed,
            self.state.issues_deferred,
            self.state.issues_remaining,
        )

    def auto_defer_remaining(
        self,
        issues: list[ValidationIssue],
        reason: ExitReason,
    ) -> list[ValidationIssue]:
        """Auto-defer all remaining FIX issues when loop exits.

        When the loop must exit with remaining issues (max iterations,
        stall detection), this method changes all FIX-triaged issues
        to DEFER with an appropriate explanation.

        Args:
            issues: List of all validation issues.
            reason: The exit reason triggering the auto-defer.

        Returns:
            The modified list of issues with FIX changed to DEFER.
        """
        # Build reason text based on exit condition
        reason_text = {
            ExitReason.MAX_ITERATIONS: (
                f"Max iterations reached ({self.config.max_iterations})"
            ),
            ExitReason.STALL_DETECTED: (
                f"No progress after {self.state.stall_count} iterations"
            ),
        }.get(reason, "Loop exited")

        deferred_count = 0
        for issue in issues:
            if issue.triage_decision == "FIX":
                issue.triage_decision = "DEFER"
                issue.triage_reason = reason_text
                deferred_count += 1
                logger.info(
                    "Auto-deferring issue %s: %s",
                    issue.id,
                    reason_text,
                )

        if deferred_count > 0:
            logger.info(
                "Auto-deferred %d issues due to: %s",
                deferred_count,
                reason_text,
            )

        return issues


__all__ = ["ExitReason", "LoopState", "ValidationLoopController"]
