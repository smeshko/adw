"""Live stream transport for real-time logging to live.log.

This module provides the LiveStreamTransport class that writes all activity
to a single human-readable log file with ANSI color formatting.

The live.log file captures:
- Phase transitions
- LLM token streams (with start/end markers)
- Tool calls
- Errors and warnings

Format:
    [2026-01-21 14:32:01] [PHASE] Starting build phase
    [2026-01-21 14:32:02] [LLM] ▶ Token stream begins
    Here is my analysis of the code...
    [2026-01-21 14:32:15] [LLM] ◀ Token stream ends (1,234 tokens)
    [2026-01-21 14:32:15] [TOOL] Read: src/main.py
"""

import logging
from datetime import datetime
from pathlib import Path

from filelock import FileLock

from adw.models.logging import LogCategory, LogEvent, LogLevel

_logger = logging.getLogger(__name__)

# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "bold_red": "\033[1;31m",
    "magenta": "\033[35m",
    "bold": "\033[1m",
}

# Level styles
LEVEL_COLORS: dict[LogLevel, str] = {
    LogLevel.TRACE: "dim",
    LogLevel.DEBUG: "dim",
    LogLevel.INFO: "green",
    LogLevel.WARN: "yellow",
    LogLevel.ERROR: "red",
    LogLevel.FATAL: "bold_red",
}

# Category styles
CATEGORY_COLORS: dict[LogCategory, str] = {
    LogCategory.PHASE: "magenta",
    LogCategory.LLM: "cyan",
    LogCategory.HOOK: "yellow",
    LogCategory.STATE: "green",
    LogCategory.ERROR: "red",
    LogCategory.PERFORMANCE: "dim",
    LogCategory.WEBHOOK: "cyan",
}


class LiveStreamTransport:
    """Transport for writing to live.log with ANSI formatting.

    Writes all log events to a single human-readable file with:
    - Timestamps
    - Category markers with color
    - Unbuffered/flushed writes for real-time tailing

    Attributes:
        path: Path to the live.log file

    Example:
        >>> transport = LiveStreamTransport(Path(".adw/runs/123/live.log"))
        >>> transport.write(event)
        >>> transport.write_llm_start()
        >>> transport.write_llm_token("Hello world")
        >>> transport.write_llm_end(1234)
    """

    def __init__(self, path: Path | str) -> None:
        """Initialize the live stream transport.

        Args:
            path: Path to the live.log file
        """
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        self._closed = False
        self._in_llm_stream = False

    @property
    def path(self) -> Path:
        """Get the log file path."""
        return self._path

    def _colorize(self, text: str, color: str) -> str:
        """Apply ANSI color to text.

        Args:
            text: Text to colorize
            color: Color name from COLORS dict

        Returns:
            Colorized text with ANSI codes
        """
        color_code = COLORS.get(color, "")
        reset = COLORS["reset"]
        return f"{color_code}{text}{reset}" if color_code else text

    def _write_line(self, line: str, *, flush: bool = True) -> None:
        """Write a line to the log file.

        Creates the file and parent directories if they don't exist.
        Uses file locking for concurrent write safety.
        Flushes immediately by default for real-time tailing.

        Args:
            line: Line to write (without newline)
            flush: Whether to flush immediately (default True)
        """
        if self._closed:
            return

        try:
            # Ensure parent directories exist
            self._path.parent.mkdir(parents=True, exist_ok=True)

            # Write with file locking for concurrency safety
            with FileLock(self._lock_path):
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                    if flush:
                        f.flush()
        except OSError as e:
            _logger.warning("Failed to write to live.log %s: %s", self._path, e)

    def _format_timestamp(self) -> str:
        """Format current timestamp for log line.

        Returns:
            Formatted timestamp string
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def write(self, event: LogEvent) -> None:
        """Write a log event to the file.

        Formats the event with timestamp, level, category, and message.

        Args:
            event: The log event to write
        """
        if self._closed:
            return

        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_color = LEVEL_COLORS.get(event.level, "")
        category_color = CATEGORY_COLORS.get(event.category, "cyan")

        # Format: [timestamp] [LEVEL] [category] message
        level_str = self._colorize(f"[{event.level.value.upper()}]", level_color)
        category_str = self._colorize(f"[{event.category.value.upper()}]", category_color)

        # Build context if present
        context_parts = []
        if event.context.run_id:
            context_parts.append(f"run={event.context.run_id[:8]}")
        if event.context.phase:
            context_parts.append(f"phase={event.context.phase}")
        context_str = ""
        if context_parts:
            ctx = " ".join(context_parts)
            context_str = self._colorize(f" {{{ctx}}}", "dim")

        line = f"[{timestamp}] {level_str} {category_str}{context_str} {event.message}"
        self._write_line(line)

    def write_llm_start(self, phase: str | None = None) -> None:
        """Write LLM token stream start marker.

        Args:
            phase: Optional phase name for context
        """
        if self._closed:
            return

        self._in_llm_stream = True
        timestamp = self._format_timestamp()
        marker = self._colorize("▶", "cyan")
        label = self._colorize("[LLM]", "cyan")
        phase_str = f" ({phase})" if phase else ""

        line = f"[{timestamp}] {label} {marker} Token stream begins{phase_str}"
        self._write_line(line)

    def write_llm_token(self, content: str) -> None:
        """Write LLM token content.

        Tokens are written as-is for replay fidelity.

        Args:
            content: Token text content
        """
        if self._closed:
            return

        # Write token content directly (no timestamp, just the text)
        # This preserves the stream for replay
        self._write_line(content, flush=True)

    def write_llm_end(self, token_count: int = 0, duration_ms: int = 0) -> None:
        """Write LLM token stream end marker.

        Args:
            token_count: Total tokens in the stream
            duration_ms: Duration of the stream in milliseconds
        """
        if self._closed:
            return

        self._in_llm_stream = False
        timestamp = self._format_timestamp()
        marker = self._colorize("◀", "cyan")
        label = self._colorize("[LLM]", "cyan")

        stats_parts = []
        if token_count > 0:
            stats_parts.append(f"{token_count:,} tokens")
        if duration_ms > 0:
            seconds = duration_ms / 1000
            stats_parts.append(f"{seconds:.1f}s")
        stats = f" ({', '.join(stats_parts)})" if stats_parts else ""

        line = f"\n[{timestamp}] {label} {marker} Token stream ends{stats}"
        self._write_line(line)

    def write_tool_call(
        self,
        tool_name: str,
        context: str | None = None,
    ) -> None:
        """Write a tool call log entry.

        Args:
            tool_name: Name of the tool being called
            context: Brief context (e.g., file path for Read)
        """
        if self._closed:
            return

        timestamp = self._format_timestamp()
        label = self._colorize("[TOOL]", "yellow")
        tool = self._colorize(tool_name, "bold")
        ctx = f": {context}" if context else ""

        line = f"[{timestamp}] {label} {tool}{ctx}"
        self._write_line(line)

    def write_phase(self, phase: str, event: str = "started") -> None:
        """Write a phase transition log entry.

        Args:
            phase: Phase name
            event: Event type (started, completed, failed)
        """
        if self._closed:
            return

        timestamp = self._format_timestamp()
        label = self._colorize("[PHASE]", "magenta")
        phase_name = self._colorize(phase, "bold")

        line = f"[{timestamp}] {label} Phase '{phase_name}' {event}"
        self._write_line(line)

    def write_error(self, message: str) -> None:
        """Write an error log entry.

        Args:
            message: Error message
        """
        if self._closed:
            return

        timestamp = self._format_timestamp()
        label = self._colorize("[ERROR]", "red")
        msg = self._colorize(message, "red")

        line = f"[{timestamp}] {label} {msg}"
        self._write_line(line)

    def write_raw(self, content: str) -> None:
        """Write raw content without formatting.

        Useful for preserving LLM output exactly as received.

        Args:
            content: Content to write
        """
        if self._closed:
            return

        self._write_line(content, flush=True)

    def close(self) -> None:
        """Close the transport and clean up resources.

        Removes the lock file if it exists.
        """
        self._closed = True
        try:
            if self._lock_path.exists():
                self._lock_path.unlink()
        except OSError:
            pass

    def __enter__(self) -> "LiveStreamTransport":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - ensures cleanup."""
        self.close()
