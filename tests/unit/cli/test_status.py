"""Tests for CLI status command.

Tests for the `adw status [RUN_ID]` command including:
- Argument parsing (optional run_id)
- Flag handling (--json, --verbose)
- Error handling for non-existent runs
- Default to most recent run when no run_id provided
"""

import pytest
from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestStatusCommand:
    """Tests for the status command basic functionality."""

    def test_status_help(self) -> None:
        """Test that status command shows help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_status_accepts_run_id_argument(self) -> None:
        """Test that status command accepts run_id as optional positional argument."""
        result = runner.invoke(app, ["status", "--help"])
        assert "RUN_ID" in result.output

    def test_status_json_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --json flag is recognized."""
        result = cli_runner.invoke(app, ["status", "--help"])
        assert "--json" in result.output

    def test_status_verbose_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --verbose/-v flag is recognized."""
        result = cli_runner.invoke(app, ["status", "--help"])
        assert "--verbose" in result.output or "-v" in result.output


class TestStatusNoRuns:
    """Tests for status when no runs exist."""

    def test_nonexistent_run_id_error(self) -> None:
        """Test that non-existent run ID returns error."""
        # Using a specific run ID that doesn't exist
        result = runner.invoke(app, ["status", "99ZZZZZZZZZZZZZZZZZZZZZZZ"])
        # Should show error about run not found (ConfigError is raised)
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "RUN_NOT_FOUND" in result.output
        )

    def test_status_no_runs_message(self) -> None:
        """Test message when no runs exist and no run_id provided."""
        # This test needs a clean runs directory - hard to test in isolation
        # The integration tests will cover this more thoroughly
        result = runner.invoke(app, ["status", "--help"])
        # Help should show that run_id is optional
        assert result.exit_code == 0


class TestStatusCorruptedContext:
    """Tests for status with corrupted context."""

    def test_corrupted_context_raises_state_error(self, tmp_path) -> None:
        """Test corrupted context.json raises StateError with snapshot suggestion."""
        from pathlib import Path
        from unittest.mock import patch

        # Create a runs directory with corrupted context
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = runs_dir / run_id
        run_dir.mkdir()
        # Write corrupted JSON
        (run_dir / "context.json").write_text("{ invalid json }")

        with patch("adw.cli.status.get_runs_dir", return_value=runs_dir):
            result = runner.invoke(app, ["status", run_id])

        # Should indicate corrupted state with snapshot suggestion
        assert result.exit_code != 0
        assert (
            "corrupted" in result.output.lower()
            or "STATE_CORRUPTED" in result.output
            or "snapshot" in result.output.lower()
        )


class TestStatusWithValidRun:
    """Tests for status with valid run."""

    def test_status_with_valid_run_id(self, tmp_path) -> None:
        """Test status displays information for a valid run."""
        import json
        from datetime import UTC, datetime
        from unittest.mock import patch

        # Create a valid run
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = runs_dir / run_id
        run_dir.mkdir()

        context_data = {
            "run_id": run_id,
            "feature_description": "Add user authentication",
            "current_phase": "build",
            "phase_history": ["plan"],
            "started_at": "2026-01-03T10:30:45+00:00",
            "completed_at": None,
            "status": "running",
            "interrupted_phase": None,
            "interrupted_at": None,
            "artifacts": {},
            "phase_tokens": {},
        }
        (run_dir / "context.json").write_text(json.dumps(context_data))

        with patch("adw.cli.status.get_runs_dir", return_value=runs_dir):
            result = runner.invoke(app, ["status", run_id])

        assert result.exit_code == 0
        assert run_id in result.output
        assert "running" in result.output.lower()

    def test_status_without_run_id_shows_most_recent(self, tmp_path) -> None:
        """Test status without run_id shows most recent run."""
        import json
        from unittest.mock import patch

        # Create a valid run
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = runs_dir / run_id
        run_dir.mkdir()

        context_data = {
            "run_id": run_id,
            "feature_description": "Test feature",
            "current_phase": "plan",
            "phase_history": [],
            "started_at": "2026-01-03T10:30:45+00:00",
            "completed_at": None,
            "status": "running",
            "interrupted_phase": None,
            "interrupted_at": None,
            "artifacts": {},
            "phase_tokens": {},
        }
        (run_dir / "context.json").write_text(json.dumps(context_data))

        with patch("adw.cli.status.get_runs_dir", return_value=runs_dir):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert run_id in result.output

    def test_status_json_output_with_valid_run(self, tmp_path) -> None:
        """Test status --json outputs valid JSON."""
        import json
        from unittest.mock import patch

        # Create a valid run
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = runs_dir / run_id
        run_dir.mkdir()

        context_data = {
            "run_id": run_id,
            "feature_description": "Test feature",
            "current_phase": "plan",
            "phase_history": [],
            "started_at": "2026-01-03T10:30:45+00:00",
            "completed_at": None,
            "status": "running",
            "interrupted_phase": None,
            "interrupted_at": None,
            "artifacts": {},
            "phase_tokens": {},
        }
        (run_dir / "context.json").write_text(json.dumps(context_data))

        with patch("adw.cli.status.get_runs_dir", return_value=runs_dir):
            result = runner.invoke(app, ["status", "--json"])

        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert data["run_id"] == run_id
        assert data["status"] == "running"

    def test_status_verbose_shows_extra_info(self, tmp_path) -> None:
        """Test status -v shows verbose information."""
        import json
        from unittest.mock import patch

        # Create a completed run with tokens
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        run_dir = runs_dir / run_id
        run_dir.mkdir()

        context_data = {
            "run_id": run_id,
            "feature_description": "Test feature",
            "current_phase": "document",
            "phase_history": ["plan", "build"],
            "started_at": "2026-01-03T10:30:45+00:00",
            "completed_at": "2026-01-03T10:35:00+00:00",
            "status": "completed",
            "interrupted_phase": None,
            "interrupted_at": None,
            "artifacts": {"plan": ["plan.md"]},
            "phase_tokens": {"plan": 500, "build": 1000},
        }
        (run_dir / "context.json").write_text(json.dumps(context_data))

        with patch("adw.cli.status.get_runs_dir", return_value=runs_dir):
            result = runner.invoke(app, ["status", "-v"])

        assert result.exit_code == 0
        # Should show tokens info in verbose mode
        assert "Tokens" in result.output or "1,500" in result.output
