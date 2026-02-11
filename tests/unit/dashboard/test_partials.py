"""Tests for dashboard partial helpers.

Covers build_cost_strip_context() bar height calculation and formatting.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from adw.dashboard.partials import build_cost_strip_context
from adw.models.stats import GlobalStatistics, TokenUsage


def _mock_stats_aggregator(
    cost_this_week: float = 5.67,
    tokens_this_week: TokenUsage | None = None,
    daily_tokens: list[dict] | None = None,
) -> MagicMock:
    """Build a mock StatsAggregator for cost strip testing."""
    mock = MagicMock()
    stats = GlobalStatistics(
        generated_at=datetime.now(UTC),
        tokens_this_week=tokens_this_week or TokenUsage(input_tokens=900_000, output_tokens=300_000),
        cost_this_week=cost_this_week,
    )
    mock.get_global_stats.return_value = stats

    today = datetime.now(UTC).date()
    if daily_tokens is None:
        daily_tokens = [
            {"date": today - timedelta(days=i), "tokens": 0}
            for i in range(6, -1, -1)
        ]
    mock.get_daily_token_counts.return_value = daily_tokens

    return mock


class TestBuildCostStripContext:
    """Tests for build_cost_strip_context function."""

    def test_returns_cost_display(self) -> None:
        """Returns formatted cost display string."""
        sa = _mock_stats_aggregator(cost_this_week=12.34)
        result = build_cost_strip_context(sa, None)
        assert result["cost_strip_cost_display"] == "$12.34"

    def test_returns_tokens_display(self) -> None:
        """Returns formatted tokens display string."""
        sa = _mock_stats_aggregator(
            tokens_this_week=TokenUsage(input_tokens=1_500_000, output_tokens=500_000),
        )
        result = build_cost_strip_context(sa, None)
        assert result["cost_strip_tokens_display"] == "2M"

    def test_daily_bars_count(self) -> None:
        """Returns correct number of daily bars."""
        today = datetime.now(UTC).date()
        daily = [
            {"date": today - timedelta(days=i), "tokens": 100}
            for i in range(6, -1, -1)
        ]
        sa = _mock_stats_aggregator(daily_tokens=daily)
        result = build_cost_strip_context(sa, None)
        assert len(result["daily_bars"]) == 7

    def test_max_day_gets_100_percent(self) -> None:
        """The day with most tokens gets 100% height."""
        today = datetime.now(UTC).date()
        daily = [{"date": today - timedelta(days=i), "tokens": 0} for i in range(6, -1, -1)]
        daily[-1] = {"date": today, "tokens": 5000}  # Today has max
        sa = _mock_stats_aggregator(daily_tokens=daily)
        result = build_cost_strip_context(sa, None)
        # Last bar (today) should be 100%
        assert result["daily_bars"][-1]["height_pct"] == 100

    def test_proportional_heights(self) -> None:
        """Other days get proportional heights relative to max."""
        today = datetime.now(UTC).date()
        daily = [{"date": today - timedelta(days=i), "tokens": 0} for i in range(6, -1, -1)]
        daily[-1] = {"date": today, "tokens": 1000}  # Max
        daily[-2] = {"date": today - timedelta(days=1), "tokens": 500}  # 50%
        sa = _mock_stats_aggregator(daily_tokens=daily)
        result = build_cost_strip_context(sa, None)
        assert result["daily_bars"][-1]["height_pct"] == 100
        assert result["daily_bars"][-2]["height_pct"] == 50

    def test_all_zeros_returns_zero_heights(self) -> None:
        """All-zero days get 0% height."""
        sa = _mock_stats_aggregator()
        result = build_cost_strip_context(sa, None)
        assert all(bar["height_pct"] == 0 for bar in result["daily_bars"])

    def test_bars_have_date_labels(self) -> None:
        """Each bar has the correct weekday label for its date."""
        from datetime import date

        # Use a known Monday (2026-02-09) so labels are deterministic
        monday = date(2026, 2, 9)
        daily = [
            {"date": monday + timedelta(days=i), "tokens": 0}
            for i in range(7)
        ]
        sa = _mock_stats_aggregator(daily_tokens=daily)
        result = build_cost_strip_context(sa, None)
        expected_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        actual_labels = [bar["date_label"] for bar in result["daily_bars"]]
        assert actual_labels == expected_labels

    def test_project_filter_passed(self) -> None:
        """Project name is passed to stats_aggregator methods."""
        sa = _mock_stats_aggregator()
        build_cost_strip_context(sa, "my-project")
        sa.get_global_stats.assert_called_once_with(project_name="my-project")
        sa.get_daily_token_counts.assert_called_once_with(project_name="my-project")

    def test_cost_format_zero(self) -> None:
        """Zero cost displays as $0.00."""
        sa = _mock_stats_aggregator(cost_this_week=0.0)
        result = build_cost_strip_context(sa, None)
        assert result["cost_strip_cost_display"] == "$0.00"
