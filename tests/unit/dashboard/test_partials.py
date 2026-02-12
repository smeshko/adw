"""Tests for dashboard partial helpers.

Covers build_cost_strip_context() bar height calculation and formatting,
recent runs partial route, project breakdown partial route,
overview integration, duration formatting, empty states, and project
filter behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from adw.dashboard.partials import build_cost_strip_context
from adw.dashboard.server import create_dashboard_app
from adw.models.stats import GlobalStatistics, ProjectStatistics, TokenUsage

# ── Helpers ────────────────────────────────────────────────────────


def _mock_cost_strip_aggregator(
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


def _mock_index_manager(
    entries: list[MagicMock] | None = None,
    active_count: int = 0,
) -> MagicMock:
    """Build a mock IndexManager with configurable run data."""
    mock = MagicMock()
    running_runs = [MagicMock() for _ in range(active_count)]
    recent_entries = entries or []

    def get_recent_side_effect(**kwargs):
        if kwargs.get("status") == "running":
            return running_runs
        limit = kwargs.get("limit", 10)
        project_name = kwargs.get("project_name")
        project_path = kwargs.get("project_path")
        filtered = recent_entries
        if project_path:
            pp_str = str(project_path)
            filtered = [e for e in filtered if getattr(e, "project_path", "") == pp_str]
        elif project_name:
            filtered = [e for e in filtered if e.project_name == project_name]
        return filtered[:limit]

    mock.get_recent_runs.side_effect = get_recent_side_effect
    return mock


def _make_entry(
    run_id: str = "01KDSG2VDHNK0W4HSCZWJZXWSQ",
    project_name: str = "test-project",
    feature_description: str = "Add auth feature",
    status: str = "completed",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    duration_minutes: int = 5,
) -> MagicMock:
    """Build a mock IndexEntry."""
    entry = MagicMock()
    entry.run_id = run_id
    entry.project_name = project_name
    entry.feature_description = feature_description
    entry.status = status
    entry.started_at = started_at or (datetime.now(UTC) - timedelta(minutes=25))
    if status == "running":
        entry.completed_at = None
    else:
        entry.completed_at = completed_at or (
            entry.started_at + timedelta(minutes=duration_minutes)
        )
    return entry


def _mock_stats_aggregator(
    projects: list[ProjectStatistics] | None = None,
    **kwargs,
) -> MagicMock:
    """Build a mock StatsAggregator returning configurable GlobalStatistics."""
    mock = MagicMock()
    stats = GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=kwargs.get("total_runs", 142),
        runs_this_week=kwargs.get("runs_this_week", 42),
        runs_today=5,
        completed_runs=124,
        failed_runs=18,
        success_rate=kwargs.get("success_rate", 0.875),
        average_duration_ms=kwargs.get("average_duration_ms", 185000),
        tokens=TokenUsage(input_tokens=1_800_000, output_tokens=600_000),
        estimated_cost=kwargs.get("estimated_cost", 12.45),
        previous_week_total_runs=kwargs.get("previous_week_total_runs", 35),
        previous_week_success_rate=kwargs.get("previous_week_success_rate", 0.82),
        previous_week_average_duration_ms=195000,
        tokens_this_week=TokenUsage(input_tokens=900_000, output_tokens=300_000),
        cost_this_week=kwargs.get("cost_this_week", 5.67),
        projects=projects or [],
    )
    mock.get_global_stats.return_value = stats
    return mock


def _mock_project_registry(
    project_names: list[str] | None = None,
) -> MagicMock:
    """Build a mock ProjectRegistryManager."""
    mock = MagicMock()
    projects = []
    for name in project_names or []:
        p = MagicMock()
        p.name = name
        p.path = f"/projects/{name}"
        projects.append(p)
    mock.get_all.return_value = projects
    return mock


def _make_client_with_mocks(
    index_manager: MagicMock | None = None,
    stats_aggregator: MagicMock | None = None,
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


# ── Cost Strip Context ────────────────────────────────────────────


class TestBuildCostStripContext:
    """Tests for build_cost_strip_context function."""

    def test_returns_cost_display(self) -> None:
        """Returns formatted cost display string."""
        sa = _mock_cost_strip_aggregator(cost_this_week=12.34)
        result = build_cost_strip_context(sa, None)
        assert result["cost_strip_cost_display"] == "$12.34"

    def test_returns_tokens_display(self) -> None:
        """Returns formatted tokens display string."""
        sa = _mock_cost_strip_aggregator(
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
        sa = _mock_cost_strip_aggregator(daily_tokens=daily)
        result = build_cost_strip_context(sa, None)
        assert len(result["daily_bars"]) == 7

    def test_max_day_gets_100_percent(self) -> None:
        """The day with most tokens gets 100% height."""
        today = datetime.now(UTC).date()
        daily = [{"date": today - timedelta(days=i), "tokens": 0} for i in range(6, -1, -1)]
        daily[-1] = {"date": today, "tokens": 5000}  # Today has max
        sa = _mock_cost_strip_aggregator(daily_tokens=daily)
        result = build_cost_strip_context(sa, None)
        # Last bar (today) should be 100%
        assert result["daily_bars"][-1]["height_pct"] == 100

    def test_proportional_heights(self) -> None:
        """Other days get proportional heights relative to max."""
        today = datetime.now(UTC).date()
        daily = [{"date": today - timedelta(days=i), "tokens": 0} for i in range(6, -1, -1)]
        daily[-1] = {"date": today, "tokens": 1000}  # Max
        daily[-2] = {"date": today - timedelta(days=1), "tokens": 500}  # 50%
        sa = _mock_cost_strip_aggregator(daily_tokens=daily)
        result = build_cost_strip_context(sa, None)
        assert result["daily_bars"][-1]["height_pct"] == 100
        assert result["daily_bars"][-2]["height_pct"] == 50

    def test_all_zeros_returns_zero_heights(self) -> None:
        """All-zero days get 0% height."""
        sa = _mock_cost_strip_aggregator()
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
        sa = _mock_cost_strip_aggregator(daily_tokens=daily)
        result = build_cost_strip_context(sa, None)
        expected_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        actual_labels = [bar["date_label"] for bar in result["daily_bars"]]
        assert actual_labels == expected_labels

    def test_project_filter_passed(self) -> None:
        """Project name is passed to stats_aggregator methods."""
        sa = _mock_cost_strip_aggregator()
        build_cost_strip_context(sa, "my-project")
        sa.get_global_stats.assert_called_once_with(project_name="my-project")
        sa.get_daily_token_counts.assert_called_once_with(project_name="my-project")

    def test_cost_format_zero(self) -> None:
        """Zero cost displays as $0.00."""
        sa = _mock_cost_strip_aggregator(cost_this_week=0.0)
        result = build_cost_strip_context(sa, None)
        assert result["cost_strip_cost_display"] == "$0.00"


# ── Recent Runs Partial Route ─────────────────────────────────────


class TestRecentRunsPartial:
    """Tests for GET /partials/recent-runs route."""

    def test_returns_200(self) -> None:
        """Recent runs partial returns HTTP 200."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs")
        assert response.status_code == 200

    def test_returns_html(self) -> None:
        """Recent runs partial returns HTML content type."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs")
        assert "text/html" in response.headers["content-type"]

    def test_empty_state_message(self) -> None:
        """Shows 'No runs found' when index is empty."""
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=[]),
        )
        response = client.get("/partials/recent-runs")
        assert "No runs found" in response.text

    def test_has_section_id(self) -> None:
        """Section has id='recent-runs' for HTMX targeting."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs")
        assert 'id="recent-runs"' in response.text

    def test_has_polling_attributes(self) -> None:
        """Section has HTMX polling at 15s interval."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs")
        assert 'hx-trigger="every 15s"' in response.text

    def test_polling_url_no_push(self) -> None:
        """Polling request does NOT include hx-push-url on the section."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs")
        # The section's hx-get should not have hx-push-url
        text = response.text
        section_start = text.find('id="recent-runs"')
        section_tag_end = text.find(">", section_start)
        section_tag = text[section_start:section_tag_end]
        assert "hx-push-url" not in section_tag

    def test_has_view_all_link(self) -> None:
        """Section header contains 'View All →' link."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs")
        assert "View All →" in response.text

    def test_view_all_targets_runs_page(self) -> None:
        """View All link navigates to /runs via HTMX."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs")
        assert 'hx-get="/runs"' in response.text
        assert 'hx-push-url="/runs"' in response.text

    def test_has_compact_table(self) -> None:
        """Contains a table with table-sm class inside card-compact."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/partials/recent-runs")
        assert "table table-sm" in response.text
        assert "card card-compact" in response.text

    def test_has_overflow_wrapper(self) -> None:
        """Table has overflow-x-auto wrapper for responsive layout."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs")
        assert "overflow-x-auto" in response.text

    def test_displays_project_name(self) -> None:
        """Run row displays the project name."""
        entries = [_make_entry(project_name="my-api")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/partials/recent-runs")
        assert "my-api" in response.text

    def test_displays_feature_description(self) -> None:
        """Run row displays the feature description with truncate."""
        entries = [_make_entry(feature_description="Add user authentication")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/partials/recent-runs")
        assert "Add user authentication" in response.text
        assert "truncate" in response.text

    def test_displays_status_badge(self) -> None:
        """Run row displays a status badge."""
        entries = [_make_entry(status="completed")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/partials/recent-runs")
        assert "badge" in response.text
        assert "completed" in response.text

    def test_displays_duration_for_completed(self) -> None:
        """Completed run shows duration in 'Xm Ys' format."""
        entries = [_make_entry(duration_minutes=3)]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/partials/recent-runs")
        assert "3m 0s" in response.text

    def test_displays_dash_for_running(self) -> None:
        """Running entry (no completed_at) shows '—' for duration."""
        entries = [_make_entry(status="running")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/partials/recent-runs")
        assert "—" in response.text

    def test_displays_relative_time(self) -> None:
        """Started column shows relative time like 'Xm ago'."""
        entries = [
            _make_entry(
                started_at=datetime.now(UTC) - timedelta(minutes=25),
            ),
        ]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/partials/recent-runs")
        assert "25m ago" in response.text

    def test_rows_are_clickable(self) -> None:
        """Each row has hx-get and cursor-pointer for navigation."""
        entries = [_make_entry(run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/partials/recent-runs")
        assert "cursor-pointer" in response.text
        assert 'hx-get="/runs/01KDSG2VDHNK0W4HSCZWJZXWSQ"' in response.text

    def test_limits_to_5_entries(self) -> None:
        """Only the 5 most recent runs are shown."""
        entries = [
            _make_entry(run_id=f"01KDSG2VDHNK0W4HSCZWJZXWS{chr(65 + i)}")
            for i in range(7)
        ]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        client.get("/partials/recent-runs")
        # Verify the mock was called with limit=5
        calls = im.get_recent_runs.call_args_list
        limit_call = [c for c in calls if c.kwargs.get("limit") == 5]
        assert len(limit_call) == 1

    def test_respects_project_filter(self) -> None:
        """Project filter parameter is resolved to project_path."""
        im = _mock_index_manager()
        pr = _mock_project_registry(project_names=["my-api"])
        client = _make_client_with_mocks(index_manager=im, project_registry=pr)
        client.get("/partials/recent-runs?project=my-api")
        calls = im.get_recent_runs.call_args_list
        project_call = [
            c for c in calls
            if c.kwargs.get("project_path") == Path("/projects/my-api")
        ]
        assert len(project_call) == 1

    def test_project_filter_in_polling_url(self) -> None:
        """Polling URL includes project parameter when set."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs?project=my-api")
        assert (
            'hx-get="/partials/recent-runs?project=my-api"' in response.text
        )

    def test_view_all_includes_project_filter(self) -> None:
        """View All link includes project filter when set."""
        client = _make_client_with_mocks()
        response = client.get("/partials/recent-runs?project=my-api")
        assert 'hx-get="/runs?project=my-api"' in response.text


# ── Project Breakdown Partial Route ───────────────────────────────


class TestProjectBreakdownPartial:
    """Tests for GET /partials/projects route."""

    def test_returns_200(self) -> None:
        """Project breakdown partial returns HTTP 200."""
        client = _make_client_with_mocks()
        response = client.get("/partials/projects")
        assert response.status_code == 200

    def test_returns_html(self) -> None:
        """Project breakdown partial returns HTML content type."""
        client = _make_client_with_mocks()
        response = client.get("/partials/projects")
        assert "text/html" in response.headers["content-type"]

    def test_has_section_id(self) -> None:
        """Section has id='project-breakdown'."""
        client = _make_client_with_mocks()
        response = client.get("/partials/projects")
        assert 'id="project-breakdown"' in response.text

    def test_empty_state_message(self) -> None:
        """Shows 'No projects registered' when no projects exist."""
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=[]),
        )
        response = client.get("/partials/projects")
        assert "No projects registered" in response.text

    def test_displays_project_cards(self) -> None:
        """Renders project cards with flex wrap layout."""
        projects = [
            ProjectStatistics(
                name="alpha",
                path="/p/alpha",
                total_runs=50,
                success_rate=0.9,
                estimated_cost=25.50,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects")
        assert "flex gap-3 flex-wrap" in response.text
        assert "alpha" in response.text

    def test_project_card_shows_name(self) -> None:
        """Project card shows the project name with font-semibold."""
        projects = [
            ProjectStatistics(
                name="my-api", path="/p", total_runs=10, success_rate=0.8,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects")
        assert "font-semibold text-sm" in response.text
        assert "my-api" in response.text

    def test_project_card_shows_run_count(self) -> None:
        """Project card shows run count."""
        projects = [
            ProjectStatistics(
                name="api", path="/p", total_runs=42, success_rate=0.8,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects")
        assert "42 runs" in response.text

    def test_success_rate_green(self) -> None:
        """Success rate >= 80% shows text-success (green)."""
        projects = [
            ProjectStatistics(
                name="api", path="/p", total_runs=10, success_rate=0.9,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects")
        assert "text-success" in response.text
        assert "90% success" in response.text

    def test_success_rate_yellow(self) -> None:
        """Success rate 50-79% shows text-warning (yellow)."""
        projects = [
            ProjectStatistics(
                name="api", path="/p", total_runs=10, success_rate=0.6,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects")
        assert "text-warning" in response.text
        assert "60% success" in response.text

    def test_success_rate_red(self) -> None:
        """Success rate < 50% shows text-error (red)."""
        projects = [
            ProjectStatistics(
                name="api", path="/p", total_runs=10, success_rate=0.3,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects")
        assert "text-error" in response.text
        assert "30% success" in response.text

    def test_project_card_shows_cost(self) -> None:
        """Project card shows estimated cost in font-mono."""
        projects = [
            ProjectStatistics(
                name="api",
                path="/p",
                total_runs=10,
                success_rate=0.8,
                estimated_cost=25.50,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects")
        assert "$25.50" in response.text
        assert "font-mono text-xs" in response.text

    def test_project_card_is_clickable(self) -> None:
        """Project card has hx-get for project filter navigation."""
        projects = [
            ProjectStatistics(
                name="alpha", path="/p", total_runs=10, success_rate=0.8,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects")
        assert 'hx-get="/?project=alpha"' in response.text
        assert 'hx-push-url="/?project=alpha"' in response.text

    def test_selected_project_has_ring(self) -> None:
        """Selected project card shows ring ring-primary outline."""
        projects = [
            ProjectStatistics(
                name="alpha", path="/p", total_runs=10, success_rate=0.8,
            ),
            ProjectStatistics(
                name="beta", path="/p", total_runs=5, success_rate=0.6,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects?project=alpha")
        assert "ring ring-primary" in response.text

    def test_filtered_title_shown(self) -> None:
        """Section title shows 'Filtered: {name}' when filter active."""
        client = _make_client_with_mocks()
        response = client.get("/partials/projects?project=alpha")
        assert "Filtered: alpha" in response.text

    def test_clear_filter_button(self) -> None:
        """Clear button (×) appears when filter is active."""
        client = _make_client_with_mocks()
        response = client.get("/partials/projects?project=alpha")
        assert "×" in response.text
        assert 'hx-get="/"' in response.text

    def test_no_filter_shows_plain_title(self) -> None:
        """Section title shows 'Projects' without filter."""
        client = _make_client_with_mocks()
        response = client.get("/partials/projects")
        assert "Projects</h2>" in response.text
        assert "Filtered" not in response.text

    def test_all_cards_visible_when_filtered(self) -> None:
        """All project cards remain visible even when a filter is active."""
        projects = [
            ProjectStatistics(
                name="alpha", path="/p/a", total_runs=10, success_rate=0.8,
            ),
            ProjectStatistics(
                name="beta", path="/p/b", total_runs=5, success_rate=0.6,
            ),
            ProjectStatistics(
                name="gamma", path="/p/g", total_runs=3, success_rate=0.9,
            ),
        ]
        client = _make_client_with_mocks(
            stats_aggregator=_mock_stats_aggregator(projects=projects),
        )
        response = client.get("/partials/projects?project=alpha")
        # All three projects should be visible (unfiltered card list)
        assert "alpha" in response.text
        assert "beta" in response.text
        assert "gamma" in response.text
        # Only alpha should have the ring highlight
        assert "ring ring-primary" in response.text


# ── Overview Integration ──────────────────────────────────────────


class TestOverviewIncludesNewSections:
    """Tests for recent runs and projects in the overview page."""

    def test_overview_contains_recent_runs_section(self) -> None:
        """Overview page includes the recent-runs section."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
            project_registry=_mock_project_registry(["test-project"]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert 'id="recent-runs"' in response.text

    def test_overview_contains_project_breakdown_section(self) -> None:
        """Overview page includes the project-breakdown section."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
            project_registry=_mock_project_registry(["test-project"]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert 'id="project-breakdown"' in response.text

    def test_overview_no_placeholder(self) -> None:
        """Overview no longer shows the old placeholder message."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
            project_registry=_mock_project_registry(["test-project"]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert "More content coming" not in response.text

    def test_overview_recent_runs_data(self) -> None:
        """Overview includes recent runs data in context."""
        entries = [_make_entry(project_name="my-proj")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
            project_registry=_mock_project_registry(["my-proj"]),
        )
        response = client.get("/")
        assert "my-proj" in response.text

    def test_overview_project_stats_data(self) -> None:
        """Overview includes project stats data in context."""
        projects = [
            ProjectStatistics(
                name="demo",
                path="/p",
                total_runs=10,
                success_rate=0.8,
                estimated_cost=5.0,
            ),
        ]
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
            stats_aggregator=_mock_stats_aggregator(projects=projects),
            project_registry=_mock_project_registry(["demo"]),
        )
        response = client.get("/")
        assert "demo" in response.text
        assert "10 runs" in response.text


# ── Duration Formatting ──────────────────────────────────────────


class TestDurationFormatting:
    """Tests for run duration display logic."""

    def test_completed_run_duration(self) -> None:
        """Completed run shows correct 'Xm Ys' duration."""
        from adw.dashboard.partials import _format_duration

        # 3 minutes = 180000ms
        assert _format_duration(180000) == "3m 0s"

    def test_short_duration(self) -> None:
        """Short duration shows seconds correctly."""
        from adw.dashboard.partials import _format_duration

        # 45 seconds = 45000ms
        assert _format_duration(45000) == "45s"

    def test_long_duration(self) -> None:
        """Long duration shows minutes and seconds."""
        from adw.dashboard.partials import _format_duration

        # 7 min 30 sec = 450000ms
        assert _format_duration(450000) == "7m 30s"

    def test_running_entry_shows_dash(self) -> None:
        """Running entry with no completed_at shows em-dash."""
        entries = [_make_entry(status="running")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/partials/recent-runs")
        # The em-dash character
        assert "—" in response.text
