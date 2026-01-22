"""Console transport for multi-tier logging.

This module provides console output for log events using Rich
for TTY terminals and plain text for non-TTY (piped/redirected).
"""

import sys
from typing import TYPE_CHECKING, TextIO

from rich.console import Console
from rich.text import Text

from adw.models.logging import VERBOSITY_LEVEL_MAP, LogEvent, LogLevel, Verbosity

if TYPE_CHECKING:
    from rich.live import Live

# Module-level reference to active Live display for spinner/log coordination.
# When a spinner is active, logs should stop the Live display first to
# prevent output overlap (e.g., "⠧ LLM executing...14:36:35 [WARN]").
_active_live: "Live | None" = None


def set_active_live(live: "Live | None") -> None:
    """Set the active Live display for spinner/log coordination.

    Called by ProgressDisplay.on_llm_start() to register the spinner,
    and on_llm_complete() to unregister it.

    Args:
        live: The active Live display, or None to clear.
    """
    global _active_live
    _active_live = live


def get_active_live() -> "Live | None":
    """Get the currently active Live display.

    Returns:
        The active Live display, or None if no spinner is running.
    """
    return _active_live


# Level styling configuration for Rich console
LEVEL_STYLES: dict[LogLevel, str] = {
    LogLevel.TRACE: "dim",
    LogLevel.DEBUG: "dim cyan",
    LogLevel.INFO: "green",
    LogLevel.WARN: "yellow",
    LogLevel.ERROR: "bold red",
    LogLevel.FATAL: "bold white on red",
}

# Level ordering for comparison
LEVEL_ORDER: dict[LogLevel, int] = {
    LogLevel.TRACE: 0,
    LogLevel.DEBUG: 1,
    LogLevel.INFO: 2,
    LogLevel.WARN: 3,
    LogLevel.ERROR: 4,
    LogLevel.FATAL: 5,
}


def should_log(level: LogLevel, verbosity: Verbosity) -> bool:
    """Check if an event at the given level should be logged for the verbosity.

    Args:
        level: The log level of the event
        verbosity: The current verbosity setting

    Returns:
        True if the event should be logged, False otherwise

    Examples:
        >>> should_log(LogLevel.DEBUG, Verbosity.VERBOSE)
        True
        >>> should_log(LogLevel.DEBUG, Verbosity.NORMAL)
        False
    """
    threshold = VERBOSITY_LEVEL_MAP[verbosity]
    return LEVEL_ORDER[level] >= LEVEL_ORDER[threshold]


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
        verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        """Initialize the console transport.

        Args:
            file: Output file (defaults to sys.stdout)
            force_tty: Force TTY mode (True/False) or auto-detect (None)
            verbosity: Verbosity level for filtering (default: NORMAL)
        """
        self._file = file or sys.stdout
        self._verbosity = verbosity

        # Determine TTY mode
        if force_tty is not None:
            self._is_tty = force_tty
        elif hasattr(self._file, "isatty"):
            self._is_tty = self._file.isatty()
        else:
            self._is_tty = False

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

    @property
    def verbosity(self) -> Verbosity:
        """Get the current verbosity level."""
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value: Verbosity) -> None:
        """Set the verbosity level.

        Args:
            value: New verbosity level
        """
        self._verbosity = value

    def write(self, event: LogEvent) -> None:
        """Write a log event to the console.

        For TTY terminals, uses Rich formatting with colors and styles.
        For non-TTY output, uses plain text without ANSI codes.

        Events are filtered based on verbosity level:
        - QUIET: Only ERROR and FATAL
        - NORMAL: INFO and above
        - VERBOSE: DEBUG and above
        - TRACE: All levels

        When a spinner is active, stops it temporarily to prevent output
        overlap (e.g., "⠧ LLM executing...14:36:35 [WARN]").

        Args:
            event: The log event to write
        """
        # Filter based on verbosity
        if not should_log(event.level, self._verbosity):
            return

        # Stop active Live display to prevent spinner/log overlap
        # The Live will be restarted by the next on_llm_progress() call
        live = get_active_live()
        if live is not None:
            live.stop()
            # Clear the module reference since we stopped it
            set_active_live(None)

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

        # Level (styled based on level, no padding)
        text.append(f"[{level_name}] ", style=level_style)

        # Category (cyan)
        text.append(f"[{event.category.value}] ", style="cyan")

        # Context (if present) - only show extra fields, not run_id or phase
        # Run_id is shown in run header and file logs; phase is shown in panel
        if event.context.extra:
            extra_str = " ".join(f"{k}={v}" for k, v in event.context.extra.items())
            text.append(f"{{{extra_str}}} ", style="dim italic")

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

        # Build context string - only include extra fields
        # Run_id is shown in run header and file logs; phase is shown in panel
        context_parts: list[str] = []
        if event.context.extra:
            extra_str = " ".join(f"{k}={v}" for k, v in event.context.extra.items())
            context_parts.append(f"{{{extra_str}}}")
        context_str = " ".join(context_parts)
        if context_str:
            context_str = f" {context_str}"

        # Format: TIMESTAMP [LEVEL] [category] {extra} message
        category = event.category.value
        line = f"{timestamp} [{level_name}] [{category}]{context_str} {event.message}"

        # Use console.print to ensure consistent output, but without markup
        self._console.print(line, markup=False, highlight=False)
