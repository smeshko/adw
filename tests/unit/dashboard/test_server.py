"""Tests for dashboard server application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from adw.dashboard.server import create_dashboard_app


class TestCreateDashboardApp:
    """Tests for the create_dashboard_app factory."""

    def test_returns_fastapi_instance(self) -> None:
        """Factory returns a FastAPI application."""
        app = create_dashboard_app()
        assert isinstance(app, FastAPI)

    def test_has_dashboard_title(self) -> None:
        """App has dashboard title."""
        app = create_dashboard_app()
        assert app.title == "ADW Dashboard"

    def test_state_contains_host_and_port(self) -> None:
        """State contains dashboard_host and dashboard_port."""
        app = create_dashboard_app(host="0.0.0.0", port=9000)
        assert app.state.dashboard_host == "0.0.0.0"
        assert app.state.dashboard_port == 9000

    def test_default_host_is_localhost(self) -> None:
        """Default host is 127.0.0.1."""
        app = create_dashboard_app()
        assert app.state.dashboard_host == "127.0.0.1"

    def test_default_port_is_8100(self) -> None:
        """Default port is 8100."""
        app = create_dashboard_app()
        assert app.state.dashboard_port == 8100

    def test_templates_in_state(self) -> None:
        """Jinja2Templates object is available on app.state."""
        app = create_dashboard_app()
        assert hasattr(app.state, "templates")

    def test_health_endpoint(self) -> None:
        """Dashboard health endpoint returns 200."""
        app = create_dashboard_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "dashboard"

    def test_health_includes_request_id(self) -> None:
        """Health endpoint response has x-request-id from shared middleware."""
        app = create_dashboard_app()
        client = TestClient(app)
        response = client.get("/health")
        assert "x-request-id" in response.headers

    def test_overview_page_returns_html(self) -> None:
        """Overview page returns HTML content."""
        app = create_dashboard_app()
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "ADW Dashboard" in response.text

    def test_htmx_request_returns_partial(self) -> None:
        """HTMX request to overview returns partial (no full HTML wrapper)."""
        app = create_dashboard_app()
        client = TestClient(app)
        response = client.get("/", headers={"HX-Request": "true"})
        assert response.status_code == 200
        # Partial should not contain <html> tag
        assert "<!DOCTYPE" not in response.text
        assert "overview" in response.text.lower()

    def test_static_files_served(self) -> None:
        """Static files (htmx.min.js) are accessible."""
        app = create_dashboard_app()
        client = TestClient(app)
        response = client.get("/static/htmx.min.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")


class TestCSRFIntegration:
    """Tests for CSRF protection on the dashboard."""

    def test_post_without_csrf_returns_403(self) -> None:
        """POST request without CSRF token is rejected."""
        from fastapi import APIRouter, Depends

        from adw.dashboard.dependencies import validate_csrf

        app = create_dashboard_app()
        router = APIRouter()

        @router.post("/test-mutation")
        async def test_mutation(_: None = Depends(validate_csrf)) -> dict[str, str]:
            return {"status": "ok"}

        app.include_router(router)
        client = TestClient(app)

        response = client.post("/test-mutation")
        assert response.status_code == 403

    def test_post_with_valid_csrf_header_succeeds(self) -> None:
        """POST request with valid CSRF header succeeds."""
        from unittest.mock import MagicMock

        from fastapi import APIRouter, Depends

        from adw.dashboard.dependencies import generate_csrf_token, validate_csrf

        app = create_dashboard_app()
        router = APIRouter()

        @router.post("/test-mutation")
        async def test_mutation(_: None = Depends(validate_csrf)) -> dict[str, str]:
            return {"status": "ok"}

        app.include_router(router)
        client = TestClient(app)

        # Generate a valid token
        mock_request = MagicMock()
        token = generate_csrf_token(mock_request)

        response = client.post(
            "/test-mutation",
            headers={"x-csrf-token": token},
        )
        assert response.status_code == 200

    def test_post_with_invalid_csrf_header_returns_403(self) -> None:
        """POST request with invalid CSRF header is rejected."""
        from fastapi import APIRouter, Depends

        from adw.dashboard.dependencies import validate_csrf

        app = create_dashboard_app()
        router = APIRouter()

        @router.post("/test-mutation")
        async def test_mutation(_: None = Depends(validate_csrf)) -> dict[str, str]:
            return {"status": "ok"}

        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/test-mutation",
            headers={"x-csrf-token": "invalid:token"},
        )
        assert response.status_code == 403
