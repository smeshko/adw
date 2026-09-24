"""The run's live.log writer.

LiveStreamHandler writes one human-readable file per run, with ANSI colours,
for `adw logs follow` and the dashboard to tail. It captures:
- The ``adw`` logger's records (phase transitions, warnings, errors)
- LLM text (between start/end markers)
- Tool calls

Timestamps are UTC. Format:
    [2026-01-21 14:32:01] [INFO] {phase=build} Phase build started
    [2026-01-21 14:32:02] [LLM] ▶ Token stream begins (build)
    Here is my analysis of the code...
    [2026-01-21 14:32:15] [LLM] ◀ Token stream ends (1,234 tokens, 13.0s)
    [2026-01-21 14:32:15] [TOOL] Read: src/main.py
"""

import logging
import time
from datetime import UTC, datetime
from io import TextIOWrapper
from pathlib import Path

# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "bold_red": "\033[1;31m",
    "bold": "\033[1m",
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
