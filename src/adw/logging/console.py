"""Console output for ADW's log records.

ConsoleHandler prints the ``adw`` logger's records on a Rich console. While a
spinner is running (registered by ProgressDisplay through set_active_live),
the handler stops it before printing, so a log line never runs into it.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text

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


# Tag and Rich style per stdlib level. WARN/FATAL match the tags live.log has
# always used, which the dashboard and `adw logs follow` key on.
_LEVEL_STYLES: dict[int, tuple[str, str]] = {
    logging.DEBUG: ("DEBUG", "dim cyan"),
    logging.INFO: ("INFO", "green"),
    logging.WARNING: ("WARN", "yellow"),
    logging.ERROR: ("ERROR", "bold red"),
    logging.CRITICAL: ("FATAL", "bold white on red"),
}


class ConsoleHandler(logging.Handler):
    """Print log records on a Rich console as ``HH:MM:SS [LEVEL] message``.

    Times are UTC. When a spinner is active, it is stopped first so the line
    doesn't run into it (e.g. "⠧ LLM executing...14:36:35 [WARN]"); the next
    progress update restarts it.
    """

    def __init__(self, console: Console) -> None:
        """Initialize the handler.

        Args:
            console: The Rich console to print on
        """
        super().__init__()
        self.console = console

    def emit(self, record: logging.LogRecord) -> None:
        """Print one record, stopping any active spinner first.

        Args:
            record: The record to print
        """
        try:
            live = get_active_live()
            if live is not None:
                live.stop()
                set_active_live(None)

            tag, style = _LEVEL_STYLES.get(record.levelno, (record.levelname, ""))
            stamp = datetime.fromtimestamp(record.created, UTC).strftime("%H:%M:%S")
            text = Text()
            text.append(f"{stamp} ", style="dim")
            text.append(f"[{tag}] ", style=style)
            text.append(
                self.format(record),
                style=style if record.levelno >= logging.ERROR else "",
            )
            self.console.print(text)
        except Exception:
            self.handleError(record)
