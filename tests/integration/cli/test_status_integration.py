"""Integration tests for CLI status command.

Tests the full status command execution including:
- Status of running run
- Status of completed run
- Status of failed run with resume hint (UX-3)
- Output formatting verification
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.models import RunContext

runner = CliRunner()


@pytest.fixture
def mock_runs_dir(tmp_path: Path):
    """Fixture that creates a runs directory and patches get_runs_dir."""
    runs_dir = tmp_path / ".adw" / "runs"
    runs_dir.mkdir(parents=True)

    # Patch in both places where it might be imported
    with (
        patch("adw.cli.status.get_runs_dir", return_value=runs_dir),
        patch("adw.cli.bootstrap.get_runs_dir", return_value=runs_dir),
    ):
        yield runs_dir


def create_test_run_context(
    runs_dir: Path,
    run_id: str,
    status: str = "running",
    current_phase: str = "build",
    phase_history: list[str] | None = None,
    feature: str = "Test feature",
    completed_at: datetime | None = None,
    phase_tokens: dict[str, int] | None = None,
    artifacts: dict[str, list[str]] | None = None,
) -> RunContext:
    """Create a test run directory with context.

    Args:
        runs_dir: Path to .adw/runs directory.
        run_id: ULID for the run.
        status: Run status.
        current_phase: Current phase.
        phase_history: Phases that completed.
        feature: Feature description.
        completed_at: When run completed.
        phase_tokens: Token usage per phase.
        artifacts: Artifacts per phase.

    Returns:
        Created RunContext.
    """
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    context = RunContext(
        run_id=run_id,
        feature_description=feature,
        current_phase=current_phase,
        phase_history=phase_history or [],
        started_at=datetime.now(UTC),
        completed_at=completed_at,
        status=status,
        phase_tokens=phase_tokens or {},
        artifacts=artifacts or {},
    )

    context_path = run_dir / "context.json"
    context_path.write_text(context.model_dump_json(indent=2))

    return context


class TestStatusCommandIntegration:
    """Integration tests for the status command."""

    def test_status_running_run(self, mock_runs_dir: Path) -> None:
        """Test status command shows running run correctly."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="running",
            current_phase="build",
            phase_history=["plan"],
            feature="Add user authentication",
        )

        result = runner.invoke(app, ["status", run_id])

        assert result.exit_code == 0
        assert run_id in result.output
        assert "running" in result.output.lower()
        assert "build" in result.output.lower()

    def test_status_completed_run(self, mock_runs_dir: Path) -> None:
        """Test status command shows completed run with duration."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        started = datetime(2026, 1, 3, 10, 30, 0, tzinfo=UTC)
        completed = datetime(2026, 1, 3, 10, 34, 27, tzinfo=UTC)

        # Create context with specific timestamps
        run_dir = mock_runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        context = RunContext(
            run_id=run_id,
            feature_description="Add feature",
            current_phase="document",
            phase_history=["plan", "build", "validate", "document"],
            started_at=started,
            completed_at=completed,
            status="completed",
            phase_tokens={"plan": 500, "build": 1000},
            artifacts={"plan": ["plan.md"]},
        )
        (run_dir / "context.json").write_text(context.model_dump_json(indent=2))

        result = runner.invoke(app, ["status", run_id])

        assert result.exit_code == 0
        assert run_id in result.output
        assert "completed" in result.output.lower()
        # Should show duration (4m 27s)
        assert "4m 27s" in result.output or "Duration" in result.output

    def test_status_failed_run_shows_resume_hint(self, mock_runs_dir: Path) -> None:
        """Test status of failed run shows resume command (UX-3)."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="failed",
            current_phase="build",
            phase_history=["plan"],
            feature="Test feature",
        )

        result = runner.invoke(app, ["status", run_id])

        assert result.exit_code == 0
        assert run_id in result.output
        assert "failed" in result.output.lower()
        # UX-3: Should show resume command
        assert "adw resume" in result.output
        assert run_id in result.output

    def test_status_without_run_id(self, mock_runs_dir: Path) -> None:
        """Test status without run_id shows most recent run."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="running",
            current_phase="plan",
        )

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert run_id in result.output


class TestStatusOutputFormatting:
    """Integration tests for status output formatting."""

    def test_status_verbose_shows_extra_info(self, mock_runs_dir: Path) -> None:
        """Test verbose mode shows phases, tokens, and artifacts."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="completed",
            current_phase="document",
            phase_history=["plan", "build"],
            phase_tokens={"plan": 500, "build": 1000},
            artifacts={"plan": ["plan.md"]},
            completed_at=datetime.now(UTC),
        )

        result = runner.invoke(app, ["status", run_id, "-v"])

        assert result.exit_code == 0
        # Verbose output should include tokens
        assert "Tokens" in result.output or "1,500" in result.output

    def test_status_json_output(self, mock_runs_dir: Path) -> None:
        """Test JSON output format is valid."""
        import json

        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="running",
            current_phase="build",
        )

        result = runner.invoke(app, ["status", run_id, "--json"])

        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert data["run_id"] == run_id
        assert data["status"] == "running"
        assert "duration_ms" in data
        assert "artifact_count" in data

    def test_status_truncates_long_feature(self, mock_runs_dir: Path) -> None:
        """Test that long feature descriptions are truncated."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        long_feature = "A" * 100
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="running",
            feature=long_feature,
        )

        result = runner.invoke(app, ["status", run_id])

        assert result.exit_code == 0
        # Full feature shouldn't appear, should be truncated with ...
        assert long_feature not in result.output
        assert "..." in result.output


class TestStatusErrorHandling:
    """Integration tests for status error handling."""

    def test_status_nonexistent_run(self, mock_runs_dir: Path) -> None:
        """Test status of non-existent run shows error."""
        result = runner.invoke(app, ["status", "NONEXISTENTRUNID123456"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "RUN_NOT_FOUND" in result.output

    def test_status_corrupted_context(self, mock_runs_dir: Path) -> None:
        """Test status of run with corrupted context shows error."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = mock_runs_dir / run_id
        run_dir.mkdir(parents=True)
        # Write corrupted JSON
        (run_dir / "context.json").write_text("{ invalid json }")

        result = runner.invoke(app, ["status", run_id])

        assert result.exit_code != 0
        assert (
            "corrupted" in result.output.lower()
            or "STATE_CORRUPTED" in result.output
            or "snapshot" in result.output.lower()
        )

    def test_status_no_runs_exist(self, mock_runs_dir: Path) -> None:
        """Test status when no runs exist."""
        # Don't create any runs
        result = runner.invoke(app, ["status"])

        # Should exit gracefully with message
        assert "No runs found" in result.output or result.exit_code == 0
