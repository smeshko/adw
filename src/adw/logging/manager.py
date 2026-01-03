"""Log manager for multi-tier logging.

This module provides the central LogManager class that coordinates
logging across all transports (console, file, JSONL).
"""

from typing import Any, Protocol, runtime_checkable

from adw.models.logging import LogCategory, LogContext, LogEvent, LogLevel


# Level ordering for filtering
LEVEL_ORDER: dict[LogLevel, int] = {
    LogLevel.TRACE: 0,
    LogLevel.DEBUG: 1,
    LogLevel.INFO: 2,
    LogLevel.WARN: 3,
    LogLevel.ERROR: 4,
    LogLevel.FATAL: 5,
}


@runtime_checkable
class Transport(Protocol):
    """Protocol for log transports.

    Any class implementing a write(event: LogEvent) method
    can be used as a transport.
    """

    def write(self, event: LogEvent) -> None:
        """Write a log event to the transport."""
        ...


class LogManager:
    """Central manager for multi-tier logging.

    LogManager coordinates logging across multiple transports,
    handles level filtering, and supports scoped child loggers.

    Attributes:
        level: Minimum log level to process
        transports: Registered transport instances

    Example:
        >>> manager = LogManager(level=LogLevel.INFO)
        >>> manager.register(ConsoleTransport())
        >>> manager.register(StructuredFileTransport(Path("logs.jsonl")))
        >>> manager.info(LogCategory.PHASE, "Phase started")
        >>>
        >>> # Create child logger with context
        >>> child = manager.child(run_id="01HQ123ABC", phase="build")
        >>> child.debug(LogCategory.LLM, "LLM request sent")
    """

    def __init__(
        self,
        *,
        level: LogLevel = LogLevel.INFO,
        context: LogContext | None = None,
        transports: list[Transport] | None = None,
    ) -> None:
        """Initialize the log manager.

        Args:
            level: Minimum log level to process (default: INFO)
            context: Initial context for all events
            transports: Initial transports to register
        """
        self._level = level
        self._context = context or LogContext()
        self._transports: list[Transport] = list(transports) if transports else []

    @property
    def level(self) -> LogLevel:
        """Get the current log level."""
        return self._level

    @property
    def transports(self) -> list[Transport]:
        """Get the registered transports."""
        return self._transports

    def set_level(self, level: LogLevel) -> None:
        """Set the log level.

        Args:
            level: New minimum log level
        """
        self._level = level

    def register(self, transport: Transport) -> None:
        """Register a transport.

        Args:
            transport: Transport to register
        """
        self._transports.append(transport)

    def child(
        self,
        *,
        run_id: str | None = None,
        phase: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> "LogManager":
        """Create a child logger with extended context.

        Child loggers inherit the parent's transports and level,
        but can add additional context that is included in all events.

        Args:
            run_id: Run ID to add to context
            phase: Phase name to add to context
            extra: Additional context fields

        Returns:
            New LogManager with merged context
        """
        new_context = self._context.merge(
            run_id=run_id,
            phase=phase,
            extra=extra,
        )
        return LogManager(
            level=self._level,
            context=new_context,
            transports=self._transports,
        )

    def _should_log(self, level: LogLevel) -> bool:
        """Check if an event at the given level should be logged.

        Args:
            level: Log level to check

        Returns:
            True if the level is at or above the configured level
        """
        return LEVEL_ORDER[level] >= LEVEL_ORDER[self._level]

    def _log(self, level: LogLevel, category: LogCategory, message: str) -> None:
        """Log an event at the specified level.

        Args:
            level: Log level
            category: Log category
            message: Log message
        """
        if not self._should_log(level):
            return

        event = LogEvent(
            level=level,
            category=category,
            message=message,
            context=self._context,
        )

        for transport in self._transports:
            transport.write(event)

    def trace(self, category: LogCategory, message: str) -> None:
        """Log at TRACE level.

        Args:
            category: Log category
            message: Log message
        """
        self._log(LogLevel.TRACE, category, message)

    def debug(self, category: LogCategory, message: str) -> None:
        """Log at DEBUG level.

        Args:
            category: Log category
            message: Log message
        """
        self._log(LogLevel.DEBUG, category, message)

    def info(self, category: LogCategory, message: str) -> None:
        """Log at INFO level.

        Args:
            category: Log category
            message: Log message
        """
        self._log(LogLevel.INFO, category, message)

    def warn(self, category: LogCategory, message: str) -> None:
        """Log at WARN level.

        Args:
            category: Log category
            message: Log message
        """
        self._log(LogLevel.WARN, category, message)

    def error(self, category: LogCategory, message: str) -> None:
        """Log at ERROR level.

        Args:
            category: Log category
            message: Log message
        """
        self._log(LogLevel.ERROR, category, message)

    def fatal(self, category: LogCategory, message: str) -> None:
        """Log at FATAL level.

        Args:
            category: Log category
            message: Log message
        """
        self._log(LogLevel.FATAL, category, message)
