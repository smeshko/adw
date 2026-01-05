"""Tests for logging-related Pydantic models.

Focused on validation and behavior tests only.
Trivial enum/serialization smoke tests removed per TEST_REDUCTION_PLAN.md
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adw.models.logging import (
    VERBOSITY_LEVEL_MAP,
    LogCategory,
    LogContext,
    LogEvent,
    LogLevel,
    Verbosity,
)


class TestVerbosityLevelMapping:
    """Tests for verbosity-to-log-level mapping (business logic)."""

    def test_verbosity_level_map_correct_mapping(self) -> None:
        """VERBOSITY_LEVEL_MAP has correct verbosity-to-level mapping.

        - QUIET: Only ERROR and FATAL (threshold at ERROR)
        - NORMAL: INFO and above (threshold at INFO)
        - VERBOSE: DEBUG and above (threshold at DEBUG)
        - TRACE: Everything including TRACE (threshold at TRACE)
        """
        assert VERBOSITY_LEVEL_MAP[Verbosity.QUIET] == LogLevel.ERROR
        assert VERBOSITY_LEVEL_MAP[Verbosity.NORMAL] == LogLevel.INFO
        assert VERBOSITY_LEVEL_MAP[Verbosity.VERBOSE] == LogLevel.DEBUG
        assert VERBOSITY_LEVEL_MAP[Verbosity.TRACE] == LogLevel.TRACE


class TestLogContext:
    """Tests for the LogContext model behavior."""

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


class TestLogEventValidation:
    """Tests for LogEvent validation (required fields)."""

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
