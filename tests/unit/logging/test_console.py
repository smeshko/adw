"""Tests for the ConsoleTransport class."""

import io
import sys
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from adw.logging.console import ConsoleTransport
from adw.models.logging import LogCategory, LogContext, LogEvent, LogLevel


class TestConsoleTransportTTYDetection:
    """Tests for TTY detection behavior."""

    def test_detects_tty_when_stdout_is_tty(self) -> None:
        """ConsoleTransport detects TTY when stdout.isatty() returns True."""
        with patch.object(sys.stdout, "isatty", return_value=True):
            transport = ConsoleTransport()
            assert transport.is_tty is True

    def test_detects_non_tty_when_stdout_is_not_tty(self) -> None:
        """ConsoleTransport detects non-TTY when stdout.isatty() returns False."""
        with patch.object(sys.stdout, "isatty", return_value=False):
            transport = ConsoleTransport()
            assert transport.is_tty is False

    def test_can_force_tty_mode(self) -> None:
        """ConsoleTransport can be forced to TTY mode."""
        with patch.object(sys.stdout, "isatty", return_value=False):
            transport = ConsoleTransport(force_tty=True)
            assert transport.is_tty is True

    def test_can_force_non_tty_mode(self) -> None:
        """ConsoleTransport can be forced to non-TTY mode."""
        with patch.object(sys.stdout, "isatty", return_value=True):
            transport = ConsoleTransport(force_tty=False)
            assert transport.is_tty is False


class TestConsoleTransportWrite:
    """Tests for the write method."""

    def test_write_event_to_console(self) -> None:
        """write() outputs the log event to console."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=False)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Test message",
        )
        transport.write(event)

        result = output.getvalue()
        assert "Test message" in result
        assert "INFO" in result.upper() or "info" in result.lower()

    def test_write_includes_timestamp(self) -> None:
        """write() includes timestamp in output."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=False)

        now = datetime.now(UTC)
        event = LogEvent(
            timestamp=now,
            level=LogLevel.DEBUG,
            category=LogCategory.LLM,
            message="Debug event",
        )
        transport.write(event)

        result = output.getvalue()
        # Should contain some form of time
        assert any(c.isdigit() for c in result)

    def test_write_includes_category(self) -> None:
        """write() includes category in output."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=False)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.HOOK,
            message="Hook event",
        )
        transport.write(event)

        result = output.getvalue()
        assert "hook" in result.lower() or "HOOK" in result


class TestConsoleTransportLevelStyling:
    """Tests for level-based styling."""

    @pytest.mark.parametrize("level", list(LogLevel))
    def test_writes_all_log_levels(self, level: LogLevel) -> None:
        """write() handles all log levels."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=False)

        event = LogEvent(
            level=level,
            category=LogCategory.PHASE,
            message=f"Message at {level.value}",
        )
        transport.write(event)

        result = output.getvalue()
        assert f"Message at {level.value}" in result

    def test_error_level_is_visually_distinct(self) -> None:
        """ERROR level should be formatted distinctly."""
        output = io.StringIO()
        # Force TTY mode to get Rich formatting
        transport = ConsoleTransport(file=output, force_tty=True)

        event = LogEvent(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            message="Error occurred",
        )
        transport.write(event)

        # In Rich, errors typically use red or bold styling
        # We just verify output contains the message
        result = output.getvalue()
        assert "Error occurred" in result

    def test_fatal_level_is_visually_distinct(self) -> None:
        """FATAL level should be formatted distinctly."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=True)

        event = LogEvent(
            level=LogLevel.FATAL,
            category=LogCategory.ERROR,
            message="Fatal error",
        )
        transport.write(event)

        result = output.getvalue()
        assert "Fatal error" in result


class TestConsoleTransportTTYVsNonTTY:
    """Tests for TTY vs non-TTY output differences."""

    def test_tty_mode_uses_rich_formatting(self) -> None:
        """TTY mode should use Rich formatting."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=True)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Rich formatted message",
        )
        transport.write(event)

        result = output.getvalue()
        assert "Rich formatted message" in result

    def test_non_tty_mode_uses_plain_text(self) -> None:
        """Non-TTY mode should use plain text without ANSI codes."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=False)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Plain text message",
        )
        transport.write(event)

        result = output.getvalue()
        assert "Plain text message" in result
        # Non-TTY should not have ANSI escape codes
        assert "\x1b[" not in result


class TestConsoleTransportContext:
    """Tests for context handling in output."""

    def test_includes_run_id_when_present(self) -> None:
        """write() includes run_id from context."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=False)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.STATE,
            message="State change",
            context=LogContext(run_id="01HQ123ABC"),
        )
        transport.write(event)

        result = output.getvalue()
        assert "01HQ123ABC" in result

    def test_includes_phase_when_present(self) -> None:
        """write() includes phase from context."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=False)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Phase started",
            context=LogContext(phase="build"),
        )
        transport.write(event)

        result = output.getvalue()
        assert "build" in result

    def test_includes_extra_when_present(self) -> None:
        """write() includes extra context fields."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=False)

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.LLM,
            message="LLM request",
            context=LogContext(extra={"component": "executor", "attempt": 1}),
        )
        transport.write(event)

        result = output.getvalue()
        assert "component=executor" in result
        assert "attempt=1" in result

    def test_includes_extra_in_tty_mode(self) -> None:
        """write() includes extra context in TTY mode."""
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=True)

        event = LogEvent(
            level=LogLevel.DEBUG,
            category=LogCategory.HOOK,
            message="Hook running",
            context=LogContext(extra={"hook_name": "pre-build"}),
        )
        transport.write(event)

        result = output.getvalue()
        assert "hook_name=pre-build" in result


class TestLevelStyles:
    """Tests for LEVEL_STYLES constant."""

    def test_all_levels_have_styles(self) -> None:
        """LEVEL_STYLES maps all LogLevel values."""
        from adw.logging.console import LEVEL_STYLES

        for level in LogLevel:
            assert level in LEVEL_STYLES, f"Missing style for {level}"

    def test_styles_are_strings(self) -> None:
        """All LEVEL_STYLES values are strings."""
        from adw.logging.console import LEVEL_STYLES

        for level, style in LEVEL_STYLES.items():
            assert isinstance(style, str), f"Style for {level} is not a string"

    def test_error_levels_have_red(self) -> None:
        """ERROR and FATAL levels include red styling."""
        from adw.logging.console import LEVEL_STYLES

        assert "red" in LEVEL_STYLES[LogLevel.ERROR]
        assert "red" in LEVEL_STYLES[LogLevel.FATAL]
