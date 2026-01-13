"""Tests for resume models (ResumeInfo, ResumeStatus).

Tests verify the dataclasses work correctly:
- ResumeInfo: holds resume operation data
- ResumeStatus: provides status summary for display
"""

from datetime import UTC, datetime

import pytest

from adw.models import RunContext
from adw.models.resume import ResumeInfo, ResumeStatus


# Valid 26-character ULIDs for testing
SAMPLE_RUN_ID = "01HQTEST1234567890ABCDEF12"


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample run context."""
    return RunContext(
        run_id=SAMPLE_RUN_ID,
        feature_description="Test feature",
        current_phase="build",
        status="running",
        phase_history=["plan"],
        started_at=datetime.now(UTC),
    )


class TestResumeInfo:
    """Tests for ResumeInfo dataclass."""

    def test_immutable(self, sample_context: RunContext) -> None:
        """ResumeInfo is immutable (frozen)."""
        info = ResumeInfo(
            context=sample_context,
            resume_phase="build",
        )
        with pytest.raises(AttributeError):
            info.resume_phase = "plan"  # type: ignore[misc]

    def test_convenience_properties(self, sample_context: RunContext) -> None:
        """Convenience properties delegate to context."""
        info = ResumeInfo(
            context=sample_context,
            resume_phase="build",
        )

        assert info.run_id == SAMPLE_RUN_ID
        assert info.feature_description == "Test feature"
        assert info.completed_phases == ["plan"]

    def test_default_valid(self, sample_context: RunContext) -> None:
        """Default is_valid is True."""
        info = ResumeInfo(
            context=sample_context,
            resume_phase="build",
        )

        assert info.is_valid is True
        assert info.validation_error is None

    def test_invalid_with_error(self, sample_context: RunContext) -> None:
        """Invalid info has error message."""
        info = ResumeInfo(
            context=sample_context,
            resume_phase="build",
            is_valid=False,
            validation_error="Test error",
        )

        assert info.is_valid is False
        assert info.validation_error == "Test error"


class TestResumeStatus:
    """Tests for ResumeStatus dataclass."""

    def test_immutable(self) -> None:
        """ResumeStatus is immutable (frozen)."""
        status = ResumeStatus(
            run_id=SAMPLE_RUN_ID,
            status="running",
            current_phase="build",
            interrupted_phase=None,
            completed_phases=["plan"],
            can_resume=True,
            resume_phase="build",
        )
        with pytest.raises(AttributeError):
            status.status = "completed"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        """to_dict returns all fields."""
        status = ResumeStatus(
            run_id=SAMPLE_RUN_ID,
            status="interrupted",
            current_phase="build",
            interrupted_phase="build",
            completed_phases=["plan"],
            can_resume=True,
            resume_phase="build",
        )

        result = status.to_dict()

        assert result == {
            "run_id": SAMPLE_RUN_ID,
            "status": "interrupted",
            "current_phase": "build",
            "interrupted_phase": "build",
            "completed_phases": ["plan"],
            "can_resume": True,
            "resume_phase": "build",
        }

    def test_to_dict_with_none_values(self) -> None:
        """to_dict handles None values."""
        status = ResumeStatus(
            run_id=SAMPLE_RUN_ID,
            status="completed",
            current_phase="document",
            interrupted_phase=None,
            completed_phases=["plan", "build", "validate", "document"],
            can_resume=False,
            resume_phase=None,
        )

        result = status.to_dict()

        assert result["interrupted_phase"] is None
        assert result["resume_phase"] is None
        assert result["can_resume"] is False
