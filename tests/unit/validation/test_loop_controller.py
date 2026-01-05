"""Tests for ValidationLoopController.

Story 11.5: Iteration Limits and Exit Conditions
Task 1: Create ValidationLoopController
"""

import pytest

from adw.validation.config import ValidationConfig
from adw.validation.loop_controller import (
    ExitReason,
    LoopState,
    ValidationLoopController,
)


class TestValidationLoopControllerInit:
    """Tests for ValidationLoopController initialization."""

    def test_init_with_default_config(self) -> None:
        """Controller initializes with default ValidationConfig."""
        controller = ValidationLoopController(ValidationConfig())

        assert controller.config.max_iterations == 5
        assert controller.config.stall_threshold == 2
        assert controller.state.current_iteration == 0

    def test_init_with_custom_config(self) -> None:
        """Controller respects custom config values."""
        config = ValidationConfig(
            max_iterations=10,
            stall_threshold=3,
            max_fix_attempts_per_issue=5,
        )
        controller = ValidationLoopController(config)

        assert controller.config.max_iterations == 10
        assert controller.config.stall_threshold == 3


class TestValidationLoopControllerIteration:
    """Tests for iteration tracking."""

    def test_start_iteration_increments_counter(self) -> None:
        """start_iteration increments and returns the iteration number."""
        controller = ValidationLoopController(ValidationConfig())

        iteration_1 = controller.start_iteration()
        assert iteration_1 == 1
        assert controller.state.current_iteration == 1

        iteration_2 = controller.start_iteration()
        assert iteration_2 == 2
        assert controller.state.current_iteration == 2

    def test_state_tracks_stall_count(self) -> None:
        """LoopState properly tracks stall count."""
        controller = ValidationLoopController(ValidationConfig())
        controller.start_iteration()

        assert controller.state.stall_count == 0
        controller.state.stall_count = 2
        assert controller.state.stall_count == 2


class TestLoopState:
    """Tests for LoopState dataclass."""

    def test_default_values(self) -> None:
        """LoopState has correct default values."""
        state = LoopState()

        assert state.current_iteration == 0
        assert state.total_issues_found == 0
        assert state.issues_resolved == 0
        assert state.issues_dismissed == 0
        assert state.issues_deferred == 0
        assert state.issues_remaining == 0
        assert state.stall_count == 0
        assert state.last_progress_iteration == 0
        assert state.previous_issue_fingerprints == set()


class TestExitReason:
    """Tests for ExitReason enum."""

    def test_exit_reason_values(self) -> None:
        """ExitReason has all required values."""
        assert ExitReason.ALL_RESOLVED.value == "ALL_RESOLVED"
        assert ExitReason.MAX_ITERATIONS.value == "MAX_ITERATIONS"
        assert ExitReason.STALL_DETECTED.value == "STALL_DETECTED"
        assert ExitReason.USER_CANCELLED.value == "USER_CANCELLED"
