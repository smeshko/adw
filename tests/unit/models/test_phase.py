"""Tests for phase models (PhaseStatus, PhaseResult, Artifact).

Focused on validation, error handling, and calculated properties.
Trivial enum/creation/serialization tests removed per TEST_REDUCTION_PLAN.md
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from adw.models import (
    PhaseResult,
    PhaseStatus,
)


class TestPhaseResultValidation:
    """Tests for PhaseResult validation and error handling."""

    def test_invalid_status_string(self) -> None:
        """Invalid status string raises ValidationError."""
        with pytest.raises(ValidationError):
            PhaseResult(
                phase="plan",
                status="invalid_status",  # type: ignore
                started_at=datetime.now(),
            )


class TestPhaseResultCalculatedProperties:
    """Tests for PhaseResult calculated properties (business logic)."""

    def test_duration_ms_calculation(self) -> None:
        """duration_ms correctly calculates elapsed time."""
        start = datetime(2024, 1, 15, 10, 0, 0)
        end = datetime(2024, 1, 15, 10, 1, 30)  # 90 seconds later

        result = PhaseResult(
            phase="build",
            status=PhaseStatus.COMPLETED,
            started_at=start,
            completed_at=end,
        )
        assert result.duration_ms == 90000  # 90 seconds in ms

    def test_duration_ms_none_when_not_completed(self) -> None:
        """duration_ms is None when phase not completed."""
        result = PhaseResult(
            phase="build",
            status=PhaseStatus.RUNNING,
            started_at=datetime.now(),
        )
        assert result.duration_ms is None

    def test_completed_phase_with_artifacts_calculates_duration(self) -> None:
        """PhaseResult tracks artifacts and calculates duration for completed phase."""
        start = datetime.now()
        end = start + timedelta(seconds=30)

        result = PhaseResult(
            phase="code",
            status=PhaseStatus.COMPLETED,
            started_at=start,
            completed_at=end,
            artifacts=["src/auth.py", "src/login.py"],
        )
        assert result.artifacts == ["src/auth.py", "src/login.py"]
        assert result.duration_ms == 30000

    def test_failed_phase_with_error(self) -> None:
        """PhaseResult tracks error for failed phase."""
        result = PhaseResult(
            phase="test",
            status=PhaseStatus.FAILED,
            started_at=datetime.now(),
            error="Test suite failed: 3 tests failed",
        )
        assert result.error == "Test suite failed: 3 tests failed"
        assert result.status == PhaseStatus.FAILED
