"""Tests for the triage system - Story 11.3.

Tests for TriageDecision enum, TriagedIssue wrapper, and TriageSystem class.
"""

import pytest

from adw.validation.config import ValidationConfig
from adw.validation.models import (
    IssueSeverity,
    IssueSource,
    TriageDecision,
    TriagedIssue,
    ValidationIssue,
)
from adw.validation.triage import TriageSystem


class TestTriageDecision:
    """Tests for TriageDecision enum."""

    def test_triage_decision_values(self) -> None:
        """Verify TriageDecision enum has expected members."""
        assert TriageDecision.FIX.value == "FIX"
        assert TriageDecision.DISMISS.value == "DISMISS"
        assert TriageDecision.DEFER.value == "DEFER"

    def test_triage_decision_is_string_enum(self) -> None:
        """TriageDecision should be a string enum for serialization."""
        decision = TriageDecision.FIX
        assert isinstance(decision, str)
        assert decision == "FIX"


class TestTriagedIssue:
    """Tests for TriagedIssue wrapper model."""

    @pytest.fixture
    def sample_issue(self) -> ValidationIssue:
        """Create a sample ValidationIssue for testing."""
        return ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: test_login",
        )

    def test_triaged_issue_creation(self, sample_issue: ValidationIssue) -> None:
        """TriagedIssue wraps an issue with decision metadata."""
        triaged = TriagedIssue(
            issue=sample_issue,
            decision=TriageDecision.FIX,
            reason="Critical test failure must be fixed",
        )

        assert triaged.issue == sample_issue
        assert triaged.decision == TriageDecision.FIX
        assert triaged.reason == "Critical test failure must be fixed"

    def test_triaged_issue_auto_decided_default(
        self, sample_issue: ValidationIssue
    ) -> None:
        """TriagedIssue has auto_decided flag defaulting to False."""
        triaged = TriagedIssue(
            issue=sample_issue,
            decision=TriageDecision.DISMISS,
            reason="Not relevant",
        )

        assert triaged.auto_decided is False

    def test_triaged_issue_auto_decided_true(
        self, sample_issue: ValidationIssue
    ) -> None:
        """TriagedIssue can be marked as auto-decided."""
        triaged = TriagedIssue(
            issue=sample_issue,
            decision=TriageDecision.DISMISS,
            reason="Auto-dismissed INFO severity",
            auto_decided=True,
        )

        assert triaged.auto_decided is True

    def test_triaged_issue_serialization(self, sample_issue: ValidationIssue) -> None:
        """TriagedIssue can be serialized to dict."""
        triaged = TriagedIssue(
            issue=sample_issue,
            decision=TriageDecision.DEFER,
            reason="Low priority",
            auto_decided=True,
        )

        data = triaged.model_dump(mode="json")

        assert data["decision"] == "DEFER"
        assert data["reason"] == "Low priority"
        assert data["auto_decided"] is True
        assert "issue" in data
        assert data["issue"]["source"] == "TEST"


class TestTriageSystem:
    """Tests for TriageSystem class."""

    @pytest.fixture
    def config(self) -> ValidationConfig:
        """Create a default ValidationConfig."""
        return ValidationConfig()

    @pytest.fixture
    def sample_issues(self) -> list[ValidationIssue]:
        """Create a list of sample issues for testing."""
        return [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Test failed: test_login",
            ),
            ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.WARNING,
                description="Unused variable 'x'",
            ),
            ValidationIssue(
                source=IssueSource.EVIDENCE,
                severity=IssueSeverity.INFO,
                description="Screenshot slightly different",
            ),
        ]

    def test_triage_system_creation(self, config: ValidationConfig) -> None:
        """TriageSystem can be created with config."""
        system = TriageSystem(config=config)

        assert system.config == config

    def test_triage_system_with_executor(self, config: ValidationConfig) -> None:
        """TriageSystem accepts optional LLM executor."""
        from adw.executors.mock import MockExecutor

        executor = MockExecutor()
        system = TriageSystem(config=config, llm_executor=executor)

        assert system.llm_executor is executor

    def test_triage_empty_issues_list(self, config: ValidationConfig) -> None:
        """Triage with empty issues list returns empty result."""
        system = TriageSystem(config=config)

        result = system.triage([])

        assert result == []

    def test_triage_mode_from_config(self, config: ValidationConfig) -> None:
        """Triage uses mode from config when not explicitly specified."""
        system = TriageSystem(config=config)

        # Default config has triage_mode="auto"
        assert system.config.triage_mode == "auto"

    def test_triage_mode_override(self, config: ValidationConfig) -> None:
        """Triage mode can be overridden in method call."""
        system = TriageSystem(config=config)
        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.INFO,
                description="Info issue",
            )
        ]

        # Should use passed mode, not config mode
        result = system.triage(issues, mode="auto")

        # With auto_dismiss_info=True, INFO issues should be auto-dismissed
        assert len(result) == 1
        assert result[0].decision == TriageDecision.DISMISS
