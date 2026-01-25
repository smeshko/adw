"""Unit tests for `adw global stats` command.

Tests for the stats command in global_commands.py.
"""

import json
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from adw.cli.global_commands import global_app
from adw.models.stats import GlobalStatistics, ProjectStatistics, TokenUsage


runner = CliRunner()


@pytest.fixture
def mock_stats() -> GlobalStatistics:
    """Create mock GlobalStatistics for testing."""
    return GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=1247,
        runs_this_week=89,
        runs_today=12,
        completed_runs=1175,
        failed_runs=72,
        success_rate=0.943,
        average_duration_ms=263000,
        tokens=TokenUsage(input_tokens=2_400_000, output_tokens=148_000),
        estimated_cost=47.82,
        projects=[
            ProjectStatistics(
                name="adw-final",
                path="/path/to/adw",
                total_runs=423,
                completed_runs=407,
                failed_runs=16,
                success_rate=0.962,
                tokens=TokenUsage(input_tokens=892_000, output_tokens=48_000),
                estimated_cost=18.24,
            ),
            ProjectStatistics(
                name="my-api",
                path="/path/to/my-api",
                total_runs=512,
                completed_runs=480,
                failed_runs=32,
                success_rate=0.938,
                tokens=TokenUsage(input_tokens=1_100_000, output_tokens=80_000),
                estimated_cost=21.45,
            ),
        ],
    )


class TestStatsCommand:
    """Tests for stats command."""

    def test_stats_command_exists(self) -> None:
        """stats command is registered on global_app."""
        result = runner.invoke(global_app, ["stats", "--help"])
        assert result.exit_code == 0
        assert "statistics" in result.stdout.lower() or "stats" in result.stdout.lower()

    def test_stats_default_output(self, mock_stats: GlobalStatistics) -> None:
        """stats command displays table output by default."""
        with patch(
            "adw.cli.global_commands.StatsAggregator"
        ) as mock_aggregator_class:
            mock_aggregator = MagicMock()
            mock_aggregator.get_global_stats.return_value = mock_stats
            mock_aggregator_class.return_value = mock_aggregator

            result = runner.invoke(global_app, ["stats"])

            assert result.exit_code == 0
            # Check for key stats in output
            assert "1,247" in result.stdout or "1247" in result.stdout
            mock_aggregator.get_global_stats.assert_called_once()

    def test_stats_project_filter(self, mock_stats: GlobalStatistics) -> None:
        """stats --project filters to specific project."""
        with patch(
            "adw.cli.global_commands.StatsAggregator"
        ) as mock_aggregator_class:
            mock_aggregator = MagicMock()
            mock_aggregator.get_global_stats.return_value = mock_stats
            mock_aggregator_class.return_value = mock_aggregator

            result = runner.invoke(global_app, ["stats", "--project", "my-api"])

            assert result.exit_code == 0
            mock_aggregator.get_global_stats.assert_called_once_with(
                project_name="my-api",
                since=None,
                force_refresh=False,
            )

    def test_stats_force_flag(self, mock_stats: GlobalStatistics) -> None:
        """stats --force bypasses cache."""
        with patch(
            "adw.cli.global_commands.StatsAggregator"
        ) as mock_aggregator_class:
            mock_aggregator = MagicMock()
            mock_aggregator.get_global_stats.return_value = mock_stats
            mock_aggregator_class.return_value = mock_aggregator

            result = runner.invoke(global_app, ["stats", "--force"])

            assert result.exit_code == 0
            mock_aggregator.get_global_stats.assert_called_once_with(
                project_name=None,
                since=None,
                force_refresh=True,
            )

    def test_stats_since_filter(self, mock_stats: GlobalStatistics) -> None:
        """stats --since filters by time period."""
        with patch(
            "adw.cli.global_commands.StatsAggregator"
        ) as mock_aggregator_class:
            mock_aggregator = MagicMock()
            mock_aggregator.get_global_stats.return_value = mock_stats
            mock_aggregator_class.return_value = mock_aggregator

            result = runner.invoke(global_app, ["stats", "--since", "7d"])

            assert result.exit_code == 0
            # Verify since parameter was passed (datetime object)
            call_args = mock_aggregator.get_global_stats.call_args
            assert call_args.kwargs["since"] is not None

    def test_stats_invalid_since_format(self) -> None:
        """stats command rejects invalid --since format."""
        result = runner.invoke(global_app, ["stats", "--since", "invalid"])

        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_stats_json_format(self, mock_stats: GlobalStatistics) -> None:
        """stats --format json outputs JSON."""
        with patch(
            "adw.cli.global_commands.StatsAggregator"
        ) as mock_aggregator_class:
            mock_aggregator = MagicMock()
            mock_aggregator.get_global_stats.return_value = mock_stats
            mock_aggregator_class.return_value = mock_aggregator

            result = runner.invoke(global_app, ["stats", "--format", "json"])

            assert result.exit_code == 0
            # Output should be valid JSON
            output = json.loads(result.stdout)
            assert "total_runs" in output
            assert output["total_runs"] == 1247

    def test_stats_json_includes_all_fields(self, mock_stats: GlobalStatistics) -> None:
        """JSON output includes all expected fields."""
        with patch(
            "adw.cli.global_commands.StatsAggregator"
        ) as mock_aggregator_class:
            mock_aggregator = MagicMock()
            mock_aggregator.get_global_stats.return_value = mock_stats
            mock_aggregator_class.return_value = mock_aggregator

            result = runner.invoke(global_app, ["stats", "--format", "json"])

            output = json.loads(result.stdout)
            assert "generated_at" in output
            assert "total_runs" in output
            assert "runs_this_week" in output
            assert "runs_today" in output
            assert "success_rate" in output
            assert "average_duration_ms" in output
            assert "total_tokens" in output
            assert "estimated_cost" in output
            assert "projects" in output

    def test_stats_empty_results(self) -> None:
        """stats command handles empty statistics gracefully."""
        empty_stats = GlobalStatistics(generated_at=datetime.now(UTC))

        with patch(
            "adw.cli.global_commands.StatsAggregator"
        ) as mock_aggregator_class:
            mock_aggregator = MagicMock()
            mock_aggregator.get_global_stats.return_value = empty_stats
            mock_aggregator_class.return_value = mock_aggregator

            result = runner.invoke(global_app, ["stats"])

            assert result.exit_code == 0
            # Should show 0 runs or "no statistics"
            assert "0" in result.stdout or "no" in result.stdout.lower()

    def test_stats_combined_filters(self, mock_stats: GlobalStatistics) -> None:
        """stats command accepts multiple filters together."""
        with patch(
            "adw.cli.global_commands.StatsAggregator"
        ) as mock_aggregator_class:
            mock_aggregator = MagicMock()
            mock_aggregator.get_global_stats.return_value = mock_stats
            mock_aggregator_class.return_value = mock_aggregator

            result = runner.invoke(
                global_app,
                ["stats", "--project", "my-api", "--since", "30d", "--force"],
            )

            assert result.exit_code == 0
            call_args = mock_aggregator.get_global_stats.call_args
            assert call_args.kwargs["project_name"] == "my-api"
            assert call_args.kwargs["since"] is not None
            assert call_args.kwargs["force_refresh"] is True


class TestStatsFormatters:
    """Tests for stats formatting functions."""

    def test_format_tokens_thousands(self) -> None:
        """_format_tokens formats thousands correctly."""
        from adw.cli.global_commands import _format_tokens

        assert _format_tokens(1234) == "1.2K"
        assert _format_tokens(45678) == "45.7K"
        assert _format_tokens(999) == "999"

    def test_format_tokens_millions(self) -> None:
        """_format_tokens formats millions correctly."""
        from adw.cli.global_commands import _format_tokens

        assert _format_tokens(1_234_567) == "1.2M"
        assert _format_tokens(12_345_678) == "12.3M"

    def test_format_cost(self) -> None:
        """_format_cost formats currency correctly."""
        from adw.cli.global_commands import _format_cost

        assert _format_cost(47.82) == "$47.82"
        assert _format_cost(0.05) == "$0.05"
        assert _format_cost(0) == "$0.00"

    def test_format_cost_large_amounts(self) -> None:
        """_format_cost handles large amounts with comma."""
        from adw.cli.global_commands import _format_cost

        assert _format_cost(1234.56) == "$1,234.56"
        assert _format_cost(12345.67) == "$12,345.67"

    def test_format_duration_ms(self) -> None:
        """_format_duration_ms formats durations correctly."""
        from adw.cli.global_commands import _format_duration_ms

        assert _format_duration_ms(45000) == "45s"
        assert _format_duration_ms(125000) == "2m 5s"
        assert _format_duration_ms(3725000) == "1h 2m"

    def test_format_rate(self) -> None:
        """_format_rate formats percentages correctly."""
        from adw.cli.global_commands import _format_rate

        assert _format_rate(0.943) == "94.3%"
        assert _format_rate(1.0) == "100.0%"
        assert _format_rate(0) == "0.0%"
