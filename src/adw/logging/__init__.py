"""ADW logging: stdlib logging with one redaction filter.

ADW modules log through ``logging.getLogger(__name__)``, under the ``adw``
logger. ``setup_logging`` attaches the handlers:
- a Rich console handler, at the level the CLI verbosity picks
- during a run, one live.log handler, which the executor also writes the LLM
  stream through
Both carry the same RedactingFilter, built from project.yaml's
logging.redaction section.
"""

import logging
from pathlib import Path

from rich.console import Console

from adw.core.constants import LIVE_LOG
from adw.logging.console import ConsoleHandler
from adw.logging.handler import LogManagerHandler
from adw.logging.live_stream import LiveStreamHandler
from adw.logging.manager import LogManager
from adw.logging.redactor import RedactingFilter, Redactor, configure_redactor
from adw.models.config import RedactionConfig
from adw.models.logging import Verbosity

# Console level per CLI verbosity. stdlib has no TRACE level, so --trace
# shows the same as -v.
_CONSOLE_LEVELS: dict[Verbosity, int] = {
    Verbosity.QUIET: logging.ERROR,
    Verbosity.NORMAL: logging.INFO,
    Verbosity.VERBOSE: logging.DEBUG,
    Verbosity.TRACE: logging.DEBUG,
}


def create_redactor_from_config(
    *,
    enabled: bool = True,
    patterns: list[str] | None = None,
    disable_defaults: bool = False,
) -> Redactor | None:
    """Create a redactor from configuration options.

    This function builds a Redactor based on the configuration settings
    from project.yaml's logging.redaction section.

    Args:
        enabled: Whether redaction is active (default: True)
        patterns: Additional custom patterns to add
        disable_defaults: If True, only use custom patterns

    Returns:
        Configured Redactor instance, or None if disabled

    Example:
        >>> redactor = create_redactor_from_config(
        ...     patterns=["ACME_[A-Z0-9]+"],
        ...     disable_defaults=False,
        ... )
    """
    if not enabled:
        logging.getLogger(__name__).warning(
            "Secret redaction is DISABLED - sensitive data may appear in logs"
        )
        return None

    return configure_redactor(
        patterns=patterns,
        disable_defaults=disable_defaults,
    )


def setup_logging(
    verbosity: Verbosity,
    run_dir: Path | None = None,
    *,
    console: Console | None = None,
    redaction: RedactionConfig | None = None,
) -> LiveStreamHandler | None:
    """Attach ADW's console and live.log handlers to the ``adw`` logger.

    Each call first removes and closes the handlers already on the logger, so
    calling it again (console-only first, then with the run directory) swaps
    them rather than stacking them. The console shows ERROR at QUIET, INFO at
    NORMAL and DEBUG at VERBOSE/TRACE. live.log records INFO, or DEBUG at
    VERBOSE/TRACE; QUIET quiets the console only.

    Args:
        verbosity: CLI verbosity
        run_dir: The run's directory. When given, a live.log handler is
            attached; the file is created on its first line.
        console: Rich console to print on (a new one when omitted)
        redaction: project.yaml's logging.redaction (defaults when omitted)

    Returns:
        The live.log handler, for the executor's LLM stream, or None
        without a run directory.
    """
    logger = logging.getLogger("adw")
    for old in logger.handlers[:]:
        logger.removeHandler(old)
        old.close()

    console_handler = ConsoleHandler(console or Console())
    console_handler.setLevel(_CONSOLE_LEVELS[verbosity])
    handlers: list[logging.Handler] = [console_handler]

    live_handler: LiveStreamHandler | None = None
    if run_dir is not None:
        live_handler = LiveStreamHandler(run_dir / LIVE_LOG)
        verbose = verbosity in (Verbosity.VERBOSE, Verbosity.TRACE)
        live_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        handlers.append(live_handler)

    for handler in handlers:
        logger.addHandler(handler)
    logger.setLevel(min(handler.level for handler in handlers))

    # After the handlers are attached, so a "DISABLED" warning reaches them
    redaction = redaction or RedactionConfig()
    redactor = create_redactor_from_config(
        enabled=redaction.enabled,
        patterns=redaction.patterns or None,
        disable_defaults=redaction.disable_defaults,
    )
    if redactor is not None:
        for handler in handlers:
            handler.addFilter(RedactingFilter(redactor))

    return live_handler


__all__ = [
    "LogManager",
    "LogManagerHandler",
    "create_redactor_from_config",
    "setup_logging",
]
