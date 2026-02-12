"""Tests for keyboard help partial endpoint and keyboard navigation integration.

Covers the GET /partials/keyboard-help route, verifying the modal
structure, keyboard shortcut badges, and dialog attributes.  Also
verifies data-navigable-row attributes in list partials and the
keyboard shortcut script block in the base template.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from adw.dashboard.server import create_dashboard_app
from adw.models.stats import GlobalStatistics, TokenUsage


def _make_client() -> TestClient:
    """Create a TestClient with minimal mocks for the keyboard help route."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()

    # Keyboard help is a static partial — no data dependencies needed,
    # but the app requires these overrides to boot.
    mock_im = MagicMock()
    mock_im.get_recent_runs.return_value = []
    mock_sa = MagicMock()
    mock_pr = MagicMock()
    mock_pr.get_all.return_value = []

    app.dependency_overrides[dependencies.get_index_manager] = lambda: mock_im
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: mock_sa
    app.dependency_overrides[dependencies.get_project_registry] = lambda: mock_pr

    return TestClient(app)


def _make_run_entry(
    run_id: str = "01KDSG2VDHNK0W4HSCZWJZXWSQ",
    project_name: str = "test-project",
    status: str = "completed",
) -> MagicMock:
    """Build a mock IndexEntry for list rendering."""
    entry = MagicMock()
    entry.run_id = run_id
    entry.project_name = project_name
    entry.project_path = "/tmp/test"
    entry.feature_description = "Test feature"
    entry.status = status
    entry.phase_reached = "build"
    entry.phases_completed = ["plan"]
    entry.started_at = datetime.now(UTC) - timedelta(minutes=10)
    entry.completed_at = datetime.now(UTC)
    return entry


def _make_client_with_runs(entries: list[MagicMock]) -> TestClient:
    """Create a TestClient with mock data for runs."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()

    mock_im = MagicMock()

    def get_recent_side_effect(**kwargs):
        if kwargs.get("status") == "running":
            return []
        limit = kwargs.get("limit", 10)
        return entries[:limit]

    mock_im.get_recent_runs.side_effect = get_recent_side_effect

    mock_sa = MagicMock()
    stats = GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=len(entries),
        tokens=TokenUsage(input_tokens=100, output_tokens=50),
        estimated_cost=0.50,
        tokens_this_week=TokenUsage(input_tokens=50, output_tokens=25),
        cost_this_week=0.25,
    )
    mock_sa.get_global_stats.return_value = stats
    mock_sa.get_daily_token_counts.return_value = []

    mock_pr = MagicMock()
    mock_pr.get_all.return_value = []

    app.dependency_overrides[dependencies.get_index_manager] = lambda: mock_im
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: mock_sa
    app.dependency_overrides[dependencies.get_project_registry] = lambda: mock_pr

    return TestClient(app)


class TestKeyboardHelpPartial:
    """Tests for GET /partials/keyboard-help."""

    def test_returns_200(self) -> None:
        client = _make_client()
        resp = client.get("/partials/keyboard-help")
        assert resp.status_code == 200

    def test_returns_html(self) -> None:
        client = _make_client()
        resp = client.get("/partials/keyboard-help")
        assert "text/html" in resp.headers["content-type"]

    def test_contains_dialog_element(self) -> None:
        client = _make_client()
        resp = client.get("/partials/keyboard-help")
        body = resp.text
        assert '<dialog id="keyboard-help-dialog"' in body
        assert "modal-open" in body

    def test_contains_kbd_badges(self) -> None:
        client = _make_client()
        resp = client.get("/partials/keyboard-help")
        body = resp.text
        # Should have kbd elements for shortcut keys
        assert "kbd kbd-sm" in body
        assert ">?</kbd>" in body
        assert ">g</kbd>" in body
        assert ">h</kbd>" in body
        assert ">r</kbd>" in body
        assert ">a</kbd>" in body
        assert ">j</kbd>" in body
        assert ">k</kbd>" in body
        assert ">n</kbd>" in body
        assert ">Esc</kbd>" in body
        assert ">Enter</kbd>" in body
        assert ">/</kbd>" in body

    def test_contains_shortcut_descriptions(self) -> None:
        client = _make_client()
        resp = client.get("/partials/keyboard-help")
        body = resp.text
        assert "Toggle this overlay" in body
        assert "Go to Overview" in body
        assert "Go to Runs" in body
        assert "Go to Analytics" in body
        assert "Refresh" in body
        assert "Next item" in body
        assert "Previous item" in body
        assert "Open selected run" in body
        assert "New Run" in body
        assert "Focus search input" in body
        assert "Close modal / go back" in body

    def test_contains_section_headers(self) -> None:
        client = _make_client()
        resp = client.get("/partials/keyboard-help")
        body = resp.text
        assert "Global" in body
        assert "Lists" in body
        assert "Page" in body

    def test_contains_close_button(self) -> None:
        client = _make_client()
        resp = client.get("/partials/keyboard-help")
        body = resp.text
        assert "modal-backdrop" in body
        assert "modal-action" in body

    def test_contains_modal_container_clear(self) -> None:
        """Close button should clear #modal-container."""
        client = _make_client()
        resp = client.get("/partials/keyboard-help")
        body = resp.text
        assert "modal-container" in body


class TestNavigableRowAttributes:
    """Verify data-navigable-row attributes are present in list templates."""

    def test_recent_runs_has_navigable_rows(self) -> None:
        entries = [_make_run_entry()]
        client = _make_client_with_runs(entries)
        resp = client.get("/partials/recent-runs")
        assert resp.status_code == 200
        assert "data-navigable-row" in resp.text

    def test_runs_table_has_navigable_rows(self) -> None:
        """Verify runs_table.html template contains data-navigable-row.

        The runs list page uses get_paginated_runs which needs complex mock
        setup. Instead, verify the template source directly since the
        recent_runs partial (tested above) proves the pattern works.
        """
        from pathlib import Path

        template_path = (
            Path(__file__).resolve().parents[3]
            / "src" / "adw" / "dashboard" / "templates" / "partials" / "runs_table.html"
        )
        content = template_path.read_text()
        assert "data-navigable-row" in content


class TestKeyboardShortcutScript:
    """Verify the keyboard shortcut script is present in base pages."""

    def test_overview_page_has_keyboard_script(self) -> None:
        client = _make_client()
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Keyboard shortcuts" in resp.text
        assert "pendingG" in resp.text

    def test_keyboard_script_has_input_guard(self) -> None:
        client = _make_client()
        resp = client.get("/")
        body = resp.text
        assert "input, textarea, select, [contenteditable]" in body

    def test_keyboard_script_has_g_prefix_handler(self) -> None:
        client = _make_client()
        resp = client.get("/")
        body = resp.text
        assert 'data-page="overview"' in body
        assert 'data-page="runs"' in body
        assert 'data-page="analytics"' in body
