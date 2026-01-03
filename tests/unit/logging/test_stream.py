"""Tests for StreamLogger class (Story 7.3)."""

import time

import pytest

from adw.logging.stream import StreamLogger
from adw.models.logging import LLMStats, LLMStreamEvent, StreamEventType


class TestStreamLoggerCreation:
    """Tests for StreamLogger initialization."""

    def test_create_stream_logger(self) -> None:
        """StreamLogger can be created."""
        logger = StreamLogger()
        assert logger is not None

    def test_stream_logger_empty_events(self) -> None:
        """New StreamLogger has no events."""
        logger = StreamLogger()
        events = logger.get_events()
        assert events == []


class TestStreamLoggerToken:
    """Tests for StreamLogger.token() method."""

    def test_token_captures_content(self) -> None:
        """token() captures text content."""
        logger = StreamLogger()
        logger.token("Hello")
        events = logger.get_events()
        assert len(events) == 1
        assert events[0].type == StreamEventType.TOKEN
        assert events[0].content == "Hello"

    def test_token_has_timestamp(self) -> None:
        """token() events have relative timestamps."""
        logger = StreamLogger()
        logger.token("Hello")
        events = logger.get_events()
        assert events[0].t >= 0

    def test_multiple_tokens(self) -> None:
        """Multiple tokens can be captured in sequence."""
        logger = StreamLogger()
        logger.token("Hello")
        logger.token(" world")
        events = logger.get_events()
        assert len(events) == 2
        assert events[0].content == "Hello"
        assert events[1].content == " world"
        # Second token should have later timestamp
        assert events[1].t >= events[0].t


class TestStreamLoggerToolCall:
    """Tests for StreamLogger.tool_call() method."""

    def test_tool_call_captures_details(self) -> None:
        """tool_call() captures tool invocation details."""
        logger = StreamLogger()
        logger.tool_call(id="call_01", name="create_file", input={"path": "test.py"})
        events = logger.get_events()
        assert len(events) == 1
        assert events[0].type == StreamEventType.TOOL_CALL_START
        assert events[0].id == "call_01"
        assert events[0].name == "create_file"
        assert events[0].input == {"path": "test.py"}


class TestStreamLoggerToolResult:
    """Tests for StreamLogger.tool_result() method."""

    def test_tool_result_captures_outcome(self) -> None:
        """tool_result() captures tool execution result."""
        logger = StreamLogger()
        logger.tool_result(id="call_01", success=True, duration_ms=45)
        events = logger.get_events()
        assert len(events) == 1
        assert events[0].type == StreamEventType.TOOL_CALL_END
        assert events[0].id == "call_01"
        assert events[0].success is True
        assert events[0].duration_ms == 45

    def test_tool_result_failure(self) -> None:
        """tool_result() can capture failures."""
        logger = StreamLogger()
        logger.tool_result(id="call_01", success=False, duration_ms=100)
        events = logger.get_events()
        assert events[0].success is False


class TestStreamLoggerThinking:
    """Tests for StreamLogger.thinking() method."""

    def test_thinking_captures_reasoning(self) -> None:
        """thinking() captures reasoning block content."""
        logger = StreamLogger()
        logger.thinking("Let me analyze this...")
        events = logger.get_events()
        assert len(events) == 1
        assert events[0].type == StreamEventType.THINKING
        assert events[0].content == "Let me analyze this..."


class TestStreamLoggerEnd:
    """Tests for StreamLogger.end() method."""

    def test_end_captures_stats(self) -> None:
        """end() captures completion with stats."""
        logger = StreamLogger()
        stats = LLMStats(input_tokens=4521, output_tokens=3892, duration_ms=47333)
        logger.end(stats)
        events = logger.get_events()
        assert len(events) == 1
        assert events[0].type == StreamEventType.COMPLETE
        assert events[0].stats is not None
        assert events[0].stats.input_tokens == 4521
        assert events[0].stats.output_tokens == 3892


class TestStreamLoggerError:
    """Tests for StreamLogger.error() method."""

    def test_error_captures_message(self) -> None:
        """error() captures error message."""
        logger = StreamLogger()
        logger.error("Connection timeout")
        events = logger.get_events()
        assert len(events) == 1
        assert events[0].type == StreamEventType.ERROR
        assert events[0].error == "Connection timeout"


class TestStreamLoggerIntegration:
    """Integration tests for StreamLogger."""

    def test_full_stream_sequence(self) -> None:
        """StreamLogger captures a complete stream sequence."""
        logger = StreamLogger()

        # Simulate a complete LLM interaction
        logger.token("I'll")
        logger.token(" create")
        logger.token(" a")
        logger.token(" file")
        logger.tool_call(id="call_01", name="create_file", input={"path": "test.py"})
        logger.tool_result(id="call_01", success=True, duration_ms=45)
        logger.token(" Done!")
        logger.end(LLMStats(input_tokens=100, output_tokens=50, duration_ms=1000))

        events = logger.get_events()
        assert len(events) == 8

        # Verify event types in sequence
        assert events[0].type == StreamEventType.TOKEN
        assert events[4].type == StreamEventType.TOOL_CALL_START
        assert events[5].type == StreamEventType.TOOL_CALL_END
        assert events[6].type == StreamEventType.TOKEN
        assert events[7].type == StreamEventType.COMPLETE

    def test_timestamps_are_monotonic(self) -> None:
        """Event timestamps increase monotonically."""
        logger = StreamLogger()
        logger.token("Hello")
        time.sleep(0.01)  # Small delay
        logger.token(" world")

        events = logger.get_events()
        assert events[1].t >= events[0].t

    def test_get_events_returns_copy(self) -> None:
        """get_events() returns a copy, not the internal list."""
        logger = StreamLogger()
        logger.token("Hello")
        events1 = logger.get_events()
        events2 = logger.get_events()
        assert events1 is not events2
        assert events1 == events2

    def test_clear_resets_logger(self) -> None:
        """clear() removes all captured events."""
        logger = StreamLogger()
        logger.token("Hello")
        logger.token(" world")
        assert len(logger.get_events()) == 2

        logger.clear()
        assert len(logger.get_events()) == 0

    def test_stream_events_are_llm_stream_event_models(self) -> None:
        """Events returned are LLMStreamEvent Pydantic models."""
        logger = StreamLogger()
        logger.token("Hello")
        events = logger.get_events()
        assert isinstance(events[0], LLMStreamEvent)
