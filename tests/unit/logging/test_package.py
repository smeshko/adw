# REDUCED: Removed TestPackageExports (import verification) and test_reset_logger_exported.
# Kept only tests that verify actual logging behavior.
"""Tests for the logging package convenience functions."""

from pathlib import Path

from adw.logging import (
    ConsoleTransport,
    LogLevel,
    LogManager,
    RawFileTransport,
    StructuredFileTransport,
    configure_default_logger,
    get_logger,
    reset_logger,
)


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_log_manager(self) -> None:
        """get_logger returns a LogManager instance."""
        reset_logger()

        logger = get_logger()
        assert isinstance(logger, LogManager)

    def test_get_logger_returns_same_instance(self) -> None:
        """get_logger returns the same instance on repeated calls."""
        reset_logger()

        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2


class TestConfigureDefaultLogger:
    """Tests for configure_default_logger function."""

    def test_configure_with_custom_level(self) -> None:
        """configure_default_logger accepts custom level."""
        reset_logger()

        logger = configure_default_logger(level=LogLevel.DEBUG)
        assert logger.level == LogLevel.DEBUG

    def test_configure_with_console_true(self) -> None:
        """configure_default_logger adds console transport by default."""
        reset_logger()

        logger = configure_default_logger(console=True)
        assert len(logger.transports) == 1
        assert isinstance(logger.transports[0], ConsoleTransport)

    def test_configure_with_console_false(self) -> None:
        """configure_default_logger can skip console transport."""
        reset_logger()

        logger = configure_default_logger(console=False)
        assert len(logger.transports) == 0

    def test_configure_with_raw_file(self, tmp_path: Path) -> None:
        """configure_default_logger adds raw file transport."""
        reset_logger()
        log_path = tmp_path / "raw.log"

        logger = configure_default_logger(
            console=False,
            raw_file=str(log_path),
        )
        assert len(logger.transports) == 1
        assert isinstance(logger.transports[0], RawFileTransport)

    def test_configure_with_jsonl_file(self, tmp_path: Path) -> None:
        """configure_default_logger adds JSONL file transport."""
        reset_logger()
        log_path = tmp_path / "logs.jsonl"

        logger = configure_default_logger(
            console=False,
            jsonl_file=str(log_path),
        )
        assert len(logger.transports) == 1
        assert isinstance(logger.transports[0], StructuredFileTransport)

    def test_configure_with_all_transports(self, tmp_path: Path) -> None:
        """configure_default_logger can add all transports."""
        reset_logger()

        logger = configure_default_logger(
            console=True,
            raw_file=str(tmp_path / "raw.log"),
            jsonl_file=str(tmp_path / "logs.jsonl"),
        )
        assert len(logger.transports) == 3

    def test_configure_replaces_previous_logger(self) -> None:
        """configure_default_logger replaces the previous default logger."""
        reset_logger()

        logger1 = configure_default_logger(level=LogLevel.INFO)
        logger2 = configure_default_logger(level=LogLevel.DEBUG)

        assert logger1 is not logger2
        assert get_logger() is logger2


class TestResetLogger:
    """Tests for reset_logger function."""

    def test_reset_logger_clears_default(self) -> None:
        """reset_logger clears the default logger."""
        reset_logger()
        logger1 = get_logger()

        reset_logger()
        logger2 = get_logger()

        assert logger1 is not logger2
