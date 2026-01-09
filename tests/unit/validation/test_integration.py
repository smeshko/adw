"""Integration tests for the simplified validation phase (Story 16.4).

Tests for the complete validation flow with the simplified model.
"""

from datetime import UTC, datetime

import pytest

from adw.models import RunContext
from adw.validation import ValidationConfig, ValidationPhase
from adw.validation.models import ValidationResult


@pytest.fixture
def mock_context() -> RunContext:
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


class TestValidationPhaseIntegration:
    """Integration tests for full validation phase execution."""

    def test_phase_returns_validation_result(
        self, mock_context: RunContext
    ) -> None:
        """Phase returns ValidationResult."""
        config = ValidationConfig(
            enable_tests=True,
            enable_review=True,
            enable_evidence=True,
        )
        phase = ValidationPhase(config=config)

        result = phase.run(mock_context)

        assert isinstance(result, ValidationResult)
        assert hasattr(result, "passed")
        assert hasattr(result, "tests_passed")
        assert hasattr(result, "code_review_passed")
        assert hasattr(result, "issues_fixed")
        assert hasattr(result, "issues_remaining")
        assert hasattr(result, "summary")

    def test_from_llm_response_integration(self) -> None:
        """ValidationPhase.from_llm_response creates valid result."""
        # Simulate LLM validation response JSON
        llm_response = {
            "passed": True,
            "tests_passed": True,
            "code_review_passed": True,
            "issues_fixed": [
                "Fixed null check in authentication handler",
                "Added error handling for network timeouts",
            ],
            "issues_remaining": [],
            "summary": "All tests pass, code review clean, validation successful",
        }

        result = ValidationPhase.from_llm_response(llm_response)

        assert isinstance(result, ValidationResult)
        assert result.passed is True
        assert result.tests_passed is True
        assert result.code_review_passed is True
        assert len(result.issues_fixed) == 2
        assert result.issues_remaining == []

    def test_from_llm_response_with_failures(self) -> None:
        """ValidationPhase.from_llm_response handles failed validation."""
        llm_response = {
            "passed": False,
            "tests_passed": False,
            "code_review_passed": True,
            "issues_fixed": ["Fixed one minor issue"],
            "issues_remaining": [
                "Test test_user_authentication still fails",
                "Database connection timeout in integration tests",
            ],
            "summary": "Some tests still failing after fixes",
        }

        result = ValidationPhase.from_llm_response(llm_response)

        assert result.passed is False
        assert result.tests_passed is False
        assert len(result.issues_remaining) == 2


class TestConfigBasedBehavior:
    """Tests for configuration-based validation behavior."""

    def test_config_settings_preserved(self) -> None:
        """ValidationPhase preserves config settings."""
        config = ValidationConfig(
            enable_tests=False,
            enable_review=True,
            enable_evidence=False,
        )
        phase = ValidationPhase(config=config)

        assert phase.config.enable_tests is False
        assert phase.config.enable_review is True
        assert phase.config.enable_evidence is False

    def test_default_config_enables_all(self) -> None:
        """Default config enables all validation types."""
        config = ValidationConfig()
        phase = ValidationPhase(config=config)

        assert phase.config.enable_tests is True
        assert phase.config.enable_review is True
        assert phase.config.enable_evidence is True


class TestValidationResultCreation:
    """Tests for creating ValidationResult objects."""

    def test_create_passing_result(self) -> None:
        """Create a passing validation result."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=[],
            issues_remaining=[],
            summary="All validation checks passed",
        )

        assert result.passed is True
        assert len(result.issues_fixed) == 0
        assert len(result.issues_remaining) == 0

    def test_create_failing_result(self) -> None:
        """Create a failing validation result."""
        result = ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=True,
            issues_fixed=["Fixed typo"],
            issues_remaining=["Test test_login still fails"],
            summary="Tests failing",
        )

        assert result.passed is False
        assert len(result.issues_remaining) == 1

    def test_result_serialization(self) -> None:
        """ValidationResult can be serialized to dict."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed issue"],
            issues_remaining=[],
            summary="Done",
        )

        data = result.model_dump()

        assert isinstance(data, dict)
        assert data["passed"] is True
        assert data["issues_fixed"] == ["Fixed issue"]
