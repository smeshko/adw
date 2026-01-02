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


class TestStateSnapshotCreation:
    """Tests for StateSnapshot model creation."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_phase_result(self) -> PhaseResult:
        """Create a sample PhaseResult for testing."""
        return PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            artifacts=["plan.md"],
            tokens_used=500,
        )

    def test_pre_phase_snapshot_creation(self, sample_context: RunContext) -> None:
        """Pre-phase snapshot creates correctly without phase_result."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=None,
            label="pre_plan",
            sequence=1,
        )
        assert snapshot.context == sample_context
        assert snapshot.phase_result is None
        assert snapshot.label == "pre_plan"
        assert snapshot.sequence == 1
        assert snapshot.timestamp is not None

    def test_post_phase_snapshot_creation(
        self, sample_context: RunContext, sample_phase_result: PhaseResult
    ) -> None:
        """Post-phase snapshot creates correctly with phase_result."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=sample_phase_result,
            label="post_plan",
            sequence=2,
        )
        assert snapshot.context == sample_context
        assert snapshot.phase_result == sample_phase_result
        assert snapshot.label == "post_plan"
        assert snapshot.sequence == 2

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

    def test_explicit_timestamp(self, sample_context: RunContext) -> None:
        """Explicit timestamp is preserved."""
        explicit_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=None,
            timestamp=explicit_time,
            label="pre_plan",
            sequence=1,
        )
        assert snapshot.timestamp == explicit_time


class TestStateSnapshotValidation:
    """Tests for StateSnapshot model validation."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

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

    def test_sequence_cannot_be_negative(self, sample_context: RunContext) -> None:
        """Sequence cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            StateSnapshot(
                context=sample_context,
                phase_result=None,
                label="pre_plan",
                sequence=-1,
            )
        errors = exc_info.value.errors()
        assert any("sequence" in str(e) for e in errors)


class TestStateSnapshotSerialization:
    """Tests for StateSnapshot JSON serialization."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )

    @pytest.fixture
    def sample_phase_result(self) -> PhaseResult:
        """Create a sample PhaseResult for testing."""
        return PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            completed_at=datetime(2024, 1, 15, 10, 31, 0, tzinfo=UTC),
            artifacts=["plan.md"],
            tokens_used=500,
        )

    def test_serialization_to_json(
        self, sample_context: RunContext, sample_phase_result: PhaseResult
    ) -> None:
        """StateSnapshot serializes to JSON correctly."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=sample_phase_result,
            timestamp=datetime(2024, 1, 15, 10, 31, 0, tzinfo=UTC),
            label="post_plan",
            sequence=2,
        )
        json_str = snapshot.model_dump_json()

        # Should be valid JSON
        import json

        data = json.loads(json_str)

        # Check top-level fields
        assert "context" in data
        assert "phase_result" in data
        assert "timestamp" in data
        assert "label" in data
        assert "sequence" in data

        # Check nested context
        assert data["context"]["run_id"] == "01KDSG2VDHNK0W4HSCZWJZXWSQ"

        # Check nested phase_result
        assert data["phase_result"]["phase"] == "plan"
        assert data["phase_result"]["status"] == "completed"

    def test_deserialization_from_json(
        self, sample_context: RunContext, sample_phase_result: PhaseResult
    ) -> None:
        """StateSnapshot deserializes from JSON correctly."""
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

    def test_serialization_snake_case(self, sample_context: RunContext) -> None:
        """StateSnapshot uses snake_case in JSON (not camelCase)."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=None,
            label="pre_plan",
            sequence=1,
        )
        json_str = snapshot.model_dump_json()

        # Should contain snake_case
        assert "phase_result" in json_str

        # Should NOT contain camelCase
        assert "phaseResult" not in json_str

    def test_roundtrip_with_none_phase_result(self, sample_context: RunContext) -> None:
        """Pre-phase snapshot (no phase_result) round-trips correctly."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=None,
            label="pre_plan",
            sequence=1,
        )
        json_str = snapshot.model_dump_json()
        restored = StateSnapshot.model_validate_json(json_str)

        assert restored.phase_result is None
        assert restored.label == "pre_plan"


class TestStateSnapshotLabels:
    """Tests for StateSnapshot label conventions."""

    @pytest.fixture
    def sample_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(UTC),
        )

    def test_pre_plan_label(self, sample_context: RunContext) -> None:
        """Pre-plan snapshot uses correct label format."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=None,
            label="pre_plan",
            sequence=1,
        )
        assert snapshot.label == "pre_plan"

    def test_post_plan_label(self, sample_context: RunContext) -> None:
        """Post-plan snapshot uses correct label format."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=None,
            label="post_plan",
            sequence=2,
        )
        assert snapshot.label == "post_plan"

    def test_pre_build_label(self, sample_context: RunContext) -> None:
        """Pre-build snapshot uses correct label format."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=None,
            label="pre_build",
            sequence=3,
        )
        assert snapshot.label == "pre_build"

    def test_post_verify_label(self, sample_context: RunContext) -> None:
        """Post-verify snapshot uses correct label format."""
        snapshot = StateSnapshot(
            context=sample_context,
            phase_result=None,
            label="post_verify",
            sequence=10,
        )
        assert snapshot.label == "post_verify"
