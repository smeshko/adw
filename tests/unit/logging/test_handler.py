"""Tests for LogManagerHandler that bridges Python logging to ADW LogManager."""

import logging

import pytest

from adw.logging.handler import LogManagerHandler
from adw.logging.manager import LogManager
from adw.models.logging import LogCategory, LogContext, LogEvent, LogLevel


class MockTransport:
    """Mock transport that captures written events for testing."""

    def __init__(self) -> None:
        self.events: list[LogEvent] = []

    def write(self, event: LogEvent) -> None:
        self.events.append(event)


class TestLogManagerHandler:
    """Tests for LogManagerHandler."""

    def test_handler_bridges_python_logging_to_log_manager(self) -> None:
        """Verify Python logging calls flow through to LogManager transports."""
        # Arrange
        transport = MockTransport()
        log_manager = LogManager(level=LogLevel.DEBUG)
        log_manager.register(transport)

        handler = LogManagerHandler(log_manager)
        logger = logging.getLogger("test.bridge")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Act
        logger.info("Test message from Python logging")

        # Assert
        assert len(transport.events) == 1
        event = transport.events[0]
        assert event.message == "Test message from Python logging"
        assert event.level == LogLevel.INFO

        # Cleanup
        logger.removeHandler(handler)

    @pytest.mark.parametrize(
        "python_level,expected_adw_level",
        [
            (logging.DEBUG, LogLevel.DEBUG),
            (logging.INFO, LogLevel.INFO),
            (logging.WARNING, LogLevel.WARN),
            (logging.ERROR, LogLevel.ERROR),
            (logging.CRITICAL, LogLevel.FATAL),
        ],
    )
    def test_level_mapping(
        self, python_level: int, expected_adw_level: LogLevel
    ) -> None:
        """Verify Python log levels map correctly to ADW levels."""
        # Arrange
        transport = MockTransport()
        log_manager = LogManager(level=LogLevel.TRACE)
        log_manager.register(transport)

        handler = LogManagerHandler(log_manager)
        logger = logging.getLogger(f"test.levels.{python_level}")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Act
        logger.log(python_level, "Test message")

        # Assert
        assert len(transport.events) == 1
        assert transport.events[0].level == expected_adw_level

        # Cleanup
        logger.removeHandler(handler)

    @pytest.mark.parametrize(
        "logger_name,expected_category",
        [
            ("adw.core.phase_runner", LogCategory.PHASE),
            ("adw.core.orchestrator", LogCategory.PHASE),
            ("adw.executors.claude_code", LogCategory.LLM),
            ("adw.hooks.shell", LogCategory.HOOK),
            ("adw.state.manager", LogCategory.STATE),
            ("adw.some.other.module", LogCategory.PHASE),  # Default for adw modules
            ("some.external.library", LogCategory.PHASE),  # Default fallback
        ],
    )
    def test_category_inference_from_logger_name(
        self, logger_name: str, expected_category: LogCategory
    ) -> None:
        """Verify logger names map to appropriate ADW categories."""
        # Arrange
        transport = MockTransport()
        log_manager = LogManager(level=LogLevel.DEBUG)
        log_manager.register(transport)

        handler = LogManagerHandler(log_manager)
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Act
        logger.info("Test message")

        # Assert
        assert len(transport.events) == 1
        assert transport.events[0].category == expected_category

        # Cleanup
        logger.removeHandler(handler)

    def test_handler_preserves_context_from_log_manager(self) -> None:
        """Verify context from LogManager is included in events."""
        # Arrange
        transport = MockTransport()
        context = LogContext(run_id="01TEST123", phase="build")
        log_manager = LogManager(level=LogLevel.DEBUG, context=context)
        log_manager.register(transport)

        handler = LogManagerHandler(log_manager)
        logger = logging.getLogger("test.context")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Act
        logger.info("Test with context")

        # Assert
        assert len(transport.events) == 1
        event = transport.events[0]
        assert event.context.run_id == "01TEST123"
        assert event.context.phase == "build"

        # Cleanup
        logger.removeHandler(handler)

    def test_handler_respects_log_manager_level(self) -> None:
        """Verify handler respects LogManager's level filtering."""
        # Arrange
        transport = MockTransport()
        log_manager = LogManager(level=LogLevel.WARN)  # Only WARN and above
        log_manager.register(transport)

        handler = LogManagerHandler(log_manager)
        logger = logging.getLogger("test.filtering")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Act
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Assert - only WARN and ERROR should be written
        assert len(transport.events) == 2
        assert transport.events[0].level == LogLevel.WARN
        assert transport.events[1].level == LogLevel.ERROR

        # Cleanup
        logger.removeHandler(handler)

    def test_handler_formats_exception_info(self) -> None:
        """Verify exception info is included in log message."""
        # Arrange
        transport = MockTransport()
        log_manager = LogManager(level=LogLevel.DEBUG)
        log_manager.register(transport)

        handler = LogManagerHandler(log_manager)
        logger = logging.getLogger("test.exception")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Act
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("An error occurred")

        # Assert
        assert len(transport.events) == 1
        event = transport.events[0]
        assert "An error occurred" in event.message
        assert "ValueError: Test error" in event.message
        assert "Traceback" in event.message

        # Cleanup
        logger.removeHandler(handler)
