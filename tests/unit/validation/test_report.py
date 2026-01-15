"""Tests for ValidationReportGenerator and ValidationReport (Story 16.4).

Tests focus on:
- Report generation from simplified ValidationResult
- Confidence calculation logic
- Markdown formatting
- File storage operations
"""

from pathlib import Path

import pytest

from adw.validation.models import ValidationResult
from adw.validation.report import (
    ConfidenceLevel,
    ValidationReport,
    ValidationReportGenerator,
)


class TestValidationReportGenerator:
    """Tests for ValidationReportGenerator."""

    def test_generate_report_from_result(self) -> None:
        """Report generated from ValidationResult with correct metrics."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed null check", "Added error handling"],
            issues_remaining=[],
            summary="All tests pass, code review clean",
        )
        generator = ValidationReportGenerator(run_id="01TEST123")

        report = generator.generate(result)

        assert report.run_id == "01TEST123"
        assert report.passed is True
        assert report.tests_passed is True
        assert report.code_review_passed is True
        assert report.issues_fixed == ["Fixed null check", "Added error handling"]
        assert report.issues_remaining == []

    def test_generate_with_no_issues(self) -> None:
        """Report handles validation with no issues."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=[],
            issues_remaining=[],
            summary="All tests pass, no issues found",
        )
        generator = ValidationReportGenerator(run_id="01TEST123")

        report = generator.generate(result)

        assert report.issues_fixed == []
        assert report.issues_remaining == []
        assert report.confidence == ConfidenceLevel.HIGH

    def test_generate_with_remaining_issues(self) -> None:
        """Report includes remaining issues."""
        result = ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=True,
            issues_fixed=["Fixed one bug"],
            issues_remaining=[
                "Test test_login still fails",
                "Database connection timeout",
            ],
            summary="Some tests still failing",
        )
        generator = ValidationReportGenerator(run_id="01TEST123")

        report = generator.generate(result)

        assert report.passed is False
        assert len(report.issues_remaining) == 2
        assert "test_login" in report.issues_remaining[0]

    def test_save_creates_both_formats(self, tmp_path: Path) -> None:
        """Both MD and JSON files created."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            summary="All good",
        )
        generator = ValidationReportGenerator(run_id="01TEST123", output_dir=tmp_path)
        report = generator.generate(result)

        md_path = generator.save(report)

        assert md_path is not None
        assert md_path.exists()
        assert md_path.name == "validation_report.md"
        json_path = md_path.with_name("validation_report.json")
        assert json_path.exists()

    def test_save_returns_none_without_output_dir(self) -> None:
        """save() returns None when no output_dir configured."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
        )
        generator = ValidationReportGenerator(run_id="01TEST123")
        report = generator.generate(result)

        path = generator.save(report)

        assert path is None


class TestConfidenceCalculation:
    """Tests for confidence level calculation."""

    def test_high_no_issues(self) -> None:
        """HIGH when no issues at all."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=[],
            issues_remaining=[],
        )
        generator = ValidationReportGenerator(run_id="test")
        conf = generator._calculate_confidence(result)

        assert conf == ConfidenceLevel.HIGH

    def test_high_all_resolved(self) -> None:
        """HIGH when all issues were fixed (none remaining)."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed bug 1", "Fixed bug 2", "Fixed bug 3"],
            issues_remaining=[],
        )
        generator = ValidationReportGenerator(run_id="test")
        conf = generator._calculate_confidence(result)

        assert conf == ConfidenceLevel.HIGH

    def test_medium_some_remaining(self) -> None:
        """MEDIUM when < 30% remaining."""
        result = ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=True,
            issues_fixed=["Fixed 1", "Fixed 2", "Fixed 3", "Fixed 4", "Fixed 5",
                          "Fixed 6", "Fixed 7", "Fixed 8"],
            issues_remaining=["Still failing 1", "Still failing 2"],  # 2/10 = 20%
        )
        generator = ValidationReportGenerator(run_id="test")
        conf = generator._calculate_confidence(result)

        assert conf == ConfidenceLevel.MEDIUM

    def test_low_many_remaining(self) -> None:
        """LOW when >= 30% remaining."""
        result = ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=False,
            issues_fixed=["Fixed 1", "Fixed 2"],
            issues_remaining=["Fail 1", "Fail 2", "Fail 3", "Fail 4"],  # 4/6 = 67%
        )
        generator = ValidationReportGenerator(run_id="test")
        conf = generator._calculate_confidence(result)

        assert conf == ConfidenceLevel.LOW


class TestValidationReportMarkdown:
    """Tests for ValidationReport.to_markdown() method."""

    @pytest.fixture
    def passing_report(self) -> ValidationReport:
        """Create a passing validation report."""
        return ValidationReport(
            run_id="01TEST123",
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed null check in auth handler"],
            issues_remaining=[],
            summary="All tests pass, code review clean",
            confidence=ConfidenceLevel.HIGH,
        )

    @pytest.fixture
    def failing_report(self) -> ValidationReport:
        """Create a failing validation report."""
        return ValidationReport(
            run_id="01TEST456",
            passed=False,
            tests_passed=False,
            code_review_passed=True,
            issues_fixed=["Fixed one issue"],
            issues_remaining=[
                "Test test_login_validation still fails",
                "Database timeout in test_user_create",
            ],
            summary="2 tests still failing",
            confidence=ConfidenceLevel.LOW,
        )

    def test_includes_header(self, passing_report: ValidationReport) -> None:
        """Markdown includes header with run ID."""
        md = passing_report.to_markdown()

        assert "# Validation Report" in md
        assert passing_report.run_id in md

    def test_includes_status(self, passing_report: ValidationReport) -> None:
        """Markdown includes pass/fail status."""
        md = passing_report.to_markdown()

        assert "PASSED" in md or "Pass" in md

    def test_includes_summary(self, passing_report: ValidationReport) -> None:
        """Markdown includes summary."""
        md = passing_report.to_markdown()

        assert "All tests pass" in md

    def test_includes_results_table(self, passing_report: ValidationReport) -> None:
        """Markdown includes results table."""
        md = passing_report.to_markdown()

        assert "| Check |" in md or "| Tests |" in md
        assert "Pass" in md or "Fail" in md

    def test_includes_fixed_issues_section(
        self, passing_report: ValidationReport
    ) -> None:
        """Markdown includes fixed issues section."""
        md = passing_report.to_markdown()

        assert "Fixed null check" in md

    def test_includes_remaining_issues_section(
        self, failing_report: ValidationReport
    ) -> None:
        """Markdown includes remaining issues section."""
        md = failing_report.to_markdown()

        assert "Issues Remaining" in md
        assert "test_login_validation" in md

    def test_no_remaining_section_when_empty(
        self, passing_report: ValidationReport
    ) -> None:
        """No remaining issues section when none exist."""
        md = passing_report.to_markdown()

        # Should not have "Issues Remaining" section
        assert "Issues Remaining" not in md


class TestValidationReportSerialization:
    """Tests for ValidationReport JSON serialization."""

    def test_to_json_dict(self) -> None:
        """Report can be serialized to JSON-compatible dict."""
        report = ValidationReport(
            run_id="01TEST123",
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed bug"],
            issues_remaining=[],
            summary="All good",
            confidence=ConfidenceLevel.HIGH,
        )

        data = report.model_dump(mode="json")

        assert data["run_id"] == "01TEST123"
        assert data["passed"] is True
        assert data["confidence"] == "HIGH"
        # generated_at should be serializable
        assert "generated_at" in data
