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
