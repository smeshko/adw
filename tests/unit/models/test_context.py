"""Tests for context models (RunContext, SessionContext, ProjectContext)."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from adw.models import (
    ProjectContext,
    RunContext,
    SessionContext,
    StateSnapshot,
)


class TestRunContext:
    """Tests for RunContext model."""

    def test_creation_with_valid_data(self) -> None:
        """RunContext creates with valid data."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="plan",
            started_at=datetime.now(),
        )
        assert context.run_id == "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        assert context.feature_description == "Add user authentication"
        assert context.current_phase == "plan"
        assert context.status == "running"
        assert context.phase_history == []
        assert context.artifacts == {}
        assert context.completed_at is None

    def test_creation_with_all_fields(self) -> None:
        """RunContext creates with all optional fields."""
        now = datetime.now()
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add login",
            current_phase="build",
            phase_history=["plan", "code"],
            started_at=now,
            completed_at=now,
            status="completed",
            artifacts={"plan": ["plan.md"], "code": ["src/auth.py"]},
        )
        assert context.phase_history == ["plan", "code"]
        assert context.status == "completed"
        assert context.artifacts["plan"] == ["plan.md"]

    def test_serialization_snake_case(self) -> None:
        """RunContext serializes to snake_case JSON."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime(2024, 1, 15, 10, 30, 0),
        )
        json_str = context.model_dump_json()
        data = json.loads(json_str)

        # Verify snake_case keys
        assert "run_id" in data
        assert "feature_description" in data
        assert "current_phase" in data
        assert "phase_history" in data
        assert "started_at" in data

        # Verify NO camelCase
        assert "runId" not in data
        assert "featureDescription" not in data
        assert "currentPhase" not in data

    def test_immutability_with_model_copy(self) -> None:
        """model_copy creates new instance without modifying original."""
        original = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(),
        )
        original_phase = original.current_phase

        # Create updated copy
        updated = original.model_copy(update={"current_phase": "build"})

        # Original unchanged
        assert original.current_phase == original_phase
        assert original.current_phase == "plan"

        # Updated has new value
        assert updated.current_phase == "build"

        # They are different objects
        assert original is not updated

    def test_invalid_ulid_length(self) -> None:
        """Invalid ULID length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RunContext(
                run_id="short",
                feature_description="Test",
                current_phase="plan",
                started_at=datetime.now(),
            )
        assert "ULID must be 26 characters" in str(exc_info.value)

    def test_invalid_ulid_characters(self) -> None:
        """Invalid ULID characters raise ValidationError."""
        # U is not valid in Crockford Base32 (26 chars with invalid U)
        with pytest.raises(ValidationError) as exc_info:
            RunContext(
                run_id="01KDSG2VDHNK0W4HSCUUUUUUUU",  # 26 chars with U
                feature_description="Test",
                current_phase="plan",
                started_at=datetime.now(),
            )
        assert "Invalid ULID character" in str(exc_info.value)

    def test_required_fields_missing(self) -> None:
        """Missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RunContext(
                run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
                # Missing feature_description, current_phase, started_at
            )  # type: ignore
        errors = exc_info.value.errors()
        missing_fields = {e["loc"][0] for e in errors}
        assert "feature_description" in missing_fields
        assert "current_phase" in missing_fields
        assert "started_at" in missing_fields


class TestTokenAggregation:
    """Tests for token tracking and aggregation in RunContext."""

    def test_phase_tokens_defaults_to_empty(self) -> None:
        """phase_tokens defaults to empty dict."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(),
        )
        assert context.phase_tokens == {}

    def test_phase_tokens_can_be_set(self) -> None:
        """phase_tokens can be set during creation."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(),
            phase_tokens={"plan": 500, "code": 1200},
        )
        assert context.phase_tokens == {"plan": 500, "code": 1200}

    def test_total_tokens_empty(self) -> None:
        """total_tokens is 0 when no phases have tokens."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(),
        )
        assert context.total_tokens == 0

    def test_total_tokens_single_phase(self) -> None:
        """total_tokens equals single phase tokens."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(),
            phase_tokens={"plan": 500},
        )
        assert context.total_tokens == 500

    def test_total_tokens_multiple_phases(self) -> None:
        """total_tokens sums all phase tokens."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="verify",
            started_at=datetime.now(),
            phase_tokens={"plan": 500, "code": 1200, "test": 800, "verify": 300},
        )
        assert context.total_tokens == 2800  # 500 + 1200 + 800 + 300

    def test_total_tokens_after_model_copy(self) -> None:
        """total_tokens recalculates after model_copy update."""
        original = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(),
            phase_tokens={"plan": 500},
        )
        assert original.total_tokens == 500

        # Add more tokens via model_copy
        updated = original.model_copy(
            update={"phase_tokens": {"plan": 500, "code": 1000}}
        )
        assert updated.total_tokens == 1500

        # Original unchanged
        assert original.total_tokens == 500

    def test_phase_tokens_in_serialization(self) -> None:
        """phase_tokens is included in JSON serialization."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(),
            phase_tokens={"plan": 500},
        )
        json_str = context.model_dump_json()
        data = json.loads(json_str)

        assert "phase_tokens" in data
        assert data["phase_tokens"] == {"plan": 500}

    def test_total_tokens_in_serialization(self) -> None:
        """total_tokens computed field is included in JSON serialization."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(),
            phase_tokens={"plan": 500, "code": 300},
        )
        json_str = context.model_dump_json()
        data = json.loads(json_str)

        assert "total_tokens" in data
        assert data["total_tokens"] == 800


class TestSessionContext:
    """Tests for SessionContext model."""

    def test_creation(self) -> None:
        """SessionContext creates correctly."""
        session = SessionContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            current_phase="plan",
        )
        assert session.run_id == "01KDSG2VDHNK0W4HSCZWJZXWSQ"
        assert session.current_phase == "plan"
        assert session.is_resuming is False
        assert session.last_checkpoint is None

    def test_resuming_session(self) -> None:
        """SessionContext tracks resuming state."""
        session = SessionContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            current_phase="build",
            is_resuming=True,
            last_checkpoint="/tmp/checkpoint.json",
        )
        assert session.is_resuming is True
        assert session.last_checkpoint == "/tmp/checkpoint.json"


class TestProjectContext:
    """Tests for ProjectContext model."""

    def test_creation(self) -> None:
        """ProjectContext creates correctly."""
        project = ProjectContext(
            project_root=Path("/tmp/myproject"),
            config_path=Path("/tmp/myproject/adw.yaml"),
            runs_dir=Path("/tmp/myproject/.adw/runs"),
            language="python",
        )
        assert project.project_root == Path("/tmp/myproject")
        assert project.language == "python"
        assert project.framework is None
        assert project.platform == "cli"

    def test_with_framework(self) -> None:
        """ProjectContext with framework set."""
        project = ProjectContext(
            project_root=Path("/tmp/myproject"),
            config_path=Path("/tmp/myproject/adw.yaml"),
            runs_dir=Path("/tmp/myproject/.adw/runs"),
            language="python",
            framework="fastapi",
            platform="api",
        )
        assert project.framework == "fastapi"
        assert project.platform == "api"


class TestStateSnapshot:
    """Tests for StateSnapshot model."""

    def test_creation(self) -> None:
        """StateSnapshot creates correctly."""
        snapshot = StateSnapshot(
            snapshot_id="snap-001",
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            phase="plan",
            timestamp=datetime.now(),
            context_json='{"run_id": "01KDSG2VDHNK0W4HSCZWJZXWSQ"}',
        )
        assert snapshot.snapshot_id == "snap-001"
        assert snapshot.phase == "plan"
        assert snapshot.notes is None

    def test_with_notes(self) -> None:
        """StateSnapshot with notes."""
        snapshot = StateSnapshot(
            snapshot_id="snap-002",
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            phase="code",
            timestamp=datetime.now(),
            context_json="{}",
            notes="Checkpoint before risky operation",
        )
        assert snapshot.notes == "Checkpoint before risky operation"
