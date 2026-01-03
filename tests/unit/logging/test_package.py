"""Tests for the logging package exports and convenience functions."""

from pathlib import Path

import pytest

from adw import logging as adw_logging
from adw.logging import (
    ConsoleTransport,
    LogCategory,
    LogContext,
    LogEvent,
    LogLevel,
    LogManager,
    RawFileTransport,
    StructuredFileTransport,
    Transport,
    configure_default_logger,
    get_logger,
)


class TestPackageExports:
    """Tests for package-level exports."""

    def test_exports_log_manager(self) -> None:
        """Package exports LogManager."""
        assert LogManager is not None
        manager = LogManager()
        assert isinstance(manager, LogManager)

    def test_exports_transport_protocol(self) -> None:
        """Package exports Transport protocol."""
        assert Transport is not None

    def test_exports_console_transport(self) -> None:
        """Package exports ConsoleTransport."""
        assert ConsoleTransport is not None

    def test_exports_raw_file_transport(self) -> None:
        """Package exports RawFileTransport."""
        assert RawFileTransport is not None

    def test_exports_structured_file_transport(self) -> None:
        """Package exports StructuredFileTransport."""
        assert StructuredFileTransport is not None

    def test_exports_log_level(self) -> None:
        """Package exports LogLevel enum."""
        assert LogLevel is not None
        assert LogLevel.INFO.value == "info"

    def test_exports_log_category(self) -> None:
        """Package exports LogCategory enum."""
        assert LogCategory is not None
        assert LogCategory.PHASE.value == "phase"

    def test_exports_log_context(self) -> None:
        """Package exports LogContext."""
        assert LogContext is not None

    def test_exports_log_event(self) -> None:
        """Package exports LogEvent."""
        assert LogEvent is not None


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_log_manager(self) -> None:
        """get_logger returns a LogManager instance."""
        # Reset module state for clean test
        adw_logging._default_logger = None

        logger = get_logger()
        assert isinstance(logger, LogManager)

    def test_get_logger_returns_same_instance(self) -> None:
        """get_logger returns the same instance on repeated calls."""
        adw_logging._default_logger = None

        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2

    def test_get_logger_default_level_is_info(self) -> None:
        """get_logger default level is INFO."""
        adw_logging._default_logger = None

        logger = get_logger()
        assert logger.level == LogLevel.INFO


class TestConfigureDefaultLogger:
    """Tests for configure_default_logger function."""

    def test_configure_creates_new_logger(self) -> None:
        """configure_default_logger creates a new logger."""
        adw_logging._default_logger = None

        logger = configure_default_logger()
        assert isinstance(logger, LogManager)

    def test_configure_with_custom_level(self) -> None:
        """configure_default_logger accepts custom level."""
        adw_logging._default_logger = None

        logger = configure_default_logger(level=LogLevel.DEBUG)
        assert logger.level == LogLevel.DEBUG

    def test_configure_with_console_true(self) -> None:
        """configure_default_logger adds console transport by default."""
        adw_logging._default_logger = None

        logger = configure_default_logger(console=True)
        assert len(logger.transports) == 1
        assert isinstance(logger.transports[0], ConsoleTransport)

    def test_configure_with_console_false(self) -> None:
        """configure_default_logger can skip console transport."""
        adw_logging._default_logger = None

        logger = configure_default_logger(console=False)
        assert len(logger.transports) == 0

    def test_configure_with_raw_file(self, tmp_path: Path) -> None:
        """configure_default_logger adds raw file transport."""
        adw_logging._default_logger = None
        log_path = tmp_path / "raw.log"

        logger = configure_default_logger(
            console=False,
            raw_file=str(log_path),
        )
        assert len(logger.transports) == 1
        assert isinstance(logger.transports[0], RawFileTransport)

    def test_configure_with_jsonl_file(self, tmp_path: Path) -> None:
        """configure_default_logger adds JSONL file transport."""
        adw_logging._default_logger = None
        log_path = tmp_path / "logs.jsonl"

        logger = configure_default_logger(
            console=False,
            jsonl_file=str(log_path),
        )
        assert len(logger.transports) == 1
        assert isinstance(logger.transports[0], StructuredFileTransport)

    def test_configure_with_all_transports(self, tmp_path: Path) -> None:
        """configure_default_logger can add all transports."""
        adw_logging._default_logger = None

        logger = configure_default_logger(
            console=True,
            raw_file=str(tmp_path / "raw.log"),
            jsonl_file=str(tmp_path / "logs.jsonl"),
        )
        assert len(logger.transports) == 3

    def test_configure_replaces_previous_logger(self) -> None:
        """configure_default_logger replaces the previous default logger."""
        adw_logging._default_logger = None

        logger1 = configure_default_logger(level=LogLevel.INFO)
        logger2 = configure_default_logger(level=LogLevel.DEBUG)

        assert logger1 is not logger2
        assert get_logger() is logger2
