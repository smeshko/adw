"""Tests for analytics page route and build_analytics_context helper.

Covers:
- Analytics route with range query parameter and HTMX dual-response pattern
- build_analytics_context delta calculations for all 4 stat cards
- Time range tab rendering and active state
- Empty state for periods with no data
- Project filter preservation across range changes
- URL bookmarkability with range param
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from adw.dashboard.partials import build_analytics_context
from adw.dashboard.server import create_dashboard_app
from adw.models.stats import GlobalStatistics, TokenUsage


# ── Helpers ────────────────────────────────────────────────────────


def _mock_stats_aggregator_for_analytics(
    *,
    current_total_runs: int = 50,
    current_tokens: TokenUsage | None = None,
    current_cost: float = 10.50,
    prev_total_runs: int = 80,
    prev_tokens: TokenUsage | None = None,
    prev_cost: float = 18.00,
) -> MagicMock:
    """Build a mock StatsAggregator for analytics testing.

    When called with since=now-N days, returns current_* stats.
    When called with since=now-2N days, returns combined (prev + current) stats.
    """
    mock = MagicMock()

    cur_tok = current_tokens or TokenUsage(
        input_tokens=1_500_000, output_tokens=500_000,
    )
    prev_tok = prev_tokens or TokenUsage(
        input_tokens=2_500_000, output_tokens=1_000_000,
    )

    current_stats = GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=current_total_runs,
        tokens=cur_tok,
        estimated_cost=current_cost,
    )

    # Combined stats = current + previous period
    combined_stats = GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=current_total_runs + prev_total_runs,
        tokens=TokenUsage(
            input_tokens=cur_tok.input_tokens + prev_tok.input_tokens,
            output_tokens=cur_tok.output_tokens + prev_tok.output_tokens,
        ),
        estimated_cost=current_cost + prev_cost,
    )

    def get_global_stats_side_effect(**kwargs):
        since = kwargs.get("since")
        if since is None:
            return current_stats
        # Rough heuristic: if since is further back (larger timedelta), return combined
        now = datetime.now(UTC)
        delta_days = (now - since).days
        # For range_key=7d: first call since ~7 days, second call since ~14 days
        if delta_days > 10:
            return combined_stats
        return current_stats

    mock.get_global_stats.side_effect = get_global_stats_side_effect
    return mock


def _mock_empty_stats_aggregator() -> MagicMock:
    """Build a mock StatsAggregator returning zero data."""
    mock = MagicMock()
    empty_stats = GlobalStatistics(generated_at=datetime.now(UTC))
    mock.get_global_stats.return_value = empty_stats
    return mock


def _mock_index_manager() -> MagicMock:
    """Build a mock IndexManager."""
    mock = MagicMock()
    mock.get_recent_runs.return_value = []
    return mock


def _mock_project_registry(project_names: list[str] | None = None) -> MagicMock:
    """Build a mock ProjectRegistryManager."""
    mock = MagicMock()
    projects = []
    for name in project_names or []:
        p = MagicMock()
        p.name = name
        projects.append(p)
    mock.get_all.return_value = projects
    return mock


def _make_client(
    stats_aggregator: MagicMock | None = None,
    index_manager: MagicMock | None = None,
    project_registry: MagicMock | None = None,
) -> TestClient:
    """Create a TestClient with dependency overrides."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    im = index_manager or _mock_index_manager()
    sa = stats_aggregator or _mock_stats_aggregator_for_analytics()
    pr = project_registry or _mock_project_registry()

    app.dependency_overrides[dependencies.get_index_manager] = lambda: im
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: sa
    app.dependency_overrides[dependencies.get_project_registry] = lambda: pr

    return TestClient(app)


# ── build_analytics_context Unit Tests ─────────────────────────────


RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "all": None}


class TestBuildAnalyticsContext:
    """Tests for build_analytics_context function."""

    def test_returns_has_analytics_data_true(self) -> None:
        """Returns has_analytics_data=True when data exists."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["has_analytics_data"] is True

    def test_returns_has_analytics_data_false_when_empty(self) -> None:
        """Returns has_analytics_data=False when no data exists."""
        sa = _mock_empty_stats_aggregator()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["has_analytics_data"] is False

    def test_total_tokens_formatted(self) -> None:
        """Total tokens is formatted with abbreviation."""
        sa = _mock_stats_aggregator_for_analytics(
            current_tokens=TokenUsage(input_tokens=1_800_000, output_tokens=600_000),
        )
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["analytics_total_tokens"] == "2.4M"

    def test_total_cost_formatted(self) -> None:
        """Total cost uses $X.XX format."""
        sa = _mock_stats_aggregator_for_analytics(current_cost=12.34)
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["analytics_total_cost"] == "$12.34"

    def test_avg_tokens_per_run(self) -> None:
        """Avg tokens/run is calculated correctly."""
        sa = _mock_stats_aggregator_for_analytics(
            current_total_runs=10,
            current_tokens=TokenUsage(input_tokens=100_000, output_tokens=50_000),
        )
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        # 150K tokens / 10 runs = 15K per run
        assert result["analytics_avg_tokens"] == "15K"

    def test_total_runs_value(self) -> None:
        """Total runs is an integer value."""
        sa = _mock_stats_aggregator_for_analytics(current_total_runs=42)
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["analytics_total_runs"] == 42

    def test_positive_tokens_delta(self) -> None:
        """Positive token delta when current > previous."""
        sa = _mock_stats_aggregator_for_analytics(
            current_tokens=TokenUsage(input_tokens=2_000_000, output_tokens=500_000),
            prev_tokens=TokenUsage(input_tokens=1_000_000, output_tokens=200_000),
        )
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["tokens_delta"] > 0

    def test_negative_runs_delta(self) -> None:
        """Negative runs delta when current < previous."""
        sa = _mock_stats_aggregator_for_analytics(
            current_total_runs=10,
            prev_total_runs=30,
        )
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["runs_delta"] < 0

    def test_cost_delta_display_format(self) -> None:
        """Cost delta display uses $X.XX format."""
        sa = _mock_stats_aggregator_for_analytics(
            current_cost=15.00,
            prev_cost=10.00,
        )
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["cost_delta_display"] == "$5.00"

    def test_all_time_range_no_deltas(self) -> None:
        """All-time range returns zero deltas (no comparison period)."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="all",
            range_days=RANGE_DAYS,
        )
        assert result["tokens_delta"] == 0
        assert result["cost_delta"] == 0.0
        assert result["runs_delta"] == 0
        assert result["avg_tokens_delta"] == 0

    def test_project_filter_passed_to_aggregator(self) -> None:
        """Project name is forwarded to get_global_stats."""
        sa = _mock_stats_aggregator_for_analytics()
        build_analytics_context(
            stats_aggregator=sa,
            project_name="my-api",
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        calls = sa.get_global_stats.call_args_list
        # All calls should include project_name="my-api"
        for call in calls:
            assert call.kwargs["project_name"] == "my-api"


# ── Analytics Route Tests ──────────────────────────────────────────


class TestAnalyticsRoute:
    """Tests for GET /analytics route."""

    def test_returns_200(self) -> None:
        """Analytics page returns HTTP 200."""
        client = _make_client()
        response = client.get("/analytics")
        assert response.status_code == 200

    def test_returns_html(self) -> None:
        """Analytics page returns HTML content type."""
        client = _make_client()
        response = client.get("/analytics")
        assert "text/html" in response.headers["content-type"]

    def test_full_page_has_title(self) -> None:
        """Full page response includes page title in <title>."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Token &amp; Cost Analytics" in response.text

    def test_page_heading(self) -> None:
        """Page has 'Token & Cost Analytics' heading."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Token &amp; Cost Analytics" in response.text

    def test_htmx_returns_partial(self) -> None:
        """HTMX request returns partial without base template."""
        client = _make_client()
        response = client.get(
            "/analytics", headers={"HX-Request": "true"},
        )
        assert response.status_code == 200
        assert 'id="analytics"' in response.text
        # Should NOT include the full <html> wrapper
        assert "<!DOCTYPE html>" not in response.text

    def test_full_page_includes_base(self) -> None:
        """Non-HTMX request includes full HTML page."""
        client = _make_client()
        response = client.get("/analytics")
        assert "<!DOCTYPE html>" in response.text

    def test_default_range_is_7d(self) -> None:
        """Default range is 7 days when no range param given."""
        client = _make_client()
        response = client.get("/analytics")
        # The 7d tab should be active
        text = response.text
        # Find 7 days tab and check it has tab-active
        idx_7d = text.find("7 days")
        assert idx_7d > 0
        # Look backward for tab-active
        section = text[max(0, idx_7d - 200):idx_7d]
        assert "tab-active" in section

    def test_range_30d_selects_correct_tab(self) -> None:
        """Range=30d makes the 30 days tab active."""
        client = _make_client()
        response = client.get("/analytics?range=30d")
        text = response.text
        idx_30d = text.find("30 days")
        assert idx_30d > 0
        section = text[max(0, idx_30d - 200):idx_30d]
        assert "tab-active" in section

    def test_range_90d_selects_correct_tab(self) -> None:
        """Range=90d makes the 90 days tab active."""
        client = _make_client()
        response = client.get("/analytics?range=90d")
        text = response.text
        idx_90d = text.find("90 days")
        assert idx_90d > 0
        section = text[max(0, idx_90d - 200):idx_90d]
        assert "tab-active" in section

    def test_range_all_selects_correct_tab(self) -> None:
        """Range=all makes the All time tab active."""
        client = _make_client()
        response = client.get("/analytics?range=all")
        text = response.text
        idx_all = text.find("All time")
        assert idx_all > 0
        section = text[max(0, idx_all - 200):idx_all]
        assert "tab-active" in section

    def test_invalid_range_defaults_to_7d(self) -> None:
        """Invalid range param falls back to 7d."""
        client = _make_client()
        response = client.get("/analytics?range=invalid")
        text = response.text
        idx_7d = text.find("7 days")
        assert idx_7d > 0
        section = text[max(0, idx_7d - 200):idx_7d]
        assert "tab-active" in section

    def test_tabs_have_htmx_attributes(self) -> None:
        """Time range tabs have hx-get, hx-target, hx-swap, hx-push-url."""
        client = _make_client()
        response = client.get("/analytics")
        assert 'hx-target="#analytics"' in response.text
        assert 'hx-swap="outerHTML"' in response.text
        assert "hx-push-url" in response.text

    def test_tab_urls_include_range(self) -> None:
        """Tab hx-get URLs include the range parameter."""
        client = _make_client()
        response = client.get("/analytics")
        assert 'hx-get="/analytics?range=7d"' in response.text
        assert 'hx-get="/analytics?range=30d"' in response.text
        assert 'hx-get="/analytics?range=90d"' in response.text
        assert 'hx-get="/analytics?range=all"' in response.text

    def test_analytics_content_div_exists(self) -> None:
        """The analytics-content swap target div exists."""
        client = _make_client()
        response = client.get("/analytics")
        assert 'id="analytics-content"' in response.text


class TestAnalyticsStatCards:
    """Tests for analytics stat card rendering."""

    def test_four_stat_cards_rendered(self) -> None:
        """Four stat cards are rendered."""
        client = _make_client()
        response = client.get("/analytics")
        text = response.text
        assert text.count("stat-title") == 4

    def test_total_tokens_card(self) -> None:
        """Total Tokens stat card is present."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Total Tokens" in response.text

    def test_total_cost_card(self) -> None:
        """Total Cost stat card is present."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Total Cost" in response.text

    def test_avg_tokens_per_run_card(self) -> None:
        """Avg Tokens/Run stat card is present."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Avg Tokens/Run" in response.text

    def test_total_runs_card(self) -> None:
        """Total Runs stat card is present."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Total Runs" in response.text

    def test_positive_delta_green(self) -> None:
        """Positive delta shows green (text-success) with up arrow."""
        sa = _mock_stats_aggregator_for_analytics(
            current_total_runs=50,
            prev_total_runs=30,
        )
        client = _make_client(stats_aggregator=sa)
        response = client.get("/analytics?range=7d")
        assert "text-success" in response.text
        assert "&#x25B2;" in response.text  # Up arrow

    def test_negative_delta_red(self) -> None:
        """Negative delta shows red (text-error) with down arrow."""
        sa = _mock_stats_aggregator_for_analytics(
            current_total_runs=10,
            prev_total_runs=50,
        )
        client = _make_client(stats_aggregator=sa)
        response = client.get("/analytics?range=7d")
        assert "text-error" in response.text
        assert "&#x25BC;" in response.text  # Down arrow

    def test_stat_cards_font_mono(self) -> None:
        """Stat card values use font-mono."""
        client = _make_client()
        response = client.get("/analytics")
        assert "font-mono" in response.text


class TestAnalyticsEmptyState:
    """Tests for analytics empty state."""

    def test_empty_state_message(self) -> None:
        """Shows empty state when no data for period."""
        sa = _mock_empty_stats_aggregator()
        client = _make_client(stats_aggregator=sa)
        response = client.get("/analytics")
        assert "No data for the selected period" in response.text
        assert "Try a wider time range" in response.text

    def test_empty_state_no_stat_cards(self) -> None:
        """No stat cards rendered in empty state."""
        sa = _mock_empty_stats_aggregator()
        client = _make_client(stats_aggregator=sa)
        response = client.get("/analytics")
        assert "stat-title" not in response.text

    def test_tabs_still_shown_in_empty_state(self) -> None:
        """Time range tabs are shown even in empty state."""
        sa = _mock_empty_stats_aggregator()
        client = _make_client(stats_aggregator=sa)
        response = client.get("/analytics")
        assert "tabs tabs-box" in response.text
        assert "7 days" in response.text


class TestAnalyticsProjectFilter:
    """Tests for project filter on analytics page."""

    def test_project_filter_in_tab_urls(self) -> None:
        """Tab URLs include project param when filter is set."""
        client = _make_client()
        response = client.get("/analytics?project=my-api")
        assert "project=my-api" in response.text

    def test_project_filter_preserved_with_range(self) -> None:
        """Project filter preserved when changing time range."""
        client = _make_client()
        response = client.get("/analytics?range=30d&project=my-api")
        # All tab hrefs should include project
        text = response.text
        # Check at least one tab URL has both range and project
        assert "range=7d&amp;project=my-api" in text or "range=7d&project=my-api" in text

    def test_nav_shows_analytics_active(self) -> None:
        """Navigation bar highlights analytics when on analytics page."""
        client = _make_client()
        response = client.get("/analytics")
        text = response.text
        # Find the analytics nav link and check it has the active indicator
        idx = text.find('data-page="analytics"')
        assert idx > 0
        section = text[max(0, idx - 300):idx + 100]
        assert "font-semibold" in section
