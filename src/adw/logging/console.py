"""Console transport for multi-tier logging.

This module provides console output for log events using Rich
for TTY terminals and plain text for non-TTY (piped/redirected).
"""

import sys
from typing import TextIO

from rich.console import Console
from rich.text import Text

from adw.models.logging import LogCategory, LogEvent, LogLevel


# Level styling configuration for Rich console
LEVEL_STYLES: dict[LogLevel, str] = {
    LogLevel.TRACE: "dim",
    LogLevel.DEBUG: "dim cyan",
    LogLevel.INFO: "green",
    LogLevel.WARN: "yellow",
    LogLevel.ERROR: "bold red",
    LogLevel.FATAL: "bold white on red",
}


class ConsoleTransport:
    """Console transport for log events.

    Outputs log events to the console using Rich for TTY terminals
    and plain text for non-TTY (piped/redirected) output per UX-7.

    Attributes:
        is_tty: Whether the output is a TTY terminal
        console: Rich Console instance for TTY output

    Example:
        >>> transport = ConsoleTransport()
        >>> event = LogEvent(
        ...     level=LogLevel.INFO,
        ...     category=LogCategory.PHASE,
        ...     message="Phase completed",
        ... )
        >>> transport.write(event)
    """

    def __init__(
        self,
        *,
        file: TextIO | None = None,
        force_tty: bool | None = None,
    ) -> None:
        """Initialize the console transport.

        Args:
            file: Output file (defaults to sys.stdout)
            force_tty: Force TTY mode (True/False) or auto-detect (None)
        """
        self._file = file or sys.stdout

        # Determine TTY mode
        if force_tty is not None:
            self._is_tty = force_tty
        else:
            self._is_tty = self._file.isatty() if hasattr(self._file, "isatty") else False

        # Create Rich console for TTY output
        # force_terminal=None uses is_terminal detection
        # force_terminal=True/False forces the mode
        self._console = Console(
            file=self._file,
            force_terminal=self._is_tty,
            no_color=not self._is_tty,
        )

    @property
    def is_tty(self) -> bool:
        """Check if output is to a TTY terminal."""
        return self._is_tty

    def write(self, event: LogEvent) -> None:
        """Write a log event to the console.

        For TTY terminals, uses Rich formatting with colors and styles.
        For non-TTY output, uses plain text without ANSI codes.

        Args:
            event: The log event to write
        """
        if self._is_tty:
            self._write_rich(event)
        else:
            self._write_plain(event)

    def _write_rich(self, event: LogEvent) -> None:
        """Write event with Rich formatting for TTY."""
        # Format timestamp
        timestamp = event.timestamp.strftime("%H:%M:%S")

        # Build the log line with Rich markup
        level_style = LEVEL_STYLES.get(event.level, "")
        level_name = event.level.value.upper()

        # Build text with styling
        text = Text()

        # Timestamp (dim)
        text.append(f"{timestamp} ", style="dim")

        # Level (styled based on level)
        text.append(f"[{level_name:5}] ", style=level_style)

        # Category (cyan)
        text.append(f"[{event.category.value}] ", style="cyan")

        # Context (if present)
        if event.context.run_id:
            text.append(f"({event.context.run_id}) ", style="dim")
        if event.context.phase:
            text.append(f"[{event.context.phase}] ", style="magenta")

        # Message (styled based on level for errors)
        if event.level in (LogLevel.ERROR, LogLevel.FATAL):
            text.append(event.message, style=level_style)
        else:
            text.append(event.message)

        self._console.print(text)

    def _write_plain(self, event: LogEvent) -> None:
        """Write event as plain text for non-TTY."""
        # Format timestamp
        timestamp = event.timestamp.strftime("%H:%M:%S")
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

        # Format: TIMESTAMP [LEVEL] [category] (run_id) [phase] message
        line = f"{timestamp} [{level_name:5}] [{event.category.value}]{context_str} {event.message}"

        # Use console.print to ensure consistent output, but without markup
        self._console.print(line, markup=False, highlight=False)
