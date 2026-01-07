"""CLI evidence gatherer for the Validate phase.

This module provides the CLIEvidenceGatherer class that orchestrates
CLI terminal output evidence gathering during the Validate phase.
"""

from pathlib import Path

from adw.evidence.cli_capture import CLICaptureStrategy
from adw.evidence.config_loader import load_evidence_commands
from adw.evidence.file_writer import EvidenceFileWriter
from adw.evidence.summary_generator import SummaryGenerator
from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    CLIEvidenceSummary,
    CommandResult,
    PlatformType,
)


class CLIEvidenceGatherer:
    """Orchestrator for CLI evidence gathering.

    Coordinates the loading of command configurations, execution of commands,
    writing of evidence files, and generation of summaries.

    Attributes:
        project_root: Path to the project root directory
        evidence_dir: Path to the evidence output directory

    Example:
        >>> gatherer = CLIEvidenceGatherer(
        ...     project_root=Path("/my/project"),
        ...     evidence_dir=Path("/run/evidence/cli"),
        ... )
        >>> if gatherer.should_gather(platform):
        ...     summary = gatherer.gather()
        ...     print(f"{summary.passed} passed, {summary.failed} failed")
    """

    def __init__(
        self,
        project_root: Path,
        evidence_dir: Path,
    ) -> None:
        """Initialize the CLI evidence gatherer.

        Args:
            project_root: Path to the project root directory
            evidence_dir: Path to the evidence output directory
        """
        self.project_root = project_root
        self.evidence_dir = evidence_dir

    def should_gather(self, platform: PlatformType) -> bool:
        """Check if CLI evidence should be gathered for this platform.

        Args:
            platform: The detected platform type

        Returns:
            True if CLI evidence should be gathered, False otherwise
        """
        logger = get_logger()
        should = platform in (PlatformType.CLI, PlatformType.UNKNOWN)

        if should and platform == PlatformType.UNKNOWN:
            logger.info(
                LogCategory.STATE,
                "Platform unknown - defaulting to CLI evidence gathering",
            )

        return should

    def gather(self) -> CLIEvidenceSummary:
        """Gather CLI evidence from configured commands.

        Loads command configurations, executes each command, writes
        evidence files, and returns an aggregate summary.

        Returns:
            CLIEvidenceSummary with all command results

        Note:
            Command failures do not stop the gathering process.
            Each command is executed independently.
        """
        # Load command configurations
        commands = load_evidence_commands(self.project_root)

        if not commands:
            # No commands configured, return empty summary
            return CLIEvidenceSummary(
                total_commands=0,
                passed=0,
                failed=0,
                results=[],
            )

        # Initialize components
        capture_strategy = CLICaptureStrategy()
        file_writer = EvidenceFileWriter(self.evidence_dir)
        summary_generator = SummaryGenerator(self.evidence_dir)

        # Execute commands and collect results
        results: list[CommandResult] = []
        for config in commands:
            result = capture_strategy.execute_command_config(config)
            results.append(result)

            # Write evidence file for this command
            file_writer.write_command_result(config.name, result)

        # Generate and write summary
        summary = summary_generator.generate_summary(results)
        summary_generator.write_summary(summary)

        return summary
