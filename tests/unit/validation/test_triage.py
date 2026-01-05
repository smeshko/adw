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


class TestAutoTriage:
    """Tests for auto triage functionality."""

    @pytest.fixture
    def config(self) -> ValidationConfig:
        """Create a ValidationConfig for auto triage testing."""
        return ValidationConfig(triage_mode="auto", auto_dismiss_info=True)

    def test_auto_triage_info_severity_dismissed(
        self, config: ValidationConfig
    ) -> None:
        """INFO severity issues are auto-dismissed when configured."""
        system = TriageSystem(config=config)
        issues = [
            ValidationIssue(
                source=IssueSource.EVIDENCE,
                severity=IssueSeverity.INFO,
                description="Minor visual difference",
            )
        ]

        result = system.triage(issues, mode="auto")

        assert len(result) == 1
        assert result[0].decision == TriageDecision.DISMISS
        assert "INFO" in result[0].reason
        assert result[0].auto_decided is True

    def test_auto_triage_with_llm_executor(
        self, config: ValidationConfig
    ) -> None:
        """Auto triage uses LLM for non-INFO severity issues."""
        from adw.executors.mock import MockExecutor

        executor = MockExecutor()
        # Configure mock to return a valid triage response
        executor.configure_responses([
            {"content": '{"decision": "FIX", "reason": "Test failure blocks functionality"}'}
        ])
        system = TriageSystem(config=config, llm_executor=executor)
        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Test failed: test_login",
            )
        ]

        result = system.triage(issues, mode="auto")

        assert len(result) == 1
        assert result[0].decision == TriageDecision.FIX
        assert result[0].auto_decided is True

    def test_auto_triage_parses_defer_decision(
        self, config: ValidationConfig
    ) -> None:
        """Auto triage correctly parses DEFER decisions from LLM."""
        from adw.executors.mock import MockExecutor

        executor = MockExecutor()
        executor.configure_responses([
            {"content": '{"decision": "DEFER", "reason": "Low priority, can address later"}'}
        ])
        system = TriageSystem(config=config, llm_executor=executor)
        issues = [
            ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.WARNING,
                description="Unused variable x",
            )
        ]

        result = system.triage(issues, mode="auto")

        assert len(result) == 1
        assert result[0].decision == TriageDecision.DEFER
        assert "Low priority" in result[0].reason

    def test_auto_triage_fallback_on_llm_error(
        self, config: ValidationConfig
    ) -> None:
        """Auto triage falls back to FIX when LLM fails."""
        from adw.executors.mock import MockExecutor

        executor = MockExecutor()
        executor.configure_responses([
            {"content": "Invalid JSON response - not valid JSON!"}
        ])
        system = TriageSystem(config=config, llm_executor=executor)
        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Test failed",
            )
        ]

        result = system.triage(issues, mode="auto")

        assert len(result) == 1
        assert result[0].decision == TriageDecision.FIX
        assert result[0].auto_decided is True

    def test_auto_triage_without_executor_uses_defaults(
        self, config: ValidationConfig
    ) -> None:
        """Auto triage without LLM executor uses severity-based defaults."""
        system = TriageSystem(config=config)  # No executor
        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Error issue",
            ),
            ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.WARNING,
                description="Warning issue",
            ),
        ]

        result = system.triage(issues, mode="auto")

        # Without LLM, ERROR defaults to FIX
        assert result[0].decision == TriageDecision.FIX
        # WARNING also defaults to FIX without LLM
        assert result[1].decision == TriageDecision.FIX

    def test_auto_triage_fallback_on_llm_success_false(
        self, config: ValidationConfig
    ) -> None:
        """Auto triage falls back to FIX when LLM returns success=False."""
        from adw.executors.mock import MockExecutor

        executor = MockExecutor()
        # Configure mock to return success=False
        executor.configure_responses([{"success": False, "content": ""}])
        system = TriageSystem(config=config, llm_executor=executor)
        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Test failed",
            )
        ]

        result = system.triage(issues, mode="auto")

        assert len(result) == 1
        assert result[0].decision == TriageDecision.FIX
        assert result[0].auto_decided is True
        assert "failed" in result[0].reason.lower()


class TestManualTriage:
    """Tests for manual triage functionality."""

    @pytest.fixture
    def config(self) -> ValidationConfig:
        """Create a ValidationConfig for manual triage testing."""
        return ValidationConfig(triage_mode="manual")

    def test_manual_triage_prompts_user(
        self, config: ValidationConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Manual triage prompts user for each issue."""
        from io import StringIO

        from rich.console import Console

        # Create console with string output
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        # Mock Rich Prompt - first call returns decision, second returns empty reason
        from unittest.mock import patch

        with patch("adw.validation.triage.Prompt.ask", side_effect=["f", ""]):
            system = TriageSystem(config=config, console=console)
            issues = [
                ValidationIssue(
                    source=IssueSource.TEST,
                    severity=IssueSeverity.ERROR,
                    description="Test failed: test_login",
                )
            ]

            result = system.triage(issues, mode="manual")

            assert len(result) == 1
            assert result[0].decision == TriageDecision.FIX
            assert result[0].auto_decided is False
            assert result[0].reason == "User selected FIX"

    def test_manual_triage_dismiss_option(
        self, config: ValidationConfig
    ) -> None:
        """Manual triage allows DISMISS option."""
        from io import StringIO
        from unittest.mock import patch

        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=True)

        with patch("adw.validation.triage.Prompt.ask", return_value="d"):
            system = TriageSystem(config=config, console=console)
            issues = [
                ValidationIssue(
                    source=IssueSource.REVIEW,
                    severity=IssueSeverity.WARNING,
                    description="Unused variable",
                )
            ]

            result = system.triage(issues, mode="manual")

            assert result[0].decision == TriageDecision.DISMISS

    def test_manual_triage_defer_option(
        self, config: ValidationConfig
    ) -> None:
        """Manual triage allows DEFER option."""
        from io import StringIO
        from unittest.mock import patch

        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=True)

        with patch("adw.validation.triage.Prompt.ask", return_value="e"):
            system = TriageSystem(config=config, console=console)
            issues = [
                ValidationIssue(
                    source=IssueSource.EVIDENCE,
                    severity=IssueSeverity.INFO,
                    description="Minor difference",
                )
            ]

            result = system.triage(issues, mode="manual")

            assert result[0].decision == TriageDecision.DEFER

    def test_manual_triage_captures_reason(
        self, config: ValidationConfig
    ) -> None:
        """Manual triage captures user's reasoning."""
        from io import StringIO
        from unittest.mock import patch

        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=True)

        # First call returns decision, second returns reason
        with patch(
            "adw.validation.triage.Prompt.ask",
            side_effect=["f", "Critical bug that must be fixed"],
        ):
            system = TriageSystem(config=config, console=console)
            issues = [
                ValidationIssue(
                    source=IssueSource.TEST,
                    severity=IssueSeverity.ERROR,
                    description="Test failed",
                )
            ]

            result = system.triage(issues, mode="manual")

            assert result[0].reason == "Critical bug that must be fixed"


class TestHybridTriage:
    """Tests for hybrid triage functionality."""

    @pytest.fixture
    def config(self) -> ValidationConfig:
        """Create a ValidationConfig for hybrid triage testing."""
        return ValidationConfig(triage_mode="hybrid", auto_dismiss_info=True)

    def test_hybrid_auto_for_info_severity(
        self, config: ValidationConfig
    ) -> None:
        """Hybrid mode auto-dismisses INFO severity issues."""
        system = TriageSystem(config=config)
        issues = [
            ValidationIssue(
                source=IssueSource.EVIDENCE,
                severity=IssueSeverity.INFO,
                description="Minor visual difference",
            )
        ]

        result = system.triage(issues, mode="hybrid")

        assert len(result) == 1
        assert result[0].decision == TriageDecision.DISMISS
        assert result[0].auto_decided is True

    def test_hybrid_auto_for_warning_severity(
        self, config: ValidationConfig
    ) -> None:
        """Hybrid mode auto-triages WARNING severity issues."""
        system = TriageSystem(config=config)
        issues = [
            ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.WARNING,
                description="Unused import",
            )
        ]

        result = system.triage(issues, mode="hybrid")

        assert len(result) == 1
        # WARNING defaults to FIX without LLM
        assert result[0].decision == TriageDecision.FIX
        assert result[0].auto_decided is True

    def test_hybrid_manual_for_error_severity(
        self, config: ValidationConfig
    ) -> None:
        """Hybrid mode prompts user for ERROR severity issues."""
        from io import StringIO
        from unittest.mock import patch

        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=True)

        with patch(
            "adw.validation.triage.Prompt.ask",
            side_effect=["f", "Must fix this bug"],
        ):
            system = TriageSystem(config=config, console=console)
            issues = [
                ValidationIssue(
                    source=IssueSource.TEST,
                    severity=IssueSeverity.ERROR,
                    description="Test failed: test_login",
                )
            ]

            result = system.triage(issues, mode="hybrid")

            assert len(result) == 1
            assert result[0].decision == TriageDecision.FIX
            assert result[0].auto_decided is False
            assert result[0].reason == "Must fix this bug"

    def test_hybrid_mixed_severities(
        self, config: ValidationConfig
    ) -> None:
        """Hybrid mode correctly handles mixed severity issues."""
        from io import StringIO
        from unittest.mock import patch

        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=True)

        # Only ERROR will prompt, INFO is auto-dismissed
        with patch(
            "adw.validation.triage.Prompt.ask",
            side_effect=["d", "False positive"],  # Only for ERROR
        ):
            system = TriageSystem(config=config, console=console)
            issues = [
                ValidationIssue(
                    source=IssueSource.EVIDENCE,
                    severity=IssueSeverity.INFO,
                    description="Info issue",
                ),
                ValidationIssue(
                    source=IssueSource.TEST,
                    severity=IssueSeverity.ERROR,
                    description="Error issue",
                ),
            ]

            result = system.triage(issues, mode="hybrid")

            assert len(result) == 2
            # INFO auto-dismissed
            assert result[0].decision == TriageDecision.DISMISS
            assert result[0].auto_decided is True
            # ERROR manually dismissed
            assert result[1].decision == TriageDecision.DISMISS
            assert result[1].auto_decided is False


class TestTriageRules:
    """Tests for configurable triage rules."""

    @pytest.fixture
    def config(self) -> ValidationConfig:
        """Create a ValidationConfig for rules testing."""
        return ValidationConfig(triage_mode="auto", auto_dismiss_info=False)

    def test_rule_always_dismiss_by_description(
        self, config: ValidationConfig
    ) -> None:
        """Rules can dismiss issues by description pattern."""
        from adw.validation.triage import TriageRule

        rules = [
            TriageRule(
                action=TriageDecision.DISMISS,
                description_pattern="unused.*import",
                reason="Linting warning - auto-dismissed",
            )
        ]
        system = TriageSystem(config=config, rules=rules)
        issues = [
            ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.WARNING,
                description="Unused import: os",
            )
        ]

        result = system.triage(issues, mode="auto")

        assert len(result) == 1
        assert result[0].decision == TriageDecision.DISMISS
        assert "Linting warning" in result[0].reason
        assert result[0].auto_decided is True

    def test_rule_always_fix_test_failures(
        self, config: ValidationConfig
    ) -> None:
        """Rules can require FIX for test failures."""
        from adw.validation.triage import TriageRule

        rules = [
            TriageRule(
                action=TriageDecision.FIX,
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                reason="Test failures must always be fixed",
            )
        ]
        system = TriageSystem(config=config, rules=rules)
        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Test failed: test_login",
            )
        ]

        result = system.triage(issues, mode="auto")

        assert len(result) == 1
        assert result[0].decision == TriageDecision.FIX
        assert "Test failures" in result[0].reason

    def test_rules_applied_before_llm(
        self, config: ValidationConfig
    ) -> None:
        """Rules are applied before falling back to LLM."""
        from adw.executors.mock import MockExecutor
        from adw.validation.triage import TriageRule

        # Mock would return DEFER, but rule should override
        executor = MockExecutor()
        executor.configure_responses([
            {"content": '{"decision": "DEFER", "reason": "Can wait"}'}
        ])

        rules = [
            TriageRule(
                action=TriageDecision.DISMISS,
                source=IssueSource.REVIEW,
                reason="All review issues dismissed by rule",
            )
        ]
        system = TriageSystem(config=config, llm_executor=executor, rules=rules)
        issues = [
            ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.WARNING,
                description="Consider using const",
            )
        ]

        result = system.triage(issues, mode="auto")

        assert result[0].decision == TriageDecision.DISMISS
        # LLM should not have been called
        assert executor.call_count == 0

    def test_multiple_rules_first_match_wins(
        self, config: ValidationConfig
    ) -> None:
        """First matching rule is applied."""
        from adw.validation.triage import TriageRule

        rules = [
            TriageRule(
                action=TriageDecision.DISMISS,
                description_pattern=".*import.*",
                reason="Import issues dismissed",
            ),
            TriageRule(
                action=TriageDecision.FIX,
                source=IssueSource.REVIEW,
                reason="Review issues fixed",
            ),
        ]
        system = TriageSystem(config=config, rules=rules)
        issues = [
            ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.WARNING,
                description="Unused import: json",
            )
        ]

        result = system.triage(issues, mode="auto")

        # First rule (import pattern) should match
        assert result[0].decision == TriageDecision.DISMISS
        assert "Import issues" in result[0].reason


class TestTriageResult:
    """Tests for triage result summary and logging."""

    @pytest.fixture
    def config(self) -> ValidationConfig:
        """Create a ValidationConfig for result testing."""
        return ValidationConfig(triage_mode="auto", auto_dismiss_info=True)

    def test_triage_result_statistics(
        self, config: ValidationConfig
    ) -> None:
        """Triage returns statistics about decisions made."""
        from adw.validation.triage import TriageResult

        system = TriageSystem(config=config)
        issues = [
            ValidationIssue(
                source=IssueSource.EVIDENCE,
                severity=IssueSeverity.INFO,
                description="Info 1",
            ),
            ValidationIssue(
                source=IssueSource.EVIDENCE,
                severity=IssueSeverity.INFO,
                description="Info 2",
            ),
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Error 1",
            ),
        ]

        result = system.triage_with_result(issues, mode="auto")

        assert isinstance(result, TriageResult)
        assert len(result.triaged_issues) == 3
        assert result.stats.fix_count == 1
        assert result.stats.dismiss_count == 2
        assert result.stats.defer_count == 0

    def test_triage_result_summary(
        self, config: ValidationConfig
    ) -> None:
        """TriageResult can generate a summary string."""

        system = TriageSystem(config=config)
        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Error",
            ),
        ]

        result = system.triage_with_result(issues, mode="auto")

        summary = result.summary()
        assert "1 FIX" in summary

    def test_triage_result_to_dict(
        self, config: ValidationConfig
    ) -> None:
        """TriageResult can be serialized for logging."""

        system = TriageSystem(config=config)
        issues = [
            ValidationIssue(
                source=IssueSource.EVIDENCE,
                severity=IssueSeverity.INFO,
                description="Info issue",
            ),
        ]

        result = system.triage_with_result(issues, mode="auto")

        data = result.to_dict()
        assert "triaged_issues" in data
        assert "stats" in data
        assert data["stats"]["dismiss_count"] == 1


class TestTriageRuleMatching:
    """Edge case tests for TriageRule matching logic."""

    def test_rule_no_criteria_matches_all(self) -> None:
        """Rule with no criteria matches all issues."""
        from adw.validation.triage import TriageRule

        rule = TriageRule(
            action=TriageDecision.DISMISS,
            reason="Dismiss everything",
        )
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Any issue",
        )

        assert rule.matches(issue) is True

    def test_rule_description_pattern_case_insensitive(self) -> None:
        """Description pattern matching is case insensitive."""
        from adw.validation.triage import TriageRule

        rule = TriageRule(
            action=TriageDecision.DISMISS,
            description_pattern="UNUSED.*IMPORT",
            reason="Dismiss imports",
        )
        issue = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.WARNING,
            description="unused variable import found",
        )

        assert rule.matches(issue) is True

    def test_rule_all_criteria_must_match(self) -> None:
        """All specified criteria must match for rule to apply."""
        from adw.validation.triage import TriageRule

        rule = TriageRule(
            action=TriageDecision.FIX,
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description_pattern="login",
            reason="Fix login tests",
        )
        # Wrong severity
        wrong_severity = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.WARNING,
            description="login failed",
        )
        # Wrong source
        wrong_source = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.ERROR,
            description="login issue",
        )
        # Matching issue
        matching = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: login",
        )

        assert rule.matches(wrong_severity) is False
        assert rule.matches(wrong_source) is False
        assert rule.matches(matching) is True


class TestTriageStatsHelpers:
    """Tests for TriageStats helper methods."""

    def test_triage_result_get_issues_to_fix(self) -> None:
        """get_issues_to_fix returns only FIX issues."""
        from adw.validation.triage import TriageResult, TriageStats

        fix_issue = TriagedIssue(
            issue=ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Error",
            ),
            decision=TriageDecision.FIX,
            reason="Fix it",
            auto_decided=True,
        )
        dismiss_issue = TriagedIssue(
            issue=ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.INFO,
                description="Info",
            ),
            decision=TriageDecision.DISMISS,
            reason="Dismiss it",
            auto_decided=True,
        )

        result = TriageResult(
            triaged_issues=[fix_issue, dismiss_issue],
            stats=TriageStats(fix_count=1, dismiss_count=1),
        )

        fix_issues = result.get_issues_to_fix()
        assert len(fix_issues) == 1
        assert fix_issues[0] == fix_issue

    def test_triage_stats_total(self) -> None:
        """TriageStats.total sums all decision counts."""
        from adw.validation.triage import TriageStats

        stats = TriageStats(fix_count=3, dismiss_count=2, defer_count=1)

        assert stats.total == 6
