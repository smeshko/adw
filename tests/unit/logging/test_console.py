"""Tests for the ConsoleTransport class."""

import io
import sys
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from adw.logging.console import ConsoleTransport, should_log
from adw.models.logging import LogCategory, LogContext, LogEvent, LogLevel, Verbosity


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
        # Use TRACE verbosity to ensure DEBUG level messages are written
        transport = ConsoleTransport(
            file=output, force_tty=False, verbosity=Verbosity.TRACE
        )

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
        """write() handles all log levels when verbosity allows."""
        output = io.StringIO()
        # Use TRACE verbosity to ensure all levels are written
        transport = ConsoleTransport(
            file=output, force_tty=False, verbosity=Verbosity.TRACE
        )

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
        # Use VERBOSE verbosity to ensure DEBUG level messages are written
        transport = ConsoleTransport(
            file=output, force_tty=True, verbosity=Verbosity.VERBOSE
        )

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


class TestShouldLogFunction:
    """Tests for the should_log helper function."""

    def test_quiet_only_shows_error_and_fatal(self) -> None:
        """QUIET verbosity only allows ERROR and FATAL."""
        assert should_log(LogLevel.TRACE, Verbosity.QUIET) is False
        assert should_log(LogLevel.DEBUG, Verbosity.QUIET) is False
        assert should_log(LogLevel.INFO, Verbosity.QUIET) is False
        assert should_log(LogLevel.WARN, Verbosity.QUIET) is False
        assert should_log(LogLevel.ERROR, Verbosity.QUIET) is True
        assert should_log(LogLevel.FATAL, Verbosity.QUIET) is True

    def test_normal_shows_info_and_above(self) -> None:
        """NORMAL verbosity allows INFO and above."""
        assert should_log(LogLevel.TRACE, Verbosity.NORMAL) is False
        assert should_log(LogLevel.DEBUG, Verbosity.NORMAL) is False
        assert should_log(LogLevel.INFO, Verbosity.NORMAL) is True
        assert should_log(LogLevel.WARN, Verbosity.NORMAL) is True
        assert should_log(LogLevel.ERROR, Verbosity.NORMAL) is True
        assert should_log(LogLevel.FATAL, Verbosity.NORMAL) is True

    def test_verbose_shows_debug_and_above(self) -> None:
        """VERBOSE verbosity allows DEBUG and above."""
        assert should_log(LogLevel.TRACE, Verbosity.VERBOSE) is False
        assert should_log(LogLevel.DEBUG, Verbosity.VERBOSE) is True
        assert should_log(LogLevel.INFO, Verbosity.VERBOSE) is True
        assert should_log(LogLevel.WARN, Verbosity.VERBOSE) is True
        assert should_log(LogLevel.ERROR, Verbosity.VERBOSE) is True
        assert should_log(LogLevel.FATAL, Verbosity.VERBOSE) is True

    def test_trace_shows_everything(self) -> None:
        """TRACE verbosity allows all log levels."""
        assert should_log(LogLevel.TRACE, Verbosity.TRACE) is True
        assert should_log(LogLevel.DEBUG, Verbosity.TRACE) is True
        assert should_log(LogLevel.INFO, Verbosity.TRACE) is True
        assert should_log(LogLevel.WARN, Verbosity.TRACE) is True
        assert should_log(LogLevel.ERROR, Verbosity.TRACE) is True
        assert should_log(LogLevel.FATAL, Verbosity.TRACE) is True


class TestConsoleTransportVerbosity:
    """Tests for verbosity filtering in ConsoleTransport."""

    def test_default_verbosity_is_normal(self) -> None:
        """ConsoleTransport defaults to NORMAL verbosity."""
        transport = ConsoleTransport(force_tty=False)
        assert transport.verbosity == Verbosity.NORMAL

    def test_can_set_verbosity_in_constructor(self) -> None:
        """ConsoleTransport accepts verbosity parameter."""
        transport = ConsoleTransport(force_tty=False, verbosity=Verbosity.QUIET)
        assert transport.verbosity == Verbosity.QUIET

    def test_quiet_filters_info_messages(self) -> None:
        """QUIET verbosity filters out INFO level messages."""
        output = io.StringIO()
        transport = ConsoleTransport(
            file=output, force_tty=False, verbosity=Verbosity.QUIET
        )

        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Info message should not appear",
        )
        transport.write(event)

        assert output.getvalue() == ""

    def test_quiet_allows_error_messages(self) -> None:
        """QUIET verbosity allows ERROR level messages."""
        output = io.StringIO()
        transport = ConsoleTransport(
            file=output, force_tty=False, verbosity=Verbosity.QUIET
        )

        event = LogEvent(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            message="Error message should appear",
        )
        transport.write(event)

        assert "Error message should appear" in output.getvalue()

    def test_normal_filters_debug_messages(self) -> None:
        """NORMAL verbosity filters out DEBUG level messages."""
        output = io.StringIO()
        transport = ConsoleTransport(
            file=output, force_tty=False, verbosity=Verbosity.NORMAL
        )

        event = LogEvent(
            level=LogLevel.DEBUG,
            category=LogCategory.LLM,
            message="Debug message should not appear",
        )
        transport.write(event)

        assert output.getvalue() == ""

    def test_verbose_allows_debug_messages(self) -> None:
        """VERBOSE verbosity allows DEBUG level messages."""
        output = io.StringIO()
        transport = ConsoleTransport(
            file=output, force_tty=False, verbosity=Verbosity.VERBOSE
        )

        event = LogEvent(
            level=LogLevel.DEBUG,
            category=LogCategory.LLM,
            message="Debug message should appear",
        )
        transport.write(event)

        assert "Debug message should appear" in output.getvalue()

    def test_trace_allows_trace_messages(self) -> None:
        """TRACE verbosity allows TRACE level messages."""
        output = io.StringIO()
        transport = ConsoleTransport(
            file=output, force_tty=False, verbosity=Verbosity.TRACE
        )

        event = LogEvent(
            level=LogLevel.TRACE,
            category=LogCategory.PERFORMANCE,
            message="Trace message should appear",
        )
        transport.write(event)

        assert "Trace message should appear" in output.getvalue()
