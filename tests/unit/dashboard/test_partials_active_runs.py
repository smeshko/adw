"""Tests for Story 1.4: Active Runs Section with Live Updates.

Covers the /partials/active-runs route, phase pipeline computation,
elapsed time formatting, empty state, project filter, and template
rendering with HTMX attributes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from adw.dashboard.server import create_dashboard_app


def _make_client() -> TestClient:
    """Create a TestClient for the dashboard app."""
    return TestClient(create_dashboard_app())


def _make_index_entry(
    *,
    run_id: str = "01JMXXXXXXXXXXXXXXXXXXXXXX",
    project_name: str = "my-api",
    feature_description: str = "Add user authentication feature",
    started_at: datetime | None = None,
    status: str = "running",
    phase_reached: str = "build",
    phases_completed: list[str] | None = None,
) -> MagicMock:
    """Build a mock IndexEntry for active run tests."""
    entry = MagicMock()
    entry.run_id = run_id
    entry.project_name = project_name
    entry.project_path = f"/path/to/{project_name}"
    entry.feature_description = feature_description
    entry.started_at = started_at or (datetime.now(UTC) - timedelta(minutes=5))
    entry.completed_at = None
    entry.status = status
    entry.phase_reached = phase_reached
    entry.phases_completed = phases_completed or ["plan"]
    return entry


def _make_run_context(
    *,
    run_id: str = "01JMXXXXXXXXXXXXXXXXXXXXXX",
    current_phase: str = "build",
    phase_history: list[str] | None = None,
) -> MagicMock:
    """Build a mock RunContext for active run tests."""
    ctx = MagicMock()
    ctx.run_id = run_id
    ctx.current_phase = current_phase
    ctx.phase_history = phase_history or ["plan"]
    return ctx


class TestActiveRunsPartialRoute:
    """Tests for GET /partials/active-runs route."""

    def test_returns_html_fragment(self) -> None:
        """Active runs partial returns HTML fragment, not full page."""
        client = _make_client()
        response = client.get("/partials/active-runs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<!DOCTYPE" not in response.text

    def test_empty_state_returns_empty_div(self) -> None:
        """When no active runs exist, returns empty div with id and polling attributes."""
        from adw.dashboard.dependencies import get_index_manager

        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = []

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        assert response.status_code == 200
        assert 'id="active-runs"' in response.text
        assert "Active Runs" not in response.text

    def test_empty_state_preserves_polling(self) -> None:
        """Empty state div retains hx-get and hx-trigger for continued polling."""
        from adw.dashboard.dependencies import get_index_manager

        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = []

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        assert 'hx-get="/partials/active-runs"' in response.text
        assert 'hx-trigger="every 3s"' in response.text
        assert 'hx-swap="outerHTML"' in response.text

    @patch("adw.dashboard.partials.ContextManager")
    def test_with_active_runs_shows_cards(self, mock_cm_cls: MagicMock) -> None:
        """When active runs exist, response contains run card elements."""
        from adw.dashboard.dependencies import get_index_manager

        entry = _make_index_entry(
            project_name="my-api",
            feature_description="Add user auth",
            phase_reached="build",
            phases_completed=["plan"],
        )

        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = [entry]

        mock_ctx = _make_run_context(current_phase="build", phase_history=["plan"])
        mock_cm_cls.return_value.load.return_value = mock_ctx

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        assert response.status_code == 200
        assert "my-api" in response.text
        assert "Add user auth" in response.text
        assert "Active Runs" in response.text

    @patch("adw.dashboard.partials.ContextManager")
    def test_count_badge_shows_run_count(self, mock_cm_cls: MagicMock) -> None:
        """Active runs header shows count badge with correct number."""
        from adw.dashboard.dependencies import get_index_manager

        entries = [
            _make_index_entry(run_id="01JMXXXXXXXXXXXXXXXXXXXXXA", project_name="api-1"),
            _make_index_entry(run_id="01JMXXXXXXXXXXXXXXXXXXXXXB", project_name="api-2"),
        ]

        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = entries

        mock_ctx = _make_run_context()
        mock_cm_cls.return_value.load.return_value = mock_ctx

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        assert "badge" in response.text
        assert ">2<" in response.text

    @patch("adw.dashboard.partials.ContextManager")
    def test_project_filter_scopes_results(self, mock_cm_cls: MagicMock) -> None:
        """Project filter query parameter is passed to index manager."""
        from adw.dashboard.dependencies import get_index_manager

        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = []

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        client.get("/partials/active-runs?project=my-api")
        mock_im.get_recent_runs.assert_called_with(
            status="running", project_name="my-api"
        )

    @patch("adw.dashboard.partials.ContextManager")
    def test_polling_attributes_present(self, mock_cm_cls: MagicMock) -> None:
        """Active runs section has correct HTMX polling attributes."""
        from adw.dashboard.dependencies import get_index_manager

        entry = _make_index_entry()
        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = [entry]

        mock_ctx = _make_run_context()
        mock_cm_cls.return_value.load.return_value = mock_ctx

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        assert 'hx-get="/partials/active-runs"' in response.text
        assert 'hx-trigger="every 3s"' in response.text
        assert 'hx-swap="outerHTML"' in response.text

    @patch("adw.dashboard.partials.ContextManager")
    def test_card_has_navigation_attributes(self, mock_cm_cls: MagicMock) -> None:
        """Each active run card has HTMX navigation attributes for clicking."""
        from adw.dashboard.dependencies import get_index_manager

        entry = _make_index_entry(run_id="01JMXXXXXXXXXXXXXXXXXXXXXX")
        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = [entry]

        mock_ctx = _make_run_context()
        mock_cm_cls.return_value.load.return_value = mock_ctx

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        assert 'hx-get="/runs/01JMXXXXXXXXXXXXXXXXXXXXXX"' in response.text
        assert 'hx-target="#main"' in response.text
        assert 'hx-push-url="/runs/01JMXXXXXXXXXXXXXXXXXXXXXX"' in response.text

    @patch("adw.dashboard.partials.ContextManager")
    def test_card_shows_elapsed_time(self, mock_cm_cls: MagicMock) -> None:
        """Active run card displays elapsed time in font-mono."""
        from adw.dashboard.dependencies import get_index_manager

        entry = _make_index_entry(
            started_at=datetime.now(UTC) - timedelta(minutes=3, seconds=42),
        )
        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = [entry]

        mock_ctx = _make_run_context()
        mock_cm_cls.return_value.load.return_value = mock_ctx

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        assert "font-mono" in response.text
        # Should show approximately "3m 42s" (may be off by 1s due to test timing)
        assert "3m" in response.text

    @patch("adw.dashboard.partials.ContextManager")
    def test_feature_description_truncated(self, mock_cm_cls: MagicMock) -> None:
        """Long feature descriptions are truncated to ~40 chars with ellipsis."""
        from adw.dashboard.dependencies import get_index_manager

        long_desc = "This is a very long feature description that exceeds forty characters easily"
        entry = _make_index_entry(feature_description=long_desc)
        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = [entry]

        mock_ctx = _make_run_context()
        mock_cm_cls.return_value.load.return_value = mock_ctx

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        # The full description should NOT appear
        assert long_desc not in response.text
        # An ellipsis character should appear
        assert "…" in response.text

    @patch("adw.dashboard.partials.ContextManager")
    def test_graceful_fallback_when_context_unavailable(
        self, mock_cm_cls: MagicMock
    ) -> None:
        """When RunContext cannot be loaded, falls back to IndexEntry data."""
        from adw.dashboard.dependencies import get_index_manager
        from adw.exceptions import StateError

        entry = _make_index_entry(
            phase_reached="validate",
            phases_completed=["plan", "build"],
        )
        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = [entry]

        mock_cm_cls.return_value.load.side_effect = StateError(
            code="CONTEXT_NOT_FOUND",
            message="Context not found",
        )

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        assert response.status_code == 200
        assert entry.project_name in response.text

    @patch("adw.dashboard.partials.ContextManager")
    def test_phase_pipeline_renders_steps(self, mock_cm_cls: MagicMock) -> None:
        """Phase pipeline shows all 5 phases with correct step classes."""
        from adw.dashboard.dependencies import get_index_manager

        entry = _make_index_entry(
            phase_reached="validate",
            phases_completed=["plan", "build"],
        )
        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = [entry]

        mock_ctx = _make_run_context(
            current_phase="validate",
            phase_history=["plan", "build"],
        )
        mock_cm_cls.return_value.load.return_value = mock_ctx

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs")
        text = response.text
        assert "steps" in text
        assert "step-success" in text  # completed phases
        assert "step-warning" in text  # active phase
        assert "Plan" in text
        assert "Build" in text

    def test_no_project_filter_queries_all(self) -> None:
        """Without project filter, queries all runs."""
        from adw.dashboard.dependencies import get_index_manager

        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = []

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        client.get("/partials/active-runs")
        mock_im.get_recent_runs.assert_called_with(
            status="running", project_name=None
        )

    @patch("adw.dashboard.partials.ContextManager")
    def test_polling_url_includes_project_filter(
        self, mock_cm_cls: MagicMock
    ) -> None:
        """When project filter is set, polling URL includes project parameter."""
        from adw.dashboard.dependencies import get_index_manager

        mock_im = MagicMock()
        mock_im.get_recent_runs.return_value = []

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/partials/active-runs?project=my-api")
        assert 'hx-get="/partials/active-runs?project=my-api"' in response.text


class TestPhasePipelineComputation:
    """Tests for phase pipeline status computation."""

    def test_completed_active_pending_mapping(self) -> None:
        """Given phases_completed and current_phase, pipeline statuses are correct."""
        from adw.dashboard.partials import _build_phase_pipeline

        phases = _build_phase_pipeline(
            phases_completed=["plan", "build"],
            current_phase="validate",
        )
        assert len(phases) == 5
        assert phases[0] == {"name": "Plan", "status": "completed"}
        assert phases[1] == {"name": "Build", "status": "completed"}
        assert phases[2] == {"name": "Valid", "status": "active"}
        assert phases[3] == {"name": "Doc", "status": "pending"}
        assert phases[4] == {"name": "Ship", "status": "pending"}

    def test_first_phase_active(self) -> None:
        """When no phases completed and plan is active, only plan is active."""
        from adw.dashboard.partials import _build_phase_pipeline

        phases = _build_phase_pipeline(
            phases_completed=[],
            current_phase="plan",
        )
        assert phases[0] == {"name": "Plan", "status": "active"}
        assert phases[1] == {"name": "Build", "status": "pending"}

    def test_all_completed_except_ship(self) -> None:
        """When 4 phases completed and ship is active."""
        from adw.dashboard.partials import _build_phase_pipeline

        phases = _build_phase_pipeline(
            phases_completed=["plan", "build", "validate", "document"],
            current_phase="ship",
        )
        assert phases[0] == {"name": "Plan", "status": "completed"}
        assert phases[1] == {"name": "Build", "status": "completed"}
        assert phases[2] == {"name": "Valid", "status": "completed"}
        assert phases[3] == {"name": "Doc", "status": "completed"}
        assert phases[4] == {"name": "Ship", "status": "active"}


class TestElapsedTimeFormatting:
    """Tests for elapsed time formatting."""

    def test_format_elapsed_seconds_only(self) -> None:
        """Elapsed time under a minute shows 0m Xs."""
        from adw.dashboard.partials import _format_elapsed

        result = _format_elapsed(timedelta(seconds=42))
        assert result == "0m 42s"

    def test_format_elapsed_minutes_and_seconds(self) -> None:
        """Elapsed time with minutes shows Xm Ys."""
        from adw.dashboard.partials import _format_elapsed

        result = _format_elapsed(timedelta(minutes=3, seconds=15))
        assert result == "3m 15s"

    def test_format_elapsed_hours(self) -> None:
        """Elapsed time over an hour shows minutes correctly."""
        from adw.dashboard.partials import _format_elapsed

        result = _format_elapsed(timedelta(hours=1, minutes=5, seconds=30))
        assert result == "65m 30s"

    def test_format_elapsed_zero(self) -> None:
        """Zero elapsed time shows 0m 0s."""
        from adw.dashboard.partials import _format_elapsed

        result = _format_elapsed(timedelta(seconds=0))
        assert result == "0m 0s"


class TestActiveRunsInOverview:
    """Tests for active runs section appearing in the overview page."""

    @patch("adw.dashboard.partials.ContextManager")
    def test_overview_includes_active_runs_section(
        self, mock_cm_cls: MagicMock
    ) -> None:
        """Overview page includes the active runs section."""
        from adw.dashboard.dependencies import get_index_manager

        entry = _make_index_entry()
        mock_im = MagicMock()

        def get_recent_side_effect(**kwargs):
            if kwargs.get("status") == "running":
                return [entry]
            return [entry]

        mock_im.get_recent_runs.side_effect = get_recent_side_effect

        mock_ctx = _make_run_context()
        mock_cm_cls.return_value.load.return_value = mock_ctx

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert 'id="active-runs"' in response.text

    def test_overview_no_active_runs_hides_section(self) -> None:
        """Overview page with no active runs shows empty active runs div."""
        from adw.dashboard.dependencies import get_index_manager

        entry = _make_index_entry()
        mock_im = MagicMock()

        def get_recent_side_effect(**kwargs):
            if kwargs.get("status") == "running":
                return []  # No active runs
            return [entry]  # Has runs (for has_runs check)

        mock_im.get_recent_runs.side_effect = get_recent_side_effect

        app = create_dashboard_app()
        app.dependency_overrides[get_index_manager] = lambda: mock_im
        client = TestClient(app)

        response = client.get("/", headers={"HX-Request": "true"})
        assert response.status_code == 200
        # Should have the empty active-runs div for polling
        assert 'id="active-runs"' in response.text
        # But no "Active Runs" header
        assert "Active Runs" not in response.text
