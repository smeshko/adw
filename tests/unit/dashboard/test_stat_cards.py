"""Tests for Story 1.3: Overview Stat Cards & Status Vocabulary.

Covers stat cards partial route, formatting, trend indicators,
status badge rendering, OOB swap, polling, and responsive layout.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from adw.dashboard.server import create_dashboard_app
from adw.models.stats import GlobalStatistics, TokenUsage


# ── Helpers ────────────────────────────────────────────────────────


def _make_client() -> TestClient:
    """Create a TestClient for the dashboard app."""
    return TestClient(create_dashboard_app())


def _mock_index_manager(
    active_count: int = 0,
    last_completed: datetime | None = None,
) -> MagicMock:
    """Build a mock IndexManager with configurable run data."""
    mock = MagicMock()

    running_runs = [MagicMock() for _ in range(active_count)]
    if last_completed:
        recent_entry = MagicMock()
        recent_entry.completed_at = last_completed
        recent_entry.started_at = last_completed - timedelta(minutes=5)
        recent_runs = [recent_entry]
    else:
        recent_runs = []

    def get_recent_side_effect(**kwargs):
        if kwargs.get("status") == "running":
            return running_runs
        return recent_runs

    mock.get_recent_runs.side_effect = get_recent_side_effect
    return mock


def _mock_project_registry(project_names: list[str] | None = None) -> MagicMock:
    """Build a mock ProjectRegistryManager with project list."""
    mock = MagicMock()
    projects = []
    for name in (project_names or []):
        p = MagicMock()
        p.name = name
        projects.append(p)
    mock.get_all.return_value = projects
    return mock


def _mock_stats_aggregator(
    total_runs: int = 142,
    success_rate: float = 0.875,
    average_duration_ms: int = 185000,
    tokens: TokenUsage | None = None,
    estimated_cost: float = 12.45,
    runs_this_week: int = 42,
    previous_week_total_runs: int = 35,
    previous_week_success_rate: float = 0.82,
    previous_week_average_duration_ms: int = 195000,
    tokens_this_week: TokenUsage | None = None,
    cost_this_week: float = 5.67,
) -> MagicMock:
    """Build a mock StatsAggregator returning configurable GlobalStatistics."""
    mock = MagicMock()
    stats = GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=total_runs,
        runs_this_week=runs_this_week,
        runs_today=5,
        completed_runs=int(total_runs * success_rate),
        failed_runs=total_runs - int(total_runs * success_rate),
        success_rate=success_rate,
        average_duration_ms=average_duration_ms,
        tokens=tokens or TokenUsage(input_tokens=1_800_000, output_tokens=600_000),
        estimated_cost=estimated_cost,
        previous_week_total_runs=previous_week_total_runs,
        previous_week_success_rate=previous_week_success_rate,
        previous_week_average_duration_ms=previous_week_average_duration_ms,
        tokens_this_week=tokens_this_week or TokenUsage(input_tokens=900_000, output_tokens=300_000),
        cost_this_week=cost_this_week,
    )
    mock.get_global_stats.return_value = stats
    return mock


def _make_client_with_mocks(
    stats_aggregator: MagicMock | None = None,
    index_manager: MagicMock | None = None,
    project_registry: MagicMock | None = None,
) -> TestClient:
    """Create a TestClient with dependency overrides."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    im = index_manager or _mock_index_manager()
    sa = stats_aggregator or _mock_stats_aggregator()
    pr = project_registry or _mock_project_registry()

    app.dependency_overrides[dependencies.get_index_manager] = lambda: im
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: sa
    app.dependency_overrides[dependencies.get_project_registry] = lambda: pr

    return TestClient(app)


# ── Task 1: GlobalStatistics Model Trend Fields ───────────────────


class TestGlobalStatisticsTrendFields:
    """Tests for new trend comparison fields on GlobalStatistics."""

    def test_previous_week_total_runs_defaults_to_zero(self) -> None:
        """previous_week_total_runs defaults to 0."""
        stats = GlobalStatistics(generated_at=datetime.now(UTC))
        assert stats.previous_week_total_runs == 0

    def test_previous_week_success_rate_defaults_to_zero(self) -> None:
        """previous_week_success_rate defaults to 0.0."""
        stats = GlobalStatistics(generated_at=datetime.now(UTC))
        assert stats.previous_week_success_rate == 0.0

    def test_previous_week_average_duration_ms_defaults_to_zero(self) -> None:
        """previous_week_average_duration_ms defaults to 0."""
        stats = GlobalStatistics(generated_at=datetime.now(UTC))
        assert stats.previous_week_average_duration_ms == 0

    def test_tokens_this_week_defaults_to_empty(self) -> None:
        """tokens_this_week defaults to empty TokenUsage."""
        stats = GlobalStatistics(generated_at=datetime.now(UTC))
        assert stats.tokens_this_week.input_tokens == 0
        assert stats.tokens_this_week.output_tokens == 0

    def test_cost_this_week_defaults_to_zero(self) -> None:
        """cost_this_week defaults to 0.0."""
        stats = GlobalStatistics(generated_at=datetime.now(UTC))
        assert stats.cost_this_week == 0.0

    def test_trend_fields_serialize_correctly(self) -> None:
        """Trend fields are included in model_dump(mode='json')."""
        stats = GlobalStatistics(
            generated_at=datetime.now(UTC),
            previous_week_total_runs=35,
            previous_week_success_rate=0.82,
            previous_week_average_duration_ms=195000,
            tokens_this_week=TokenUsage(input_tokens=500_000, output_tokens=200_000),
            cost_this_week=3.50,
        )
        data = stats.model_dump(mode="json")
        assert data["previous_week_total_runs"] == 35
        assert data["previous_week_success_rate"] == 0.82
        assert data["previous_week_average_duration_ms"] == 195000
        assert data["tokens_this_week"]["input_tokens"] == 500_000
        assert data["cost_this_week"] == 3.50

    def test_trend_fields_deserialize_correctly(self) -> None:
        """Trend fields can be validated from dict."""
        data = {
            "generated_at": datetime.now(UTC).isoformat(),
            "previous_week_total_runs": 28,
            "previous_week_success_rate": 0.9,
            "previous_week_average_duration_ms": 180000,
            "tokens_this_week": {"input_tokens": 400_000, "output_tokens": 150_000},
            "cost_this_week": 2.75,
        }
        stats = GlobalStatistics.model_validate(data)
        assert stats.previous_week_total_runs == 28
        assert stats.previous_week_success_rate == 0.9
        assert stats.tokens_this_week.total_tokens == 550_000
        assert stats.cost_this_week == 2.75
