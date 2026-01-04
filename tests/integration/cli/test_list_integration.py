"""Integration tests for list CLI command (Story 6.4).

These tests verify the list command works correctly with real
file system operations and run data.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.models import RunContext

runner = CliRunner()


@pytest.fixture
def mock_runs_dir(tmp_path: Path):
    """Fixture that creates a runs directory and patches _get_runs_dir."""
    runs_dir = tmp_path / ".adw" / "runs"
    runs_dir.mkdir(parents=True)

    with patch("adw.cli.list._get_runs_dir", return_value=runs_dir):
        yield runs_dir


def create_run(
    runs_dir: Path,
    run_id: str,
    feature: str = "Test feature",
    status: str = "completed",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> RunContext:
    """Create a run with context file in the runs directory."""
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    context = RunContext(
        run_id=run_id,
        feature_description=feature,
        current_phase="plan",
        phase_history=["plan"],
        started_at=started_at or datetime.now(UTC),
        completed_at=completed_at,
        status=status,
    )

    (run_dir / "context.json").write_text(context.model_dump_json(indent=2))
    return context


class TestListWithMultipleRuns:
    """Tests for listing multiple runs."""

    def test_list_with_multiple_runs_shows_all(self, mock_runs_dir: Path) -> None:
        """Test that listing multiple runs shows them all."""
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A")
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B")
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3C")

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "(3)" in result.output

    def test_list_sorting_order(self, mock_runs_dir: Path) -> None:
        """Test that runs are sorted newest first by ULID."""
        # Create runs with specific ULIDs
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y30")  # Oldest
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A")  # Middle
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3Z")  # Newest

        result = runner.invoke(app, ["list", "--json"])

        assert result.exit_code == 0
        # Parse JSON to verify order
        json_start = result.output.find("[")
        data = json.loads(result.output[json_start:])

        # Z > A > 0 in ULID order
        assert data[0]["run_id"] == "01HQXK5P3Z7V8R2M4N6T9W1Y3Z"
        assert data[1]["run_id"] == "01HQXK5P3Z7V8R2M4N6T9W1Y3A"
        assert data[2]["run_id"] == "01HQXK5P3Z7V8R2M4N6T9W1Y30"


class TestListFilterCombinations:
    """Tests for combining filter options."""

    def test_list_with_status_and_limit(self, mock_runs_dir: Path) -> None:
        """Test combining status filter with limit."""
        # Create 5 failed runs and 3 completed runs
        for i in range(5):
            create_run(
                mock_runs_dir,
                f"01HQXK5P3Z7V8R2M4N6T9WFA{i:02d}",
                status="failed",
            )
        for i in range(3):
            create_run(
                mock_runs_dir,
                f"01HQXK5P3Z7V8R2M4N6T9WC0{i:02d}",
                status="completed",
            )

        # Get only 3 failed runs
        result = runner.invoke(app, ["list", "--status", "failed", "--limit", "3"])

        assert result.exit_code == 0
        assert "(3)" in result.output

    def test_list_filters_correctly_with_mixed_statuses(
        self, mock_runs_dir: Path
    ) -> None:
        """Test that status filter works with mixed statuses."""
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3B", status="failed")
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3C", status="running")
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3D", status="interrupted")

        # Test each status filter
        for status in ["completed", "failed", "running", "interrupted"]:
            result = runner.invoke(app, ["list", "--status", status, "--json"])

            assert result.exit_code == 0
            json_start = result.output.find("[")
            data = json.loads(result.output[json_start:])
            assert len(data) == 1
            assert data[0]["status"] == status


class TestListVerifySortingOrder:
    """Tests for verifying correct sorting order."""

    def test_newest_runs_appear_first(self, mock_runs_dir: Path) -> None:
        """Verify newest runs appear at the top."""
        # Create runs in specific ULID order
        create_run(
            mock_runs_dir,
            "01HQXK5P3Z7V8R2M4N6T9W0000",
            feature="Oldest run",
        )
        create_run(
            mock_runs_dir,
            "01HQXK5P3Z7V8R2M4N6T9WFFFF",
            feature="Newest run",
        )
        create_run(
            mock_runs_dir,
            "01HQXK5P3Z7V8R2M4N6T9W5555",
            feature="Middle run",
        )

        result = runner.invoke(app, ["list", "--json"])

        assert result.exit_code == 0
        json_start = result.output.find("[")
        data = json.loads(result.output[json_start:])

        # Verify order
        assert data[0]["feature"] == "Newest run"
        assert data[1]["feature"] == "Middle run"
        assert data[2]["feature"] == "Oldest run"


class TestListJsonOutput:
    """Tests for JSON output format."""

    def test_json_output_structure(self, mock_runs_dir: Path) -> None:
        """Verify JSON output has correct structure."""
        started = datetime.now(UTC)
        completed = started + timedelta(hours=1)

        create_run(
            mock_runs_dir,
            "01HQXK5P3Z7V8R2M4N6T9W1Y3A",
            feature="Add authentication",
            status="completed",
            started_at=started,
            completed_at=completed,
        )

        result = runner.invoke(app, ["list", "--json"])

        assert result.exit_code == 0
        json_start = result.output.find("[")
        data = json.loads(result.output[json_start:])

        assert len(data) == 1
        run = data[0]

        # Verify all expected fields are present
        assert "run_id" in run
        assert "feature" in run
        assert "status" in run
        assert "started_at" in run
        assert "completed_at" in run

        # Verify values
        assert run["run_id"] == "01HQXK5P3Z7V8R2M4N6T9W1Y3A"
        assert run["feature"] == "Add authentication"
        assert run["status"] == "completed"

    def test_json_output_with_null_completed_at(self, mock_runs_dir: Path) -> None:
        """Verify JSON output handles running runs (no completed_at)."""
        create_run(
            mock_runs_dir,
            "01HQXK5P3Z7V8R2M4N6T9W1Y3A",
            status="running",
        )

        result = runner.invoke(app, ["list", "--json"])

        assert result.exit_code == 0
        json_start = result.output.find("[")
        data = json.loads(result.output[json_start:])

        assert data[0]["completed_at"] is None


class TestListEmptyStates:
    """Tests for empty state handling."""

    def test_empty_runs_directory(self, mock_runs_dir: Path) -> None:
        """Test message when runs directory is empty."""
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No runs found" in result.output

    def test_no_adw_directory(self, tmp_path: Path) -> None:
        """Test message when .adw directory doesn't exist and global index empty."""
        # Patch to return None (no runs dir) and mock global index as empty
        with (
            patch("adw.cli.list._get_runs_dir", return_value=None),
            patch("adw.cli.list.IndexManager") as mock_index,
        ):
            mock_index.return_value.get_recent_runs.return_value = []
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "No runs found" in result.output

    def test_filter_with_no_matches(self, mock_runs_dir: Path) -> None:
        """Test message when filter returns no results."""
        create_run(mock_runs_dir, "01HQXK5P3Z7V8R2M4N6T9W1Y3A", status="completed")

        result = runner.invoke(app, ["list", "--status", "failed"])

        assert result.exit_code == 0
        assert "No runs with status 'failed'" in result.output
