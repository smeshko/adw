"""Tests for the triage system - Story 11.3.

Tests for TriageDecision enum, TriagedIssue wrapper, and TriageSystem class.
"""

import pytest

from adw.validation.models import (
    IssueSeverity,
    IssueSource,
    TriageDecision,
    TriagedIssue,
    ValidationIssue,
)


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
