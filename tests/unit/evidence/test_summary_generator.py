"""Tests for CLI evidence summary generation.

Tests the SummaryGenerator class that creates summaries and logs results.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from adw.evidence.summary_generator import SummaryGenerator
from adw.models.evidence import CLIEvidenceSummary, CommandResult


class TestSummaryGenerator:
    """Tests for SummaryGenerator class."""

    def test_init(self, tmp_path: Path) -> None:
        """SummaryGenerator should initialize with evidence dir."""
        evidence_dir = tmp_path / "evidence" / "cli"
        generator = SummaryGenerator(evidence_dir)
        assert generator.evidence_dir == evidence_dir


class TestGenerateSummary:
    """Tests for generate_summary method."""

    def test_generate_empty_summary(self, tmp_path: Path) -> None:
        """generate_summary should handle empty results."""
        evidence_dir = tmp_path / "evidence" / "cli"
        generator = SummaryGenerator(evidence_dir)

        summary = generator.generate_summary([])

        assert isinstance(summary, CLIEvidenceSummary)
        assert summary.total_commands == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.results == []
        assert summary.platform == "cli"

    def test_generate_summary_all_passed(self, tmp_path: Path) -> None:
        """generate_summary should count all passed commands."""
        evidence_dir = tmp_path / "evidence" / "cli"
        generator = SummaryGenerator(evidence_dir)

        results = [
            CommandResult(
                command="echo a",
                exit_code=0,
                stdout="a",
                stderr="",
                duration_seconds=0.1,
                success=True,
            ),
            CommandResult(
                command="echo b",
                exit_code=0,
                stdout="b",
                stderr="",
                duration_seconds=0.1,
                success=True,
            ),
        ]

        summary = generator.generate_summary(results)

        assert summary.total_commands == 2
        assert summary.passed == 2
        assert summary.failed == 0

    def test_generate_summary_with_failures(self, tmp_path: Path) -> None:
        """generate_summary should count failed commands."""
        evidence_dir = tmp_path / "evidence" / "cli"
        generator = SummaryGenerator(evidence_dir)

        results = [
            CommandResult(
                command="true",
                exit_code=0,
                stdout="",
                stderr="",
                duration_seconds=0.1,
                success=True,
            ),
            CommandResult(
                command="false",
                exit_code=1,
                stdout="",
                stderr="error",
                duration_seconds=0.1,
                success=False,
            ),
            CommandResult(
                command="timeout",
                exit_code=-1,
                stdout="",
                stderr="timed out",
                duration_seconds=30.0,
                success=False,
            ),
        ]

        summary = generator.generate_summary(results)

        assert summary.total_commands == 3
        assert summary.passed == 1
        assert summary.failed == 2

    def test_generate_summary_stores_results(self, tmp_path: Path) -> None:
        """generate_summary should store all results in summary."""
        evidence_dir = tmp_path / "evidence" / "cli"
        generator = SummaryGenerator(evidence_dir)

        results = [
            CommandResult(
                command="cmd1",
                exit_code=0,
                stdout="out1",
                stderr="",
                duration_seconds=0.1,
                success=True,
            ),
        ]

        summary = generator.generate_summary(results)

        assert len(summary.results) == 1
        assert summary.results[0].command == "cmd1"


class TestWriteSummary:
    """Tests for write_summary method."""

    def test_write_summary_creates_file(self, tmp_path: Path) -> None:
        """write_summary should create summary.json."""
        evidence_dir = tmp_path / "evidence" / "cli"
        evidence_dir.mkdir(parents=True)
        generator = SummaryGenerator(evidence_dir)

        summary = CLIEvidenceSummary(
            total_commands=2,
            passed=1,
            failed=1,
            results=[],
        )

        output_path = generator.write_summary(summary)

        assert output_path.exists()
        assert output_path.name == "summary.json"

    def test_write_summary_json_content(self, tmp_path: Path) -> None:
        """write_summary should write valid JSON."""
        evidence_dir = tmp_path / "evidence" / "cli"
        evidence_dir.mkdir(parents=True)
        generator = SummaryGenerator(evidence_dir)

        result = CommandResult(
            command="test-cmd",
            exit_code=0,
            stdout="output",
            stderr="",
            duration_seconds=0.5,
            success=True,
            executed_at=datetime(2026, 1, 3, 10, 30, 45, tzinfo=UTC),
        )
        summary = CLIEvidenceSummary(
            total_commands=1,
            passed=1,
            failed=0,
            results=[result],
            captured_at=datetime(2026, 1, 3, 10, 31, 0, tzinfo=UTC),
        )

        output_path = generator.write_summary(summary)

        content = json.loads(output_path.read_text())
        assert content["total_commands"] == 1
        assert content["passed"] == 1
        assert content["failed"] == 0
        assert content["platform"] == "cli"
        assert len(content["results"]) == 1


class TestFormatSummaryText:
    """Tests for format_summary_text method."""

    def test_format_all_passed(self, tmp_path: Path) -> None:
        """format_summary_text should show all passed."""
        evidence_dir = tmp_path / "evidence" / "cli"
        generator = SummaryGenerator(evidence_dir)

        summary = CLIEvidenceSummary(
            total_commands=5,
            passed=5,
            failed=0,
            results=[],
        )

        text = generator.format_summary_text(summary)

        assert "5 passed" in text
        assert "0 failed" in text

    def test_format_mixed_results(self, tmp_path: Path) -> None:
        """format_summary_text should show mixed results."""
        evidence_dir = tmp_path / "evidence" / "cli"
        generator = SummaryGenerator(evidence_dir)

        summary = CLIEvidenceSummary(
            total_commands=10,
            passed=7,
            failed=3,
            results=[],
        )

        text = generator.format_summary_text(summary)

        assert "7 passed" in text
        assert "3 failed" in text

    def test_format_empty_results(self, tmp_path: Path) -> None:
        """format_summary_text should handle empty results."""
        evidence_dir = tmp_path / "evidence" / "cli"
        generator = SummaryGenerator(evidence_dir)

        summary = CLIEvidenceSummary(
            total_commands=0,
            passed=0,
            failed=0,
            results=[],
        )

        text = generator.format_summary_text(summary)

        assert "0 passed" in text
        assert "0 failed" in text
