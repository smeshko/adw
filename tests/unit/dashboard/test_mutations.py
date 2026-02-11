"""Tests for Story 3.1: Dashboard mutations (POST /runs/start).

Covers CSRF validation, form validation, run trigger invocation,
success response, and error handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from adw.dashboard.dependencies import generate_csrf_token
from adw.dashboard.server import create_dashboard_app


# ── Helpers ────────────────────────────────────────────────────────


def _mock_project_registry(
    project_names: list[str] | None = None,
    paths: list[str] | None = None,
) -> MagicMock:
    """Build a mock ProjectRegistryManager with project list."""
    mock = MagicMock()
    projects = []
    names = project_names or []
    project_paths = paths or [f"/projects/{n}" for n in names]
    for name, path in zip(names, project_paths):
        p = MagicMock()
        p.name = name
        p.path = path
        projects.append(p)
    mock.get_all.return_value = projects

    def get_by_path_side_effect(path):
        for p in projects:
            if p.path == str(path):
                return p
        return None

    mock.get_by_path.side_effect = get_by_path_side_effect
    return mock


def _mock_run_trigger(success: bool = True, process_id: int = 42, error: str | None = None) -> MagicMock:
    """Build a mock RunTrigger."""
    from adw.core.run_trigger import RunTriggerResult

    mock = MagicMock()
    result = RunTriggerResult(
        success=success,
        process_id=process_id if success else None,
        error=error,
    )
    mock.start_run = AsyncMock(return_value=result)
    return mock


def _mock_index_manager() -> MagicMock:
    """Build a minimal mock IndexManager."""
    mock = MagicMock()
    mock.get_recent_runs.return_value = []
    return mock


def _mock_stats_aggregator() -> MagicMock:
    """Build a minimal mock StatsAggregator."""
    from datetime import UTC, datetime

    from adw.models.stats import GlobalStatistics

    mock = MagicMock()
    mock.get_global_stats.return_value = GlobalStatistics(generated_at=datetime.now(UTC))
    mock.get_daily_token_counts.return_value = []
    return mock


def _make_client_with_mocks(
    project_registry: MagicMock | None = None,
    run_trigger: MagicMock | None = None,
) -> TestClient:
    """Create a TestClient with dependency overrides for mutations testing."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    pr = project_registry or _mock_project_registry()
    rt = run_trigger or _mock_run_trigger()
    im = _mock_index_manager()
    sa = _mock_stats_aggregator()

    app.dependency_overrides[dependencies.get_project_registry] = lambda: pr
    app.dependency_overrides[dependencies.get_run_trigger] = lambda: rt
    app.dependency_overrides[dependencies.get_index_manager] = lambda: im
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: sa

    return TestClient(app)


def _get_csrf_token(client: TestClient) -> str:
    """Get a valid CSRF token by hitting a page route."""
    # The overview route generates a CSRF token; we extract it from cookies/state
    # But since CSRF tokens are HMAC-based, we can generate one directly.
    from starlette.testclient import TestClient as _TC
    from fastapi import Request
    from unittest.mock import MagicMock

    # Generate a token using the module function
    mock_request = MagicMock(spec=Request)
    mock_request.state = MagicMock()
    return generate_csrf_token(mock_request)


# ── CSRF Validation ────────────────────────────────────────────────


class TestCSRFValidation:
    """Tests for CSRF protection on /runs/start."""

    def test_missing_csrf_returns_403(self) -> None:
        """POST without CSRF token returns 403."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.post(
            "/runs/start",
            data={"project": "/projects/my-project", "feature": "Add login"},
        )
        assert response.status_code == 403

    def test_invalid_csrf_returns_403(self) -> None:
        """POST with invalid CSRF token returns 403."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add login",
                "csrf_token": "invalid:token",
            },
        )
        assert response.status_code == 403

    def test_valid_csrf_passes(self) -> None:
        """POST with valid CSRF token does not return 403."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add login",
                "csrf_token": token,
            },
        )
        assert response.status_code != 403


# ── Form Validation ────────────────────────────────────────────────


class TestFormValidation:
    """Tests for form input validation."""

    def test_empty_project_shows_error(self) -> None:
        """Missing project shows validation error."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={"project": "", "feature": "Add login", "csrf_token": token},
        )
        assert response.status_code == 200
        assert "Please select a project" in response.text

    def test_empty_feature_shows_error(self) -> None:
        """Missing feature shows validation error."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "",
                "csrf_token": token,
            },
        )
        assert response.status_code == 200
        assert "describe the feature" in response.text.lower()

    def test_both_empty_shows_both_errors(self) -> None:
        """Both fields empty shows both error messages."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={"project": "", "feature": "", "csrf_token": token},
        )
        assert "Please select a project" in response.text
        assert "describe the feature" in response.text.lower()

    def test_whitespace_only_feature_shows_error(self) -> None:
        """Whitespace-only feature is treated as empty."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "   ",
                "csrf_token": token,
            },
        )
        assert "describe the feature" in response.text.lower()

    def test_unregistered_project_shows_error(self) -> None:
        """Project not in registry shows error."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/nonexistent/project",
                "feature": "Add login",
                "csrf_token": token,
            },
        )
        assert "not found or not registered" in response.text.lower()

    def test_validation_error_re_renders_modal(self) -> None:
        """Validation error re-renders the modal form."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={"project": "", "feature": "", "csrf_token": token},
        )
        assert "Start New Run" in response.text
        assert "new-run-dialog" in response.text

    def test_validation_error_preserves_feature_input(self) -> None:
        """Validation error preserves the feature textarea value."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "",
                "feature": "My awesome feature",
                "csrf_token": token,
            },
        )
        assert "My awesome feature" in response.text


# ── Successful Run Start ───────────────────────────────────────────


class TestSuccessfulRunStart:
    """Tests for successful run creation."""

    def test_success_returns_confirmation(self) -> None:
        """Successful run start returns confirmation view."""
        rt = _mock_run_trigger(success=True, process_id=99)
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add dark mode",
                "csrf_token": token,
            },
        )
        assert response.status_code == 200
        assert "Run Started" in response.text

    def test_success_shows_project_name(self) -> None:
        """Success view shows the project name."""
        rt = _mock_run_trigger(success=True)
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add dark mode",
                "csrf_token": token,
            },
        )
        assert "my-project" in response.text

    def test_success_calls_run_trigger(self) -> None:
        """Run trigger is called with correct arguments."""
        rt = _mock_run_trigger(success=True)
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
        )
        token = _get_csrf_token(client)
        client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add dark mode",
                "csrf_token": token,
            },
        )
        rt.start_run.assert_called_once_with(
            project_path="/projects/my-project",
            feature="Add dark mode",
        )

    def test_success_sets_hx_push_url(self) -> None:
        """Successful response sets HX-Push-Url header."""
        rt = _mock_run_trigger(success=True)
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add dark mode",
                "csrf_token": token,
            },
        )
        assert response.headers.get("hx-push-url") == "/"


# ── Run Trigger Failure ────────────────────────────────────────────


class TestRunTriggerFailure:
    """Tests for run trigger failure handling."""

    def test_trigger_failure_shows_error(self) -> None:
        """Failed trigger shows error in modal."""
        rt = _mock_run_trigger(success=False, error="ADW command not found: adw")
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add dark mode",
                "csrf_token": token,
            },
        )
        assert response.status_code == 200
        assert "Failed to start run" in response.text
        assert "new-run-dialog" in response.text
