"""Evidence file writer for API evidence capture.

This module provides the APIEvidenceWriter class that writes
captured API evidence to files in a structured directory format.
"""

import json
import re
from pathlib import Path

from adw.logging import LogCategory, get_logger
from adw.models.evidence import APIEvidenceResult, APIEvidenceSummary


class APIEvidenceWriter:
    """Writer for API evidence files.

    Writes captured API evidence to JSON files in a structured
    directory format within the run directory.

    Directory structure:
        .adw/runs/<run_id>/evidence/api/
            health.json         # Individual endpoint result
            users.json          # Individual endpoint result
            summary.json        # Aggregate summary

    Attributes:
        run_dir: Path to the run directory

    Example:
        >>> writer = APIEvidenceWriter(run_dir=Path(".adw/runs/run123"))
        >>> writer.write_result(result)
        Path('.adw/runs/run123/evidence/api/health.json')
    """

    def __init__(self, run_dir: Path) -> None:
        """Initialize the evidence writer.

        Args:
            run_dir: Path to the run directory
        """
        self.run_dir = run_dir
        self._logger = get_logger()

    def get_evidence_dir(self) -> Path:
        """Get the evidence directory path.

        Returns:
            Path to the evidence/api directory
        """
        return self.run_dir / "evidence" / "api"

    def write_result(self, result: APIEvidenceResult) -> Path:
        """Write a single API evidence result to a file.

        Creates the evidence directory if it doesn't exist and writes
        the result to a JSON file named after the endpoint.

        Args:
            result: API evidence result to write

        Returns:
            Path to the written file
        """
        evidence_dir = self.get_evidence_dir()
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize endpoint name for filename
        safe_name = self._sanitize_filename(result.endpoint_name)
        file_path = evidence_dir / f"{safe_name}.json"

        # Serialize with datetime handling
        data = result.model_dump(mode="json")

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self._logger.debug(
            LogCategory.STATE,
            f"Wrote API evidence for '{result.endpoint_name}' to {file_path}",
        )

        return file_path

    def write_summary(self, summary: APIEvidenceSummary) -> Path:
        """Write the API evidence summary to a file.

        Creates the evidence directory if it doesn't exist and writes
        the aggregate summary to summary.json.

        Args:
            summary: API evidence summary to write

        Returns:
            Path to the written file
        """
        evidence_dir = self.get_evidence_dir()
        evidence_dir.mkdir(parents=True, exist_ok=True)

        file_path = evidence_dir / "summary.json"

        # Serialize with datetime handling
        data = summary.model_dump(mode="json")

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self._logger.debug(
            LogCategory.STATE,
            f"Wrote API evidence summary to {file_path}",
        )

        return file_path

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename.

        Replaces unsafe characters with underscores.

        Args:
            name: Original name string

        Returns:
            Sanitized filename-safe string
        """
        # Replace slashes and other unsafe characters with underscores
        safe = re.sub(r"[/\\:*?\"<>|]", "_", name)
        # Remove leading/trailing underscores
        safe = safe.strip("_")
        # Collapse multiple underscores
        safe = re.sub(r"_+", "_", safe)
        return safe if safe else "unnamed"
