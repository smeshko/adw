"""Tests for the LogManager class."""

import io
from pathlib import Path
from unittest.mock import MagicMock

from adw.logging.console import ConsoleTransport
from adw.logging.file import RawFileTransport, StructuredFileTransport
from adw.logging.manager import LogManager
from adw.models.logging import LogCategory, LogEvent, LogLevel, Verbosity


class TestLogManagerCreation:
    """Tests for LogManager instantiation."""

    def test_create_log_manager(self) -> None:
        """LogManager can be created."""
        manager = LogManager()
        assert manager is not None

    def test_log_manager_default_level(self) -> None:
        """LogManager defaults to INFO level."""
        manager = LogManager()
        assert manager.level == LogLevel.INFO

    def test_log_manager_custom_level(self) -> None:
        """LogManager can be created with custom level."""
        manager = LogManager(level=LogLevel.DEBUG)
        assert manager.level == LogLevel.DEBUG


class TestTransportRegistration:
    """Tests for transport registration."""

    def test_register_console_transport(self) -> None:
        """LogManager can register ConsoleTransport."""
        manager = LogManager()
        output = io.StringIO()
        transport = ConsoleTransport(file=output, force_tty=False)

        manager.register(transport)

        assert len(manager.transports) == 1

    def test_register_multiple_transports(self, tmp_path: Path) -> None:
        """LogManager can register multiple transports."""
        manager = LogManager()
        output = io.StringIO()
        console = ConsoleTransport(file=output, force_tty=False)
        raw_file = RawFileTransport(tmp_path / "raw.log")
        jsonl_file = StructuredFileTransport(tmp_path / "logs.jsonl")

        manager.register(console)
        manager.register(raw_file)
        manager.register(jsonl_file)

        assert len(manager.transports) == 3

    def test_register_custom_transport(self) -> None:
        """LogManager can register custom transports implementing Transport protocol."""
        manager = LogManager()

        class CustomTransport:
            def write(self, event: LogEvent) -> None:
                pass

        transport = CustomTransport()
        manager.register(transport)

        assert len(manager.transports) == 1

    def test_transports_returns_copy(self) -> None:
        """transports property returns a copy, not the internal list."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        # Get the transports list
        transports1 = manager.transports
        transports2 = manager.transports

        # Should be different list objects
        assert transports1 is not transports2

        # Mutating the returned list should not affect internal state
        transports1.clear()
        assert len(manager.transports) == 1


class TestLogLevelMethods:
    """Tests for level-specific logging methods."""

    def test_trace_method(self) -> None:
        """LogManager has trace() method."""
        manager = LogManager(level=LogLevel.TRACE)
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.trace(LogCategory.PHASE, "Trace message")

        mock_transport.write.assert_called_once()
        event = mock_transport.write.call_args[0][0]
        assert event.level == LogLevel.TRACE
        assert event.message == "Trace message"

    def test_debug_method(self) -> None:
        """LogManager has debug() method."""
        manager = LogManager(level=LogLevel.DEBUG)
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.debug(LogCategory.LLM, "Debug message")

        mock_transport.write.assert_called_once()
        event = mock_transport.write.call_args[0][0]
        assert event.level == LogLevel.DEBUG

    def test_info_method(self) -> None:
        """LogManager has info() method."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.info(LogCategory.PHASE, "Info message")

        mock_transport.write.assert_called_once()
        event = mock_transport.write.call_args[0][0]
        assert event.level == LogLevel.INFO

    def test_warn_method(self) -> None:
        """LogManager has warn() method."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.warn(LogCategory.HOOK, "Warning message")

        mock_transport.write.assert_called_once()
        event = mock_transport.write.call_args[0][0]
        assert event.level == LogLevel.WARN

    def test_error_method(self) -> None:
        """LogManager has error() method."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.error(LogCategory.ERROR, "Error message")

        mock_transport.write.assert_called_once()
        event = mock_transport.write.call_args[0][0]
        assert event.level == LogLevel.ERROR

    def test_fatal_method(self) -> None:
        """LogManager has fatal() method."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.fatal(LogCategory.ERROR, "Fatal message")

        mock_transport.write.assert_called_once()
        event = mock_transport.write.call_args[0][0]
        assert event.level == LogLevel.FATAL


class TestLogLevelFiltering:
    """Tests for log level filtering."""

    def test_filters_below_level(self) -> None:
        """LogManager filters events below configured level."""
        manager = LogManager(level=LogLevel.WARN)
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.debug(LogCategory.PHASE, "Should not appear")
        manager.info(LogCategory.PHASE, "Should not appear")

        mock_transport.write.assert_not_called()

    def test_allows_at_level(self) -> None:
        """LogManager allows events at configured level."""
        manager = LogManager(level=LogLevel.WARN)
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.warn(LogCategory.PHASE, "Should appear")

        mock_transport.write.assert_called_once()

    def test_allows_above_level(self) -> None:
        """LogManager allows events above configured level."""
        manager = LogManager(level=LogLevel.WARN)
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.error(LogCategory.ERROR, "Should appear")
        manager.fatal(LogCategory.ERROR, "Should appear")

        assert mock_transport.write.call_count == 2


class TestEventRouting:
    """Tests for routing events to transports."""

    def test_routes_to_all_transports(self, tmp_path: Path) -> None:
        """LogManager routes events to all registered transports."""
        manager = LogManager()

        output = io.StringIO()
        console = ConsoleTransport(file=output, force_tty=False)
        raw_file = RawFileTransport(tmp_path / "raw.log")
        jsonl_file = StructuredFileTransport(tmp_path / "logs.jsonl")

        manager.register(console)
        manager.register(raw_file)
        manager.register(jsonl_file)

        manager.info(LogCategory.PHASE, "Broadcast message")

        # Check console
        assert "Broadcast message" in output.getvalue()

        # Check raw file
        assert "Broadcast message" in (tmp_path / "raw.log").read_text()

        # Check JSONL file
        assert "Broadcast message" in (tmp_path / "logs.jsonl").read_text()

    def test_includes_category_in_event(self) -> None:
        """LogManager includes category in events."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.info(LogCategory.LLM, "LLM interaction")

        event = mock_transport.write.call_args[0][0]
        assert event.category == LogCategory.LLM


class TestChildLoggers:
    """Tests for child logger creation."""

    def test_child_inherits_transports(self) -> None:
        """Child logger inherits parent's transports."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        child = manager.child(run_id="01HQ123ABC")
        child.info(LogCategory.PHASE, "Child message")

        mock_transport.write.assert_called_once()

    def test_child_inherits_context(self) -> None:
        """Child logger inherits and extends parent's context."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        child = manager.child(run_id="01HQ123ABC")
        child.info(LogCategory.PHASE, "Message")

        event = mock_transport.write.call_args[0][0]
        assert event.context.run_id == "01HQ123ABC"

    def test_child_can_extend_context(self) -> None:
        """Child logger can add additional context."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        child = manager.child(run_id="01HQ123ABC")
        grandchild = child.child(phase="build")
        grandchild.info(LogCategory.PHASE, "Grandchild message")

        event = mock_transport.write.call_args[0][0]
        assert event.context.run_id == "01HQ123ABC"
        assert event.context.phase == "build"

    def test_child_inherits_level(self) -> None:
        """Child logger inherits parent's level."""
        manager = LogManager(level=LogLevel.DEBUG)
        child = manager.child(run_id="01HQ123ABC")

        assert child.level == LogLevel.DEBUG

    def test_child_can_have_extra_context(self) -> None:
        """Child logger can have extra context fields."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        child = manager.child(run_id="01HQ123ABC", extra={"component": "executor"})
        child.info(LogCategory.LLM, "With extra")

        event = mock_transport.write.call_args[0][0]
        assert event.context.extra["component"] == "executor"


class TestLogManagerSetLevel:
    """Tests for dynamic level changes."""

    def test_set_level(self) -> None:
        """LogManager level can be changed."""
        manager = LogManager(level=LogLevel.INFO)
        manager.set_level(LogLevel.DEBUG)

        assert manager.level == LogLevel.DEBUG

    def test_level_change_affects_filtering(self) -> None:
        """Level change affects subsequent filtering."""
        manager = LogManager(level=LogLevel.ERROR)
        mock_transport = MagicMock()
        manager.register(mock_transport)

        # Initially filtered
        manager.info(LogCategory.PHASE, "Filtered")
        assert mock_transport.write.call_count == 0

        # Change level
        manager.set_level(LogLevel.INFO)

        # Now allowed
        manager.info(LogCategory.PHASE, "Allowed")
        assert mock_transport.write.call_count == 1


class TestLogManagerVerbosity:
    """Tests for verbosity control in LogManager."""

    def test_set_verbosity_updates_console_transports(self) -> None:
        """set_verbosity() updates verbosity on console transports."""
        manager = LogManager()
        output = io.StringIO()
        console = ConsoleTransport(file=output, force_tty=False)
        manager.register(console)

        manager.set_verbosity(Verbosity.QUIET)

        assert console.verbosity == Verbosity.QUIET

    def test_set_verbosity_does_not_affect_file_transports(
        self, tmp_path: Path
    ) -> None:
        """set_verbosity() does not affect file transports."""
        manager = LogManager()
        output = io.StringIO()
        console = ConsoleTransport(file=output, force_tty=False)
        raw_file = RawFileTransport(tmp_path / "raw.log")

        manager.register(console)
        manager.register(raw_file)

        # Set verbosity to quiet
        manager.set_verbosity(Verbosity.QUIET)

        # Log at INFO level
        manager.info(LogCategory.PHASE, "Info message")

        # Console should not show INFO (filtered by QUIET)
        assert output.getvalue() == ""

        # File should still have the message (files ignore verbosity)
        assert "Info message" in (tmp_path / "raw.log").read_text()

    def test_set_verbosity_filters_console_output(self) -> None:
        """set_verbosity() filters messages on console."""
        manager = LogManager()
        output = io.StringIO()
        console = ConsoleTransport(file=output, force_tty=False)
        manager.register(console)

        # Set to quiet - only errors
        manager.set_verbosity(Verbosity.QUIET)

        manager.info(LogCategory.PHASE, "Info filtered")
        manager.error(LogCategory.ERROR, "Error shown")

        result = output.getvalue()
        assert "Info filtered" not in result
        assert "Error shown" in result

    def test_verbosity_property(self) -> None:
        """LogManager has verbosity property."""
        manager = LogManager()
        assert manager.verbosity == Verbosity.NORMAL

        manager.set_verbosity(Verbosity.VERBOSE)
        assert manager.verbosity == Verbosity.VERBOSE

    def test_child_inherits_verbosity(self) -> None:
        """Child logger inherits parent's verbosity setting."""
        manager = LogManager()
        output = io.StringIO()
        console = ConsoleTransport(file=output, force_tty=False)
        manager.register(console)
        manager.set_verbosity(Verbosity.QUIET)

        child = manager.child(run_id="01HQ123ABC")

        # Child should also have QUIET verbosity effect
        assert child.verbosity == Verbosity.QUIET


class TestLogManagerRedaction:
    """Tests for secret redaction in LogManager."""

    def test_redactor_is_none_by_default(self) -> None:
        """LogManager has no redactor by default."""
        manager = LogManager()
        assert manager.redactor is None

    def test_redactor_can_be_set_in_constructor(self) -> None:
        """LogManager can be created with a redactor."""
        from adw.logging.redactor import Redactor

        redactor = Redactor(["test"])
        manager = LogManager(redactor=redactor)
        assert manager.redactor is redactor

    def test_set_redactor_method(self) -> None:
        """LogManager.set_redactor() sets the redactor."""
        from adw.logging.redactor import Redactor

        manager = LogManager()
        redactor = Redactor(["test"])
        manager.set_redactor(redactor)
        assert manager.redactor is redactor

    def test_set_redactor_to_none_disables(self) -> None:
        """LogManager.set_redactor(None) disables redaction."""
        from adw.logging.redactor import Redactor

        manager = LogManager(redactor=Redactor(["test"]))
        manager.set_redactor(None)
        assert manager.redactor is None

    def test_redaction_applied_to_messages(self) -> None:
        """Redactor is applied to log messages."""
        from adw.logging.redactor import DEFAULT_REDACTION_PATTERNS, Redactor

        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        manager = LogManager(redactor=redactor)
        mock_transport = MagicMock()
        manager.register(mock_transport)

        manager.info(LogCategory.LLM, "API key: sk-" + "a" * 50)

        mock_transport.write.assert_called_once()
        event = mock_transport.write.call_args[0][0]
        assert "sk-" not in event.message
        assert "[REDACTED]" in event.message

    def test_no_redaction_without_redactor(self) -> None:
        """Messages are not redacted when no redactor is set."""
        manager = LogManager()
        mock_transport = MagicMock()
        manager.register(mock_transport)

        secret = "sk-" + "a" * 50
        manager.info(LogCategory.LLM, f"API key: {secret}")

        mock_transport.write.assert_called_once()
        event = mock_transport.write.call_args[0][0]
        assert secret in event.message

    def test_child_inherits_redactor(self) -> None:
        """Child logger inherits parent's redactor."""
        from adw.logging.redactor import Redactor

        redactor = Redactor(["secret_[0-9]+"])
        manager = LogManager(redactor=redactor)

        child = manager.child(run_id="test-run")

        assert child.redactor is redactor

    def test_child_uses_inherited_redactor(self) -> None:
        """Child logger applies inherited redactor to messages."""
        from adw.logging.redactor import Redactor

        redactor = Redactor(["secret_[0-9]+"])
        manager = LogManager(redactor=redactor)
        mock_transport = MagicMock()
        manager.register(mock_transport)

        child = manager.child(run_id="test-run")
        child.info(LogCategory.LLM, "Code: secret_12345")

        mock_transport.write.assert_called_once()
        event = mock_transport.write.call_args[0][0]
        assert "secret_12345" not in event.message
        assert "[REDACTED]" in event.message

    def test_redaction_at_all_log_levels(self) -> None:
        """Redaction is applied at all log levels."""
        from adw.logging.redactor import Redactor

        redactor = Redactor(["secret"])
        manager = LogManager(level=LogLevel.TRACE, redactor=redactor)
        mock_transport = MagicMock()
        manager.register(mock_transport)

        levels = [
            manager.trace,
            manager.debug,
            manager.info,
            manager.warn,
            manager.error,
            manager.fatal,
        ]

        for log_method in levels:
            log_method(LogCategory.LLM, "Contains secret data")

        assert mock_transport.write.call_count == 6
        for call in mock_transport.write.call_args_list:
            event = call[0][0]
            assert "secret" not in event.message
            assert "[REDACTED]" in event.message
