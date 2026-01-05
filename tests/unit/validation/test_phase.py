"""Unit tests for ValidationPhase class.

Tests for the unified validation phase that combines evidence gathering,
code review, and test execution.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.models import RunContext
from adw.models.phase import PhaseResult, PhaseStatus
from adw.validation import ValidationPhase
from adw.validation.models import (
    IssueSeverity,
    ValidationIssue,
    ValidationResult,
    ValidationSource,
)


class TestValidationPhase:
    """Test cases for ValidationPhase class."""

    @pytest.fixture
    def mock_context(self) -> RunContext:
        """Create a mock RunContext for testing."""
        return RunContext(
            run_id="01HQ0000000000000000000000",
            feature_description="Test feature",
            current_phase="validation",
            phase_history=["plan", "build"],
            started_at=datetime.now(UTC),
            completed_at=None,
            status="running",
            artifacts={},
            phase_tokens={},
            worktree_path=None,
            use_worktree=False,
            branch_name=None,
        )

    @pytest.fixture
    def validation_phase(self) -> ValidationPhase:
        """Create a ValidationPhase instance for testing."""
        return ValidationPhase()

    def test_run_all_validators_pass(
        self, validation_phase: ValidationPhase, mock_context: RunContext
    ) -> None:
        """Phase completes successfully when all validators pass."""
        # Arrange - mock validators to return no issues
        with patch.object(
            validation_phase, "_run_validators", return_value=[]
        ):
            # Act
            result = validation_phase.run(mock_context)

            # Assert
            assert isinstance(result, ValidationResult)
            assert result.passed is True
            assert result.issues == []
            assert result.iteration == 1

    def test_run_collects_all_issues(
        self, validation_phase: ValidationPhase, mock_context: RunContext
    ) -> None:
        """Phase aggregates issues from all validators."""
        # Arrange - mock validators to return issues
        mock_issues = [
            ValidationIssue(
                source=ValidationSource.TEST,
                message="Test failed: test_example",
                severity="high",
                file_path="tests/test_example.py",
                line_number=10,
            ),
            ValidationIssue(
                source=ValidationSource.REVIEW,
                message="Missing error handling",
                severity="medium",
                file_path="src/main.py",
                line_number=25,
            ),
        ]
        with patch.object(
            validation_phase, "_run_validators", return_value=mock_issues
        ):
            # Act
            result = validation_phase.run(mock_context)

            # Assert
            assert isinstance(result, ValidationResult)
            assert result.passed is False
            assert len(result.issues) == 2
            assert result.issues[0].source == ValidationSource.TEST
            assert result.issues[1].source == ValidationSource.REVIEW

    def test_run_respects_config_disabled(
        self, mock_context: RunContext
    ) -> None:
        """Disabled validators are not executed."""
        from adw.validation.config import ValidationConfig

        # Create mock validators
        test_validator = MagicMock()
        test_validator.name = "test"
        test_validator.validate.return_value = [
            ValidationIssue(
                source=ValidationSource.TEST,
                message="Test issue",
                severity="low",
            )
        ]

        review_validator = MagicMock()
        review_validator.name = "review"
        review_validator.validate.return_value = [
            ValidationIssue(
                source=ValidationSource.REVIEW,
                message="Review issue",
                severity="medium",
            )
        ]

        # Config disables evidence and review, enables tests
        config = ValidationConfig(
            enable_evidence=False,
            enable_review=False,
            enable_tests=True,
        )
        phase = ValidationPhase(config=config)

        # Register both validators
        phase.register_validator(test_validator)
        phase.register_validator(review_validator)

        # Act
        result = phase.run(mock_context)

        # Assert - only test validator should have been called
        test_validator.validate.assert_called_once_with(mock_context)
        review_validator.validate.assert_not_called()
        assert isinstance(result, ValidationResult)
        assert len(result.issues) == 1
        assert result.issues[0].source == ValidationSource.TEST

    def test_run_continues_after_validator_error(
        self, mock_context: RunContext
    ) -> None:
        """Phase continues to next validator on error and creates issue for crash."""
        # Create a validator that crashes
        crashing_validator = MagicMock()
        crashing_validator.name = "test"
        crashing_validator.validate.side_effect = RuntimeError("Validator crashed!")

        # Create a validator that succeeds
        working_validator = MagicMock()
        working_validator.name = "review"
        working_validator.validate.return_value = [
            ValidationIssue(
                source=ValidationSource.REVIEW,
                message="Found a review issue",
                severity="medium",
            )
        ]

        phase = ValidationPhase()
        phase.register_validator(crashing_validator)
        phase.register_validator(working_validator)

        # Act
        result = phase.run(mock_context)

        # Assert - both validators were called
        crashing_validator.validate.assert_called_once_with(mock_context)
        working_validator.validate.assert_called_once_with(mock_context)

        # Assert - phase returned issues from both
        assert isinstance(result, ValidationResult)
        assert result.passed is False  # Has issues, so should fail
        assert len(result.issues) == 2

        # Check that crash created an issue
        crash_issues = [i for i in result.issues if "crashed" in i.message.lower()]
        assert len(crash_issues) == 1
        assert crash_issues[0].severity == IssueSeverity.ERROR  # critical maps to ERROR
        assert crash_issues[0].source == ValidationSource.TEST

        # Check working validator issue was also collected
        review_issues = [i for i in result.issues if i.source == ValidationSource.REVIEW]
        assert len(review_issues) == 1

    def test_run_returns_validation_result(
        self, validation_phase: ValidationPhase, mock_context: RunContext
    ) -> None:
        """Phase returns proper ValidationResult structure."""
        with patch.object(validation_phase, "_run_validators", return_value=[]):
            # Act
            result = validation_phase.run(mock_context)

            # Assert
            assert isinstance(result, ValidationResult)
            assert hasattr(result, "passed")
            assert hasattr(result, "issues")
            assert hasattr(result, "iteration")
            assert isinstance(result.passed, bool)
            assert isinstance(result.issues, list)
            assert isinstance(result.iteration, int)


class TestValidationResult:
    """Test cases for ValidationResult model."""

    def test_validation_result_passed_when_no_issues(self) -> None:
        """ValidationResult.passed is True when issues list is empty."""
        result = ValidationResult(passed=True, issues=[], iteration=1)
        assert result.passed is True
        assert len(result.issues) == 0

    def test_validation_result_failed_with_issues(self) -> None:
        """ValidationResult.passed is False when issues exist."""
        issues = [
            ValidationIssue(
                source=ValidationSource.TEST,
                message="Test failed",
                severity="high",
            )
        ]
        result = ValidationResult(passed=False, issues=issues, iteration=1)
        assert result.passed is False
        assert len(result.issues) == 1

    def test_validation_result_tracks_iteration(self) -> None:
        """ValidationResult tracks iteration number."""
        result = ValidationResult(passed=True, issues=[], iteration=3)
        assert result.iteration == 3


class TestValidationIssue:
    """Test cases for ValidationIssue model."""

    def test_validation_issue_test_source(self) -> None:
        """ValidationIssue can have TEST source."""
        issue = ValidationIssue(
            source=ValidationSource.TEST,
            message="Test failed: test_something",
            severity="high",  # Legacy string, normalized to ERROR
            file_path="tests/test_something.py",
            line_number=42,
        )
        assert issue.source == ValidationSource.TEST
        assert issue.severity == IssueSeverity.ERROR  # high maps to ERROR
        assert issue.location.file_path == "tests/test_something.py"
        assert issue.location.line_start == 42

    def test_validation_issue_review_source(self) -> None:
        """ValidationIssue can have REVIEW source."""
        issue = ValidationIssue(
            source=ValidationSource.REVIEW,
            message="Security vulnerability detected",
            severity="critical",  # Legacy string, normalized to ERROR
        )
        assert issue.source == ValidationSource.REVIEW
        assert issue.severity == IssueSeverity.ERROR  # critical maps to ERROR

    def test_validation_issue_evidence_source(self) -> None:
        """ValidationIssue can have EVIDENCE source."""
        issue = ValidationIssue(
            source=ValidationSource.EVIDENCE,
            message="Missing screenshot for login flow",
            severity="medium",
        )
        assert issue.source == ValidationSource.EVIDENCE

    def test_validation_issue_optional_fields(self) -> None:
        """ValidationIssue has optional file_path and line_number."""
        issue = ValidationIssue(
            source=ValidationSource.TEST,
            message="Generic test failure",
            severity="low",
        )
        assert issue.file_path is None
        assert issue.line_number is None


class TestValidationPhaseStatePersistence:
    """Tests for ValidationPhase state persistence integration."""

    @pytest.fixture
    def mock_context(self) -> RunContext:
        """Create a mock RunContext for testing."""
        return RunContext(
            run_id="01HQ0000000000000000000000",
            feature_description="Test feature",
            current_phase="validation",
            phase_history=["plan", "build"],
            started_at=datetime.now(UTC),
            completed_at=None,
            status="running",
            artifacts={},
            phase_tokens={},
            worktree_path=None,
            use_worktree=False,
            branch_name=None,
        )

    def test_phase_saves_state_after_iteration(
        self, tmp_path: Path, mock_context: RunContext
    ) -> None:
        """Phase saves state after each iteration when state manager configured."""
        from pathlib import Path

        # Create runs directory structure
        run_id = "run-123"
        runs_dir = tmp_path / ".adw" / "runs"
        (runs_dir / run_id).mkdir(parents=True)

        # Create phase with state manager
        phase = ValidationPhase(run_id=run_id, runs_dir=runs_dir)

        # Mock validators to return some issues
        mock_issues = [
            ValidationIssue(
                source=ValidationSource.TEST,
                message="Test failed",
                severity="high",
            )
        ]
        with patch.object(phase, "_run_validators", return_value=mock_issues):
            phase.run(mock_context)

        # Verify state was saved
        assert phase.state_manager is not None
        assert phase.state_manager.state_file.exists()
        assert phase.state_manager.issues_file.exists()

    def test_phase_clears_state_on_success(
        self, tmp_path: Path, mock_context: RunContext
    ) -> None:
        """Phase clears state when validation passes (no issues)."""
        from pathlib import Path

        # Create runs directory structure
        run_id = "run-456"
        runs_dir = tmp_path / ".adw" / "runs"
        (runs_dir / run_id).mkdir(parents=True)

        # Create phase with state manager
        phase = ValidationPhase(run_id=run_id, runs_dir=runs_dir)

        # Mock validators to return no issues (pass)
        with patch.object(phase, "_run_validators", return_value=[]):
            result = phase.run(mock_context)

        # Verify validation passed
        assert result.passed is True

        # Verify state was cleared
        assert phase.state_manager is not None
        assert not phase.state_manager.state_file.exists()
        assert not phase.state_manager.issues_file.exists()

    def test_phase_resumes_from_saved_state(
        self, tmp_path: Path, mock_context: RunContext
    ) -> None:
        """Phase resumes from saved state when available."""
        from adw.validation.models import LoopState, ValidationState
        from adw.validation.state_manager import ValidationStateManager

        # Create runs directory structure
        run_id = "run-789"
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        # Pre-create saved state at iteration 3
        state_manager = ValidationStateManager(run_id, run_dir)
        saved_state = ValidationState(
            run_id=run_id,
            current_iteration=3,
            total_iterations=5,
            loop_state=LoopState(issues_remaining=2),
        )
        state_manager.save_state(saved_state)

        # Create phase - should resume
        phase = ValidationPhase(run_id=run_id, runs_dir=runs_dir)

        # Verify iteration was restored
        assert phase._iteration == 3

    def test_phase_without_state_manager_still_works(
        self, mock_context: RunContext
    ) -> None:
        """Phase works normally without state manager (no run_id)."""
        phase = ValidationPhase()

        # Mock validators
        with patch.object(phase, "_run_validators", return_value=[]):
            result = phase.run(mock_context)

        # Verify it works
        assert result.passed is True
        assert phase.state_manager is None

    def test_phase_preserves_loop_state_counters(
        self, tmp_path: Path, mock_context: RunContext
    ) -> None:
        """Phase preserves loop state counters when saving state."""
        from adw.validation.models import LoopState, ValidationState
        from adw.validation.state_manager import ValidationStateManager

        # Create runs directory structure
        run_id = "run-counters"
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        # Pre-create saved state with non-zero counters
        state_manager = ValidationStateManager(run_id, run_dir)
        saved_state = ValidationState(
            run_id=run_id,
            current_iteration=2,
            total_iterations=5,
            loop_state=LoopState(
                issues_resolved=5,
                issues_dismissed=2,
                issues_deferred=1,
                issues_remaining=3,
                stall_count=1,
            ),
        )
        state_manager.save_state(saved_state)

        # Create phase - should resume with existing state
        phase = ValidationPhase(run_id=run_id, runs_dir=runs_dir)

        # Mock validators to return 2 issues (updating issues_remaining)
        mock_issues = [
            ValidationIssue(
                source=ValidationSource.TEST,
                message="Issue 1",
                severity="high",
            ),
            ValidationIssue(
                source=ValidationSource.TEST,
                message="Issue 2",
                severity="medium",
            ),
        ]
        with patch.object(phase, "_run_validators", return_value=mock_issues):
            phase.run(mock_context)

        # Load the saved state and verify counters were preserved
        loaded_state = state_manager.load_state_model()
        assert loaded_state is not None
        # Existing counters should be preserved
        assert loaded_state.loop_state.issues_resolved == 5
        assert loaded_state.loop_state.issues_dismissed == 2
        assert loaded_state.loop_state.issues_deferred == 1
        assert loaded_state.loop_state.stall_count == 1
        # issues_remaining should be updated to current issue count
        assert loaded_state.loop_state.issues_remaining == 2

    def test_phase_uses_config_max_iterations_for_total(
        self, tmp_path: Path, mock_context: RunContext
    ) -> None:
        """Phase uses config.max_iterations for total_iterations in state."""
        from adw.validation.config import ValidationConfig
        from adw.validation.state_manager import ValidationStateManager

        # Create runs directory structure
        run_id = "run-max-iter"
        runs_dir = tmp_path / ".adw" / "runs"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)

        # Create config with custom max_iterations (not the default 5)
        config = ValidationConfig(max_iterations=3)
        phase = ValidationPhase(config=config, run_id=run_id, runs_dir=runs_dir)

        # Mock validators to return one issue
        mock_issues = [
            ValidationIssue(
                source=ValidationSource.TEST,
                message="Test issue",
                severity="medium",
            )
        ]
        with patch.object(phase, "_run_validators", return_value=mock_issues):
            phase.run(mock_context)

        # Load the saved state and verify total_iterations matches config
        state_manager = ValidationStateManager(run_id, run_dir)
        loaded_state = state_manager.load_state_model()
        assert loaded_state is not None
        # total_iterations should match config, not default 5
        assert loaded_state.total_iterations == 3
