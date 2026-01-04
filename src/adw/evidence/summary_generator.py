"""Summary generator for CLI evidence results.

This module provides the SummaryGenerator class for creating summaries
of CLI evidence gathering results.
"""

from pathlib import Path

from adw.models.evidence import CLIEvidenceSummary, CommandResult


class SummaryGenerator:
    """Generator for CLI evidence summaries.

    Creates aggregate summaries of command execution results and
    writes them to JSON files.

    Attributes:
        evidence_dir: Path to the evidence output directory

    Example:
        >>> generator = SummaryGenerator(Path("/run/evidence/cli"))
        >>> summary = generator.generate_summary(results)
        >>> generator.write_summary(summary)
    """

    def __init__(self, evidence_dir: Path) -> None:
        """Initialize the summary generator.

        Args:
            evidence_dir: Path to the evidence output directory
        """
        self.evidence_dir = evidence_dir

    def generate_summary(
        self, results: list[CommandResult]
    ) -> CLIEvidenceSummary:
        """Generate a summary from command results.

        Args:
            results: List of command execution results

        Returns:
            CLIEvidenceSummary with aggregated statistics
        """
        passed = sum(1 for r in results if r.success)
        failed = len(results) - passed

        return CLIEvidenceSummary(
            total_commands=len(results),
            passed=passed,
            failed=failed,
            results=results,
        )

    def write_summary(self, summary: CLIEvidenceSummary) -> Path:
        """Write summary to a JSON file.

        Args:
            summary: The summary to write

        Returns:
            Path to the written summary file
        """
        output_path = self.evidence_dir / "summary.json"
        content = summary.model_dump_json(indent=2)
        output_path.write_text(content)
        return output_path

    def format_summary_text(self, summary: CLIEvidenceSummary) -> str:
        """Format summary as human-readable text.

        Args:
            summary: The summary to format

        Returns:
            Formatted summary string (e.g., "5 passed, 2 failed")
        """
        return f"{summary.passed} passed, {summary.failed} failed"
