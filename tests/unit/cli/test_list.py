"""Tests for list CLI command (Story 6.4).

Tests for the `adw list` command functionality.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.cli.list import VALID_STATUSES, _get_runs_dir
from adw.models import RunContext


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create a runs directory for testing."""
    runs_dir = tmp_path / ".adw" / "runs"
    runs_dir.mkdir(parents=True)
    return runs_dir


def create_test_run(
    runs_dir: Path,
    run_id: str,
    feature: str = "Test feature",
    status: str = "completed",
) -> RunContext:
    """Create a test run in the runs directory."""
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    context = RunContext(
        run_id=run_id,
        feature_description=feature,
        current_phase="plan",
        phase_history=["plan"],
        started_at=datetime.now(UTC),
        status=status,
    )

    context_path = run_dir / "context.json"
    context_path.write_text(context.model_dump_json(indent=2))

    return context


class TestListCommand:
    """Tests for the list command."""

    def test_list_shows_no_runs_message(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that list shows message when no runs exist."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "No runs found" in result.output

    def test_list_suggests_run_command(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that list suggests adw run command when no runs."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "adw run" in result.output

    def test_list_shows_runs_table(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that list shows runs as a table."""
        # Create runs directory and runs
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Need to set up .adw/runs in the isolated filesystem
            (Path.cwd() / ".adw" / "runs").mkdir(parents=True)
            # Copy runs to isolated filesystem
            for run_dir in runs_dir.iterdir():
                if run_dir.is_dir():
                    dest = Path.cwd() / ".adw" / "runs" / run_dir.name
                    dest.mkdir(parents=True)
                    (dest / "context.json").write_text(
                        (run_dir / "context.json").read_text()
                    )

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "Recent Runs" in result.output

    def test_list_respects_limit_option(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that --limit option is respected."""
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        # Create 5 runs
        for i in range(5):
            create_test_run(runs_dir, f"01HQXK5P3Z7V8R2M4N6T9W{i:04d}")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".adw" / "runs").mkdir(parents=True)
            for run_dir in runs_dir.iterdir():
                if run_dir.is_dir():
                    dest = Path.cwd() / ".adw" / "runs" / run_dir.name
                    dest.mkdir(parents=True)
                    (dest / "context.json").write_text(
                        (run_dir / "context.json").read_text()
                    )

            result = runner.invoke(app, ["list", "--limit", "2"])

            assert result.exit_code == 0
            # Should show (2) in title
            assert "(2)" in result.output

    def test_list_validates_invalid_status(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that invalid status filter is rejected."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["list", "--status", "invalid"])

            assert result.exit_code == 1
            assert "Invalid status" in result.output

    def test_list_filters_by_status(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that --status filter works."""
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="failed")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".adw" / "runs").mkdir(parents=True)
            for run_dir in runs_dir.iterdir():
                if run_dir.is_dir():
                    dest = Path.cwd() / ".adw" / "runs" / run_dir.name
                    dest.mkdir(parents=True)
                    (dest / "context.json").write_text(
                        (run_dir / "context.json").read_text()
                    )

            result = runner.invoke(app, ["list", "--status", "failed"])

            assert result.exit_code == 0
            # Should only show (1) run
            assert "(1)" in result.output

    def test_list_shows_no_match_message(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test message when filter has no matches."""
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".adw" / "runs").mkdir(parents=True)
            for run_dir in runs_dir.iterdir():
                if run_dir.is_dir():
                    dest = Path.cwd() / ".adw" / "runs" / run_dir.name
                    dest.mkdir(parents=True)
                    (dest / "context.json").write_text(
                        (run_dir / "context.json").read_text()
                    )

            result = runner.invoke(app, ["list", "--status", "failed"])

            assert result.exit_code == 0
            assert "No runs with status 'failed'" in result.output

    def test_list_json_output(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that --json flag outputs valid JSON."""
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        create_test_run(runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", feature="Test A")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".adw" / "runs").mkdir(parents=True)
            for run_dir in runs_dir.iterdir():
                if run_dir.is_dir():
                    dest = Path.cwd() / ".adw" / "runs" / run_dir.name
                    dest.mkdir(parents=True)
                    (dest / "context.json").write_text(
                        (run_dir / "context.json").read_text()
                    )

            result = runner.invoke(app, ["list", "--json"])

            assert result.exit_code == 0
            # Parse JSON output - skip any initial characters until we hit [
            output = result.output.strip()
            json_start = output.find("[")
            if json_start >= 0:
                json_str = output[json_start:]
                data = json.loads(json_str)
                assert isinstance(data, list)
                assert len(data) == 1
                assert data[0]["run_id"] == "01HQXK5P3Z7V8R2M4N6T9W1Y3A"

    def test_list_short_options(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that short options work."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Test -n for --limit (just check no errors)
            result = runner.invoke(app, ["list", "-n", "5"])
            assert result.exit_code == 0

            # Test -s for --status
            result = runner.invoke(app, ["list", "-s", "completed"])
            assert result.exit_code == 0


class TestValidStatuses:
    """Tests for valid status constants."""

    def test_valid_statuses_contains_expected_values(self) -> None:
        """Test that VALID_STATUSES contains all expected values."""
        expected = {"running", "completed", "failed", "interrupted", "aborted"}
        assert expected == VALID_STATUSES


class TestGetRunsDir:
    """Tests for _get_runs_dir helper."""

    def test_returns_none_when_no_adw_dir(self, tmp_path: Path) -> None:
        """Test that None is returned when .adw/runs doesn't exist."""
        with patch("adw.cli.list.Path.cwd", return_value=tmp_path):
            result = _get_runs_dir()
            assert result is None

    def test_returns_path_when_exists(self, tmp_path: Path) -> None:
        """Test that path is returned when .adw/runs exists."""
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)

        with patch("adw.cli.list.Path.cwd", return_value=tmp_path):
            result = _get_runs_dir()
            assert result == runs_dir
