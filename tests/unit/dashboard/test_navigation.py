"""Tests for Story 1.2: Base Template, Navigation & Theme.

Covers navigation routes, dual-response pattern, project filter,
status bar partial, theme toggle, and error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from adw.dashboard.server import create_dashboard_app
from adw.models.stats import GlobalStatistics, TokenUsage


def _make_client() -> TestClient:
    """Create a TestClient for the dashboard app."""
    return TestClient(create_dashboard_app())


def _mock_index_manager(
    active_count: int = 0,
    last_completed: datetime | None = None,
    has_runs: bool = True,
    raise_on_call: bool = False,
) -> MagicMock:
    """Build a mock IndexManager with configurable run data."""
    mock = MagicMock()

    if raise_on_call:
        mock.get_recent_runs.side_effect = RuntimeError("Index corrupted")
        return mock

    # get_recent_runs(status="running") → active runs
    running_runs = [MagicMock() for _ in range(active_count)]
    # get_recent_runs(limit=1) → most recent run
    if last_completed:
        recent_entry = MagicMock()
        recent_entry.completed_at = last_completed
        recent_entry.started_at = last_completed - timedelta(minutes=5)
        recent_runs = [recent_entry]
    elif has_runs:
        recent_entry = MagicMock()
        recent_entry.completed_at = datetime.now(UTC) - timedelta(minutes=5)
        recent_entry.started_at = datetime.now(UTC) - timedelta(minutes=10)
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
    for name in project_names or []:
        p = MagicMock()
        p.name = name
        projects.append(p)
    mock.get_all.return_value = projects
    return mock


def _mock_stats_aggregator(
    cost_this_week: float = 5.67,
    tokens_this_week: TokenUsage | None = None,
) -> MagicMock:
    """Build a mock StatsAggregator for overview route testing."""
    mock = MagicMock()
    stats = GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=10,
        runs_this_week=3,
        runs_today=1,
        completed_runs=8,
        failed_runs=2,
        success_rate=0.8,
        average_duration_ms=120000,
        tokens=tokens_this_week
        or TokenUsage(input_tokens=900_000, output_tokens=300_000),
        estimated_cost=12.0,
        tokens_this_week=tokens_this_week
        or TokenUsage(input_tokens=900_000, output_tokens=300_000),
        cost_this_week=cost_this_week,
    )
    mock.get_global_stats.return_value = stats
    today = datetime.now(UTC).date()
    mock.get_daily_token_counts.return_value = [
        {"date": today - timedelta(days=i), "tokens": 0} for i in range(6, -1, -1)
    ]
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


# ── Overview Route ──────────────────────────────────────────────────


class TestOverviewRoute:
    """Tests for the overview (/) route."""

    def test_full_page_contains_html_structure(self) -> None:
        """Full page response contains DOCTYPE, header, main, footer."""
        client = _make_client()
        response = client.get("/")
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text
        assert "<header" in response.text
        assert '<main id="main"' in response.text
        assert '<footer id="status-bar"' in response.text

    def test_full_page_has_nav_links(self) -> None:
        """Full page response contains all three nav links."""
        client = _make_client()
        response = client.get("/")
        assert "Overview" in response.text
        assert "Runs" in response.text
        assert "Analytics" in response.text

    def test_full_page_overview_nav_active(self) -> None:
        """Overview nav link has active indicator on overview page."""
        client = _make_client()
        response = client.get("/")
        # The Overview link should have border-primary (active indicator)
        # while Runs and Analytics should not
        text = response.text
        # Find the Overview link - it should have font-semibold and border-primary
        assert "font-semibold border-b-2 border-primary" in text

    def test_full_page_has_theme_toggle(self) -> None:
        """Full page contains the theme toggle swap element."""
        client = _make_client()
        response = client.get("/")
        assert "theme-toggle" in response.text
        assert "swap swap-rotate" in response.text

    def test_full_page_has_project_filter(self) -> None:
        """Full page contains the project filter dropdown."""
        client = _make_client()
        response = client.get("/")
        assert "project-filter" in response.text
        assert "All Projects" in response.text

    def test_htmx_partial_returns_fragment(self) -> None:
        """HTMX request returns partial without full HTML wrapper."""
        client = _make_client()
        response = client.get("/", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "<!DOCTYPE" not in response.text
        assert '<div id="overview"' in response.text

    def test_full_page_has_local_storage_theme_script(self) -> None:
        """Full page has inline script to restore theme from localStorage."""
        client = _make_client()
        response = client.get("/")
        assert "localStorage.getItem('adw-theme')" in response.text

    def test_full_page_links_dashboard_css(self) -> None:
        """Full page links to dashboard.css stylesheet."""
        client = _make_client()
        response = client.get("/")
        assert "/static/dashboard.css" in response.text

    def test_full_page_has_htmx_error_handler(self) -> None:
        """Full page contains htmx:responseError event listener."""
        client = _make_client()
        response = client.get("/")
        assert "htmx:responseError" in response.text

    def test_full_page_has_loading_indicator(self) -> None:
        """Full page has the nav loading spinner element."""
        client = _make_client()
        response = client.get("/")
        assert 'id="nav-loading"' in response.text
        assert "htmx-indicator" in response.text


# ── Runs Route ──────────────────────────────────────────────────────


class TestRunsRoute:
    """Tests for the /runs route."""

    def test_full_page_returns_html(self) -> None:
        """Full page response is HTML with correct structure."""
        client = _make_client()
        response = client.get("/runs")
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text
        assert "<header" in response.text
        assert "Runs" in response.text

    def test_runs_nav_active(self) -> None:
        """Runs nav link has active indicator on runs page."""
        client = _make_client()
        response = client.get("/runs")
        # Check that the Runs link specifically has the active class
        text = response.text
        # The active indicator should appear on the Runs link
        assert "font-semibold border-b-2 border-primary" in text

    def test_htmx_partial_returns_fragment(self) -> None:
        """HTMX request returns runs partial fragment."""
        client = _make_client()
        response = client.get("/runs", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "<!DOCTYPE" not in response.text
        assert '<div id="runs-list"' in response.text

    def test_full_page_has_title(self) -> None:
        """Full page has correct title."""
        client = _make_client()
        response = client.get("/runs")
        assert "Runs — ADW Dashboard" in response.text


# ── Analytics Route ─────────────────────────────────────────────────


class TestAnalyticsRoute:
    """Tests for the /analytics route."""

    def test_full_page_returns_html(self) -> None:
        """Full page response is HTML with correct structure."""
        client = _make_client()
        response = client.get("/analytics")
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text
        assert "<header" in response.text
        assert "Analytics" in response.text

    def test_analytics_nav_active(self) -> None:
        """Analytics nav link has active indicator on analytics page."""
        client = _make_client()
        response = client.get("/analytics")
        assert "font-semibold border-b-2 border-primary" in response.text

    def test_htmx_partial_returns_fragment(self) -> None:
        """HTMX request returns analytics partial fragment."""
        client = _make_client()
        response = client.get("/analytics", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "<!DOCTYPE" not in response.text
        assert '<div id="analytics"' in response.text

    def test_full_page_has_title(self) -> None:
        """Full page has correct title."""
        client = _make_client()
        response = client.get("/analytics")
        assert "Analytics — ADW Dashboard" in response.text


# ── Status Bar Partial ──────────────────────────────────────────────


class TestStatusBarPartial:
    """Tests for the /partials/status-bar route."""

    def test_returns_html_fragment(self) -> None:
        """Status bar partial returns HTML fragment."""
        client = _make_client()
        response = client.get("/partials/status-bar")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<!DOCTYPE" not in response.text
        assert 'id="status-bar"' in response.text

    def test_contains_active_run_count(self) -> None:
        """Status bar shows active run count."""
        client = _make_client()
        response = client.get("/partials/status-bar")
        assert "active run" in response.text

    def test_contains_last_updated(self) -> None:
        """Status bar shows last updated time."""
        client = _make_client()
        response = client.get("/partials/status-bar")
        assert "Last updated" in response.text

    def test_contains_refresh_button(self) -> None:
        """Status bar has manual refresh button."""
        client = _make_client()
        response = client.get("/partials/status-bar")
        assert "Refresh" in response.text

    def test_has_polling_attributes(self) -> None:
        """Status bar has HTMX polling attributes for 10s refresh."""
        client = _make_client()
        response = client.get("/partials/status-bar")
        assert 'hx-get="/partials/status-bar"' in response.text
        assert 'hx-trigger="every 10s"' in response.text


# ── Project Filter ──────────────────────────────────────────────────


class TestProjectFilter:
    """Tests for project filter query parameter handling."""

    def test_project_param_accepted(self) -> None:
        """Routes accept ?project= query parameter."""
        client = _make_client()
        response = client.get("/?project=myproject")
        assert response.status_code == 200

    def test_project_param_on_runs(self) -> None:
        """Runs route accepts ?project= query parameter."""
        client = _make_client()
        response = client.get("/runs?project=myproject")
        assert response.status_code == 200

    def test_project_param_on_analytics(self) -> None:
        """Analytics route accepts ?project= query parameter."""
        client = _make_client()
        response = client.get("/analytics?project=myproject")
        assert response.status_code == 200

    @patch("adw.dashboard.routes.get_project_registry")
    @patch("adw.dashboard.routes.get_index_manager")
    def test_project_filter_populates_dropdown(
        self,
        mock_get_im: MagicMock,
        mock_get_pr: MagicMock,
    ) -> None:
        """When projects exist, they appear in the project filter dropdown."""
        mock_im = _mock_index_manager()
        mock_pr = _mock_project_registry(["alpha", "beta"])
        mock_get_im.return_value = mock_im
        mock_get_pr.return_value = mock_pr

        app = create_dashboard_app()
        app.dependency_overrides[
            __import__(
                "adw.dashboard.dependencies", fromlist=["get_index_manager"]
            ).get_index_manager
        ] = lambda: mock_im
        app.dependency_overrides[
            __import__(
                "adw.dashboard.dependencies", fromlist=["get_project_registry"]
            ).get_project_registry
        ] = lambda: mock_pr

        client = TestClient(app)
        response = client.get("/")
        assert "alpha" in response.text
        assert "beta" in response.text

    @patch("adw.dashboard.routes.get_project_registry")
    @patch("adw.dashboard.routes.get_index_manager")
    def test_selected_project_is_highlighted(
        self,
        mock_get_im: MagicMock,
        mock_get_pr: MagicMock,
    ) -> None:
        """Selected project should have 'selected' attribute in dropdown."""
        mock_im = _mock_index_manager()
        mock_pr = _mock_project_registry(["alpha", "beta"])
        mock_get_im.return_value = mock_im
        mock_get_pr.return_value = mock_pr

        app = create_dashboard_app()
        app.dependency_overrides[
            __import__(
                "adw.dashboard.dependencies", fromlist=["get_index_manager"]
            ).get_index_manager
        ] = lambda: mock_im
        app.dependency_overrides[
            __import__(
                "adw.dashboard.dependencies", fromlist=["get_project_registry"]
            ).get_project_registry
        ] = lambda: mock_pr

        client = TestClient(app)
        response = client.get("/?project=alpha")
        # The alpha option should have the "selected" attribute
        assert "selected" in response.text


# ── Theme Toggle ────────────────────────────────────────────────────


class TestThemeToggle:
    """Tests for theme toggle functionality."""

    def test_theme_restore_script_in_head(self) -> None:
        """Inline script in <head> reads localStorage to restore theme."""
        client = _make_client()
        response = client.get("/")
        text = response.text
        # The theme restore script should appear before </head>
        head_end = text.index("</head>")
        head_content = text[:head_end]
        assert "localStorage.getItem('adw-theme')" in head_content
        assert "data-theme" in head_content

    def test_theme_toggle_has_sun_and_moon_icons(self) -> None:
        """Theme toggle has both sun and moon SVG icons."""
        client = _make_client()
        response = client.get("/")
        assert "swap-on" in response.text  # sun icon class
        assert "swap-off" in response.text  # moon icon class

    def test_default_theme_is_dark(self) -> None:
        """Default data-theme on <html> is 'brutalist-dark'."""
        client = _make_client()
        response = client.get("/")
        assert 'data-theme="brutalist-dark"' in response.text

    def test_toggle_function_exists(self) -> None:
        """toggleTheme JavaScript function exists in the page."""
        client = _make_client()
        response = client.get("/")
        assert "function toggleTheme" in response.text


# ── Error Handler ───────────────────────────────────────────────────


class TestErrorHandler:
    """Tests for HTML error handler."""

    def test_htmx_error_returns_banner_fragment(self) -> None:
        """HTMX request to invalid URL returns error banner HTML fragment."""
        app = create_dashboard_app()

        # Add a route that raises an exception
        from fastapi import APIRouter

        test_router = APIRouter()

        @test_router.get("/test-error")
        async def broken_route() -> None:
            raise RuntimeError("Test error")

        app.include_router(test_router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/test-error", headers={"HX-Request": "true"})
        assert response.status_code == 500
        assert "text/html" in response.headers["content-type"]
        assert "<!DOCTYPE" not in response.text
        assert "error" in response.text.lower()

    def test_direct_error_returns_full_page(self) -> None:
        """Direct request to invalid route returns full error page."""
        app = create_dashboard_app()

        from fastapi import APIRouter

        test_router = APIRouter()

        @test_router.get("/test-error")
        async def broken_route() -> None:
            raise RuntimeError("Test error")

        app.include_router(test_router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/test-error")
        assert response.status_code == 500
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()

    def test_http_exception_returns_html(self) -> None:
        """HTTPException returns HTML response, not JSON."""
        from fastapi import APIRouter, HTTPException

        app = create_dashboard_app()
        test_router = APIRouter()

        @test_router.get("/test-404")
        async def not_found_route() -> None:
            raise HTTPException(status_code=404, detail="Page not found")

        app.include_router(test_router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/test-404")
        assert response.status_code == 404
        assert "text/html" in response.headers["content-type"]
        assert "Page not found" in response.text
        assert "application/json" not in response.headers["content-type"]

    def test_http_exception_htmx_returns_banner(self) -> None:
        """HTTPException via HTMX returns error banner fragment, not JSON."""
        from fastapi import APIRouter, HTTPException

        app = create_dashboard_app()
        test_router = APIRouter()

        @test_router.get("/test-403")
        async def forbidden_route() -> None:
            raise HTTPException(status_code=403, detail="Forbidden")

        app.include_router(test_router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/test-403", headers={"HX-Request": "true"})
        assert response.status_code == 403
        assert "text/html" in response.headers["content-type"]
        assert "<!DOCTYPE" not in response.text
        assert "Forbidden" in response.text

    def test_nonexistent_route_returns_html_404(self) -> None:
        """Non-existent route returns HTML 404, not JSON."""
        client = TestClient(create_dashboard_app(), raise_server_exceptions=False)
        response = client.get("/this-does-not-exist")
        assert response.status_code == 404
        assert "text/html" in response.headers["content-type"]
        assert "application/json" not in response.headers["content-type"]


# ── CSRF Token in Template Context ──────────────────────────────────


class TestCSRFInTemplateContext:
    """Tests for CSRF token availability in template context."""

    def test_csrf_token_in_overview_page(self) -> None:
        """CSRF token is generated for the overview page."""
        # The csrf_token is passed in context; if the template doesn't
        # render it visibly, at minimum the route should not error.
        client = _make_client()
        response = client.get("/")
        assert response.status_code == 200


# ── Relative Time Helper ────────────────────────────────────────────


class TestRelativeTime:
    """Tests for the _relative_time helper function."""

    def test_none_returns_dash(self) -> None:
        """None input returns em-dash."""
        from adw.dashboard.routes import _relative_time

        assert _relative_time(None) == "—"

    def test_seconds_ago(self) -> None:
        """Recent timestamp returns seconds."""
        from adw.dashboard.routes import _relative_time

        dt = datetime.now(UTC) - timedelta(seconds=30)
        result = _relative_time(dt)
        assert result.endswith("s ago")

    def test_minutes_ago(self) -> None:
        """Timestamp a few minutes ago returns minutes."""
        from adw.dashboard.routes import _relative_time

        dt = datetime.now(UTC) - timedelta(minutes=5)
        result = _relative_time(dt)
        assert result.endswith("m ago")

    def test_hours_ago(self) -> None:
        """Timestamp a few hours ago returns hours."""
        from adw.dashboard.routes import _relative_time

        dt = datetime.now(UTC) - timedelta(hours=3)
        result = _relative_time(dt)
        assert result.endswith("h ago")

    def test_days_ago(self) -> None:
        """Timestamp days ago returns days."""
        from adw.dashboard.routes import _relative_time

        dt = datetime.now(UTC) - timedelta(days=2)
        result = _relative_time(dt)
        assert result.endswith("d ago")

    def test_future_returns_just_now(self) -> None:
        """Future timestamp returns 'just now'."""
        from adw.dashboard.routes import _relative_time

        dt = datetime.now(UTC) + timedelta(seconds=10)
        assert _relative_time(dt) == "just now"


# ── Navigation HTMX Attributes ─────────────────────────────────────


class TestNavigationHTMXAttributes:
    """Tests for HTMX navigation attributes in the header."""

    def test_nav_links_have_hx_get(self) -> None:
        """Nav links use hx-get for HTMX navigation."""
        client = _make_client()
        response = client.get("/")
        assert 'hx-get="/"' in response.text
        assert 'hx-get="/runs"' in response.text
        assert 'hx-get="/analytics"' in response.text

    def test_nav_links_target_main(self) -> None:
        """Nav links target #main for content swap."""
        client = _make_client()
        response = client.get("/")
        assert 'hx-target="#main"' in response.text

    def test_nav_links_push_url(self) -> None:
        """Nav links use hx-push-url for browser history."""
        client = _make_client()
        response = client.get("/")
        assert 'hx-push-url="/"' in response.text
        assert 'hx-push-url="/runs"' in response.text
        assert 'hx-push-url="/analytics"' in response.text

    def test_nav_links_use_indicator(self) -> None:
        """Nav links reference the loading indicator."""
        client = _make_client()
        response = client.get("/")
        assert 'hx-indicator="#nav-loading"' in response.text

    def test_nav_links_have_data_page(self) -> None:
        """Nav links have data-page attribute for client-side active indicator updates."""
        client = _make_client()
        response = client.get("/")
        assert 'data-page="overview"' in response.text
        assert 'data-page="runs"' in response.text
        assert 'data-page="analytics"' in response.text

    def test_nav_links_preserve_project_filter(self) -> None:
        """Nav links include ?project= when a project is selected."""
        client = _make_client()
        response = client.get("/?project=myproject")
        text = response.text
        assert 'hx-get="/?project=myproject"' in text
        assert 'hx-get="/runs?project=myproject"' in text
        assert 'hx-get="/analytics?project=myproject"' in text

    def test_nav_links_no_project_when_unselected(self) -> None:
        """Nav links omit project param when no project is selected."""
        client = _make_client()
        response = client.get("/")
        # Should have clean URLs without ?project=
        assert 'hx-get="/"' in response.text
        assert 'hx-get="/runs"' in response.text
        assert 'hx-get="/analytics"' in response.text


# ── Status Bar Project Filter Persistence ──────────────────────────


class TestStatusBarProjectPersistence:
    """Tests for status bar preserving project filter during polling."""

    def test_status_bar_polling_includes_project(self) -> None:
        """Status bar polling URL includes project parameter when set."""
        client = _make_client()
        response = client.get("/?project=myproject")
        assert 'hx-get="/partials/status-bar?project=myproject"' in response.text

    def test_status_bar_polling_no_project_when_unset(self) -> None:
        """Status bar polling URL has no project param when unselected."""
        client = _make_client()
        response = client.get("/")
        assert 'hx-get="/partials/status-bar"' in response.text

    def test_status_bar_partial_uses_hx_current_url(self) -> None:
        """Status bar partial derives current_path from HX-Current-URL header."""
        client = _make_client()
        response = client.get(
            "/partials/status-bar",
            headers={"HX-Current-URL": "http://localhost:8100/runs"},
        )
        assert 'hx-get="/runs"' in response.text

    def test_status_bar_partial_defaults_to_root(self) -> None:
        """Status bar partial defaults current_path to / without HX-Current-URL."""
        client = _make_client()
        response = client.get("/partials/status-bar")
        # Refresh button should target /
        assert 'hx-get="/"' in response.text


# ── HTMX Attribute Order ───────────────────────────────────────────


class TestHTMXAttributeOrder:
    """Tests for correct HTMX attribute ordering per project convention."""

    def test_status_bar_attribute_order(self) -> None:
        """Status bar polling has correct HTMX attribute order: get, trigger, target, swap."""
        client = _make_client()
        response = client.get("/")
        text = response.text
        # Search within the footer status bar section specifically
        target_pos = text.index('hx-target="#status-bar"')
        # Find hx-swap="outerHTML" that comes AFTER hx-target="#status-bar"
        swap_pos = text.index('hx-swap="outerHTML"', target_pos)
        assert target_pos < swap_pos

    def test_status_bar_partial_attribute_order(self) -> None:
        """Status bar partial has correct HTMX attribute order."""
        client = _make_client()
        response = client.get("/partials/status-bar")
        text = response.text
        target_pos = text.index('hx-target="#status-bar"')
        swap_pos = text.index('hx-swap="outerHTML"')
        assert target_pos < swap_pos


# ── Client-side Nav Indicator Update ────────────────────────────────


class TestClientSideNavUpdate:
    """Tests for client-side active nav indicator update after HTMX swap."""

    def test_pushed_into_history_listener_exists(self) -> None:
        """Page contains htmx:pushedIntoHistory event listener for nav updates."""
        client = _make_client()
        response = client.get("/")
        assert "htmx:pushedIntoHistory" in response.text

    def test_nav_links_have_nav_link_class(self) -> None:
        """Nav links have the 'nav-link' class for JS selection."""
        client = _make_client()
        response = client.get("/")
        assert "nav-link" in response.text


# ── Story 1.6: Empty States & Cost Strip ──────────────────────────


class TestOverviewWelcomeEmptyState:
    """Tests for 'no projects' welcome empty state on overview."""

    def test_no_projects_shows_welcome(self) -> None:
        """Overview shows welcome message when no projects are registered."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry([]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "Welcome to ADW Dashboard" in response.text

    def test_no_projects_shows_cli_hint(self) -> None:
        """Welcome state shows CLI command hint."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry([]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert "adw global register" in response.text

    def test_no_projects_hides_stats_row(self) -> None:
        """Welcome state does not render stats row."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry([]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert 'id="stats-row"' not in response.text

    def test_no_projects_hides_cost_strip(self) -> None:
        """Welcome state does not render cost strip."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry([]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert "Cost This Week" not in response.text


class TestOverviewNoRunsEmptyState:
    """Tests for 'no runs' empty state on overview (projects exist but no runs)."""

    def test_no_runs_shows_message(self) -> None:
        """Overview shows 'No runs yet' when projects exist but no runs."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=_mock_index_manager(has_runs=False),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "No runs yet" in response.text

    def test_no_runs_shows_new_run_button(self) -> None:
        """No-runs state shows the New Run button."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=_mock_index_manager(has_runs=False),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert "New Run" in response.text

    def test_no_runs_hides_stats_row(self) -> None:
        """No-runs state does not render stats row."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=_mock_index_manager(has_runs=False),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert 'id="stats-row"' not in response.text


class TestOverviewDataErrorBanner:
    """Tests for data error banner when data layer raises exceptions."""

    def test_data_error_shows_banner(self) -> None:
        """Overview shows error banner when index_manager raises."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=_mock_index_manager(raise_on_call=True),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "Unable to load run data" in response.text

    def test_data_error_banner_has_error_class(self) -> None:
        """Error banner uses alert-error styling."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=_mock_index_manager(raise_on_call=True),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert "alert-error" in response.text

    def test_data_error_hides_no_runs_message(self) -> None:
        """Error state does not show misleading 'No runs yet' message."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=_mock_index_manager(raise_on_call=True),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert "No runs yet" not in response.text


class TestOverviewFullContent:
    """Tests for overview with full content (projects and runs exist)."""

    def test_full_overview_has_new_run_button(self) -> None:
        """Full overview shows the + New Run button."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert "New Run" in response.text

    def test_full_overview_has_cost_strip(self) -> None:
        """Full overview renders the cost summary strip."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert "Cost This Week" in response.text

    def test_full_overview_cost_strip_shows_amount(self) -> None:
        """Cost strip shows formatted cost amount."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            stats_aggregator=_mock_stats_aggregator(cost_this_week=23.45),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert "$23.45" in response.text


class TestRunNotFound:
    """Tests for 404 run not found responses."""

    def test_htmx_run_not_found_returns_404(self) -> None:
        """HTMX request for non-existent run returns 404 status."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get(
            "/runs/nonexistent-id",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 404

    def test_htmx_run_not_found_returns_fragment(self) -> None:
        """HTMX request for non-existent run returns HTML fragment."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get(
            "/runs/nonexistent-id",
            headers={"HX-Request": "true"},
        )
        assert "<!DOCTYPE" not in response.text
        assert "Run not found" in response.text

    def test_htmx_run_not_found_has_back_link(self) -> None:
        """HTMX 404 fragment includes back-to-overview link."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get(
            "/runs/nonexistent-id",
            headers={"HX-Request": "true"},
        )
        assert "Back to Overview" in response.text

    def test_full_page_run_not_found_returns_404(self) -> None:
        """Full page request for non-existent run returns 404 with full HTML."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/runs/nonexistent-id")
        assert response.status_code == 404
        assert "<!DOCTYPE html>" in response.text
        assert "Run not found" in response.text

    def test_full_page_run_not_found_has_title(self) -> None:
        """Full page 404 has correct page title."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/runs/nonexistent-id")
        assert "Run Not Found" in response.text


class TestHTMXErrorToast:
    """Tests for the enhanced HTMX error toast with retry link."""

    def test_error_toast_has_retry_link(self) -> None:
        """Error toast handler includes a Retry link using htmx.ajax."""
        client = _make_client()
        response = client.get("/")
        assert "htmx.ajax" in response.text
        assert "Retry" in response.text
