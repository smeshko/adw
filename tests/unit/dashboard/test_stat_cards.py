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


# ── Task 2: StatsAggregator Trend Computation ─────────────────────


def _make_index_entry(
    run_id: str,
    started_at: datetime,
    status: str = "completed",
    completed_at: datetime | None = None,
    project_path: str = "/projects/test",
    project_name: str = "test",
) -> MagicMock:
    """Build a mock IndexEntry for testing stats aggregation."""
    entry = MagicMock()
    entry.run_id = run_id
    entry.started_at = started_at
    entry.completed_at = completed_at or (started_at + timedelta(minutes=3))
    entry.status = status
    entry.project_path = project_path
    entry.project_name = project_name
    return entry


class TestStatsAggregatorTrendComputation:
    """Tests for StatsAggregator computing previous-week comparison data."""

    def test_previous_week_runs_counted(self) -> None:
        """Runs from 7-14 days ago are counted as previous_week_total_runs."""
        from adw.core.stats_aggregator import StatsAggregator

        now = datetime.now(UTC)
        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []

        entries = [
            # This week (0-7 days ago)
            _make_index_entry("R1", now - timedelta(days=1)),
            _make_index_entry("R2", now - timedelta(days=3)),
            # Previous week (7-14 days ago)
            _make_index_entry("R3", now - timedelta(days=8)),
            _make_index_entry("R4", now - timedelta(days=10)),
            _make_index_entry("R5", now - timedelta(days=12)),
        ]
        mock_im.get_recent_runs.return_value = entries

        aggregator = StatsAggregator(
            index_manager=mock_im,
            project_registry=mock_pr,
        )
        stats = aggregator._collect_statistics(None, None)

        assert stats.previous_week_total_runs == 3
        assert stats.runs_this_week == 2

    def test_previous_week_success_rate(self) -> None:
        """Success rate is computed correctly for previous-week runs."""
        from adw.core.stats_aggregator import StatsAggregator

        now = datetime.now(UTC)
        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []

        entries = [
            # Previous week: 2 completed, 1 failed → 66.7%
            _make_index_entry("R1", now - timedelta(days=8), status="completed"),
            _make_index_entry("R2", now - timedelta(days=9), status="completed"),
            _make_index_entry("R3", now - timedelta(days=10), status="failed",
                              completed_at=now - timedelta(days=10) + timedelta(minutes=1)),
        ]
        mock_im.get_recent_runs.return_value = entries

        aggregator = StatsAggregator(
            index_manager=mock_im,
            project_registry=mock_pr,
        )
        stats = aggregator._collect_statistics(None, None)

        assert abs(stats.previous_week_success_rate - 0.667) < 0.01

    def test_previous_week_average_duration(self) -> None:
        """Average duration is computed for completed runs in previous week."""
        from adw.core.stats_aggregator import StatsAggregator

        now = datetime.now(UTC)
        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []

        eight_days_ago = now - timedelta(days=8)
        nine_days_ago = now - timedelta(days=9)

        entries = [
            _make_index_entry("R1", eight_days_ago, status="completed",
                              completed_at=eight_days_ago + timedelta(minutes=2)),
            _make_index_entry("R2", nine_days_ago, status="completed",
                              completed_at=nine_days_ago + timedelta(minutes=4)),
        ]
        mock_im.get_recent_runs.return_value = entries

        aggregator = StatsAggregator(
            index_manager=mock_im,
            project_registry=mock_pr,
        )
        stats = aggregator._collect_statistics(None, None)

        # Average of 2min (120s=120000ms) and 4min (240s=240000ms) = 180000ms
        assert stats.previous_week_average_duration_ms == 180000

    def test_tokens_this_week_computed(self) -> None:
        """tokens_this_week accumulates tokens from runs in the last 7 days."""
        from adw.core.stats_aggregator import StatsAggregator

        now = datetime.now(UTC)
        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []

        entries = [
            _make_index_entry("R1", now - timedelta(days=1)),  # This week
            _make_index_entry("R2", now - timedelta(days=10)),  # Previous week
        ]
        mock_im.get_recent_runs.return_value = entries

        aggregator = StatsAggregator(
            index_manager=mock_im,
            project_registry=mock_pr,
        )
        # Mock _parse_llm_response_files to return controlled token counts
        call_count = [0]
        def mock_parse(run_dir):
            call_count[0] += 1
            if call_count[0] == 1:  # R1 - this week
                return TokenUsage(input_tokens=1000, output_tokens=500)
            return TokenUsage(input_tokens=2000, output_tokens=800)  # R2 - previous week

        aggregator._parse_llm_response_files = mock_parse
        stats = aggregator._collect_statistics(None, None)

        assert stats.tokens_this_week.input_tokens == 1000
        assert stats.tokens_this_week.output_tokens == 500

    def test_cost_this_week_computed(self) -> None:
        """cost_this_week is computed from this week's tokens."""
        from adw.core.stats_aggregator import StatsAggregator

        now = datetime.now(UTC)
        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []

        entries = [
            _make_index_entry("R1", now - timedelta(days=1)),  # This week
        ]
        mock_im.get_recent_runs.return_value = entries

        aggregator = StatsAggregator(
            index_manager=mock_im,
            project_registry=mock_pr,
        )
        # 1M input at $3/1M + 0.5M output at $15/1M = $3 + $7.5 = $10.5
        aggregator._parse_llm_response_files = lambda _: TokenUsage(
            input_tokens=1_000_000, output_tokens=500_000
        )
        stats = aggregator._collect_statistics(None, None)

        assert stats.cost_this_week == 10.50

    def test_no_previous_week_data(self) -> None:
        """Zero-value previous week stats when no runs in that window."""
        from adw.core.stats_aggregator import StatsAggregator

        now = datetime.now(UTC)
        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []

        entries = [
            _make_index_entry("R1", now - timedelta(days=1)),  # Only this week
        ]
        mock_im.get_recent_runs.return_value = entries

        aggregator = StatsAggregator(
            index_manager=mock_im,
            project_registry=mock_pr,
        )
        aggregator._parse_llm_response_files = lambda _: TokenUsage()
        stats = aggregator._collect_statistics(None, None)

        assert stats.previous_week_total_runs == 0
        assert stats.previous_week_success_rate == 0.0
        assert stats.previous_week_average_duration_ms == 0

    def test_zero_runs_returns_defaults(self) -> None:
        """Zero runs returns all default trend values."""
        from adw.core.stats_aggregator import StatsAggregator

        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []
        mock_im.get_recent_runs.return_value = []

        aggregator = StatsAggregator(
            index_manager=mock_im,
            project_registry=mock_pr,
        )
        stats = aggregator._collect_statistics(None, None)

        assert stats.previous_week_total_runs == 0
        assert stats.previous_week_success_rate == 0.0
        assert stats.previous_week_average_duration_ms == 0
        assert stats.tokens_this_week.total_tokens == 0
        assert stats.cost_this_week == 0.0


# ── Task 4: Stats Partial Route ───────────────────────────────────


class TestStatsPartialRoute:
    """Tests for GET /partials/stats route."""

    def test_returns_200(self) -> None:
        """Stats partial returns HTTP 200."""
        client = _make_client_with_mocks()
        response = client.get("/partials/stats")
        assert response.status_code == 200

    def test_returns_html(self) -> None:
        """Stats partial returns HTML content type."""
        client = _make_client_with_mocks()
        response = client.get("/partials/stats")
        assert "text/html" in response.headers["content-type"]

    def test_contains_five_stat_cards(self) -> None:
        """Stats partial contains 5 stat cards."""
        client = _make_client_with_mocks()
        response = client.get("/partials/stats")
        assert response.text.count("stat-title") == 5
        assert response.text.count("stat-value") == 5

    def test_has_stats_row_id(self) -> None:
        """Stats row has id='stats-row' for OOB swap."""
        client = _make_client_with_mocks()
        response = client.get("/partials/stats")
        assert 'id="stats-row"' in response.text

    def test_has_polling_attributes(self) -> None:
        """Stats row has HTMX polling at 30s interval."""
        client = _make_client_with_mocks()
        response = client.get("/partials/stats")
        assert 'hx-get="/partials/stats"' in response.text
        assert 'hx-trigger="every 30s"' in response.text

    def test_has_outerhtml_swap(self) -> None:
        """Stats row swaps outerHTML on poll."""
        client = _make_client_with_mocks()
        response = client.get("/partials/stats")
        assert 'hx-swap="outerHTML"' in response.text

    def test_has_flex_wrap_layout(self) -> None:
        """Stats row uses flex wrap for responsive layout."""
        client = _make_client_with_mocks()
        response = client.get("/partials/stats")
        assert "flex flex-wrap gap-4" in response.text

    def test_total_runs_displayed(self) -> None:
        """Total runs value is displayed."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(total_runs=142),
        )
        response = client.get("/partials/stats")
        assert "142" in response.text
        assert "Total Runs" in response.text

    def test_success_rate_formatted(self) -> None:
        """Success rate is formatted as percentage with 1 decimal."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(success_rate=0.875),
        )
        response = client.get("/partials/stats")
        assert "87.5%" in response.text
        assert "Success Rate" in response.text

    def test_duration_formatted(self) -> None:
        """Average duration is formatted as Xm Ys."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(average_duration_ms=185000),
        )
        response = client.get("/partials/stats")
        assert "3m 5s" in response.text
        assert "Avg Duration" in response.text

    def test_tokens_abbreviated(self) -> None:
        """Tokens are abbreviated (2.4M, 340K)."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(
                tokens=TokenUsage(input_tokens=1_800_000, output_tokens=600_000),
            ),
        )
        response = client.get("/partials/stats")
        assert "2.4M" in response.text
        assert "Tokens Used" in response.text

    def test_cost_formatted(self) -> None:
        """Cost is formatted as $X.XX."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(estimated_cost=12.45),
        )
        response = client.get("/partials/stats")
        assert "$12.45" in response.text
        assert "Estimated Cost" in response.text

    def test_positive_run_trend(self) -> None:
        """Positive run trend shows green with up arrow."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(
                runs_this_week=42,
                previous_week_total_runs=35,
            ),
        )
        response = client.get("/partials/stats")
        assert "text-success" in response.text
        assert "▲" in response.text or "&#x25B2;" in response.text

    def test_negative_run_trend(self) -> None:
        """Negative run trend shows red with down arrow."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(
                runs_this_week=20,
                previous_week_total_runs=35,
            ),
        )
        response = client.get("/partials/stats")
        assert "text-error" in response.text
        assert "▼" in response.text or "&#x25BC;" in response.text

    def test_neutral_run_trend(self) -> None:
        """Neutral run trend shows default color."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(
                runs_this_week=35,
                previous_week_total_runs=35,
            ),
        )
        response = client.get("/partials/stats")
        assert "No change" in response.text

    def test_project_filter_passed_to_stats(self) -> None:
        """Project filter is passed to stats aggregator."""
        sa = _mock_stats_aggregator()
        client = _make_client_with_mocks(stats_aggregator=sa)
        client.get("/partials/stats?project=myproject")
        sa.get_global_stats.assert_called_once_with(project_name="myproject")

    def test_project_filter_in_polling_url(self) -> None:
        """Polling URL includes project parameter when set."""
        client = _make_client_with_mocks()
        response = client.get("/partials/stats?project=myproject")
        assert 'hx-get="/partials/stats?project=myproject"' in response.text

    def test_no_project_filter(self) -> None:
        """Stats aggregator called with None when no project filter."""
        sa = _mock_stats_aggregator()
        client = _make_client_with_mocks(stats_aggregator=sa)
        client.get("/partials/stats")
        sa.get_global_stats.assert_called_once_with(project_name=None)


# ── Task 5: Stats Row in Overview ─────────────────────────────────


class TestStatsRowInOverview:
    """Tests for stats row inclusion in the overview page."""

    def test_overview_full_page_contains_stats_row(self) -> None:
        """Full-page overview contains the stats row with id='stats-row'."""
        client = _make_client_with_mocks()
        response = client.get("/")
        assert 'id="stats-row"' in response.text

    def test_overview_htmx_partial_contains_stats_row(self) -> None:
        """HTMX partial overview contains the stats row."""
        client = _make_client_with_mocks()
        response = client.get("/", headers={"HX-Request": "true"})
        assert 'id="stats-row"' in response.text

    def test_overview_stats_row_has_stat_cards(self) -> None:
        """Overview stats row contains 5 stat cards."""
        client = _make_client_with_mocks()
        response = client.get("/")
        assert response.text.count("stat-title") == 5

    def test_overview_stats_show_formatted_values(self) -> None:
        """Overview stats show properly formatted values."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(
                total_runs=142,
                success_rate=0.875,
            ),
        )
        response = client.get("/")
        assert "142" in response.text
        assert "87.5%" in response.text
