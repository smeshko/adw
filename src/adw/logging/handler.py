"""Python logging handler bridge to ADW LogManager.

This module provides LogManagerHandler, a standard Python logging.Handler
that bridges Python's logging module to ADW's LogManager. This enables
existing code using Python's logging to automatically write to ADW's
structured log files (logs.jsonl).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from adw.models.logging import LogCategory, LogLevel

if TYPE_CHECKING:
    from adw.logging.manager import LogManager


class LogManagerHandler(logging.Handler):
    """Bridge Python's logging module to ADW's LogManager.

    This handler translates Python LogRecords to ADW LogEvents,
    enabling seamless integration between standard Python logging
    and ADW's multi-tier logging system.

    The handler:
    - Maps Python log levels to ADW LogLevels
    - Infers LogCategory from Python logger names
    - Preserves LogManager context in all events
    - Respects LogManager's level filtering

    Example:
        >>> from adw.logging.manager import LogManager
        >>> from adw.logging.handler import LogManagerHandler
        >>>
        >>> log_manager = LogManager(level=LogLevel.DEBUG)
        >>> log_manager.register(StructuredFileTransport(path))
        >>>
        >>> handler = LogManagerHandler(log_manager)
        >>> logging.getLogger().addHandler(handler)
        >>>
        >>> # Now Python logging writes to ADW's file transports
        >>> logger = logging.getLogger("mymodule")
        >>> logger.info("This goes to logs.jsonl")
    """

    def __init__(self, log_manager: LogManager) -> None:
        """Initialize the handler with a LogManager.

        Args:
            log_manager: The LogManager to bridge logs to
        """
        super().__init__()
        self._log_manager = log_manager

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the LogManager.

        Translates the Python LogRecord to ADW's logging format
        and sends it through the LogManager to all registered transports.

        Args:
            record: The Python LogRecord to emit
        """
        try:
            level = self._map_level(record.levelno)
            category = self._infer_category(record.name)
            message = self.format(record)
            self._log_manager._log(level, category, message)
        except Exception:
            # Prevent logging errors from crashing the application
            self.handleError(record)

    def _map_level(self, levelno: int) -> LogLevel:
        """Map Python log level number to ADW LogLevel.

        Args:
            levelno: Python logging level number (e.g., logging.INFO = 20)

        Returns:
            Corresponding ADW LogLevel
        """
        if levelno <= logging.DEBUG:
            return LogLevel.DEBUG
        elif levelno <= logging.INFO:
            return LogLevel.INFO
        elif levelno <= logging.WARNING:
            return LogLevel.WARN
        elif levelno <= logging.ERROR:
            return LogLevel.ERROR
        return LogLevel.FATAL

    def _infer_category(self, name: str) -> LogCategory:
        """Infer ADW LogCategory from Python logger name.

        Uses heuristics based on module naming conventions to categorize logs:
        - Modules containing 'executor' or 'llm' -> LLM
        - Modules containing 'hook' -> HOOK
        - Modules containing 'state' -> STATE
        - Everything else -> PHASE (default for orchestration)

        Args:
            name: Python logger name (typically __name__)

        Returns:
            Inferred LogCategory
        """
        name_lower = name.lower()

        if "executor" in name_lower or "llm" in name_lower:
            return LogCategory.LLM
        elif "hook" in name_lower:
            return LogCategory.HOOK
        elif "state" in name_lower:
            return LogCategory.STATE
        else:
            # Default to PHASE for orchestration-related logs
            return LogCategory.PHASE
