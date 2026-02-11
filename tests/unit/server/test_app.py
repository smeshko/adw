"""Tests for shared server factory (server/app.py)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient

from adw.server.app import create_app


class TestCreateApp:
    """Tests for the create_app factory function."""

    def test_returns_fastapi_instance(self) -> None:
        """Factory returns a FastAPI application."""
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_custom_title_and_description(self) -> None:
        """Factory accepts custom title and description."""
        app = create_app(title="Test App", description="A test", version="2.0.0")
        assert app.title == "Test App"
        assert app.description == "A test"
        assert app.version == "2.0.0"

    def test_state_seeded_from_dict(self) -> None:
        """State dict values are set on app.state."""
        app = create_app(state={"foo": "bar", "count": 42})
        assert app.state.foo == "bar"
        assert app.state.count == 42

    def test_lifespan_accepted(self) -> None:
        """Factory accepts a lifespan context manager."""
        started = False

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
            nonlocal started
            started = True
            yield

        app = create_app(lifespan=lifespan)
        with TestClient(app):
            assert started is True


class TestRequestIDMiddleware:
    """Tests for the global RequestIDMiddleware."""

    def test_response_includes_request_id_header(self) -> None:
        """Every response includes x-request-id header."""
        app = create_app()
        router = APIRouter()

        @router.get("/test")
        async def test_endpoint() -> dict[str, Any]:
            return {"ok": "yes"}

        app.include_router(router)
        client = TestClient(app)

        response = client.get("/test")
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) == 36

    def test_request_id_propagated_from_client(self) -> None:
        """Client-supplied x-request-id is preserved."""
        app = create_app()
        router = APIRouter()

        @router.get("/echo-id")
        async def echo_id() -> dict[str, Any]:
            return {"ok": "yes"}

        app.include_router(router)
        client = TestClient(app)

        custom_id = "my-custom-request-id-12345678"
        response = client.get("/echo-id", headers={"x-request-id": custom_id})
        assert response.headers["x-request-id"] == custom_id

    def test_request_state_has_request_id(self) -> None:
        """request.state.request_id is set by middleware."""
        app = create_app()
        router = APIRouter()
        captured_ids: list[str] = []

        @router.get("/capture")
        async def capture(request: Request) -> dict[str, str]:
            captured_ids.append(request.state.request_id)
            return {"id": request.state.request_id}

        app.include_router(router)
        client = TestClient(app)

        response = client.get("/capture")
        assert response.status_code == 200
        assert len(captured_ids) == 1
        assert len(captured_ids[0]) == 36

    def test_multiple_requests_get_unique_ids(self) -> None:
        """Each request gets a unique ID when not provided."""
        app = create_app()
        router = APIRouter()

        @router.get("/test")
        async def test_endpoint() -> dict[str, Any]:
            return {"ok": "yes"}

        app.include_router(router)
        client = TestClient(app)

        ids = set()
        for _ in range(5):
            response = client.get("/test")
            ids.add(response.headers["x-request-id"])

        assert len(ids) == 5


class TestRouterComposition:
    """Tests for feature-based APIRouter composition."""

    def test_multiple_routers_can_be_included(self) -> None:
        """Multiple routers compose into one app."""
        app = create_app()

        router_a = APIRouter(prefix="/a")
        router_b = APIRouter(prefix="/b")

        @router_a.get("/hello")
        async def hello_a() -> dict[str, str]:
            return {"from": "a"}

        @router_b.get("/hello")
        async def hello_b() -> dict[str, str]:
            return {"from": "b"}

        app.include_router(router_a)
        app.include_router(router_b)

        client = TestClient(app)
        assert client.get("/a/hello").json() == {"from": "a"}
        assert client.get("/b/hello").json() == {"from": "b"}
