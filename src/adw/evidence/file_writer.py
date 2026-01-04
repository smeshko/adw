"""Evidence file writer for CLI output.

This module provides the EvidenceFileWriter class for writing command
execution results to evidence files in a human-readable format.
"""

import re
from pathlib import Path

from adw.models.evidence import CommandResult

SECTION_SEPARATOR = "=" * 80


class EvidenceFileWriter:
    """Writer for CLI evidence files.

    Writes command execution results to text files in a standardized,
    human-readable format suitable for verification and debugging.

    Attributes:
        evidence_dir: Path to the evidence output directory

    Example:
        >>> writer = EvidenceFileWriter(Path("/run/evidence/cli"))
        >>> writer.write_command_result("version", result)
        Path('/run/evidence/cli/version.txt')
    """

    def __init__(self, evidence_dir: Path) -> None:
        """Initialize the evidence file writer.

        Creates the evidence directory if it doesn't exist.

        Args:
            evidence_dir: Path to the evidence output directory
        """
        self.evidence_dir = evidence_dir
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def write_command_result(
        self, name: str, result: CommandResult
    ) -> Path:
        """Write a command result to an evidence file.

        Creates a file named <name>.txt with the command execution
        details in a human-readable format.

        Args:
            name: Name for the evidence file (without extension)
            result: Command execution result to write

        Returns:
            Path to the written evidence file
        """
        # Sanitize name to prevent path traversal
        safe_name = re.sub(r"[^\w\-]", "_", name)
        output_path = self.evidence_dir / f"{safe_name}.txt"
        content = self._format_evidence(result)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _format_evidence(self, result: CommandResult) -> str:
        """Format a command result as evidence text.

        Args:
            result: Command execution result to format

        Returns:
            Formatted evidence text
        """
        status = "PASSED" if result.success else "FAILED"
        executed_at = result.executed_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        lines = [
            SECTION_SEPARATOR,
            "COMMAND EVIDENCE",
            SECTION_SEPARATOR,
            f"Command: {result.command}",
            f"Executed: {executed_at}",
            f"Duration: {result.duration_seconds:.3f}s",
            f"Exit Code: {result.exit_code}",
            f"Status: {status}",
            "",
            SECTION_SEPARATOR,
            "STDOUT",
            SECTION_SEPARATOR,
            result.stdout if result.stdout else "(empty)",
            "",
            SECTION_SEPARATOR,
            "STDERR",
            SECTION_SEPARATOR,
            result.stderr if result.stderr else "(empty)",
        ]

        return "\n".join(lines)
