"""Integration tests for the unified validation phase.

Tests for the complete validation flow with all validators
wired together.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from adw.models import RunContext
from adw.models.llm import LLMResult
from adw.validation import (
    ValidationConfig,
    ValidationPhase,
    ValidatorRegistry,
)
from adw.validation.models import ValidationIssue, ValidationResult, ValidationSource
from adw.validation.validators import (
    EvidenceValidator,
    ReviewValidator,
    TestValidator,
)


@pytest.fixture
def mock_context() -> RunContext:
    """Create a mock RunContext for testing."""
    return RunContext(
        run_id="01HQ0000000000000000000000",
        feature_description="Test feature",
        current_phase="validation",
        phase_history=["plan", "build", "verify"],
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

    def test_phase_with_all_validators_passing(
        self, mock_context: RunContext
    ) -> None:
        """Phase passes when all validators find no issues."""
        # Create mocks
        mock_executor = MagicMock()
        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="No issues found. The code looks good!",
            tool_calls=[],
            tokens_used=100,
        )

        # Create validators
        config = ValidationConfig(
            enable_tests=True,
            enable_review=True,
            enable_evidence=True,
        )
        phase = ValidationPhase(config=config)

        # Register validators with mocked behavior
        test_validator = TestValidator(test_command="pytest")
        review_validator = ReviewValidator(executor=mock_executor, config=config)
        evidence_validator = EvidenceValidator()

        # Mock the individual validators to return no issues
        with patch.object(test_validator, "validate", return_value=[]):
            with patch.object(review_validator, "validate", return_value=[]):
                with patch.object(evidence_validator, "validate", return_value=[]):
                    phase.register_validator(test_validator)
                    phase.register_validator(review_validator)
                    phase.register_validator(evidence_validator)

                    result = phase.run(mock_context)

                    assert isinstance(result, ValidationResult)
                    assert result.passed is True
                    assert result.issues == []

    def test_phase_collects_issues_from_multiple_validators(
        self, mock_context: RunContext
    ) -> None:
        """Phase aggregates issues from all validators."""
        config = ValidationConfig()
        phase = ValidationPhase(config=config)

        # Create mock validators with different issues
        test_issues = [
            ValidationIssue(
                source=ValidationSource.TEST,
                message="test_login failed",
                severity="high",
            )
        ]
        review_issues = [
            ValidationIssue(
                source=ValidationSource.REVIEW,
                message="Missing error handling",
                severity="medium",
            )
        ]
        evidence_issues = [
            ValidationIssue(
                source=ValidationSource.EVIDENCE,
                message="Evidence missing for feature",
                severity="high",
            )
        ]

        test_validator = TestValidator()
        mock_executor = MagicMock()
        review_validator = ReviewValidator(executor=mock_executor)
        evidence_validator = EvidenceValidator()

        with patch.object(test_validator, "validate", return_value=test_issues):
            with patch.object(review_validator, "validate", return_value=review_issues):
                with patch.object(evidence_validator, "validate", return_value=evidence_issues):
                    phase.register_validator(test_validator)
                    phase.register_validator(review_validator)
                    phase.register_validator(evidence_validator)

                    result = phase.run(mock_context)

                    assert result.passed is False
                    assert len(result.issues) == 3
                    sources = {i.source for i in result.issues}
                    assert ValidationSource.TEST in sources
                    assert ValidationSource.REVIEW in sources
                    assert ValidationSource.EVIDENCE in sources

    def test_phase_continues_after_validator_raises_exception(
        self, mock_context: RunContext
    ) -> None:
        """Phase continues executing validators even if one raises."""
        config = ValidationConfig()
        phase = ValidationPhase(config=config)

        # First validator raises, second returns issues
        def raise_error(context):
            raise RuntimeError("Validator crashed")

        test_issues = [
            ValidationIssue(
                source=ValidationSource.TEST,
                message="Test completed",
                severity="low",
            )
        ]

        failing_validator = MagicMock()
        failing_validator.name = "failing"
        failing_validator.validate.side_effect = raise_error

        test_validator = TestValidator()
        with patch.object(test_validator, "validate", return_value=test_issues):
            phase.register_validator(failing_validator)
            phase.register_validator(test_validator)

            # Should not raise, should continue
            result = phase.run(mock_context)

            # Should have the issue from the working validator
            assert isinstance(result, ValidationResult)
            assert any(i.source == ValidationSource.TEST for i in result.issues)


class TestConfigBasedValidatorEnabling:
    """Tests for configuration-based validator enabling/disabling."""

    def test_registry_filters_disabled_validators(self) -> None:
        """Registry excludes disabled validators from execution."""
        config = ValidationConfig(
            enable_tests=True,
            enable_review=False,
            enable_evidence=False,
        )

        registry = ValidatorRegistry()
        registry.register(TestValidator())
        registry.register(ReviewValidator(executor=MagicMock()))
        registry.register(EvidenceValidator())

        enabled = registry.get_enabled(config)

        assert len(enabled) == 1
        assert enabled[0].name == "test"

    def test_all_validators_enabled_by_default(self) -> None:
        """All validators are enabled with default config."""
        config = ValidationConfig()  # All defaults are True

        registry = ValidatorRegistry()
        registry.register(TestValidator())
        registry.register(ReviewValidator(executor=MagicMock()))
        registry.register(EvidenceValidator())

        enabled = registry.get_enabled(config)

        assert len(enabled) == 3
        names = {v.name for v in enabled}
        assert names == {"test", "review", "evidence"}

    def test_single_validator_enabled(self) -> None:
        """Can enable only one validator."""
        config = ValidationConfig(
            enable_tests=False,
            enable_review=True,
            enable_evidence=False,
        )

        registry = ValidatorRegistry()
        registry.register(TestValidator())
        registry.register(ReviewValidator(executor=MagicMock()))
        registry.register(EvidenceValidator())

        enabled = registry.get_enabled(config)

        assert len(enabled) == 1
        assert enabled[0].name == "review"
