"""File transports for multi-tier logging.

This module provides file-based log output:
- RawFileTransport: Human-readable plain text (raw.log)
- StructuredFileTransport: JSON Lines format (logs.jsonl)

Both transports use file locking for concurrent write safety.
"""

import logging
from pathlib import Path

from filelock import FileLock

from adw.models.logging import LogEvent

# Internal logger for transport errors (avoids infinite recursion)
_logger = logging.getLogger(__name__)


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
        >>> transport.close()  # Clean up lock file
    """

    def __init__(self, path: Path | str) -> None:
        """Initialize the raw file transport.

        Args:
            path: Path to the log file
        """
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        self._closed = False

    @property
    def path(self) -> Path:
        """Get the log file path."""
        return self._path

    def write(self, event: LogEvent) -> None:
        """Write a log event to the file.

        Creates the file and parent directories if they don't exist.
        Uses file locking for concurrent write safety.
        Errors are logged but do not propagate to avoid crashing the application.

        Args:
            event: The log event to write
        """
        if self._closed:
            return

        try:
            # Ensure parent directories exist
            self._path.parent.mkdir(parents=True, exist_ok=True)

            # Format the log line
            line = self._format_event(event)

            # Write with file locking for concurrency safety
            with (
                FileLock(self._lock_path),
                open(self._path, "a", encoding="utf-8") as f,
            ):
                f.write(line + "\n")
        except OSError as e:
            # Log error but don't crash - logging should never break the app
            _logger.warning("Failed to write to log file %s: %s", self._path, e)

    def _format_event(self, event: LogEvent) -> str:
        """Format an event as a human-readable line.

        Format: TIMESTAMP [LEVEL] [category] (run_id) [phase] {extra} message

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
        if event.context.extra:
            # Format extra as key=value pairs
            extra_str = " ".join(f"{k}={v}" for k, v in event.context.extra.items())
            context_parts.append(f"{{{extra_str}}}")
        context_str = " ".join(context_parts)
        if context_str:
            context_str = f" {context_str}"

        category = event.category.value
        return f"{timestamp} [{level_name:5}] [{category}]{context_str} {event.message}"

    def close(self) -> None:
        """Close the transport and clean up resources.

        Removes the lock file if it exists.
        """
        self._closed = True
        try:
            if self._lock_path.exists():
                self._lock_path.unlink()
        except OSError:
            pass  # Ignore cleanup errors

    def __enter__(self) -> "RawFileTransport":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - ensures cleanup."""
        self.close()


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
        >>> transport.close()  # Clean up lock file
    """

    def __init__(self, path: Path | str) -> None:
        """Initialize the structured file transport.

        Args:
            path: Path to the JSONL file
        """
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        self._closed = False

    @property
    def path(self) -> Path:
        """Get the log file path."""
        return self._path

    def write(self, event: LogEvent) -> None:
        """Write a log event to the file as JSON.

        Creates the file and parent directories if they don't exist.
        Uses file locking for concurrent write safety.
        Errors are logged but do not propagate to avoid crashing the application.

        Args:
            event: The log event to write
        """
        if self._closed:
            return

        try:
            # Ensure parent directories exist
            self._path.parent.mkdir(parents=True, exist_ok=True)

            # Convert event to JSON
            json_line = event.model_dump_json()

            # Write with file locking for concurrency safety
            with (
                FileLock(self._lock_path),
                open(self._path, "a", encoding="utf-8") as f,
            ):
                f.write(json_line + "\n")
        except OSError as e:
            # Log error but don't crash - logging should never break the app
            _logger.warning("Failed to write to JSONL file %s: %s", self._path, e)

    def close(self) -> None:
        """Close the transport and clean up resources.

        Removes the lock file if it exists.
        """
        self._closed = True
        try:
            if self._lock_path.exists():
                self._lock_path.unlink()
        except OSError:
            pass  # Ignore cleanup errors

    def __enter__(self) -> "StructuredFileTransport":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - ensures cleanup."""
        self.close()
