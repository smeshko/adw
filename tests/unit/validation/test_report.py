"""Tests for ValidationReportGenerator and ValidationReport.

Story 11.7: Validation Report Generation
Tests focus on:
- Report generation with correct metrics
- Confidence calculation logic
- Markdown and PR section formatting
- File storage operations
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from adw.validation.config import ValidationConfig
from adw.validation.models import (
    IssueLocation,
    IssueSeverity,
    IssueSource,
    ValidationIssue,
)
from adw.validation.report import (
    ConfidenceLevel,
    DeferredIssueSummary,
    ValidationReport,
    ValidationReportGenerator,
)
from adw.validation.state_manager import ValidationStateManager


@pytest.fixture
def mock_state_manager(tmp_path: Path) -> ValidationStateManager:
    """Create a mock state manager."""
    return ValidationStateManager("01TEST123", tmp_path)


@pytest.fixture
def config() -> ValidationConfig:
    """Create a test validation config."""
    return ValidationConfig(max_iterations=5)


@pytest.fixture
def sample_issues() -> list[ValidationIssue]:
    """Create sample validation issues for testing."""
    return [
        ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: test_login",
            triage_decision="FIX",
            location=IssueLocation(file_path="tests/test_auth.py", line_start=42),
        ),
        ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.WARNING,
            description="Missing error handling",
            triage_decision="DISMISS",
            triage_reason="False positive",
        ),
        ValidationIssue(
            source=IssueSource.EVIDENCE,
            severity=IssueSeverity.WARNING,
            description="Screenshot mismatch",
            triage_decision="DEFER",
            triage_reason="Flaky test, needs investigation",
            location=IssueLocation(file_path="src/ui/button.py"),
        ),
    ]


@pytest.fixture
def resolved_issues() -> list[ValidationIssue]:
    """Create issues where all are resolved."""
    from adw.validation.models import FixResult

    issue = ValidationIssue(
        source=IssueSource.TEST,
        severity=IssueSeverity.ERROR,
        description="Test fixed",
        triage_decision="FIX",
        last_fix_result=FixResult.RESOLVED,
    )
    return [issue]


class TestValidationReportGenerator:
    """Tests for ValidationReportGenerator."""

    def test_generate_report(
        self,
        mock_state_manager: ValidationStateManager,
        config: ValidationConfig,
        sample_issues: list[ValidationIssue],
    ) -> None:
        """Report generated with correct metrics."""
        generator = ValidationReportGenerator(mock_state_manager, config)
        loop_summary = {
            "iterations_run": 3,
            "resolved": 1,
            "dismissed": 1,
            "deferred": 1,
            "exit_reason": "ALL_RESOLVED",
        }
        start_time = datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC)

        report = generator.generate(loop_summary, sample_issues, start_time)

        assert report.run_id == mock_state_manager.run_id
        assert report.iterations_run == 3
        assert report.issues_found == 3
        assert report.issues_fixed == 1
        assert report.issues_dismissed == 1
        assert report.issues_deferred == 1
        assert report.exit_reason == "ALL_RESOLVED"

    def test_generate_with_no_issues(
        self,
        mock_state_manager: ValidationStateManager,
        config: ValidationConfig,
    ) -> None:
        """Report handles zero issues gracefully."""
        generator = ValidationReportGenerator(mock_state_manager, config)
        loop_summary = {
            "iterations_run": 1,
            "resolved": 0,
            "dismissed": 0,
            "deferred": 0,
            "exit_reason": "ALL_RESOLVED",
        }
        start_time = datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC)

        report = generator.generate(loop_summary, [], start_time)

        assert report.issues_found == 0
        assert report.issues_fixed == 0
        assert report.confidence == ConfidenceLevel.HIGH
        assert "No issues found" in report.confidence_explanation

    def test_generate_includes_deferred(
        self,
        mock_state_manager: ValidationStateManager,
        config: ValidationConfig,
    ) -> None:
        """Deferred issues included in report."""
        deferred_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.WARNING,
            description="Flaky integration test",
            triage_decision="DEFER",
            triage_reason="Intermittent failure",
            location=IssueLocation(file_path="tests/integration/test_api.py"),
        )
        generator = ValidationReportGenerator(mock_state_manager, config)
        loop_summary = {
            "iterations_run": 5,
            "resolved": 0,
            "dismissed": 0,
            "deferred": 1,
            "exit_reason": "MAX_ITERATIONS",
        }
        start_time = datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC)

        report = generator.generate(loop_summary, [deferred_issue], start_time)

        assert len(report.deferred_issues) == 1
        assert report.deferred_issues[0].description == "Flaky integration test"
        assert report.deferred_issues[0].reason == "Intermittent failure"
        assert report.deferred_issues[0].file_path == "tests/integration/test_api.py"

    def test_save_creates_both_formats(
        self,
        mock_state_manager: ValidationStateManager,
        config: ValidationConfig,
        tmp_path: Path,
    ) -> None:
        """Both MD and JSON files created."""
        generator = ValidationReportGenerator(mock_state_manager, config)
        report = ValidationReport(
            run_id="01TEST123",
            duration_seconds=45.0,
            iterations_run=3,
            max_iterations=5,
            exit_reason="ALL_RESOLVED",
            issues_found=0,
            issues_fixed=0,
            issues_dismissed=0,
            issues_deferred=0,
            confidence=ConfidenceLevel.HIGH,
            confidence_explanation="No issues found",
        )

        md_path = generator.save(report)

        assert md_path.exists()
        assert md_path.name == "report.md"
        json_path = md_path.with_suffix(".json")
        assert json_path.exists()

    def test_save_in_artifacts_dir(
        self,
        mock_state_manager: ValidationStateManager,
        config: ValidationConfig,
    ) -> None:
        """Files created in artifacts/validation/."""
        generator = ValidationReportGenerator(mock_state_manager, config)
        report = ValidationReport(
            run_id="01TEST123",
            duration_seconds=45.0,
            iterations_run=3,
            max_iterations=5,
            exit_reason="ALL_RESOLVED",
            issues_found=0,
            issues_fixed=0,
            issues_dismissed=0,
            issues_deferred=0,
            confidence=ConfidenceLevel.HIGH,
            confidence_explanation="No issues",
        )

        md_path = generator.save(report)

        # Path should be: base_path/artifacts/validation/report.md
        assert "artifacts" in str(md_path)
        assert "validation" in str(md_path)


class TestConfidenceCalculation:
    """Tests for confidence level calculation."""

    def test_high_all_resolved(self) -> None:
        """HIGH when all issues resolved."""
        # Verify calculation via generator helper
        generator = ValidationReportGenerator.__new__(ValidationReportGenerator)
        conf, explanation = generator._calculate_confidence(
            issues_found=5, issues_fixed=5, issues_dismissed=0, issues_deferred=0
        )

        assert conf == ConfidenceLevel.HIGH
        assert "resolved" in explanation.lower() or "5 issues" in explanation.lower()

    def test_high_no_issues(self) -> None:
        """HIGH when no issues found."""
        generator = ValidationReportGenerator.__new__(ValidationReportGenerator)
        conf, explanation = generator._calculate_confidence(
            issues_found=0, issues_fixed=0, issues_dismissed=0, issues_deferred=0
        )

        assert conf == ConfidenceLevel.HIGH
        assert "no issues" in explanation.lower()

    def test_medium_some_deferred(self) -> None:
        """MEDIUM when < 30% deferred."""
        generator = ValidationReportGenerator.__new__(ValidationReportGenerator)
        # 2 deferred out of 10 = 20% < 30%
        conf, explanation = generator._calculate_confidence(
            issues_found=10, issues_fixed=7, issues_dismissed=1, issues_deferred=2
        )

        assert conf == ConfidenceLevel.MEDIUM
        assert "deferred" in explanation.lower()

    def test_low_many_deferred(self) -> None:
        """LOW when >= 30% deferred."""
        generator = ValidationReportGenerator.__new__(ValidationReportGenerator)
        # 4 deferred out of 10 = 40% >= 30%
        conf, explanation = generator._calculate_confidence(
            issues_found=10, issues_fixed=4, issues_dismissed=2, issues_deferred=4
        )

        assert conf == ConfidenceLevel.LOW
        assert "deferred" in explanation.lower()

    def test_low_many_dismissed(self) -> None:
        """LOW when >= 50% dismissed (even with no deferred)."""
        generator = ValidationReportGenerator.__new__(ValidationReportGenerator)
        # 6 dismissed out of 10 = 60% >= 50%, 0 deferred
        conf, explanation = generator._calculate_confidence(
            issues_found=10, issues_fixed=4, issues_dismissed=6, issues_deferred=0
        )

        assert conf == ConfidenceLevel.LOW
        assert "dismissed" in explanation.lower()


class TestMarkdownGeneration:
    """Tests for markdown report generation."""

    @pytest.fixture
    def sample_report(self) -> ValidationReport:
        """Create a sample report for markdown tests."""
        return ValidationReport(
            run_id="01TEST123",
            duration_seconds=45.2,
            iterations_run=3,
            max_iterations=5,
            exit_reason="ALL_RESOLVED",
            issues_found=8,
            issues_fixed=5,
            issues_dismissed=1,
            issues_deferred=2,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_explanation="2 issues deferred (25%). Review recommended.",
        )

    @pytest.fixture
    def report_with_deferred(self) -> ValidationReport:
        """Create a report with deferred issues."""
        return ValidationReport(
            run_id="01TEST123",
            duration_seconds=45.2,
            iterations_run=3,
            max_iterations=5,
            exit_reason="MAX_ITERATIONS",
            issues_found=3,
            issues_fixed=1,
            issues_dismissed=0,
            issues_deferred=2,
            confidence=ConfidenceLevel.LOW,
            confidence_explanation="2 issues deferred (67%). Manual review required.",
            deferred_issues=[
                DeferredIssueSummary(
                    issue_id="VI-01TEST1",
                    source="TEST",
                    severity="WARNING",
                    description="Flaky test",
                    reason="Intermittent failure",
                    file_path="tests/test_api.py",
                ),
                DeferredIssueSummary(
                    issue_id="VI-01TEST2",
                    source="REVIEW",
                    severity="WARNING",
                    description="Complex refactor needed",
                    reason="Beyond scope",
                ),
            ],
        )

    def test_includes_summary_table(self, sample_report: ValidationReport) -> None:
        """Markdown includes summary metrics table."""
        md = sample_report.to_markdown()

        assert "| Metric | Value |" in md
        assert "| Iterations |" in md
        assert "| Issues Found |" in md
        assert "3/5" in md  # iterations_run/max_iterations
        assert "8" in md  # issues_found

    def test_includes_deferred_section(
        self, report_with_deferred: ValidationReport
    ) -> None:
        """Markdown includes deferred issues section."""
        md = report_with_deferred.to_markdown()

        assert "## Deferred Issues" in md
        assert "VI-01TEST1" in md
        assert "Flaky test" in md
        assert "tests/test_api.py" in md

    def test_no_deferred_section_when_empty(
        self, sample_report: ValidationReport
    ) -> None:
        """No deferred section when none deferred."""
        sample_report.deferred_issues = []
        md = sample_report.to_markdown()

        assert "## Deferred Issues" not in md

    def test_github_flavored(self, sample_report: ValidationReport) -> None:
        """Uses GitHub-flavored markdown."""
        md = sample_report.to_markdown()

        # Tables use GFM format
        assert "|--------|" in md or "|-------|" in md
        # Headers use # format
        assert md.startswith("# Validation Report")


class TestPRSection:
    """Tests for PR description section generation."""

    @pytest.fixture
    def sample_report(self) -> ValidationReport:
        """Create a sample report for PR section tests."""
        return ValidationReport(
            run_id="01TEST123",
            duration_seconds=45.2,
            iterations_run=3,
            max_iterations=5,
            exit_reason="ALL_RESOLVED",
            issues_found=2,
            issues_fixed=2,
            issues_dismissed=0,
            issues_deferred=0,
            confidence=ConfidenceLevel.HIGH,
            confidence_explanation="All issues resolved",
        )

    @pytest.fixture
    def report_with_deferred(self) -> ValidationReport:
        """Create a report with deferred issues for PR section."""
        return ValidationReport(
            run_id="01TEST123",
            duration_seconds=45.2,
            iterations_run=5,
            max_iterations=5,
            exit_reason="MAX_ITERATIONS",
            issues_found=3,
            issues_fixed=1,
            issues_dismissed=0,
            issues_deferred=2,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_explanation="Some issues deferred",
            deferred_issues=[
                DeferredIssueSummary(
                    issue_id="VI-01TEST1",
                    source="TEST",
                    severity="WARNING",
                    description="Flaky integration test",
                    reason="Intermittent",
                    file_path="tests/integration/test_api.py",
                ),
            ],
        )

    def test_includes_confidence_badge(
        self, report_with_deferred: ValidationReport
    ) -> None:
        """PR section includes confidence badge."""
        pr_section = report_with_deferred.to_pr_section()

        # Should include shields.io badge
        assert "shields.io" in pr_section or "confidence" in pr_section.lower()

    def test_lists_deferred_issues(
        self, report_with_deferred: ValidationReport
    ) -> None:
        """PR section lists all deferred issues."""
        pr_section = report_with_deferred.to_pr_section()

        assert "Flaky integration test" in pr_section
        assert "TEST" in pr_section
        assert "tests/integration/test_api.py" in pr_section

    def test_empty_when_no_deferred(self, sample_report: ValidationReport) -> None:
        """Returns empty string when no deferred."""
        pr_section = sample_report.to_pr_section()

        assert pr_section == ""
