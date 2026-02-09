"""Tests for simplified ValidationPhase (Story 16.4).

Tests cover:
- ValidationPhase initialization
- ValidationPhase.run() method
- ValidationPhase.from_llm_response() method
- Integration with ValidationConfig
"""

from datetime import UTC, datetime

import pytest

from adw.models import RunContext
from adw.validation import ValidationConfig
from adw.validation.models import ValidationResult
from adw.validation.phase import ValidationPhase


class TestValidationPhaseInit:
    """Tests for ValidationPhase initialization."""

    def test_default_config(self) -> None:
        """ValidationPhase uses default config when none provided."""
        phase = ValidationPhase()
        assert phase.config is not None
        assert isinstance(phase.config, ValidationConfig)

    def test_custom_config(self) -> None:
        """ValidationPhase accepts custom config."""
        config = ValidationConfig(timeout_seconds=1200)
        phase = ValidationPhase(config=config)
        assert phase.config.timeout_seconds == 1200

    def test_run_id_stored(self) -> None:
        """ValidationPhase stores run_id for logging."""
        phase = ValidationPhase(run_id="test-run-123")
        assert phase._run_id == "test-run-123"


class TestValidationPhaseRun:
    """Tests for ValidationPhase.run() method."""

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

    def test_run_returns_validation_result(self, mock_context: RunContext) -> None:
        """run() returns a ValidationResult."""
        phase = ValidationPhase()
        result = phase.run(mock_context)
        assert isinstance(result, ValidationResult)

    def test_run_returns_default_failed_result(self, mock_context: RunContext) -> None:
        """run() returns failed result indicating LLM execution needed."""
        phase = ValidationPhase()
        result = phase.run(mock_context)

        # Default result is failed since LLM hasn't run
        assert result.passed is False
        # Check that there's some indication about needing LLM execution
        has_indicator = (
            any(
                "not yet executed" in issue.lower() for issue in result.issues_remaining
            )
            or "not yet executed" in result.summary.lower()
            or "requires" in result.summary.lower()
        )
        assert has_indicator


class TestFromLLMResponse:
    """Tests for ValidationPhase.from_llm_response() method."""

    def test_from_llm_response_valid_json(self) -> None:
        """from_llm_response creates ValidationResult from valid JSON."""
        response = {
            "passed": True,
            "tests_passed": True,
            "code_review_passed": True,
            "issues_fixed": ["Fixed null check"],
            "issues_remaining": [],
            "summary": "All tests pass",
        }

        result = ValidationPhase.from_llm_response(response)

        assert result.passed is True
        assert result.tests_passed is True
        assert result.issues_fixed == ["Fixed null check"]

    def test_from_llm_response_with_failures(self) -> None:
        """from_llm_response handles failed validation JSON."""
        response = {
            "passed": False,
            "tests_passed": False,
            "code_review_passed": True,
            "issues_fixed": [],
            "issues_remaining": ["Test test_login fails"],
            "summary": "Tests failing",
        }

        result = ValidationPhase.from_llm_response(response)

        assert result.passed is False
        assert result.tests_passed is False
        assert result.code_review_passed is True
        assert "test_login" in result.issues_remaining[0]

    def test_from_llm_response_missing_required_fields(self) -> None:
        """from_llm_response raises ValueError for missing required fields."""
        response = {
            "passed": True,
            # Missing tests_passed and code_review_passed
        }

        with pytest.raises(ValueError):
            ValidationPhase.from_llm_response(response)

    def test_from_llm_response_with_defaults(self) -> None:
        """from_llm_response uses defaults for optional fields."""
        response = {
            "passed": True,
            "tests_passed": True,
            "code_review_passed": True,
            # No issues_fixed, issues_remaining, or summary
        }

        result = ValidationPhase.from_llm_response(response)

        assert result.passed is True
        assert result.issues_fixed == []
        assert result.issues_remaining == []
        assert result.summary == ""


class TestValidationPhaseIntegration:
    """Integration tests for ValidationPhase with other components."""

    def test_full_validation_flow(self) -> None:
        """Test full validation flow from LLM response to result."""
        # Simulate what the orchestrator does:
        # 1. Execute validation prompt via LLM executor
        # 2. Parse JSON response
        # 3. Create ValidationResult

        llm_json_response = {
            "passed": True,
            "tests_passed": True,
            "code_review_passed": True,
            "issues_fixed": [
                "Fixed missing error handling in auth module",
                "Added null check in user validation",
            ],
            "issues_remaining": [],
            "summary": "All tests pass. Fixed 2 minor issues during validation.",
        }

        # Parse response using the phase helper
        result = ValidationPhase.from_llm_response(llm_json_response)

        # Verify result
        assert result.passed is True
        assert len(result.issues_fixed) == 2
        assert "auth module" in result.issues_fixed[0]
        assert result.summary.startswith("All tests")


class TestValidationResultCreation:
    """Tests for creating ValidationResult from various sources."""

    def test_create_from_dict(self) -> None:
        """ValidationResult can be created from dict."""
        data = {
            "passed": False,
            "tests_passed": True,
            "code_review_passed": False,
            "issues_fixed": [],
            "issues_remaining": ["Security concern in user input handling"],
            "summary": "Tests pass but code review found issues",
        }

        result = ValidationResult.model_validate(data)

        assert result.passed is False
        assert result.code_review_passed is False

    def test_result_allows_mutation(self) -> None:
        """ValidationResult allows mutation (frozen=False in config)."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
        )

        # Should be able to mutate
        result.passed = False
        assert result.passed is False

    def test_validation_result_passed_when_all_pass(self) -> None:
        """ValidationResult.passed is True when tests and review pass."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=[],
            issues_remaining=[],
            summary="All good",
        )
        assert result.passed is True

    def test_validation_result_failed_with_remaining_issues(self) -> None:
        """ValidationResult.passed is False when there are remaining issues."""
        result = ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=True,
            issues_fixed=["Fixed one thing"],
            issues_remaining=["This test still fails"],
            summary="One test failing",
        )
        assert result.passed is False
        assert len(result.issues_remaining) == 1
