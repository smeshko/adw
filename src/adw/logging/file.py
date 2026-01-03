"""File transports for multi-tier logging.

This module provides file-based log output:
- RawFileTransport: Human-readable plain text (raw.log)
- StructuredFileTransport: JSON Lines format (logs.jsonl)

Both transports use file locking for concurrent write safety.
"""

from pathlib import Path
from typing import Union

from filelock import FileLock

from adw.models.logging import LogEvent


class RawFileTransport:
    """Transport for writing human-readable log files.

    Writes log events as plain text lines to a raw log file.
    Uses file locking for concurrent write safety (NFR3).

    Attributes:
        path: Path to the log file

    Example:
        >>> transport = RawFileTransport(Path(".agent/runs/123/logs/raw.log"))
        >>> event = LogEvent(
        ...     level=LogLevel.INFO,
        ...     category=LogCategory.PHASE,
        ...     message="Phase completed",
        ... )
        >>> transport.write(event)
    """

    def __init__(self, path: Union[Path, str]) -> None:
        """Initialize the raw file transport.

        Args:
            path: Path to the log file
        """
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")

    @property
    def path(self) -> Path:
        """Get the log file path."""
        return self._path

    def write(self, event: LogEvent) -> None:
        """Write a log event to the file.

        Creates the file and parent directories if they don't exist.
        Uses file locking for concurrent write safety.

        Args:
            event: The log event to write
        """
        # Ensure parent directories exist
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Format the log line
        line = self._format_event(event)

        # Write with file locking for concurrency safety
        with FileLock(self._lock_path):
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def _format_event(self, event: LogEvent) -> str:
        """Format an event as a human-readable line.

        Format: TIMESTAMP [LEVEL] [category] (run_id) [phase] message

        Args:
            event: The log event to format

        Returns:
            Formatted log line
        """
        # Format timestamp
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_name = event.level.value.upper()

        # Build context string
        context_parts: list[str] = []
        if event.context.run_id:
            context_parts.append(f"({event.context.run_id})")
        if event.context.phase:
            context_parts.append(f"[{event.context.phase}]")
        context_str = " ".join(context_parts)
        if context_str:
            context_str = f" {context_str}"

        return f"{timestamp} [{level_name:5}] [{event.category.value}]{context_str} {event.message}"


class StructuredFileTransport:
    """Transport for writing structured JSONL log files.

    Writes log events as JSON Lines (one JSON object per line).
    Uses file locking for concurrent write safety (NFR3).

    The JSON format includes all LogEvent fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level string
    - category: Log category string
    - message: Log message
    - context: Context object with run_id, phase, extra

    Attributes:
        path: Path to the JSONL file

    Example:
        >>> transport = StructuredFileTransport(Path(".agent/runs/123/logs/logs.jsonl"))
        >>> event = LogEvent(
        ...     level=LogLevel.INFO,
        ...     category=LogCategory.PHASE,
        ...     message="Phase completed",
        ... )
        >>> transport.write(event)
    """

    def __init__(self, path: Union[Path, str]) -> None:
        """Initialize the structured file transport.

        Args:
            path: Path to the JSONL file
        """
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")

    @property
    def path(self) -> Path:
        """Get the log file path."""
        return self._path

    def write(self, event: LogEvent) -> None:
        """Write a log event to the file as JSON.

        Creates the file and parent directories if they don't exist.
        Uses file locking for concurrent write safety.

        Args:
            event: The log event to write
        """
        # Ensure parent directories exist
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Convert event to JSON
        json_line = event.model_dump_json()

        # Write with file locking for concurrency safety
        with FileLock(self._lock_path):
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json_line + "\n")
