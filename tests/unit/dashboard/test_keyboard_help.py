"""Tests for keyboard help partial endpoint.

Covers the GET /partials/keyboard-help route, verifying the modal
structure, keyboard shortcut badges, and dialog attributes.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from adw.dashboard.server import create_dashboard_app


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
