"""ADW logging module - multi-tier structured logging.

This package provides a comprehensive logging system with:
- Console output via Rich
- Real-time streaming via LiveStreamTransport to live.log
- TTY-aware console formatting (colors for terminals, plain text otherwise)
- Scoped child loggers with context inheritance
- Level-based filtering (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
- Category-based organization (PHASE, LLM, HOOK, STATE, ERROR, PERFORMANCE)
- File locking for concurrent write safety
"""

import logging

from adw.logging.handler import LogManagerHandler
from adw.logging.manager import LogManager
from adw.logging.redactor import Redactor, configure_redactor


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


__all__ = [
    "LogManager",
    "LogManagerHandler",
    "create_redactor_from_config",
]
