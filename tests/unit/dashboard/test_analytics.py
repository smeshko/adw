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
from adw.models.stats import GlobalStatistics, ProjectStatistics, TokenUsage


# ── Helpers ────────────────────────────────────────────────────────


def _mock_stats_aggregator_for_analytics(
    *,
    current_total_runs: int = 50,
    current_tokens: TokenUsage | None = None,
    current_cost: float = 10.50,
    prev_total_runs: int = 80,
    prev_tokens: TokenUsage | None = None,
    prev_cost: float = 18.00,
    daily_counts: list[dict] | None = None,
    phase_breakdown: dict[str, int] | None = None,
    model_breakdown: dict[str, dict[str, int]] | None = None,
) -> MagicMock:
    """Build a mock StatsAggregator for analytics testing.

    When called with since=now-N days, returns current_* stats.
    When called with since=now-2N days, returns combined (prev + current) stats.
    """
    import datetime as dt_module

    mock = MagicMock()

    cur_tok = current_tokens or TokenUsage(
        input_tokens=1_500_000, output_tokens=500_000,
    )
    prev_tok = prev_tokens or TokenUsage(
        input_tokens=2_500_000, output_tokens=1_000_000,
    )

    # Default projects for breakdown
    default_projects = [
        ProjectStatistics(
            name="my-api", path="/projects/my-api",
            total_runs=30, tokens=TokenUsage(input_tokens=900_000, output_tokens=300_000),
        ),
        ProjectStatistics(
            name="my-web", path="/projects/my-web",
            total_runs=20, tokens=TokenUsage(input_tokens=600_000, output_tokens=200_000),
        ),
    ]

    current_stats = GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=current_total_runs,
        tokens=cur_tok,
        estimated_cost=current_cost,
        projects=default_projects,
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
        projects=default_projects,
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

    # Daily token counts with input/output split
    if daily_counts is not None:
        mock.get_daily_token_counts.return_value = daily_counts
    else:
        now = datetime.now(UTC)
        mock.get_daily_token_counts.return_value = [
            {
                "date": (now - __import__("datetime").timedelta(days=6 - i)).date(),
                "tokens": 1000 * (i + 1),
                "input_tokens": 700 * (i + 1),
                "output_tokens": 300 * (i + 1),
            }
            for i in range(7)
        ]

    # Phase breakdown
    mock.get_phase_breakdown.return_value = phase_breakdown or {
        "plan": 5000, "build": 15000, "validate": 3000,
    }

    # Model breakdown
    mock.get_model_breakdown.return_value = model_breakdown or {
        "claude-3-5-sonnet": {"input_tokens": 10000, "output_tokens": 5000},
        "claude-3-haiku": {"input_tokens": 3000, "output_tokens": 1000},
    }

    # calculate_cost for model breakdown
    def calc_cost_side_effect(tokens, model="default"):
        pricing = {
            "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
            "default": {"input": 3.00, "output": 15.00},
        }
        p = pricing.get(model, pricing["default"])
        return round(
            (tokens.input_tokens / 1_000_000) * p["input"]
            + (tokens.output_tokens / 1_000_000) * p["output"],
            2,
        )

    mock.calculate_cost.side_effect = calc_cost_side_effect

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

    def test_daily_chart_bars_present(self) -> None:
        """Daily chart bar data is included in context."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert "daily_chart_bars" in result
        assert len(result["daily_chart_bars"]) == 7

    def test_daily_chart_bar_has_heights(self) -> None:
        """Each daily bar has output_height and input_height percentages."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        bar = result["daily_chart_bars"][0]
        assert "output_height" in bar
        assert "input_height" in bar
        assert "day_label" in bar

    def test_daily_chart_max_bar_is_100(self) -> None:
        """The tallest bar sums to 100% height."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        bars = result["daily_chart_bars"]
        max_total = max(b["output_height"] + b["input_height"] for b in bars)
        assert max_total == 100

    def test_project_breakdown_present(self) -> None:
        """Project breakdown data is included in context."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert "project_breakdown" in result

    def test_phase_breakdown_present(self) -> None:
        """Phase breakdown data is included in context."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert "phase_breakdown" in result
        # Check canonical order maintained
        phases = [p["name"] for p in result["phase_breakdown"]]
        assert phases == ["Plan", "Build", "Validate"]

    def test_model_breakdown_present(self) -> None:
        """Model breakdown data is included in context."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert "model_breakdown" in result
        assert len(result["model_breakdown"]) == 2

    def test_model_breakdown_has_cost(self) -> None:
        """Model breakdown entries include cost."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        for entry in result["model_breakdown"]:
            assert "cost_display" in entry
            assert "percentage" in entry


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
        text = response.text
        # Tab URLs now include sort param too
        assert "range=7d" in text
        assert "range=30d" in text
        assert "range=90d" in text
        assert "range=all" in text

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


# ── Daily Chart Route Tests ────────────────────────────────────────


class TestAnalyticsDailyChart:
    """Tests for daily usage chart rendering."""

    def test_chart_daily_class_rendered(self) -> None:
        """Daily chart container has chart-daily class."""
        client = _make_client()
        response = client.get("/analytics")
        assert "chart-daily" in response.text

    def test_chart_has_bars(self) -> None:
        """Daily chart contains chart-bar elements."""
        client = _make_client()
        response = client.get("/analytics")
        assert "chart-bar" in response.text

    def test_chart_has_legend(self) -> None:
        """Daily chart has output/input token legend."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Output tokens" in response.text
        assert "Input tokens" in response.text

    def test_chart_bars_have_height_styles(self) -> None:
        """Chart bars have inline height styles."""
        client = _make_client()
        response = client.get("/analytics")
        assert 'style="height:' in response.text

    def test_chart_has_day_labels(self) -> None:
        """Chart has day labels (Mon, Tue, etc.)."""
        client = _make_client()
        response = client.get("/analytics")
        text = response.text
        # At least some day labels should appear
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        found_labels = sum(1 for label in day_labels if label in text)
        assert found_labels >= 1

    def test_empty_state_no_chart(self) -> None:
        """Empty state does not show the daily chart."""
        sa = _mock_empty_stats_aggregator()
        client = _make_client(stats_aggregator=sa)
        response = client.get("/analytics")
        assert "chart-daily" not in response.text


# ── Breakdown Panel Route Tests ────────────────────────────────────


class TestAnalyticsBreakdownPanels:
    """Tests for breakdown panel rendering."""

    def test_project_breakdown_rendered(self) -> None:
        """Project breakdown panel is rendered."""
        client = _make_client()
        response = client.get("/analytics")
        assert "By Project" in response.text

    def test_phase_breakdown_rendered(self) -> None:
        """Phase breakdown panel is rendered."""
        client = _make_client()
        response = client.get("/analytics")
        assert "By Phase" in response.text

    def test_model_breakdown_rendered(self) -> None:
        """Model breakdown panel is rendered."""
        client = _make_client()
        response = client.get("/analytics")
        assert "By Model" in response.text

    def test_phase_names_displayed(self) -> None:
        """Phase breakdown shows phase names."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Plan" in response.text
        assert "Build" in response.text

    def test_model_names_displayed(self) -> None:
        """Model breakdown shows model names."""
        client = _make_client()
        response = client.get("/analytics")
        assert "claude-3-5-sonnet" in response.text
        assert "claude-3-haiku" in response.text

    def test_model_cost_displayed(self) -> None:
        """Model breakdown shows cost values."""
        client = _make_client()
        response = client.get("/analytics")
        # Cost display should contain $ sign
        text = response.text
        idx = text.find("By Model")
        assert idx > 0
        model_section = text[idx:]
        assert "$" in model_section

    def test_project_breakdown_clickable(self) -> None:
        """Project names in breakdown have hx-get for filter."""
        client = _make_client()
        response = client.get("/analytics")
        text = response.text
        # Project links should have hx-get with project param
        assert "hx-get" in text
        # Check the breakdown area has project filter links
        idx = text.find("By Project")
        if idx > 0:
            proj_section = text[idx:idx + 1000]
            assert "hx-target" in proj_section

    def test_phase_breakdown_not_clickable(self) -> None:
        """Phase names are not clickable (plain span, not link)."""
        client = _make_client()
        response = client.get("/analytics")
        text = response.text
        idx = text.find("By Phase")
        if idx > 0:
            phase_section = text[idx:idx + 1000]
            # Phase names should be in spans, not links
            assert "link" not in phase_section

    def test_breakdown_panels_in_grid(self) -> None:
        """Breakdown panels use grid layout."""
        client = _make_client()
        response = client.get("/analytics")
        assert "grid grid-cols-1 lg:grid-cols-2 gap-4" in response.text

    def test_breakdown_bars_have_width_styles(self) -> None:
        """Breakdown horizontal bars have inline width styles."""
        client = _make_client()
        response = client.get("/analytics")
        assert 'style="width:' in response.text

    def test_empty_state_no_breakdowns(self) -> None:
        """Empty state does not show breakdown panels."""
        sa = _mock_empty_stats_aggregator()
        client = _make_client(stats_aggregator=sa)
        response = client.get("/analytics")
        assert "By Project" not in response.text
        assert "By Phase" not in response.text
        assert "By Model" not in response.text


# ── Budget Section Tests ──────────────────────────────────────────


class TestBudgetSection:
    """Tests for budget section in analytics."""

    def test_budget_context_when_env_set(self, monkeypatch: object) -> None:
        """Budget context values present when ADW_MONTHLY_BUDGET is set."""
        monkeypatch.setenv("ADW_MONTHLY_BUDGET", "100.00")  # type: ignore[attr-defined]
        sa = _mock_stats_aggregator_for_analytics(current_cost=36.00)
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["has_budget"] is True
        assert result["budget_amount"] == 100.00
        assert result["budget_spent"] == "$36.00"
        assert result["budget_percentage"] == 36.0

    def test_budget_hidden_when_env_not_set(self, monkeypatch: object) -> None:
        """Budget context has_budget=False when env var missing."""
        monkeypatch.delenv("ADW_MONTHLY_BUDGET", raising=False)  # type: ignore[attr-defined]
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["has_budget"] is False

    def test_budget_progress_class_primary_below_70(self, monkeypatch: object) -> None:
        """Progress bar uses progress-primary when usage < 70%."""
        monkeypatch.setenv("ADW_MONTHLY_BUDGET", "100.00")  # type: ignore[attr-defined]
        sa = _mock_stats_aggregator_for_analytics(current_cost=69.00)
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["budget_progress_class"] == "progress-primary"

    def test_budget_progress_class_warning_at_70(self, monkeypatch: object) -> None:
        """Progress bar uses progress-warning when usage is 70%."""
        monkeypatch.setenv("ADW_MONTHLY_BUDGET", "100.00")  # type: ignore[attr-defined]
        sa = _mock_stats_aggregator_for_analytics(current_cost=70.00)
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["budget_progress_class"] == "progress-warning"

    def test_budget_progress_class_warning_at_90(self, monkeypatch: object) -> None:
        """Progress bar uses progress-warning when usage is exactly 90%."""
        monkeypatch.setenv("ADW_MONTHLY_BUDGET", "100.00")  # type: ignore[attr-defined]
        sa = _mock_stats_aggregator_for_analytics(current_cost=90.00)
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["budget_progress_class"] == "progress-warning"

    def test_budget_progress_class_error_above_90(self, monkeypatch: object) -> None:
        """Progress bar uses progress-error when usage > 90%."""
        monkeypatch.setenv("ADW_MONTHLY_BUDGET", "100.00")  # type: ignore[attr-defined]
        sa = _mock_stats_aggregator_for_analytics(current_cost=91.00)
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["budget_progress_class"] == "progress-error"

    def test_budget_days_remaining(self, monkeypatch: object) -> None:
        """Days remaining is calculated from daily average cost."""
        monkeypatch.setenv("ADW_MONTHLY_BUDGET", "100.00")  # type: ignore[attr-defined]
        # 7-day range with $35 spent => daily avg = $5, remaining = $65 => 13 days
        sa = _mock_stats_aggregator_for_analytics(current_cost=35.00)
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["budget_days_remaining"] == 13

    def test_budget_days_remaining_zero_cost(self, monkeypatch: object) -> None:
        """Days remaining is None when cost is zero (no daily average)."""
        monkeypatch.setenv("ADW_MONTHLY_BUDGET", "100.00")  # type: ignore[attr-defined]
        sa = _mock_stats_aggregator_for_analytics(current_cost=0.00, current_total_runs=1)
        # Force the mock to return 0 cost with data
        zero_stats = GlobalStatistics(
            generated_at=datetime.now(UTC),
            total_runs=1,
            tokens=TokenUsage(input_tokens=100, output_tokens=50),
            estimated_cost=0.0,
            projects=[],
        )
        sa.get_global_stats.side_effect = None
        sa.get_global_stats.return_value = zero_stats
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["budget_days_remaining"] is None

    def test_budget_section_shown_in_route(self, monkeypatch: object) -> None:
        """Budget section HTML rendered when budget env var is set."""
        monkeypatch.setenv("ADW_MONTHLY_BUDGET", "100.00")  # type: ignore[attr-defined]
        sa = _mock_stats_aggregator_for_analytics(current_cost=36.00)
        client = _make_client(stats_aggregator=sa)
        response = client.get("/analytics")
        assert "Monthly Budget" in response.text
        assert "progress" in response.text

    def test_budget_section_hidden_in_route(self, monkeypatch: object) -> None:
        """Budget section not rendered when budget env var is absent."""
        monkeypatch.delenv("ADW_MONTHLY_BUDGET", raising=False)  # type: ignore[attr-defined]
        sa = _mock_stats_aggregator_for_analytics()
        client = _make_client(stats_aggregator=sa)
        response = client.get("/analytics")
        assert "Monthly Budget" not in response.text


# ── Breakdown Table Tests ─────────────────────────────────────────


class TestBreakdownTable:
    """Tests for detailed breakdown table in analytics."""

    def test_breakdown_table_in_context(self) -> None:
        """Breakdown table data is present in context."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert "breakdown_table" in result
        assert len(result["breakdown_table"]) == 2

    def test_breakdown_table_has_required_fields(self) -> None:
        """Each breakdown row has name, runs, tokens, cost, avg fields."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        row = result["breakdown_table"][0]
        assert "name" in row
        assert "runs" in row
        assert "tokens_display" in row
        assert "cost_display" in row
        assert "avg_tokens_display" in row

    def test_breakdown_table_default_sort_cost_desc(self) -> None:
        """Default sort is cost_desc (highest cost first)."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        # my-api has more tokens (900K+300K=1.2M) than my-web (600K+200K=800K)
        # So my-api should have higher cost and be first
        assert result["breakdown_table"][0]["name"] == "my-api"
        assert result["breakdown_sort"] == "cost_desc"

    def test_breakdown_table_sort_cost_asc(self) -> None:
        """Sort cost_asc puts lowest cost first."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
            sort="cost_asc",
        )
        assert result["breakdown_table"][0]["name"] == "my-web"
        assert result["breakdown_sort"] == "cost_asc"

    def test_breakdown_table_sort_runs_desc(self) -> None:
        """Sort runs_desc puts highest run count first."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
            sort="runs_desc",
        )
        # my-api has 30 runs, my-web has 20
        assert result["breakdown_table"][0]["name"] == "my-api"

    def test_breakdown_table_sort_project_asc(self) -> None:
        """Sort project_asc puts alphabetically first project first."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
            sort="project_asc",
        )
        assert result["breakdown_table"][0]["name"] == "my-api"
        assert result["breakdown_table"][1]["name"] == "my-web"

    def test_breakdown_table_sort_project_desc(self) -> None:
        """Sort project_desc puts alphabetically last project first."""
        sa = _mock_stats_aggregator_for_analytics()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
            sort="project_desc",
        )
        assert result["breakdown_table"][0]["name"] == "my-web"

    def test_breakdown_table_empty_when_no_data(self) -> None:
        """Breakdown table is empty when no analytics data."""
        sa = _mock_empty_stats_aggregator()
        result = build_analytics_context(
            stats_aggregator=sa,
            project_name=None,
            range_key="7d",
            range_days=RANGE_DAYS,
        )
        assert result["breakdown_table"] == []

    def test_breakdown_table_rendered_in_route(self) -> None:
        """Breakdown table HTML rendered in route response."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Detailed Breakdown" in response.text
        assert "table-zebra" in response.text

    def test_breakdown_sort_param_in_route(self) -> None:
        """Sort parameter accepted by analytics route."""
        client = _make_client()
        response = client.get("/analytics?sort=runs_desc")
        assert response.status_code == 200

    def test_breakdown_sort_preserved_in_tab_urls(self) -> None:
        """Sort parameter is preserved in time range tab URLs."""
        client = _make_client()
        response = client.get("/analytics?sort=tokens_desc")
        # Tab URLs should include sort param
        assert "sort=tokens_desc" in response.text
