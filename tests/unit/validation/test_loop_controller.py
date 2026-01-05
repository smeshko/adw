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


class TestCheckProgress:
    """Tests for check_progress() stall detection."""

    def test_check_progress_detects_stall_same_issues(self) -> None:
        """Stall detected when issue fingerprints unchanged."""
        from adw.validation.models import IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig())
        controller.start_iteration()

        # Create issues with FIX triage decision
        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description="Test failure 1",
            ),
            ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description="Test failure 2",
            ),
        ]
        # Mark as FIX for progress tracking
        for issue in issues:
            issue.triage_decision = "FIX"
            issue.fix_attempt_count = 0

        # First check - establishes baseline
        progress_made = controller.check_progress(issues)
        assert progress_made is True
        assert controller.state.stall_count == 0

        # Second check with same issues - stall detected
        progress_made = controller.check_progress(issues)
        assert progress_made is False
        assert controller.state.stall_count == 1

    def test_check_progress_resets_on_change(self) -> None:
        """Stall counter resets when progress is made."""
        from adw.validation.models import IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig())
        controller.start_iteration()

        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description="Test failure 1",
            ),
        ]
        issues[0].triage_decision = "FIX"
        issues[0].fix_attempt_count = 0

        # Establish baseline
        controller.check_progress(issues)

        # Same issues - stall
        controller.check_progress(issues)
        assert controller.state.stall_count == 1

        # Same issues again - 2 stalls
        controller.check_progress(issues)
        assert controller.state.stall_count == 2

        # Now change fix_attempt_count - progress!
        issues[0].fix_attempt_count = 1
        progress_made = controller.check_progress(issues)
        assert progress_made is True
        assert controller.state.stall_count == 0  # Reset

    def test_check_progress_only_tracks_fix_issues(self) -> None:
        """Only FIX-triaged issues contribute to fingerprint."""
        from adw.validation.models import IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig())
        controller.start_iteration()

        # One FIX, one DEFER
        fix_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity="ERROR",
            description="Must fix",
        )
        fix_issue.triage_decision = "FIX"
        fix_issue.fix_attempt_count = 0

        defer_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity="WARNING",
            description="Deferred",
        )
        defer_issue.triage_decision = "DEFER"

        issues = [fix_issue, defer_issue]

        # Establish baseline
        controller.check_progress(issues)

        # Change defer issue - should not affect progress (it's not FIX)
        defer_issue.description = "Changed description"
        progress_made = controller.check_progress(issues)
        assert progress_made is False  # Stall - only FIX issue matters

    def test_check_progress_updates_last_progress_iteration(self) -> None:
        """last_progress_iteration updated when progress made."""
        from adw.validation.models import IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig())
        controller.start_iteration()
        assert controller.state.current_iteration == 1

        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description="Issue",
            ),
        ]
        issues[0].triage_decision = "FIX"
        issues[0].fix_attempt_count = 0

        # First progress
        controller.check_progress(issues)
        assert controller.state.last_progress_iteration == 1

        # Stall
        controller.start_iteration()
        controller.check_progress(issues)
        assert controller.state.last_progress_iteration == 1  # Unchanged

        # Progress again
        controller.start_iteration()
        issues[0].fix_attempt_count = 1
        controller.check_progress(issues)
        assert controller.state.last_progress_iteration == 3


class TestUpdateCounts:
    """Tests for update_counts() state tracking."""

    def test_update_counts_tracks_resolved_issues(self) -> None:
        """update_counts correctly counts resolved issues."""
        from adw.validation.models import FixResult, IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig())

        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description="Issue 1",
            ),
            ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description="Issue 2",
            ),
        ]
        # One resolved, one not
        issues[0].last_fix_result = FixResult.RESOLVED
        issues[1].triage_decision = "FIX"

        controller.update_counts(issues)

        assert controller.state.issues_resolved == 1
        assert controller.state.issues_remaining == 1

    def test_update_counts_tracks_all_categories(self) -> None:
        """update_counts tracks resolved, dismissed, deferred, remaining."""
        from adw.validation.models import FixResult, IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig())

        issues = []

        # 2 resolved
        for i in range(2):
            issue = ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description=f"Resolved {i}",
            )
            issue.last_fix_result = FixResult.RESOLVED
            issues.append(issue)

        # 3 dismissed
        for i in range(3):
            issue = ValidationIssue(
                source=IssueSource.TEST,
                severity="INFO",
                description=f"Dismissed {i}",
            )
            issue.triage_decision = "DISMISS"
            issues.append(issue)

        # 1 deferred
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity="WARNING",
            description="Deferred",
        )
        issue.triage_decision = "DEFER"
        issues.append(issue)

        # 4 remaining (FIX)
        for i in range(4):
            issue = ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description=f"Fix {i}",
            )
            issue.triage_decision = "FIX"
            issues.append(issue)

        controller.update_counts(issues)

        assert controller.state.issues_resolved == 2
        assert controller.state.issues_dismissed == 3
        assert controller.state.issues_deferred == 1
        assert controller.state.issues_remaining == 4

    def test_update_counts_sets_total_issues_found(self) -> None:
        """update_counts tracks total issues found."""
        from adw.validation.models import IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig())

        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description=f"Issue {i}",
            )
            for i in range(5)
        ]

        controller.update_counts(issues)

        assert controller.state.total_issues_found == 5


class TestAutoDeferRemaining:
    """Tests for auto_defer_remaining() functionality."""

    def test_auto_defer_changes_fix_to_defer(self) -> None:
        """Auto-defer changes FIX issues to DEFER."""
        from adw.validation.models import IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig(max_iterations=3))
        controller.start_iteration()
        controller.start_iteration()
        controller.start_iteration()  # At max iterations

        # Create FIX issues
        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description="Must fix 1",
            ),
            ValidationIssue(
                source=IssueSource.TEST,
                severity="ERROR",
                description="Must fix 2",
            ),
        ]
        for issue in issues:
            issue.triage_decision = "FIX"

        # Auto-defer due to max iterations
        deferred = controller.auto_defer_remaining(issues, ExitReason.MAX_ITERATIONS)

        for issue in deferred:
            assert issue.triage_decision == "DEFER"
            assert "Max iterations reached" in issue.triage_reason

    def test_auto_defer_sets_reason_for_stall(self) -> None:
        """Auto-defer sets appropriate reason for stall exit."""
        from adw.validation.models import IssueSource, ValidationIssue

        controller = ValidationLoopController(
            ValidationConfig(max_iterations=10, stall_threshold=2)
        )
        controller.start_iteration()
        controller.state.stall_count = 2  # Stall detected

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity="ERROR",
            description="Stalled issue",
        )
        issue.triage_decision = "FIX"

        deferred = controller.auto_defer_remaining([issue], ExitReason.STALL_DETECTED)

        assert deferred[0].triage_decision == "DEFER"
        assert "No progress" in deferred[0].triage_reason

    def test_auto_defer_skips_non_fix_issues(self) -> None:
        """Auto-defer only affects FIX-triaged issues."""
        from adw.validation.models import IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig(max_iterations=3))
        controller.start_iteration()
        controller.start_iteration()
        controller.start_iteration()

        fix_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity="ERROR",
            description="Needs fixing",
        )
        fix_issue.triage_decision = "FIX"

        dismiss_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity="INFO",
            description="Dismissed",
        )
        dismiss_issue.triage_decision = "DISMISS"

        defer_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity="WARNING",
            description="Already deferred",
        )
        defer_issue.triage_decision = "DEFER"

        result = controller.auto_defer_remaining(
            [fix_issue, dismiss_issue, defer_issue], ExitReason.MAX_ITERATIONS
        )

        assert result[0].triage_decision == "DEFER"  # FIX -> DEFER
        assert result[1].triage_decision == "DISMISS"  # Unchanged
        assert result[2].triage_decision == "DEFER"  # Already DEFER

    def test_auto_defer_logs_decisions(self, caplog: pytest.LogCaptureFixture) -> None:
        """Auto-defer logs each deferred issue."""
        import logging

        from adw.validation.models import IssueSource, ValidationIssue

        controller = ValidationLoopController(ValidationConfig(max_iterations=2))
        controller.start_iteration()
        controller.start_iteration()

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity="ERROR",
            description="To defer",
        )
        issue.triage_decision = "FIX"

        with caplog.at_level(logging.INFO):
            controller.auto_defer_remaining([issue], ExitReason.MAX_ITERATIONS)

        assert any("Auto-deferring" in record.message for record in caplog.records)


class TestShouldExit:
    """Tests for should_exit() exit condition checks."""

    def test_should_exit_max_iterations_reached(self) -> None:
        """Exit when current_iteration >= max_iterations."""
        config = ValidationConfig(max_iterations=3)
        controller = ValidationLoopController(config)

        # Simulate 3 iterations
        controller.start_iteration()
        controller.start_iteration()
        controller.start_iteration()

        should_exit, reason = controller.should_exit()

        assert should_exit is True
        assert reason == ExitReason.MAX_ITERATIONS

    def test_should_exit_all_resolved(self) -> None:
        """Exit when no remaining issues (all resolved/dismissed/deferred)."""
        config = ValidationConfig(max_iterations=5)
        controller = ValidationLoopController(config)
        controller.start_iteration()

        # Set state: no remaining issues
        controller.state.issues_remaining = 0
        controller.state.issues_resolved = 3
        controller.state.issues_dismissed = 1

        should_exit, reason = controller.should_exit()

        assert should_exit is True
        assert reason == ExitReason.ALL_RESOLVED

    def test_should_exit_stall_threshold_exceeded(self) -> None:
        """Exit when stall_count >= stall_threshold."""
        config = ValidationConfig(max_iterations=10, stall_threshold=2)
        controller = ValidationLoopController(config)
        controller.start_iteration()

        # Simulate 2 consecutive stalls
        controller.state.stall_count = 2
        controller.state.issues_remaining = 5  # Still have issues

        should_exit, reason = controller.should_exit()

        assert should_exit is True
        assert reason == ExitReason.STALL_DETECTED

    def test_should_not_exit_when_in_progress(self) -> None:
        """Continue when iterations remain and progress being made."""
        config = ValidationConfig(max_iterations=5, stall_threshold=2)
        controller = ValidationLoopController(config)
        controller.start_iteration()

        controller.state.issues_remaining = 3
        controller.state.stall_count = 0

        should_exit, reason = controller.should_exit()

        assert should_exit is False
        assert reason is None

    def test_should_exit_priority_max_iterations_over_stall(self) -> None:
        """Max iterations checked before stall threshold."""
        config = ValidationConfig(max_iterations=2, stall_threshold=3)
        controller = ValidationLoopController(config)

        controller.start_iteration()
        controller.start_iteration()
        controller.state.stall_count = 3  # Also exceeds stall threshold
        controller.state.issues_remaining = 5

        should_exit, reason = controller.should_exit()

        assert should_exit is True
        # Max iterations should be checked first
        assert reason == ExitReason.MAX_ITERATIONS
