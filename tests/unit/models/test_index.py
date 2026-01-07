"""Unit tests for IndexEntry model.

Tests cover:
- Model instantiation with required fields
- Default values for optional fields
- JSON serialization/deserialization round-trip
- Field validation (run_id format, timestamps)
- Status field constraints
"""

from datetime import UTC, datetime

import pytest

from adw.models.index import IndexEntry


class TestIndexEntryModel:
    """Tests for IndexEntry model instantiation and validation."""

    def test_create_minimal_index_entry(self) -> None:
        """Test creating IndexEntry with only required fields."""
        entry = IndexEntry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/path/to/project",
            project_name="my-project",
            feature_description="Add user authentication",
            started_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            status="running",
        )

        assert entry.run_id == "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        assert entry.project_path == "/path/to/project"
        assert entry.project_name == "my-project"
        assert entry.feature_description == "Add user authentication"
        assert entry.status == "running"
        assert entry.completed_at is None
        assert entry.phase_reached is None
        assert entry.phases_completed == []

    def test_create_full_index_entry(self) -> None:
        """Test creating IndexEntry with all fields."""
        started = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        completed = datetime(2024, 1, 15, 11, 45, tzinfo=UTC)

        entry = IndexEntry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/path/to/project",
            project_name="my-project",
            feature_description="Add user authentication",
            started_at=started,
            completed_at=completed,
            status="completed",
            phase_reached="validate",
            phases_completed=["plan", "build", "validate"],
        )

        assert entry.completed_at == completed
        assert entry.phase_reached == "validate"
        assert entry.phases_completed == ["plan", "build", "validate"]

    def test_default_phases_completed_is_empty_list(self) -> None:
        """Test that phases_completed defaults to empty list."""
        entry = IndexEntry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/path/to/project",
            project_name="my-project",
            feature_description="Add feature",
            started_at=datetime.now(UTC),
            status="running",
        )

        assert entry.phases_completed == []
        # Verify it's a new list, not shared mutable default
        entry.phases_completed.append("plan")
        assert entry.phases_completed == ["plan"]


class TestIndexEntryValidation:
    """Tests for IndexEntry field validation."""

    def test_run_id_must_be_26_characters(self) -> None:
        """Test that run_id must be exactly 26 characters (ULID format)."""
        with pytest.raises(ValueError, match="ULID must be 26 characters"):
            IndexEntry(
                run_id="too-short",
                project_path="/path",
                project_name="project",
                feature_description="feature",
                started_at=datetime.now(UTC),
                status="running",
            )

    def test_run_id_must_have_valid_ulid_characters(self) -> None:
        """Test that run_id must contain valid ULID characters."""
        # ULID excludes I, L, O, U
        with pytest.raises(ValueError, match="Invalid ULID character"):
            IndexEntry(
                run_id="01KDSG2VDHNK0W4HSCZWJZXWSL",  # 'L' is invalid
                project_path="/path",
                project_name="project",
                feature_description="feature",
                started_at=datetime.now(UTC),
                status="running",
            )

    def test_status_must_be_valid_value(self) -> None:
        """Test that status must be one of the allowed values."""
        # Valid statuses
        for status in ["running", "completed", "failed", "interrupted", "aborted"]:
            entry = IndexEntry(
                run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
                project_path="/path",
                project_name="project",
                feature_description="feature",
                started_at=datetime.now(UTC),
                status=status,
            )
            assert entry.status == status

    def test_invalid_status_raises_error(self) -> None:
        """Test that invalid status raises validation error."""
        with pytest.raises(ValueError):
            IndexEntry(
                run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
                project_path="/path",
                project_name="project",
                feature_description="feature",
                started_at=datetime.now(UTC),
                status="invalid-status",
            )


class TestIndexEntrySerialization:
    """Tests for IndexEntry JSON serialization."""

    def test_serialize_to_json_string(self) -> None:
        """Test serializing IndexEntry to JSON string."""
        entry = IndexEntry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/path/to/project",
            project_name="my-project",
            feature_description="Add feature",
            started_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            status="running",
        )

        json_str = entry.model_dump_json()
        assert '"run_id":"01KDSG2VDHNK0W4HSCZWJZXWSQ"' in json_str
        assert '"project_path":"/path/to/project"' in json_str
        assert '"status":"running"' in json_str

    def test_deserialize_from_json_string(self) -> None:
        """Test deserializing IndexEntry from JSON string."""
        json_str = (
            '{"run_id":"01KDSG2VDHNK0W4HSCZWJZXWSQ",'
            '"project_path":"/path/to/project",'
            '"project_name":"my-project",'
            '"feature_description":"Add feature",'
            '"started_at":"2024-01-15T10:30:00Z",'
            '"completed_at":null,'
            '"status":"running",'
            '"phase_reached":null,'
            '"phases_completed":[]}'
        )

        entry = IndexEntry.model_validate_json(json_str)
        assert entry.run_id == "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        assert entry.project_path == "/path/to/project"
        assert entry.status == "running"

    def test_round_trip_serialization(self) -> None:
        """Test that serialization round-trip preserves all data."""
        original = IndexEntry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/path/to/project",
            project_name="my-project",
            feature_description="Add user authentication",
            started_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            completed_at=datetime(2024, 1, 15, 11, 45, tzinfo=UTC),
            status="completed",
            phase_reached="validate",
            phases_completed=["plan", "build", "validate"],
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        restored = IndexEntry.model_validate_json(json_str)

        # Compare all fields
        assert restored.run_id == original.run_id
        assert restored.project_path == original.project_path
        assert restored.project_name == original.project_name
        assert restored.feature_description == original.feature_description
        assert restored.started_at == original.started_at
        assert restored.completed_at == original.completed_at
        assert restored.status == original.status
        assert restored.phase_reached == original.phase_reached
        assert restored.phases_completed == original.phases_completed

    def test_json_uses_snake_case_keys(self) -> None:
        """Test that JSON output uses snake_case keys (Pydantic default)."""
        entry = IndexEntry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/path",
            project_name="project",
            feature_description="feature",
            started_at=datetime.now(UTC),
            status="running",
            phase_reached="plan",
            phases_completed=["plan"],
        )

        json_str = entry.model_dump_json()
        # Verify snake_case keys
        assert "phase_reached" in json_str
        assert "phases_completed" in json_str
        assert "project_name" in json_str
        assert "feature_description" in json_str


class TestIndexEntryOptionalFields:
    """Tests for optional field handling."""

    def test_completed_at_is_optional(self) -> None:
        """Test that completed_at can be None for running entries."""
        entry = IndexEntry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/path",
            project_name="project",
            feature_description="feature",
            started_at=datetime.now(UTC),
            status="running",
        )

        assert entry.completed_at is None

    def test_phase_reached_is_optional(self) -> None:
        """Test that phase_reached can be None."""
        entry = IndexEntry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/path",
            project_name="project",
            feature_description="feature",
            started_at=datetime.now(UTC),
            status="running",
        )

        assert entry.phase_reached is None

    def test_model_copy_for_immutable_updates(self) -> None:
        """Test using model_copy for immutable updates."""
        original = IndexEntry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/path",
            project_name="project",
            feature_description="feature",
            started_at=datetime.now(UTC),
            status="running",
        )

        # Update using model_copy
        completed_at = datetime.now(UTC)
        updated = original.model_copy(
            update={
                "status": "completed",
                "completed_at": completed_at,
                "phase_reached": "verify",
            }
        )

        # Original unchanged
        assert original.status == "running"
        assert original.completed_at is None

        # Updated has new values
        assert updated.status == "completed"
        assert updated.completed_at == completed_at
        assert updated.phase_reached == "verify"
