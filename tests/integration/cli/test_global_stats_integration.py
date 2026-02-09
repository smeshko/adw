"""Integration tests for `adw global stats` command.

Tests the full flow of statistics gathering from actual index files
and LLM response files.
"""

import json
from datetime import datetime, UTC, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from adw.cli.global_commands import global_app
from adw.core.stats_aggregator import StatsAggregator
from adw.core.index_manager import IndexManager
from adw.core.project_registry import ProjectRegistryManager


runner = CliRunner()


@pytest.fixture
def test_env(tmp_path: Path):
    """Set up test environment with index and run directories."""
    # Set up paths
    adw_home = tmp_path / ".adw"
    adw_home.mkdir()

    index_path = adw_home / "index.jsonl"
    cache_path = adw_home / "stats-cache.json"
    registry_path = adw_home / "projects.yaml"

    yield {
        "tmp_path": tmp_path,
        "adw_home": adw_home,
        "index_path": index_path,
        "cache_path": cache_path,
        "registry_path": registry_path,
    }


def create_index_entry(
    run_id: str,
    project_name: str,
    project_path: str,
    status: str = "completed",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> dict:
    """Create an index entry dict for testing.

    Note: run_id should be a valid 26-character ULID or a short ID
    that will be padded to 26 chars (e.g., "001" -> "001" + "0" * 23).
    """
    if started_at is None:
        started_at = datetime.now(UTC)
    if completed_at is None and status == "completed":
        completed_at = started_at + timedelta(minutes=5)

    # Ensure run_id is a valid 26-character ULID format
    # Pad short IDs for test convenience
    if len(run_id) < 26:
        run_id = run_id + "0" * (26 - len(run_id))

    return {
        "run_id": run_id,
        "project_name": project_name,
        "project_path": project_path,
        "feature_description": f"Test feature for {run_id[:8]}",
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat() if completed_at else None,
        "status": status,
        "phase_reached": "validate" if status == "completed" else "build",
        "phases_completed": ["plan", "build"] if status == "completed" else ["plan"],
    }


def create_llm_response_file(
    run_dir: Path,
    phase: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Create an LLM response file in the run directory."""
    llm_dir = run_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)

    response = {
        "timestamp": datetime.now(UTC).isoformat(),
        "content": "Test response content",
        "phase": phase,
        "tool_calls": [],
        "stats": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": 5000,
        },
    }

    file_name = f"001_{phase}_response.json"
    (llm_dir / file_name).write_text(json.dumps(response))


def _create_mock_aggregator_class(test_env: dict):
    """Create a mock StatsAggregator class that uses test paths.

    This creates a class-like callable that, when instantiated,
    returns a properly configured StatsAggregator instance.
    """

    class MockStatsAggregator:
        """Mock aggregator that uses test environment paths."""

        def __init__(self, **kwargs):
            index_manager = IndexManager(index_path=test_env["index_path"])
            project_registry = ProjectRegistryManager(
                registry_path=test_env["registry_path"]
            )
            self._real = StatsAggregator(
                index_manager=index_manager,
                cache_path=test_env["cache_path"],
                project_registry=project_registry,
                **{k: v for k, v in kwargs.items() if k == "pricing"},
            )

        def get_global_stats(self, **kwargs):
            return self._real.get_global_stats(**kwargs)

        def get_token_usage(self, run_id, project_path):
            return self._real.get_token_usage(run_id, project_path)

        def calculate_cost(self, tokens, model="default"):
            return self._real.calculate_cost(tokens, model)

    return MockStatsAggregator


def register_project(
    test_env: dict, project_path: Path, name: str | None = None
) -> None:
    """Register a project in the test registry."""
    registry = ProjectRegistryManager(registry_path=test_env["registry_path"])
    registry.register(project_path, name=name)


class TestStatsIntegration:
    """Integration tests for stats command."""

    def test_empty_index(self, test_env: dict) -> None:
        """Stats command handles empty index gracefully."""
        # Create empty index file
        test_env["index_path"].write_text("")

        with patch(
            "adw.cli.global_commands.StatsAggregator",
            _create_mock_aggregator_class(test_env),
        ):
            result = runner.invoke(global_app, ["stats"])

        assert result.exit_code == 0
        assert "0" in result.stdout or "no" in result.stdout.lower()

    def test_full_flow_with_runs(self, test_env: dict) -> None:
        """Stats command shows correct statistics for actual runs."""
        project_path = test_env["tmp_path"] / "my-project"
        project_path.mkdir()

        # Register the project
        register_project(test_env, project_path, "my-project")

        # Create index entries
        now = datetime.now(UTC)
        entries = [
            create_index_entry(
                "01ABC001",
                "my-project",
                str(project_path),
                "completed",
                now - timedelta(hours=2),
            ),
            create_index_entry(
                "01ABC002",
                "my-project",
                str(project_path),
                "completed",
                now - timedelta(hours=1),
            ),
            create_index_entry(
                "01ABC003",
                "my-project",
                str(project_path),
                "failed",
                now - timedelta(minutes=30),
            ),
        ]

        # Write index
        with open(test_env["index_path"], "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Create LLM response files for the completed runs (use padded IDs)
        for short_id in ["01ABC001", "01ABC002"]:
            padded_id = short_id + "0" * (26 - len(short_id))
            run_dir = project_path / ".adw" / "runs" / padded_id
            create_llm_response_file(run_dir, "plan", 1000, 500)
            create_llm_response_file(run_dir, "build", 2000, 1000)

        with patch(
            "adw.cli.global_commands.StatsAggregator",
            _create_mock_aggregator_class(test_env),
        ):
            result = runner.invoke(global_app, ["stats"])

        assert result.exit_code == 0
        # Should show 3 total runs
        assert "3" in result.stdout
        # Should show my-project
        assert "my-project" in result.stdout

    def test_project_filter(self, test_env: dict) -> None:
        """Stats --project filters to specific project."""
        project_a = test_env["tmp_path"] / "project-a"
        project_b = test_env["tmp_path"] / "project-b"
        project_a.mkdir()
        project_b.mkdir()

        # Register both projects
        register_project(test_env, project_a, "project-a")
        register_project(test_env, project_b, "project-b")

        now = datetime.now(UTC)
        entries = [
            create_index_entry(
                "01ABC001", "project-a", str(project_a), "completed", now
            ),
            create_index_entry(
                "01ABC002", "project-a", str(project_a), "completed", now
            ),
            create_index_entry(
                "01ABC003", "project-b", str(project_b), "completed", now
            ),
        ]

        with open(test_env["index_path"], "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Filter to project-a only
        with patch(
            "adw.cli.global_commands.StatsAggregator",
            _create_mock_aggregator_class(test_env),
        ):
            result = runner.invoke(global_app, ["stats", "--project", "project-a"])

        assert result.exit_code == 0
        # Should show 2 runs (only project-a)
        assert "2" in result.stdout

    def test_json_output_format(self, test_env: dict) -> None:
        """Stats --format json outputs valid JSON."""
        project_path = test_env["tmp_path"] / "test-project"
        project_path.mkdir()

        # Register the project
        register_project(test_env, project_path, "test-project")

        now = datetime.now(UTC)
        entry = create_index_entry(
            "01ABC001",
            "test-project",
            str(project_path),
            "completed",
            now,
        )

        with open(test_env["index_path"], "w") as f:
            f.write(json.dumps(entry) + "\n")

        with patch(
            "adw.cli.global_commands.StatsAggregator",
            _create_mock_aggregator_class(test_env),
        ):
            result = runner.invoke(global_app, ["stats", "--format", "json"])

        assert result.exit_code == 0

        # Should be valid JSON
        output = json.loads(result.stdout)
        assert "total_runs" in output
        assert output["total_runs"] == 1
        assert "projects" in output

    def test_cache_behavior_fresh(self, test_env: dict) -> None:
        """Stats creates cache on first run."""
        test_env["index_path"].write_text("")

        # Ensure no cache exists
        assert not test_env["cache_path"].exists()

        with patch(
            "adw.cli.global_commands.StatsAggregator",
            _create_mock_aggregator_class(test_env),
        ):
            result = runner.invoke(global_app, ["stats"])

        assert result.exit_code == 0
        # Cache should now exist
        assert test_env["cache_path"].exists()

    def test_cache_behavior_invalidated_by_force(self, test_env: dict) -> None:
        """Stats --force ignores cache."""
        test_env["index_path"].write_text("")

        # Create a cache with fake data
        cache_data = {
            "generated_at": datetime.now(UTC).isoformat(),
            "ttl_seconds": 300,
            "index_mtime": None,
            "project_name": None,
            "since": None,
            "stats": {
                "generated_at": datetime.now(UTC).isoformat(),
                "total_runs": 999999,  # Fake high number
            },
        }

        with open(test_env["cache_path"], "w") as f:
            json.dump(cache_data, f)

        # With force, should recalculate (0 runs from empty index)
        with patch(
            "adw.cli.global_commands.StatsAggregator",
            _create_mock_aggregator_class(test_env),
        ):
            result = runner.invoke(global_app, ["stats", "--format", "json", "--force"])

        output = json.loads(result.stdout)
        assert output["total_runs"] == 0

    def test_missing_llm_files_graceful(self, test_env: dict) -> None:
        """Stats handles missing LLM files gracefully."""
        project_path = test_env["tmp_path"] / "no-llm-project"
        project_path.mkdir()

        # Register the project
        register_project(test_env, project_path, "no-llm-project")

        now = datetime.now(UTC)
        entry = create_index_entry(
            "01ABC001",
            "no-llm-project",
            str(project_path),
            "completed",
            now,
        )

        with open(test_env["index_path"], "w") as f:
            f.write(json.dumps(entry) + "\n")

        # No LLM files created - should still work
        with patch(
            "adw.cli.global_commands.StatsAggregator",
            _create_mock_aggregator_class(test_env),
        ):
            result = runner.invoke(global_app, ["stats", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["total_runs"] == 1
        # Tokens should be 0 since no LLM files
        assert output["total_tokens"]["total"] == 0

    def test_token_aggregation(self, test_env: dict) -> None:
        """Stats correctly aggregates tokens from LLM files."""
        project_path = test_env["tmp_path"] / "token-project"
        project_path.mkdir()

        # Register the project
        register_project(test_env, project_path, "token-project")

        now = datetime.now(UTC)
        # Use a short ID that will be padded to 26 chars
        short_id = "01ABC001"
        padded_id = short_id + "0" * (26 - len(short_id))

        entry = create_index_entry(
            short_id,
            "token-project",
            str(project_path),
            "completed",
            now,
        )

        with open(test_env["index_path"], "w") as f:
            f.write(json.dumps(entry) + "\n")

        # Create LLM files with known token counts (use padded ID for run dir)
        run_dir = project_path / ".adw" / "runs" / padded_id
        create_llm_response_file(run_dir, "plan", 1000, 500)
        create_llm_response_file(run_dir, "build", 2000, 1000)

        with patch(
            "adw.cli.global_commands.StatsAggregator",
            _create_mock_aggregator_class(test_env),
        ):
            result = runner.invoke(global_app, ["stats", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        # Should sum tokens: 1000+2000=3000 input, 500+1000=1500 output
        assert output["total_tokens"]["input"] == 3000
        assert output["total_tokens"]["output"] == 1500
        assert output["total_tokens"]["total"] == 4500

    def test_since_filter(self, test_env: dict) -> None:
        """Stats --since filters by time period."""
        project_path = test_env["tmp_path"] / "time-project"
        project_path.mkdir()

        # Register the project
        register_project(test_env, project_path, "time-project")

        now = datetime.now(UTC)
        entries = [
            # Recent run (within 1 day)
            create_index_entry(
                "01ABC001",
                "time-project",
                str(project_path),
                "completed",
                now - timedelta(hours=2),
            ),
            # Old run (10 days ago)
            create_index_entry(
                "01ABC002",
                "time-project",
                str(project_path),
                "completed",
                now - timedelta(days=10),
            ),
        ]

        with open(test_env["index_path"], "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Filter to last 7 days
        with patch(
            "adw.cli.global_commands.StatsAggregator",
            _create_mock_aggregator_class(test_env),
        ):
            result = runner.invoke(
                global_app, ["stats", "--since", "7d", "--format", "json"]
            )

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        # Should only show 1 run (the recent one)
        assert output["total_runs"] == 1
