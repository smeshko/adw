"""Tests for phase models (PhaseStatus, PhaseResult, Artifact)."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from adw.models import (
    Artifact,
    ArtifactType,
    PhaseResult,
    PhaseStatus,
)
from adw.models.llm import ToolCall


class TestPhaseStatus:
    """Tests for PhaseStatus enum."""

    def test_all_status_values(self) -> None:
        """PhaseStatus has all expected values."""
        assert PhaseStatus.PENDING.value == "pending"
        assert PhaseStatus.RUNNING.value == "running"
        assert PhaseStatus.COMPLETED.value == "completed"
        assert PhaseStatus.FAILED.value == "failed"

    def test_status_count(self) -> None:
        """PhaseStatus has exactly 4 values."""
        assert len(list(PhaseStatus)) == 4

    def test_string_comparison(self) -> None:
        """PhaseStatus compares to strings."""
        assert PhaseStatus.PENDING == "pending"
        assert PhaseStatus.COMPLETED == "completed"


class TestPhaseResult:
    """Tests for PhaseResult model."""

    def test_creation_with_all_status_values(self) -> None:
        """PhaseResult accepts all PhaseStatus values."""
        for status in PhaseStatus:
            result = PhaseResult(
                phase="test",
                status=status,
                started_at=datetime.now(),
            )
            assert result.status == status

    def test_creation_minimal(self) -> None:
        """PhaseResult creates with minimal required fields."""
        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.PENDING,
            started_at=datetime.now(),
        )
        assert result.phase == "plan"
        assert result.status == PhaseStatus.PENDING
        assert result.completed_at is None
        assert result.artifacts == []
        assert result.error is None
        assert result.duration_ms is None

    def test_completed_phase_with_artifacts(self) -> None:
        """PhaseResult tracks artifacts for completed phase."""
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

    def test_status_from_string(self) -> None:
        """PhaseResult accepts status as string."""
        result = PhaseResult(
            phase="plan",
            status="completed",  # type: ignore - testing string coercion
            started_at=datetime.now(),
        )
        assert result.status == PhaseStatus.COMPLETED

    def test_invalid_status_string(self) -> None:
        """Invalid status string raises ValidationError."""
        with pytest.raises(ValidationError):
            PhaseResult(
                phase="plan",
                status="invalid_status",  # type: ignore
                started_at=datetime.now(),
            )


class TestPhaseResultTokenTracking:
    """Tests for token tracking in PhaseResult."""

    def test_tokens_used_defaults_to_zero(self) -> None:
        """tokens_used defaults to 0."""
        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(),
        )
        assert result.tokens_used == 0

    def test_tokens_used_can_be_set(self) -> None:
        """tokens_used can be set during creation."""
        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(),
            tokens_used=500,
        )
        assert result.tokens_used == 500

    def test_tool_calls_defaults_to_empty_list(self) -> None:
        """tool_calls defaults to empty list."""
        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(),
        )
        assert result.tool_calls == []

    def test_tool_calls_can_be_set(self) -> None:
        """tool_calls can be set during creation."""
        tool_calls = [
            ToolCall(tool_name="read_file", arguments={"path": "/src/main.py"}),
            ToolCall(tool_name="write_file", arguments={"path": "/src/new.py"}),
        ]
        result = PhaseResult(
            phase="code",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(),
            tool_calls=tool_calls,
        )
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].tool_name == "read_file"
        assert result.tool_calls[1].tool_name == "write_file"

    def test_complete_phase_with_token_data(self) -> None:
        """PhaseResult tracks all token-related data."""
        start = datetime.now()
        end = start + timedelta(seconds=30)
        tool_calls = [
            ToolCall(
                tool_name="read_file",
                arguments={"path": "/src/main.py"},
                result_summary="File read successfully",
            ),
        ]

        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=start,
            completed_at=end,
            artifacts=["plan.md"],
            tokens_used=500,
            tool_calls=tool_calls,
        )

        assert result.phase == "plan"
        assert result.status == PhaseStatus.COMPLETED
        assert result.artifacts == ["plan.md"]
        assert result.tokens_used == 500
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].result_summary == "File read successfully"
        assert result.duration_ms == 30000

    def test_tokens_and_tools_in_serialization(self) -> None:
        """tokens_used and tool_calls are included in JSON serialization."""
        import json

        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=datetime.now(),
            tokens_used=500,
            tool_calls=[
                ToolCall(tool_name="read_file", arguments={"path": "/test.py"})
            ],
        )
        json_str = result.model_dump_json()
        data = json.loads(json_str)

        assert "tokens_used" in data
        assert data["tokens_used"] == 500
        assert "tool_calls" in data
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["tool_name"] == "read_file"


class TestArtifactType:
    """Tests for ArtifactType enum."""

    def test_all_artifact_types(self) -> None:
        """ArtifactType has all expected values."""
        expected = ["plan", "code", "test", "log", "evidence", "config", "other"]
        actual = [t.value for t in ArtifactType]
        assert sorted(actual) == sorted(expected)

    def test_type_count(self) -> None:
        """ArtifactType has expected count."""
        assert len(list(ArtifactType)) == 7


class TestArtifact:
    """Tests for Artifact model."""

    def test_creation(self) -> None:
        """Artifact creates correctly."""
        artifact = Artifact(
            path="outputs/plan.md",
            artifact_type=ArtifactType.PLAN,
            phase="plan",
            created_at=datetime.now(),
        )
        assert artifact.path == "outputs/plan.md"
        assert artifact.artifact_type == ArtifactType.PLAN
        assert artifact.phase == "plan"
        assert artifact.size_bytes is None
        assert artifact.description is None

    def test_with_all_fields(self) -> None:
        """Artifact creates with all optional fields."""
        artifact = Artifact(
            path="logs/phase.log",
            artifact_type=ArtifactType.LOG,
            phase="build",
            created_at=datetime.now(),
            size_bytes=2048,
            description="Build phase log output",
        )
        assert artifact.size_bytes == 2048
        assert artifact.description == "Build phase log output"

    def test_all_artifact_types_valid(self) -> None:
        """Artifact accepts all ArtifactType values."""
        for atype in ArtifactType:
            artifact = Artifact(
                path=f"test/{atype.value}.txt",
                artifact_type=atype,
                phase="test",
                created_at=datetime.now(),
            )
            assert artifact.artifact_type == atype

    def test_type_from_string(self) -> None:
        """Artifact accepts type as string."""
        artifact = Artifact(
            path="test.py",
            artifact_type="code",  # type: ignore - testing string coercion
            phase="code",
            created_at=datetime.now(),
        )
        assert artifact.artifact_type == ArtifactType.CODE
