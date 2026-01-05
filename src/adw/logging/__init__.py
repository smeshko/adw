"""ADW logging module - multi-tier structured logging.

This package provides a comprehensive logging system with:
- Multi-tier output: console (Rich), raw text files, structured JSONL
- TTY-aware console formatting (colors for terminals, plain text otherwise)
- Scoped child loggers with context inheritance
- Level-based filtering (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
- Category-based organization (PHASE, LLM, HOOK, STATE, ERROR, PERFORMANCE)
- File locking for concurrent write safety

Quick Start:
    >>> from adw.logging import get_logger, LogCategory
    >>> logger = get_logger()
    >>> logger.info(LogCategory.PHASE, "Phase started")

For run-scoped logging:
    >>> from adw.logging import get_logger, LogCategory
    >>> logger = get_logger()
    >>> run_logger = logger.child(run_id="01HQ123ABC", phase="build")
    >>> run_logger.debug(LogCategory.LLM, "Sending request")
"""

import logging

from adw.logging.console import ConsoleTransport
from adw.logging.file import RawFileTransport, StructuredFileTransport
from adw.logging.handler import LogManagerHandler
from adw.logging.llm_capture import LLMCaptureManager
from adw.logging.manager import LogManager, Transport
from adw.logging.redactor import (
    DEFAULT_REDACTION_PATTERNS,
    REDACTED_PLACEHOLDER,
    SENSITIVE_ENV_PATTERNS,
    Redactor,
    configure_redactor,
    get_redactor,
    reset_redactor,
)
from adw.logging.stream import StreamLogger
from adw.models.logging import LogCategory, LogContext, LogEvent, LogLevel

# Module-level default logger instance
_default_logger: LogManager | None = None


def get_logger() -> LogManager:
    """Get the default logger instance.

    Returns a module-level LogManager instance, creating it on first call.
    The default logger has no transports registered; use register() to add.

    Returns:
        The default LogManager instance

    Example:
        >>> logger = get_logger()
        >>> logger.register(ConsoleTransport())
        >>> logger.info(LogCategory.PHASE, "Application started")
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = LogManager()
    return _default_logger


def reset_logger() -> None:
    """Reset the default logger instance.

    Clears the module-level default logger, allowing a fresh instance
    to be created on the next get_logger() call. Useful for testing.
    """
    global _default_logger
    _default_logger = None


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


def configure_default_logger(
    *,
    level: LogLevel = LogLevel.INFO,
    console: bool = True,
    raw_file: str | None = None,
    jsonl_file: str | None = None,
    redaction_enabled: bool = True,
    redaction_patterns: list[str] | None = None,
    redaction_disable_defaults: bool = False,
) -> LogManager:
    """Configure and return the default logger with common transports.

    This is a convenience function for quick setup. Creates a new default
    logger with the specified transports and redaction settings.

    Args:
        level: Minimum log level (default: INFO)
        console: Whether to add console transport (default: True)
        raw_file: Path to raw log file (optional)
        jsonl_file: Path to JSONL log file (optional)
        redaction_enabled: Whether to enable secret redaction (default: True)
        redaction_patterns: Additional custom patterns for redaction
        redaction_disable_defaults: If True, only use custom patterns

    Returns:
        The configured default LogManager instance

    Example:
        >>> logger = configure_default_logger(
        ...     level=LogLevel.DEBUG,
        ...     raw_file=".agent/runs/123/logs/raw.log",
        ...     jsonl_file=".agent/runs/123/logs/logs.jsonl",
        ...     redaction_enabled=True,
        ...     redaction_patterns=["ACME_[A-Z0-9]+"],
        ... )
    """
    global _default_logger
    from pathlib import Path

    # Create redactor based on configuration
    redactor = create_redactor_from_config(
        enabled=redaction_enabled,
        patterns=redaction_patterns,
        disable_defaults=redaction_disable_defaults,
    )

    _default_logger = LogManager(level=level, redactor=redactor)

    if console:
        _default_logger.register(ConsoleTransport())

    if raw_file:
        _default_logger.register(RawFileTransport(Path(raw_file)))

    if jsonl_file:
        _default_logger.register(StructuredFileTransport(Path(jsonl_file)))

    return _default_logger


__all__ = [
    # Core classes
    "LogManager",
    "LogManagerHandler",
    "Transport",
    "StreamLogger",
    "LLMCaptureManager",
    # Transports
    "ConsoleTransport",
    "RawFileTransport",
    "StructuredFileTransport",
    # Redaction
    "Redactor",
    "DEFAULT_REDACTION_PATTERNS",
    "SENSITIVE_ENV_PATTERNS",
    "REDACTED_PLACEHOLDER",
    "get_redactor",
    "configure_redactor",
    "reset_redactor",
    # Models (re-exported for convenience)
    "LogCategory",
    "LogContext",
    "LogEvent",
    "LogLevel",
    # Functions
    "get_logger",
    "configure_default_logger",
    "create_redactor_from_config",
    "reset_logger",
]
