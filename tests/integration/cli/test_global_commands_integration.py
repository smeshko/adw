"""Integration tests for global commands CLI.

Tests the full flow of global list command using a real index file
and verifying output format.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.core.index_manager import IndexManager
from adw.models import RunContext

runner = CliRunner()


@pytest.fixture
def temp_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> IndexManager:
    """Create a temporary index for testing.

    Sets up the ADW_TEST_INDEX_PATH environment variable to isolate
    tests from the user's real global index.
    """
    index_path = tmp_path / "test-index.jsonl"
    monkeypatch.setenv("ADW_TEST_INDEX_PATH", str(index_path))
    return IndexManager(index_path=index_path)


def _create_test_context(
    run_id: str,
    feature: str = "Test feature",
    started_at: datetime | None = None,
) -> RunContext:
    """Create a test RunContext with sensible defaults."""
    return RunContext(
        run_id=run_id,
        feature_description=feature,
        current_phase="plan",
        started_at=started_at or datetime.now(UTC),
        status="running",
    )


class TestGlobalListIntegration:
    """Integration tests for adw global list command."""

    def test_list_shows_entries_from_index(self, temp_index: IndexManager) -> None:
        """Global list should show entries from the index file."""
        # Register some test runs
        context1 = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS1", "FeatureAlpha")
        context2 = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS2", "FeatureBeta")

        temp_index.register_run(context1, Path("/projects/alpha"))
        temp_index.register_run(context2, Path("/projects/beta"))

        result = runner.invoke(app, ["global", "list"])

        assert result.exit_code == 0
        # Check for run IDs and project names (columns with no truncation)
        assert "01KDSG2VDHNK0W4HSCZWJZXWS1" in result.output
        assert "01KDSG2VDHNK0W4HSCZWJZXWS2" in result.output
        assert "alpha" in result.output
        assert "beta" in result.output

    def test_list_filters_by_project(self, temp_index: IndexManager) -> None:
        """--project should filter to matching project name."""
        context1 = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS1", "FeatureA")
        context2 = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS2", "FeatureB")

        temp_index.register_run(context1, Path("/projects/my-api"))
        temp_index.register_run(context2, Path("/projects/frontend"))

        result = runner.invoke(app, ["global", "list", "--project", "my-api"])

        assert result.exit_code == 0
        # my-api run should be present, frontend run should not
        assert "01KDSG2VDHNK0W4HSCZWJZXWS1" in result.output
        assert "01KDSG2VDHNK0W4HSCZWJZXWS2" not in result.output

    def test_list_filters_by_status(self, temp_index: IndexManager) -> None:
        """--status should filter to matching status."""
        context1 = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS1", "SuccessRun")
        context2 = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS2", "FailedRun")

        temp_index.register_run(context1, Path("/projects/a"))
        temp_index.register_run(context2, Path("/projects/b"))
        temp_index.update_run(context1.run_id, status="completed")
        temp_index.update_run(context2.run_id, status="failed")

        result = runner.invoke(app, ["global", "list", "--status", "failed"])

        assert result.exit_code == 0
        # Failed run should be present, completed run should not
        assert "01KDSG2VDHNK0W4HSCZWJZXWS2" in result.output
        assert "01KDSG2VDHNK0W4HSCZWJZXWS1" not in result.output

    def test_list_filters_by_since(self, temp_index: IndexManager) -> None:
        """--since should filter to recent entries only."""
        old_time = datetime.now(UTC) - timedelta(days=30)
        recent_time = datetime.now(UTC) - timedelta(hours=1)

        context_old = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS1", "OldFeature", started_at=old_time
        )
        context_recent = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS2", "RecentFeature", started_at=recent_time
        )

        temp_index.register_run(context_old, Path("/projects/a"))
        temp_index.register_run(context_recent, Path("/projects/b"))

        result = runner.invoke(app, ["global", "list", "--since", "7d"])

        assert result.exit_code == 0
        # Recent run should be present, old run should not
        assert "01KDSG2VDHNK0W4HSCZWJZXWS2" in result.output
        assert "01KDSG2VDHNK0W4HSCZWJZXWS1" not in result.output

    def test_list_combined_filters(self, temp_index: IndexManager) -> None:
        """Multiple filters should combine with AND logic."""
        recent_time = datetime.now(UTC) - timedelta(hours=1)

        # Create 4 runs with different combinations
        context1 = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS1", "TargetRun", started_at=recent_time
        )
        context2 = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS2", "WrongProj", started_at=recent_time
        )
        context3 = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS3", "WrongStat", started_at=recent_time
        )
        context4 = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS4",
            "TooOldRun",
            started_at=datetime.now(UTC) - timedelta(days=30),
        )

        temp_index.register_run(context1, Path("/projects/my-api"))
        temp_index.register_run(context2, Path("/projects/other"))
        temp_index.register_run(context3, Path("/projects/my-api"))
        temp_index.register_run(context4, Path("/projects/my-api"))

        temp_index.update_run(context1.run_id, status="failed")
        temp_index.update_run(context2.run_id, status="failed")
        temp_index.update_run(context3.run_id, status="completed")
        temp_index.update_run(context4.run_id, status="failed")

        # Filter: my-api + failed + last 7 days - only context1 matches
        result = runner.invoke(
            app,
            [
                "global",
                "list",
                "--project",
                "my-api",
                "--status",
                "failed",
                "--since",
                "7d",
            ],
        )

        assert result.exit_code == 0
        # Only context1 should match all filters
        assert "01KDSG2VDHNK0W4HSCZWJZXWS1" in result.output
        assert "01KDSG2VDHNK0W4HSCZWJZXWS2" not in result.output
        assert "01KDSG2VDHNK0W4HSCZWJZXWS3" not in result.output
        assert "01KDSG2VDHNK0W4HSCZWJZXWS4" not in result.output

    def test_list_limit_parameter(self, temp_index: IndexManager) -> None:
        """--limit should restrict number of results."""
        # Create 10 entries with single-word features
        for i in range(10):
            context = _create_test_context(
                f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}", f"Feature{i}"
            )
            temp_index.register_run(context, Path(f"/projects/proj{i}"))

        result = runner.invoke(app, ["global", "list", "--limit", "3"])

        assert result.exit_code == 0
        # Count unique run IDs (the first 10 chars are unique timestamp parts)
        # Since we have 3 entries, we expect 3 run IDs
        run_count = result.output.count("01KDSG2VDHNK0W4HSCZWJZXW")
        assert run_count == 3

    def test_list_offset_parameter(self, temp_index: IndexManager) -> None:
        """--offset should skip first N results."""
        # Create 5 entries with distinct times
        for i in range(5):
            context = _create_test_context(
                f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}",
                f"Feature{i}",
                started_at=datetime.now(UTC) - timedelta(hours=i),
            )
            temp_index.register_run(context, Path(f"/projects/proj{i}"))

        # Skip first 2, take 2
        result = runner.invoke(app, ["global", "list", "--offset", "2", "--limit", "2"])

        assert result.exit_code == 0
        # Run IDs 00 and 01 should be skipped (most recent)
        assert "01KDSG2VDHNK0W4HSCZWJZXW00" not in result.output
        assert "01KDSG2VDHNK0W4HSCZWJZXW01" not in result.output
        # Run IDs 02 and 03 should be present
        assert "01KDSG2VDHNK0W4HSCZWJZXW02" in result.output
        assert "01KDSG2VDHNK0W4HSCZWJZXW03" in result.output

    def test_list_json_output(self, temp_index: IndexManager) -> None:
        """--json should output valid JSON array."""
        import json

        context = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS1", "JSONTest")
        temp_index.register_run(context, Path("/projects/test"))
        temp_index.update_run(context.run_id, status="completed")

        result = runner.invoke(app, ["global", "list", "--json"])

        assert result.exit_code == 0
        # Parse the JSON output
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1
        entry = data[0]
        assert entry["run_id"] == "01KDSG2VDHNK0W4HSCZWJZXWS1"
        assert entry["feature"] == "JSONTest"
        assert entry["status"] == "completed"
        assert "project_name" in entry
        assert "duration_seconds" in entry
        assert "phases_completed" in entry  # Consistent with adw list --json

    def test_list_empty_index_shows_message(
        self,
        temp_index: IndexManager,  # noqa: ARG002
    ) -> None:
        """Empty index should show helpful message, not error."""
        # Index is empty (just created fixture)
        result = runner.invoke(app, ["global", "list"])

        assert result.exit_code == 0
        assert "No runs found" in result.output

    def test_list_empty_index_json_returns_empty_array(
        self,
        temp_index: IndexManager,  # noqa: ARG002
    ) -> None:
        """Empty index with --json should return valid empty JSON array."""
        import json

        result = runner.invoke(app, ["global", "list", "--json"])

        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert data == []

    def test_list_empty_filtered_results_shows_filters(
        self, temp_index: IndexManager
    ) -> None:
        """Empty filtered results should show which filters were applied."""
        # Create one entry that won't match the filter
        context = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS1", "Test")
        temp_index.register_run(context, Path("/projects/test"))
        temp_index.update_run(context.run_id, status="completed")

        result = runner.invoke(
            app, ["global", "list", "--project", "nonexistent", "--status", "failed"]
        )

        assert result.exit_code == 0
        assert "No runs found" in result.output
        assert "Filters applied" in result.output
        assert "nonexistent" in result.output
        assert "failed" in result.output

    def test_invalid_status_shows_valid_options(
        self,
        temp_index: IndexManager,  # noqa: ARG002
    ) -> None:
        """Invalid status value should show list of valid options."""
        result = runner.invoke(app, ["global", "list", "--status", "invalid-status"])

        assert result.exit_code == 1
        assert "Invalid status" in result.output
        assert "running" in result.output
        assert "completed" in result.output
        assert "failed" in result.output

    def test_index_with_corrupted_entries_skips_them(
        self, temp_index: IndexManager
    ) -> None:
        """Corrupted index entries should be skipped, not cause crash."""
        # Add a valid entry
        context = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS1", "ValidEntry")
        temp_index.register_run(context, Path("/projects/test"))

        # Manually append corrupted line
        with open(temp_index.index_path, "a") as f:
            f.write("this is not valid json\n")

        result = runner.invoke(app, ["global", "list"])

        assert result.exit_code == 0
        # Valid entry should still be displayed
        assert "01KDSG2VDHNK0W4HSCZWJZXWS1" in result.output
