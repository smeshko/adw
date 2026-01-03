"""Tool execution logging for security auditing.

This module provides the ToolLogger class for persisting tool call logs
to JSONL files for audit and debugging purposes.
"""

import logging
from pathlib import Path

from filelock import FileLock

from adw.models.security import ToolCallLog

# Internal logger for transport errors
_logger = logging.getLogger(__name__)


class ToolLogger:
    """Logger for tool execution events.

    Writes tool call logs to a JSONL file in the run directory for
    audit and debugging purposes. Uses file locking for thread-safe
    concurrent writes.

    The log file is stored at `.adw/runs/<run_id>/tools.jsonl`.

    Example:
        >>> run_dir = Path(".adw/runs/01HQXK5P3Z")
        >>> logger = ToolLogger(run_dir)
        >>> entry = ToolCallLog(
        ...     timestamp="2026-01-03T10:30:00.123Z",
        ...     tool_name="Bash",
        ...     arguments={"command": "npm test"},
        ...     result_summary="Exit code: 0",
        ...     duration_ms=2500,
        ... )
        >>> logger.log_tool_call(entry)
        >>> logger.close()

    Context manager usage:
        >>> with ToolLogger(run_dir) as logger:
        ...     logger.log_tool_call(entry)
    """

    FILENAME = "tools.jsonl"
    """Name of the tool log file."""

    def __init__(self, run_dir: Path | str) -> None:
        """Initialize the ToolLogger.

        Args:
            run_dir: Path to the run directory (e.g., .adw/runs/01HQXK5P3Z).
        """
        self._run_dir = Path(run_dir)
        self._log_path = self._run_dir / self.FILENAME
        self._lock_path = self._log_path.with_suffix(
            self._log_path.suffix + ".lock"
        )
        self._closed = False

    @property
    def run_dir(self) -> Path:
        """Get the run directory path."""
        return self._run_dir

    @property
    def log_path(self) -> Path:
        """Get the tool log file path."""
        return self._log_path

    def log_tool_call(self, entry: ToolCallLog) -> None:
        """Log a tool call to the JSONL file.

        Creates the file and parent directories if they don't exist.
        Uses file locking for concurrent write safety.

        Args:
            entry: The tool call log entry to write.
        """
        if self._closed:
            return

        try:
            # Ensure parent directories exist
            self._run_dir.mkdir(parents=True, exist_ok=True)

            # Convert entry to JSON
            json_line = entry.model_dump_json()

            # Write with file locking for concurrency safety
            with (
                FileLock(self._lock_path),
                open(self._log_path, "a", encoding="utf-8") as f,
            ):
                f.write(json_line + "\n")

        except OSError as e:
            # Log error but don't crash - logging should never break the app
            _logger.warning(
                "Failed to write tool log to %s: %s",
                self._log_path,
                e,
            )

    def get_tool_history(self) -> list[ToolCallLog]:
        """Get all tool call entries from the log file.

        Reads and parses the JSONL file, returning all entries
        in chronological order.

        Returns:
            List of ToolCallLog entries in order they were logged.
            Returns empty list if file doesn't exist or is empty.
        """
        if not self._log_path.exists():
            return []

        entries: list[ToolCallLog] = []
        try:
            with open(self._log_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(ToolCallLog.model_validate_json(line))
        except (OSError, ValueError) as e:
            _logger.warning(
                "Failed to read tool log from %s: %s",
                self._log_path,
                e,
            )

        return entries

    @staticmethod
    def get_tool_history_for_run(
        runs_dir: Path | str,
        run_id: str,
    ) -> list[ToolCallLog]:
        """Get tool history for a specific run ID.

        Convenience static method for reading tool history without
        needing to construct the full run directory path.

        Args:
            runs_dir: Path to the runs directory (e.g., .adw/runs).
            run_id: The run ID.

        Returns:
            List of ToolCallLog entries for the run.
            Returns empty list if run or log file doesn't exist.
        """
        run_dir = Path(runs_dir) / run_id
        logger = ToolLogger(run_dir)
        return logger.get_tool_history()

    def close(self) -> None:
        """Close the logger and clean up resources.

        Removes the lock file if it exists.
        """
        self._closed = True
        try:
            if self._lock_path.exists():
                self._lock_path.unlink()
        except OSError:
            pass  # Ignore cleanup errors

    def __enter__(self) -> "ToolLogger":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - ensures cleanup."""
        self.close()
