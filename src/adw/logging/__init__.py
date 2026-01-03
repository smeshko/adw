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

from adw.logging.console import ConsoleTransport
from adw.logging.file import RawFileTransport, StructuredFileTransport
from adw.logging.llm_capture import LLMCaptureManager
from adw.logging.manager import LogManager, Transport
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


def configure_default_logger(
    *,
    level: LogLevel = LogLevel.INFO,
    console: bool = True,
    raw_file: str | None = None,
    jsonl_file: str | None = None,
) -> LogManager:
    """Configure and return the default logger with common transports.

    This is a convenience function for quick setup. Creates a new default
    logger with the specified transports.

    Args:
        level: Minimum log level (default: INFO)
        console: Whether to add console transport (default: True)
        raw_file: Path to raw log file (optional)
        jsonl_file: Path to JSONL log file (optional)

    Returns:
        The configured default LogManager instance

    Example:
        >>> logger = configure_default_logger(
        ...     level=LogLevel.DEBUG,
        ...     raw_file=".agent/runs/123/logs/raw.log",
        ...     jsonl_file=".agent/runs/123/logs/logs.jsonl",
        ... )
    """
    global _default_logger
    from pathlib import Path

    _default_logger = LogManager(level=level)

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
    "Transport",
    "StreamLogger",
    "LLMCaptureManager",
    # Transports
    "ConsoleTransport",
    "RawFileTransport",
    "StructuredFileTransport",
    # Models (re-exported for convenience)
    "LogCategory",
    "LogContext",
    "LogEvent",
    "LogLevel",
    # Functions
    "get_logger",
    "configure_default_logger",
    "reset_logger",
]
