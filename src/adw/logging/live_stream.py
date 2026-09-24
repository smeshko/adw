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
import time
from datetime import UTC, datetime
from io import TextIOWrapper
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
}


# Tag and ANSI colour per stdlib level. WARN/FATAL are the tags the dashboard
# and `adw logs follow` key on.
_LEVEL_TAGS: dict[int, tuple[str, str]] = {
    logging.DEBUG: ("DEBUG", "dim"),
    logging.INFO: ("INFO", "green"),
    logging.WARNING: ("WARN", "yellow"),
    logging.ERROR: ("ERROR", "red"),
    logging.CRITICAL: ("FATAL", "bold_red"),
}


def _colorize(text: str, color: str) -> str:
    """Wrap text in an ANSI colour from COLORS; unknown or empty colours pass."""
    color_code = COLORS.get(color, "")
    return f"{color_code}{text}{COLORS['reset']}" if color_code else text


def _utc_stamp(created: float) -> str:
    """Format a POSIX timestamp as a UTC ``YYYY-MM-DD HH:MM:SS``."""
    return datetime.fromtimestamp(created, UTC).strftime("%Y-%m-%d %H:%M:%S")


class LiveStreamHandler(logging.FileHandler):
    """The run's one live.log writer: log records plus the LLM stream.

    Opens live.log once, on the first line, appends, and flushes after every
    line so `adw logs follow` and the dashboard can tail it. The LLM stream
    lines (``write_llm_*``, ``write_tool_call``, ``write_error``) go through
    ``handle()`` like records do: the handler's filters, such as the
    RedactingFilter that setup_logging adds, apply to them, and the handler's
    lock orders them with records. A filter sees only a line's text; the
    timestamp, tag and ANSI colours are added afterwards, in ``format``.

    Example:
        >>> handler = LiveStreamHandler(Path(".adw/runs/123/live.log"))
        >>> handler.write_llm_start("plan")
        >>> handler.write_llm_token("Hello world")
        >>> handler.write_llm_end(1234)
    """

    def __init__(self, path: Path | str) -> None:
        """Initialize the handler without touching the disk.

        Args:
            path: Path to the live.log file, created on the first line
        """
        super().__init__(path, mode="a", encoding="utf-8", delay=True)

    def _open(self) -> TextIOWrapper:
        """Create the run directory, then open live.log for appending."""
        Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)
        return super()._open()

    def format(self, record: logging.LogRecord) -> str:
        """Render a record as a live.log line.

        A log record becomes ``[timestamp] [LEVEL] {run=… phase=…} message``.
        A stream line written by this handler keeps the prefix it was built
        with, followed by its (filtered) text.

        Args:
            record: The record to render

        Returns:
            The line, without its trailing newline
        """
        text = super().format(record)
        prefix = getattr(record, "live_prefix", None)
        if prefix is not None:
            return str(prefix) + _colorize(text, getattr(record, "live_color", ""))

        tag, color = _LEVEL_TAGS.get(record.levelno, (record.levelname, ""))
        parts: list[str] = []
        run_id = getattr(record, "run_id", None)
        if run_id:
            parts.append(f"run={str(run_id)[:8]}")
        phase = getattr(record, "phase", None)
        if phase:
            parts.append(f"phase={phase}")
        context = _colorize(f" {{{' '.join(parts)}}}", "dim") if parts else ""
        stamp = _utc_stamp(record.created)
        return f"[{stamp}] {_colorize(f'[{tag}]', color)}{context} {text}"

    def _write_line(
        self,
        prefix: str,
        text: str = "",
        *,
        color: str = "",
        levelno: int = logging.INFO,
    ) -> None:
        """Write one stream line through the handler's filters and lock.

        Args:
            prefix: Rendered start of the line (timestamp, tag), never filtered
            text: The line's content, which the filters see and may redact
            color: ANSI colour for the content
            levelno: Level of the line (ERROR for write_error)
        """
        self.handle(
            logging.makeLogRecord(
                {
                    "msg": text,
                    "levelno": levelno,
                    "levelname": logging.getLevelName(levelno),
                    "live_prefix": prefix,
                    "live_color": color,
                }
            )
        )

    def write_llm_start(self, phase: str | None = None) -> None:
        """Write the LLM token stream start marker.

        Args:
            phase: Optional phase name for context
        """
        label = _colorize("[LLM]", "cyan")
        marker = _colorize("▶", "cyan")
        phase_str = f" ({phase})" if phase else ""
        stamp = _utc_stamp(time.time())
        self._write_line(
            f"[{stamp}] {label} {marker} ", f"Token stream begins{phase_str}"
        )

    def write_llm_token(self, content: str) -> None:
        """Write LLM text as is, with no timestamp, for replay fidelity.

        Args:
            content: Token text content
        """
        self._write_line("", content)

    def write_llm_end(self, token_count: int = 0, duration_ms: int = 0) -> None:
        """Write the LLM token stream end marker on a line of its own.

        Args:
            token_count: Total tokens in the stream
            duration_ms: Duration of the stream in milliseconds
        """
        label = _colorize("[LLM]", "cyan")
        marker = _colorize("◀", "cyan")
        stats_parts = []
        if token_count > 0:
            stats_parts.append(f"{token_count:,} tokens")
        if duration_ms > 0:
            stats_parts.append(f"{duration_ms / 1000:.1f}s")
        stats = f" ({', '.join(stats_parts)})" if stats_parts else ""
        stamp = _utc_stamp(time.time())
        self._write_line(f"\n[{stamp}] {label} {marker} ", f"Token stream ends{stats}")

    def write_tool_call(self, tool_name: str, context: str | None = None) -> None:
        """Write a tool call line.

        Args:
            tool_name: Name of the tool being called
            context: Brief context (e.g. the file path for Read)
        """
        label = _colorize("[TOOL]", "yellow")
        tool = _colorize(tool_name, "bold")
        stamp = _utc_stamp(time.time())
        if context:
            self._write_line(f"[{stamp}] {label} {tool}: ", context)
        else:
            self._write_line(f"[{stamp}] {label} {tool}")

    def write_error(self, message: str) -> None:
        """Write an error line.

        Args:
            message: Error message
        """
        label = _colorize("[ERROR]", "red")
        stamp = _utc_stamp(time.time())
        self._write_line(
            f"[{stamp}] {label} ", message, color="red", levelno=logging.ERROR
        )


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
            with (
                FileLock(self._lock_path),
                open(self._path, "a", encoding="utf-8") as f,
            ):
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
        cat_upper = event.category.value.upper()
        category_str = self._colorize(f"[{cat_upper}]", category_color)

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
