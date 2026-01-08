"""Validation report generation.

Simplified in Epic 16 (Story 16.4) to work with the new ValidationResult model.
Reports are generated from the simplified validation result returned by the LLM.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from adw.validation.models import ValidationResult

__all__ = [
    "ConfidenceLevel",
    "ValidationReport",
    "ValidationReportGenerator",
]

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level for validation results.

    - HIGH: All issues resolved, none remaining
    - MEDIUM: Some issues remaining (<30%)
    - LOW: Many issues remaining (>=30%)
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ValidationReport(BaseModel):
    """Validation report summarizing results.

    Contains metrics and details from the validation phase execution.

    Attributes:
        run_id: The run ID this report belongs to.
        generated_at: When the report was generated.
        passed: Whether validation passed overall.
        tests_passed: Whether all tests passed.
        code_review_passed: Whether code review was clean.
        issues_fixed: List of fixed issue summaries.
        issues_remaining: List of remaining issue summaries.
        summary: Human-readable summary.
        confidence: Overall confidence level.
    """

    run_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    passed: bool
    tests_passed: bool
    code_review_passed: bool
    issues_fixed: list[str] = Field(default_factory=list)
    issues_remaining: list[str] = Field(default_factory=list)
    summary: str
    confidence: ConfidenceLevel

    model_config = {
        "frozen": False,
        "validate_assignment": True,
    }

    def to_markdown(self) -> str:
        """Generate markdown report.

        Returns:
            Markdown-formatted string.
        """
        status_emoji = "✅" if self.passed else "❌"
        tests_status = "✅ Pass" if self.tests_passed else "❌ Fail"
        review_status = "✅ Clean" if self.code_review_passed else "❌ Issues"

        lines = [
            "# Validation Report",
            "",
            f"**Run ID:** {self.run_id}",
            f"**Generated:** {self.generated_at.isoformat()}",
            f"**Status:** {status_emoji} {'PASSED' if self.passed else 'FAILED'}",
            "",
            "## Summary",
            "",
            f"{self.summary}",
            "",
            "## Results",
            "",
            "| Check | Status |",
            "|-------|--------|",
            f"| Tests | {tests_status} |",
            f"| Code Review | {review_status} |",
            f"| Confidence | {self.confidence.value} |",
            "",
        ]

        if self.issues_fixed:
            lines.extend(
                [
                    "## Issues Fixed",
                    "",
                    *[f"- {issue}" for issue in self.issues_fixed],
                    "",
                ]
            )

        if self.issues_remaining:
            lines.extend(
                [
                    "## Issues Remaining",
                    "",
                    *[f"- {issue}" for issue in self.issues_remaining],
                    "",
                ]
            )

        return "\n".join(lines)


class ValidationReportGenerator:
    """Generates validation reports from validation results.

    Attributes:
        run_id: Run ID for the report.
        output_dir: Directory to save reports.
    """

    def __init__(
        self,
        run_id: str,
        output_dir: Path | None = None,
    ) -> None:
        """Initialize the report generator.

        Args:
            run_id: Run ID for report association.
            output_dir: Directory to save reports. If None, reports are not saved.
        """
        self.run_id = run_id
        self.output_dir = output_dir

    def generate(self, result: ValidationResult) -> ValidationReport:
        """Generate validation report from result.

        Args:
            result: ValidationResult from the validation phase.

        Returns:
            ValidationReport with metrics and confidence assessment.
        """
        confidence = self._calculate_confidence(result)

        return ValidationReport(
            run_id=self.run_id,
            passed=result.passed,
            tests_passed=result.tests_passed,
            code_review_passed=result.code_review_passed,
            issues_fixed=result.issues_fixed,
            issues_remaining=result.issues_remaining,
            summary=result.summary,
            confidence=confidence,
        )

    def _calculate_confidence(self, result: ValidationResult) -> ConfidenceLevel:
        """Calculate confidence level based on validation result.

        Args:
            result: ValidationResult from validation.

        Returns:
            ConfidenceLevel based on remaining issues.
        """
        total_issues = len(result.issues_fixed) + len(result.issues_remaining)

        if total_issues == 0:
            return ConfidenceLevel.HIGH

        if len(result.issues_remaining) == 0:
            return ConfidenceLevel.HIGH

        remaining_ratio = len(result.issues_remaining) / total_issues
        if remaining_ratio >= 0.3:
            return ConfidenceLevel.LOW

        return ConfidenceLevel.MEDIUM

    def save(self, report: ValidationReport) -> Path | None:
        """Save report to output directory.

        Args:
            report: The ValidationReport to save.

        Returns:
            Path to the markdown report file, or None if no output_dir.
        """
        if not self.output_dir:
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save markdown
        md_path = self.output_dir / "validation_report.md"
        md_path.write_text(report.to_markdown())
        logger.info("Saved markdown report", extra={"path": str(md_path)})

        # Save JSON
        json_path = self.output_dir / "validation_report.json"
        json_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, default=str)
        )
        logger.info("Saved JSON report", extra={"path": str(json_path)})

        return md_path
