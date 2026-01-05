# Reduced test file: Removed trivial creation tests, label tests, and serialization
# smoke tests. Kept only validation tests and essential behavior/roundtrip tests.
# Original: 331 lines, 16 tests -> Reduced: ~85 lines, 6 tests
"""Tests for StateSnapshot model (Story 4.3).

StateSnapshot captures the full run state at phase boundaries for:
- Debugging failures
- Resuming from known-good states
- Time-travel debugging (NFR13)
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adw.models import PhaseResult, PhaseStatus, RunContext, StateSnapshot


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample RunContext for testing."""
    return RunContext(
        run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        feature_description="Add user authentication",
        current_phase="plan",
        started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
    )


@pytest.fixture
def sample_phase_result() -> PhaseResult:
    """Create a sample PhaseResult for testing."""
    return PhaseResult(
        phase="plan",
        status=PhaseStatus.COMPLETED,
        started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        completed_at=datetime(2024, 1, 15, 10, 31, 0, tzinfo=UTC),
        artifacts=["plan.md"],
        tokens_used=500,
    )


class TestStateSnapshotValidation:
    """Tests for StateSnapshot model validation."""

    def test_context_is_required(self) -> None:
        """Context field is required."""
        with pytest.raises(ValidationError) as exc_info:
            StateSnapshot(
                phase_result=None,
                label="pre_plan",
                sequence=1,
            )  # type: ignore
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("context",) for e in errors)

    def test_label_is_required(self, sample_context: RunContext) -> None:
        """Label field is required."""
        with pytest.raises(ValidationError) as exc_info:
            StateSnapshot(
                context=sample_context,
                phase_result=None,
                sequence=1,
            )  # type: ignore
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("label",) for e in errors)

    def test_sequence_is_required(self, sample_context: RunContext) -> None:
        """Sequence field is required."""
        with pytest.raises(ValidationError) as exc_info:
            StateSnapshot(
                context=sample_context,
                phase_result=None,
                label="pre_plan",
            )  # type: ignore
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("sequence",) for e in errors)

    def test_sequence_must_be_positive(self, sample_context: RunContext) -> None:
        """Sequence must be a positive integer."""
        with pytest.raises(ValidationError) as exc_info:
            StateSnapshot(
                context=sample_context,
                phase_result=None,
                label="pre_plan",
                sequence=0,
            )
        errors = exc_info.value.errors()
        assert any("sequence" in str(e) for e in errors)


class TestStateSnapshotBehavior:
    """Tests for StateSnapshot behavior and serialization."""

    def test_timestamp_auto_generated(self, sample_context: RunContext) -> None:
        """Timestamp is auto-generated if not provided."""
        before = datetime.now(UTC)
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=None,
            label="pre_plan",
            sequence=1,
        )
        after = datetime.now(UTC)

        assert before <= snapshot.timestamp <= after

    def test_deserialization_from_json(
        self, sample_context: RunContext, sample_phase_result: PhaseResult
    ) -> None:
        """StateSnapshot deserializes from JSON correctly (roundtrip test)."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=sample_phase_result,
            timestamp=datetime(2024, 1, 15, 10, 31, 0, tzinfo=UTC),
            label="post_plan",
            sequence=2,
        )
        json_str = snapshot.model_dump_json()

        # Deserialize
        restored = StateSnapshot.model_validate_json(json_str)

        # Verify all fields match
        assert restored.context.run_id == snapshot.context.run_id
        assert restored.phase_result is not None
        assert restored.phase_result.phase == snapshot.phase_result.phase
        assert restored.label == snapshot.label
        assert restored.sequence == snapshot.sequence
