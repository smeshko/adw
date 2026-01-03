"""Tests for logging-related Pydantic models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adw.models.logging import LogCategory, LogContext, LogEvent, LogLevel


class TestLogLevel:
    """Tests for the LogLevel enum."""

    def test_all_log_levels_defined(self) -> None:
        """LogLevel contains all required levels per architecture spec."""
        assert LogLevel.TRACE == "trace"
        assert LogLevel.DEBUG == "debug"
        assert LogLevel.INFO == "info"
        assert LogLevel.WARN == "warn"
        assert LogLevel.ERROR == "error"
        assert LogLevel.FATAL == "fatal"

    def test_log_level_count(self) -> None:
        """LogLevel has exactly 6 levels."""
        assert len(LogLevel) == 6

    def test_log_level_is_string_enum(self) -> None:
        """LogLevel values are strings."""
        for level in LogLevel:
            assert isinstance(level.value, str)


class TestLogCategory:
    """Tests for the LogCategory enum."""

    def test_all_log_categories_defined(self) -> None:
        """LogCategory contains all required categories per architecture spec."""
        assert LogCategory.PHASE == "phase"
        assert LogCategory.LLM == "llm"
        assert LogCategory.HOOK == "hook"
        assert LogCategory.STATE == "state"
        assert LogCategory.ERROR == "error"
        assert LogCategory.PERFORMANCE == "performance"

    def test_log_category_count(self) -> None:
        """LogCategory has exactly 6 categories."""
        assert len(LogCategory) == 6

    def test_log_category_is_string_enum(self) -> None:
        """LogCategory values are strings."""
        for category in LogCategory:
            assert isinstance(category.value, str)


class TestLogContext:
    """Tests for the LogContext model."""

    def test_create_empty_context(self) -> None:
        """LogContext can be created with no fields."""
        ctx = LogContext()
        assert ctx.run_id is None
        assert ctx.phase is None
        assert ctx.extra == {}

    def test_create_context_with_run_id(self) -> None:
        """LogContext can be created with run_id."""
        ctx = LogContext(run_id="01HQ123ABC")
        assert ctx.run_id == "01HQ123ABC"
        assert ctx.phase is None

    def test_create_context_with_phase(self) -> None:
        """LogContext can be created with phase."""
        ctx = LogContext(phase="build")
        assert ctx.phase == "build"
        assert ctx.run_id is None

    def test_create_context_with_extra(self) -> None:
        """LogContext can be created with extra fields."""
        ctx = LogContext(extra={"component": "executor", "attempt": 1})
        assert ctx.extra["component"] == "executor"
        assert ctx.extra["attempt"] == 1

    def test_context_merge(self) -> None:
        """LogContext can merge with another context."""
        parent = LogContext(run_id="01HQ123ABC", phase="plan")
        child = parent.merge(phase="build", extra={"step": 1})
        # Parent unchanged
        assert parent.phase == "plan"
        assert "step" not in parent.extra
        # Child has merged values
        assert child.run_id == "01HQ123ABC"
        assert child.phase == "build"
        assert child.extra["step"] == 1

    def test_context_serialization(self) -> None:
        """LogContext serializes to dict correctly."""
        ctx = LogContext(run_id="01HQ123ABC", phase="test")
        d = ctx.model_dump()
        assert d["run_id"] == "01HQ123ABC"
        assert d["phase"] == "test"
        assert d["extra"] == {}


class TestLogEvent:
    """Tests for the LogEvent model."""

    def test_create_minimal_event(self) -> None:
        """LogEvent can be created with required fields."""
        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Test message",
        )
        assert event.level == LogLevel.INFO
        assert event.category == LogCategory.PHASE
        assert event.message == "Test message"
        assert event.timestamp is not None
        assert event.context is not None

    def test_create_full_event(self) -> None:
        """LogEvent can be created with all fields."""
        now = datetime.now(UTC)
        ctx = LogContext(run_id="01HQ123ABC", phase="build")
        event = LogEvent(
            timestamp=now,
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            message="Something failed",
            context=ctx,
        )
        assert event.timestamp == now
        assert event.level == LogLevel.ERROR
        assert event.category == LogCategory.ERROR
        assert event.message == "Something failed"
        assert event.context.run_id == "01HQ123ABC"

    def test_event_auto_timestamp(self) -> None:
        """LogEvent auto-generates timestamp if not provided."""
        before = datetime.now(UTC)
        event = LogEvent(
            level=LogLevel.DEBUG,
            category=LogCategory.LLM,
            message="Auto timestamp test",
        )
        after = datetime.now(UTC)
        assert before <= event.timestamp <= after

    def test_event_serialization(self) -> None:
        """LogEvent serializes to dict correctly."""
        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.STATE,
            message="State changed",
            context=LogContext(run_id="01HQ123ABC"),
        )
        d = event.model_dump()
        assert d["level"] == "info"
        assert d["category"] == "state"
        assert d["message"] == "State changed"
        assert d["context"]["run_id"] == "01HQ123ABC"
        assert "timestamp" in d

    def test_event_json_serialization(self) -> None:
        """LogEvent can be serialized to JSON (JSONL format support)."""
        event = LogEvent(
            level=LogLevel.WARN,
            category=LogCategory.PERFORMANCE,
            message="Slow operation",
        )
        json_str = event.model_dump_json()
        assert '"level": "warn"' in json_str or '"level":"warn"' in json_str
        assert "Slow operation" in json_str

    def test_event_required_fields(self) -> None:
        """LogEvent requires level, category, and message fields."""
        with pytest.raises(ValidationError):
            LogEvent()  # type: ignore[call-arg]

    def test_event_requires_level(self) -> None:
        """LogEvent requires level field."""
        with pytest.raises(ValidationError):
            LogEvent(category=LogCategory.PHASE, message="test")  # type: ignore[call-arg]

    def test_event_requires_category(self) -> None:
        """LogEvent requires category field."""
        with pytest.raises(ValidationError):
            LogEvent(level=LogLevel.INFO, message="test")  # type: ignore[call-arg]

    def test_event_requires_message(self) -> None:
        """LogEvent requires message field."""
        with pytest.raises(ValidationError):
            LogEvent(level=LogLevel.INFO, category=LogCategory.PHASE)  # type: ignore[call-arg]

    def test_acceptance_criteria_fields(self) -> None:
        """LogEvent includes all fields from acceptance criteria.

        Required fields: timestamp, level, category, message, context fields
        """
        event = LogEvent(
            level=LogLevel.INFO,
            category=LogCategory.PHASE,
            message="Test",
            context=LogContext(run_id="123", phase="build"),
        )
        # Verify all AC fields exist with correct types
        assert isinstance(event.timestamp, datetime)
        assert isinstance(event.level, LogLevel)
        assert isinstance(event.category, LogCategory)
        assert isinstance(event.message, str)
        assert isinstance(event.context, LogContext)


# ============================================================================
# LLM Capture Models (Story 7.3)
# ============================================================================


class TestLLMRequest:
    """Tests for the LLMRequest model."""

    def test_create_minimal_request(self) -> None:
        """LLMRequest can be created with minimal fields."""
        from adw.models.logging import LLMRequest

        request = LLMRequest(prompt="Hello, world", phase="plan")
        assert request.prompt == "Hello, world"
        assert request.phase == "plan"
        assert request.timestamp is not None
        assert request.params == {}

    def test_create_full_request(self) -> None:
        """LLMRequest can be created with all fields."""
        from adw.models.logging import LLMRequest

        now = datetime.now(UTC)
        request = LLMRequest(
            timestamp=now,
            prompt="Generate code",
            phase="build",
            params={"model": "claude-sonnet-4-20250514", "temperature": 0, "max_tokens": 16000},
        )
        assert request.timestamp == now
        assert request.prompt == "Generate code"
        assert request.phase == "build"
        assert request.params["model"] == "claude-sonnet-4-20250514"

    def test_request_serialization(self) -> None:
        """LLMRequest serializes to JSON correctly for file storage."""
        from adw.models.logging import LLMRequest

        request = LLMRequest(
            prompt="Test prompt",
            phase="plan",
            params={"model": "claude-sonnet-4-20250514"},
        )
        json_str = request.model_dump_json()
        assert "Test prompt" in json_str
        assert "plan" in json_str
        assert "claude-sonnet-4-20250514" in json_str


class TestLLMResponse:
    """Tests for the LLMResponse model."""

    def test_create_minimal_response(self) -> None:
        """LLMResponse can be created with minimal fields."""
        from adw.models.logging import LLMResponse

        response = LLMResponse(content="Generated content", phase="build")
        assert response.content == "Generated content"
        assert response.phase == "build"
        assert response.timestamp is not None
        assert response.tool_calls == []
        assert response.stats.input_tokens == 0

    def test_create_full_response(self) -> None:
        """LLMResponse can be created with all fields."""
        from adw.models.logging import LLMResponse, LLMToolCall, LLMStats

        now = datetime.now(UTC)
        tool_call = LLMToolCall(id="call_01", name="create_file", input={"path": "test.py"})
        stats = LLMStats(input_tokens=4521, output_tokens=3892, duration_ms=47333)
        response = LLMResponse(
            timestamp=now,
            content="Here's the code",
            phase="build",
            tool_calls=[tool_call],
            stats=stats,
        )
        assert response.timestamp == now
        assert response.content == "Here's the code"
        assert response.phase == "build"
        assert len(response.tool_calls) == 1
        assert response.stats.input_tokens == 4521
        assert response.stats.output_tokens == 3892
        assert response.stats.duration_ms == 47333

    def test_response_serialization(self) -> None:
        """LLMResponse serializes to JSON correctly."""
        from adw.models.logging import LLMResponse, LLMStats

        response = LLMResponse(
            content="Response content",
            phase="build",
            stats=LLMStats(input_tokens=100, output_tokens=50, duration_ms=1000),
        )
        json_str = response.model_dump_json()
        assert "Response content" in json_str
        assert "100" in json_str  # input_tokens


class TestLLMStats:
    """Tests for the LLMStats model."""

    def test_create_stats(self) -> None:
        """LLMStats can be created with token counts and duration."""
        from adw.models.logging import LLMStats

        stats = LLMStats(input_tokens=4521, output_tokens=3892, duration_ms=47333)
        assert stats.input_tokens == 4521
        assert stats.output_tokens == 3892
        assert stats.duration_ms == 47333

    def test_stats_defaults(self) -> None:
        """LLMStats has sensible defaults."""
        from adw.models.logging import LLMStats

        stats = LLMStats()
        assert stats.input_tokens == 0
        assert stats.output_tokens == 0
        assert stats.duration_ms == 0


class TestLLMToolCall:
    """Tests for the LLMToolCall model."""

    def test_create_tool_call(self) -> None:
        """LLMToolCall captures tool invocation details."""
        from adw.models.logging import LLMToolCall

        tool_call = LLMToolCall(
            id="call_01",
            name="create_file",
            input={"path": "test.py", "content": "# test"},
        )
        assert tool_call.id == "call_01"
        assert tool_call.name == "create_file"
        assert tool_call.input["path"] == "test.py"

    def test_tool_call_serialization(self) -> None:
        """LLMToolCall serializes correctly."""
        from adw.models.logging import LLMToolCall

        tool_call = LLMToolCall(id="call_01", name="read_file", input={"path": "main.py"})
        d = tool_call.model_dump()
        assert d["id"] == "call_01"
        assert d["name"] == "read_file"


class TestLLMToolResult:
    """Tests for the LLMToolResult model."""

    def test_create_tool_result(self) -> None:
        """LLMToolResult captures tool execution result."""
        from adw.models.logging import LLMToolResult

        result = LLMToolResult(
            id="call_01",
            output="File created successfully",
            success=True,
            duration_ms=45,
        )
        assert result.id == "call_01"
        assert result.output == "File created successfully"
        assert result.success is True
        assert result.duration_ms == 45

    def test_tool_result_defaults(self) -> None:
        """LLMToolResult has sensible defaults."""
        from adw.models.logging import LLMToolResult

        result = LLMToolResult(id="call_01", output="result")
        assert result.success is True
        assert result.duration_ms == 0


class TestLLMStreamEvent:
    """Tests for the LLMStreamEvent model."""

    def test_create_token_event(self) -> None:
        """LLMStreamEvent can capture a token event."""
        from adw.models.logging import LLMStreamEvent, StreamEventType

        event = LLMStreamEvent(
            t=12,
            type=StreamEventType.TOKEN,
            content="Hello",
        )
        assert event.t == 12
        assert event.type == StreamEventType.TOKEN
        assert event.content == "Hello"

    def test_create_tool_call_event(self) -> None:
        """LLMStreamEvent can capture a tool call start event."""
        from adw.models.logging import LLMStreamEvent, StreamEventType

        event = LLMStreamEvent(
            t=1250,
            type=StreamEventType.TOOL_CALL_START,
            id="call_01",
            name="create_file",
            input={"path": "test.py"},
        )
        assert event.t == 1250
        assert event.type == StreamEventType.TOOL_CALL_START
        assert event.id == "call_01"
        assert event.name == "create_file"

    def test_create_complete_event(self) -> None:
        """LLMStreamEvent can capture completion event with stats."""
        from adw.models.logging import LLMStreamEvent, StreamEventType, LLMStats

        stats = LLMStats(input_tokens=4521, output_tokens=3892)
        event = LLMStreamEvent(
            t=45230,
            type=StreamEventType.COMPLETE,
            stats=stats,
        )
        assert event.t == 45230
        assert event.type == StreamEventType.COMPLETE
        assert event.stats is not None
        assert event.stats.input_tokens == 4521

    def test_stream_event_serialization(self) -> None:
        """LLMStreamEvent serializes to JSONL format correctly."""
        from adw.models.logging import LLMStreamEvent, StreamEventType

        event = LLMStreamEvent(t=0, type=StreamEventType.TOKEN, content="I'll")
        json_str = event.model_dump_json()
        # Should be compact for JSONL
        assert '"t":' in json_str or '"t": ' in json_str
        assert "token" in json_str
        assert "I'll" in json_str

    def test_stream_event_types(self) -> None:
        """StreamEventType has all required event types."""
        from adw.models.logging import StreamEventType

        assert StreamEventType.TOKEN == "token"
        assert StreamEventType.TOOL_CALL_START == "tool_call_start"
        assert StreamEventType.TOOL_CALL_END == "tool_call_end"
        assert StreamEventType.THINKING == "thinking"
        assert StreamEventType.COMPLETE == "complete"
        assert StreamEventType.ERROR == "error"
