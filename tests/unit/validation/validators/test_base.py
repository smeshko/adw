"""Unit tests for Validator Protocol and ValidatorRegistry.

Tests for the base validator infrastructure that manages validator
registration and execution.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from adw.models import RunContext
from adw.validation.config import ValidationConfig
from adw.validation.models import ValidationIssue, ValidationSource
from adw.validation.validators.base import ValidatorRegistry


class MockValidator:
    """Mock validator for testing."""

    def __init__(self, name: str, issues: list[ValidationIssue] | None = None) -> None:
        self._name = name
        self._issues = issues or []

    @property
    def name(self) -> str:
        return self._name

    def validate(self, context: RunContext) -> list[ValidationIssue]:
        return self._issues


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


class TestValidatorRegistry:
    """Test cases for ValidatorRegistry class."""

    def test_register_validator(self) -> None:
        """Registry can register validators."""
        registry = ValidatorRegistry()
        validator = MockValidator("test")

        registry.register(validator)

        assert len(registry.get_all()) == 1
        assert registry.get_all()[0].name == "test"

    def test_register_multiple_validators(self) -> None:
        """Registry can register multiple validators."""
        registry = ValidatorRegistry()
        validator1 = MockValidator("test")
        validator2 = MockValidator("review")
        validator3 = MockValidator("evidence")

        registry.register(validator1)
        registry.register(validator2)
        registry.register(validator3)

        assert len(registry.get_all()) == 3
        names = [v.name for v in registry.get_all()]
        assert "test" in names
        assert "review" in names
        assert "evidence" in names

    def test_get_enabled_validators_all_enabled(self) -> None:
        """Registry returns all validators when all are enabled in config."""
        config = ValidationConfig(
            enable_tests=True,
            enable_review=True,
            enable_evidence=True,
        )
        registry = ValidatorRegistry()
        registry.register(MockValidator("test"))
        registry.register(MockValidator("review"))
        registry.register(MockValidator("evidence"))

        enabled = registry.get_enabled(config)

        assert len(enabled) == 3

    def test_get_enabled_validators_some_disabled(self) -> None:
        """Registry filters validators based on config."""
        config = ValidationConfig(
            enable_tests=True,
            enable_review=False,
            enable_evidence=False,
        )
        registry = ValidatorRegistry()
        registry.register(MockValidator("test"))
        registry.register(MockValidator("review"))
        registry.register(MockValidator("evidence"))

        enabled = registry.get_enabled(config)

        assert len(enabled) == 1
        assert enabled[0].name == "test"

    def test_run_all_validators(self, mock_context: RunContext) -> None:
        """Registry can run all validators and collect issues."""
        registry = ValidatorRegistry()
        registry.register(
            MockValidator(
                "test",
                [
                    ValidationIssue(
                        source=ValidationSource.TEST,
                        message="Test failure",
                        severity="high",
                    )
                ],
            )
        )
        registry.register(
            MockValidator(
                "review",
                [
                    ValidationIssue(
                        source=ValidationSource.REVIEW,
                        message="Review issue",
                        severity="medium",
                    )
                ],
            )
        )

        issues = registry.run_all(mock_context)

        assert len(issues) == 2
        assert any(i.source == ValidationSource.TEST for i in issues)
        assert any(i.source == ValidationSource.REVIEW for i in issues)

    def test_run_all_validators_with_filter(self, mock_context: RunContext) -> None:
        """Registry can run filtered validators based on config."""
        config = ValidationConfig(
            enable_tests=True,
            enable_review=False,
            enable_evidence=False,
        )
        registry = ValidatorRegistry()
        registry.register(
            MockValidator(
                "test",
                [
                    ValidationIssue(
                        source=ValidationSource.TEST,
                        message="Test failure",
                        severity="high",
                    )
                ],
            )
        )
        registry.register(
            MockValidator(
                "review",
                [
                    ValidationIssue(
                        source=ValidationSource.REVIEW,
                        message="Review issue",
                        severity="medium",
                    )
                ],
            )
        )

        issues = registry.run_enabled(mock_context, config)

        assert len(issues) == 1
        assert issues[0].source == ValidationSource.TEST

    def test_validator_error_handling(self, mock_context: RunContext) -> None:
        """Registry continues after validator raises exception."""

        class FailingValidator:
            @property
            def name(self) -> str:
                return "failing"

            def validate(self, context: RunContext) -> list[ValidationIssue]:
                raise RuntimeError("Validator failed")

        registry = ValidatorRegistry()
        registry.register(FailingValidator())
        registry.register(
            MockValidator(
                "test",
                [
                    ValidationIssue(
                        source=ValidationSource.TEST,
                        message="Test passed after failure",
                        severity="low",
                    )
                ],
            )
        )

        # Should not raise, should continue to next validator
        issues = registry.run_all(mock_context)

        # Should have the issue from the working validator
        assert len(issues) >= 1
        assert any(i.message == "Test passed after failure" for i in issues)

    def test_clear_validators(self) -> None:
        """Registry can clear all registered validators."""
        registry = ValidatorRegistry()
        registry.register(MockValidator("test"))
        registry.register(MockValidator("review"))

        registry.clear()

        assert len(registry.get_all()) == 0
