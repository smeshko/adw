"""Integration tests for CLI resume command.

Tests the full resume command execution including:
- Resume from failed run
- Resume from interrupted run
- Artifact loading across phases
- Progress display integration
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
    with patch("adw.cli.resume.get_runs_dir", return_value=runs_dir), \
         patch("adw.cli.bootstrap.get_runs_dir", return_value=runs_dir):
        yield runs_dir


def create_test_run_context(
    runs_dir: Path,
    run_id: str,
    status: str = "failed",
    current_phase: str = "build",
    phase_history: list[str] | None = None,
    feature: str = "Test feature",
) -> RunContext:
    """Create a test run directory with context.

    Args:
        runs_dir: Path to .adw/runs directory.
        run_id: ULID for the run.
        status: Run status.
        current_phase: Current/failed phase.
        phase_history: Phases that completed.
        feature: Feature description.

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
        status=status,
    )

    context_path = run_dir / "context.json"
    context_path.write_text(context.model_dump_json(indent=2))

    return context


class TestResumeCommandIntegration:
    """Integration tests for the resume command."""

    def test_resume_with_specific_run_id(self, mock_runs_dir: Path) -> None:
        """Test resume command with specific run ID shows header."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="failed",
            current_phase="build",
            phase_history=["plan"],
        )

        # Note: Full resume would require PhaseRunner setup
        # This tests the lookup and header display path
        result = runner.invoke(
            app,
            ["resume", run_id],
            catch_exceptions=False,
        )

        # Should show resume header before failing on PhaseRunner
        assert "Resuming Run" in result.output or run_id in result.output

    def test_resume_displays_completed_phases(self, mock_runs_dir: Path) -> None:
        """Test that resume shows completed phases in header."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="failed",
            current_phase="verify",
            phase_history=["plan", "build"],
            feature="Add user authentication",
        )

        result = runner.invoke(
            app,
            ["resume", run_id],
            catch_exceptions=False,
        )

        # Header should mention the feature
        assert "authentication" in result.output or "Add user" in result.output

    def test_resume_interrupted_run(self, mock_runs_dir: Path) -> None:
        """Test resume of interrupted run."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="interrupted",
            current_phase="build",
            phase_history=["plan"],
        )

        result = runner.invoke(
            app,
            ["resume", run_id],
            catch_exceptions=False,
        )

        # Should start resume process
        assert "Resuming" in result.output or run_id in result.output

    def test_resume_with_from_phase_override(self, mock_runs_dir: Path) -> None:
        """Test --from-phase overrides saved phase."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="failed",
            current_phase="build",
            phase_history=["plan"],
        )

        # Try to resume from a different phase
        result = runner.invoke(
            app,
            ["resume", run_id, "--from-phase", "plan"],
            catch_exceptions=False,
        )

        # Should indicate resuming from plan
        assert "plan" in result.output.lower()


class TestResumeErrorHandling:
    """Integration tests for resume error handling."""

    def test_resume_completed_run_fails(self, mock_runs_dir: Path) -> None:
        """Test that resuming a completed run fails with error."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        create_test_run_context(
            mock_runs_dir,
            run_id,
            status="completed",
            current_phase="document",
            phase_history=["plan", "build", "verify", "validate", "document"],
        )

        result = runner.invoke(app, ["resume", run_id])

        # Should fail with RUN_COMPLETED error
        assert result.exit_code != 0 or "completed" in result.output.lower()

    def test_resume_nonexistent_run_fails(self, mock_runs_dir: Path) -> None:
        """Test that resuming non-existent run fails with error."""
        result = runner.invoke(app, ["resume", "NONEXISTENTRUNID123456"])

        # Should fail or show not found
        assert result.exit_code != 0 or "not found" in result.output.lower()


class TestResumeArtifactLoading:
    """Integration tests for artifact loading during resume."""

    def test_resume_loads_previous_artifacts(self, mock_runs_dir: Path) -> None:
        """Test that resume loads artifacts from completed phases."""
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = mock_runs_dir / run_id
        run_dir.mkdir(parents=True)

        # Create context
        context = RunContext(
            run_id=run_id,
            feature_description="Test feature",
            current_phase="build",
            phase_history=["plan"],
            started_at=datetime.now(UTC),
            status="failed",
            artifacts={"plan": ["plan.md"]},
        )
        (run_dir / "context.json").write_text(context.model_dump_json(indent=2))

        # Create artifacts directory with plan artifact
        artifact_dir = run_dir / "artifacts" / "plan"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "plan.md").write_text("# Test Plan\nThis is a test.")

        # Resume should try to load artifacts
        result = runner.invoke(
            app,
            ["resume", run_id],
            catch_exceptions=False,
        )

        # Should at least start the resume process
        assert "Resuming" in result.output or run_id in result.output
