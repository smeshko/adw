"""Tests for Story 3.1 & 3.2: New Run Modal, Form Submission, and Re-run Flow.

Covers CSRF validation, form validation, run trigger invocation,
success response, error handling, modal partial route, template
structure, modal-container in base.html, enabled buttons, and
the re-run flow with pre-populated modal context.
"""

from __future__ import annotations

from typing import Literal
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from adw.dashboard.dependencies import generate_csrf_token
from adw.dashboard.server import create_dashboard_app
from adw.models.index import IndexEntry


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


def _mock_index_manager(entries: list | None = None) -> MagicMock:
    """Build a minimal mock IndexManager.

    Args:
        entries: Optional list of IndexEntry objects to return from
            get_recent_runs(). Defaults to empty list.
    """
    mock = MagicMock()
    mock.get_recent_runs.return_value = entries or []
    return mock


def _make_index_entry(
    run_id: str = "01KDSG2VDHNK0W4HSCZWJZXWSQ",
    project_path: str = "/projects/my-project",
    project_name: str = "my-project",
    feature_description: str = "Add user authentication",
    status: Literal["running", "completed", "failed", "interrupted", "aborted"] = "completed",
) -> IndexEntry:
    """Build a mock IndexEntry for re-run tests."""
    from datetime import UTC, datetime

    return IndexEntry(
        run_id=run_id,
        project_path=project_path,
        project_name=project_name,
        feature_description=feature_description,
        started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC),
        status=status,
        phase_reached="ship",
        phases_completed=["plan", "build", "validate", "document", "ship"],
    )


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
    index_manager: MagicMock | None = None,
) -> TestClient:
    """Create a TestClient with dependency overrides for mutations testing."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    pr = project_registry or _mock_project_registry()
    rt = run_trigger or _mock_run_trigger()
    im = index_manager or _mock_index_manager()
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

    def test_validation_error_retargets_modal_container(self) -> None:
        """Validation error retargets response to #modal-container."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={"project": "", "feature": "", "csrf_token": token},
        )
        assert response.headers.get("hx-retarget") == "#modal-container"
        assert response.headers.get("hx-reswap") == "innerHTML"

    def test_validation_error_does_not_push_url(self) -> None:
        """Validation error does not set HX-Push-Url header."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={"project": "", "feature": "", "csrf_token": token},
        )
        assert response.headers.get("hx-push-url") is None


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

    def test_success_clears_modal_via_oob(self) -> None:
        """Successful response clears modal via out-of-band swap."""
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
        assert 'id="modal-container"' in response.text
        assert "hx-swap-oob" in response.text


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

    def test_trigger_failure_retargets_modal_container(self) -> None:
        """Failed trigger retargets response to #modal-container."""
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
        assert response.headers.get("hx-retarget") == "#modal-container"
        assert response.headers.get("hx-reswap") == "innerHTML"


# ── GET /partials/new-run Route ────────────────────────────────────


class TestNewRunPartialRoute:
    """Tests for GET /partials/new-run modal route."""

    def test_returns_200(self) -> None:
        """New-run partial returns HTTP 200."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert response.status_code == 200

    def test_returns_html(self) -> None:
        """New-run partial returns HTML content type."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert "text/html" in response.headers["content-type"]

    def test_contains_modal_dialog(self) -> None:
        """Response contains the DaisyUI modal dialog element."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert 'id="new-run-dialog"' in response.text
        assert "modal" in response.text

    def test_contains_title(self) -> None:
        """Modal contains 'Start New Run' title."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert "Start New Run" in response.text

    def test_populates_project_select(self) -> None:
        """Project select is populated with registered projects."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["alpha", "beta"]),
        )
        response = client.get("/partials/new-run")
        assert "alpha" in response.text
        assert "beta" in response.text

    def test_contains_csrf_token(self) -> None:
        """Modal includes a hidden CSRF token input."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert 'name="csrf_token"' in response.text
        assert 'type="hidden"' in response.text

    def test_contains_feature_textarea(self) -> None:
        """Modal includes the feature textarea with placeholder."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert 'name="feature"' in response.text
        assert "Describe the feature to build" in response.text

    def test_contains_submit_button(self) -> None:
        """Modal has the Start Run submit button."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert "Start Run" in response.text
        assert "btn-primary" in response.text

    def test_contains_cancel_button(self) -> None:
        """Modal has a Cancel button."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert "Cancel" in response.text
        assert "btn-ghost" in response.text

    def test_form_targets_main(self) -> None:
        """Form submits to /runs/start targeting #main."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert 'hx-post="/runs/start"' in response.text
        assert 'hx-target="#main"' in response.text

    def test_contains_loading_indicator(self) -> None:
        """Submit button has a loading spinner indicator."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert "loading loading-spinner" in response.text

    def test_no_errors_on_initial_load(self) -> None:
        """Initial modal load shows no error messages."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert "text-error" not in response.text

    def test_contains_close_button(self) -> None:
        """Modal has a close (✕) button."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert "✕" in response.text

    def test_empty_project_list(self) -> None:
        """Modal renders with no projects in select."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry([]),
        )
        response = client.get("/partials/new-run")
        assert response.status_code == 200
        assert "Select a project" in response.text


# ── Modal Container in Base Template ──────────────────────────────


class TestModalContainerInBase:
    """Tests for #modal-container in base.html."""

    def test_base_has_modal_container(self) -> None:
        """Full page has #modal-container div."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/")
        assert 'id="modal-container"' in response.text

    def test_modal_container_outside_main(self) -> None:
        """#modal-container appears after </main> in the HTML."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/")
        text = response.text
        main_end = text.index("</main>")
        container_pos = text.index('id="modal-container"')
        assert container_pos > main_end

    def test_modal_container_before_footer(self) -> None:
        """#modal-container appears before <footer> in the HTML."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/")
        text = response.text
        container_pos = text.index('id="modal-container"')
        footer_pos = text.index('id="status-bar"')
        assert container_pos < footer_pos


# ── Enabled New Run Buttons ───────────────────────────────────────


class TestNewRunButtons:
    """Tests for enabled + New Run buttons in overview."""

    def test_full_overview_button_has_htmx(self) -> None:
        """Full overview + New Run button has HTMX attributes."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        assert 'hx-get="/partials/new-run"' in response.text
        assert 'hx-target="#modal-container"' in response.text

    def test_buttons_not_disabled(self) -> None:
        """+ New Run buttons are no longer disabled."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/", headers={"HX-Request": "true"})
        # The disabled attribute should not appear on New Run buttons
        # Check that data-action="new-run" buttons don't have disabled
        text = response.text
        # Find all occurrences of data-action="new-run"
        idx = 0
        while True:
            pos = text.find('data-action="new-run"', idx)
            if pos == -1:
                break
            # Look at surrounding 200 chars before to check for disabled
            context = text[max(0, pos - 200):pos]
            assert "disabled" not in context, \
                "New Run button should not be disabled"
            idx = pos + 1


# ── Integration: Full Flow ────────────────────────────────────────


class TestFullFlow:
    """Integration test for the complete new run flow."""

    def test_open_modal_then_submit(self) -> None:
        """Open modal via GET, then submit form via POST."""
        rt = _mock_run_trigger(success=True, process_id=77)
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
        )

        # Step 1: Open modal
        modal_response = client.get("/partials/new-run")
        assert modal_response.status_code == 200
        assert "Start New Run" in modal_response.text

        # Step 2: Submit form
        token = _get_csrf_token(client)
        submit_response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add authentication",
                "csrf_token": token,
            },
        )
        assert submit_response.status_code == 200
        assert "Run Started" in submit_response.text
        rt.start_run.assert_called_once()

    def test_open_modal_submit_invalid_resubmit(self) -> None:
        """Open modal, submit invalid, fix, resubmit successfully."""
        rt = _mock_run_trigger(success=True, process_id=88)
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
        )

        # Step 1: Submit invalid (empty feature)
        token = _get_csrf_token(client)
        invalid_response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "",
                "csrf_token": token,
            },
        )
        assert "describe the feature" in invalid_response.text.lower()

        # Step 2: Resubmit with valid data
        token2 = _get_csrf_token(client)
        valid_response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add dark mode",
                "csrf_token": token2,
            },
        )
        assert "Run Started" in valid_response.text


# ── DI Provider Test ─────────────────────────────────────────────


class TestRunTriggerDI:
    """Tests for the get_run_trigger dependency provider."""

    def test_get_run_trigger_returns_instance(self) -> None:
        """get_run_trigger returns a RunTrigger instance."""
        from adw.core.run_trigger import RunTrigger
        from adw.dashboard.dependencies import get_run_trigger

        result = get_run_trigger()
        assert isinstance(result, RunTrigger)


# ── Re-run Partial Route Tests ────────────────────────────────────


class TestRerunPartialRoute:
    """Tests for GET /partials/new-run?from={run_id} re-run modal."""

    def test_rerun_returns_200(self) -> None:
        """Re-run partial with valid from param returns 200."""
        entry = _make_index_entry()
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        response = client.get(f"/partials/new-run?from={entry.run_id}")
        assert response.status_code == 200

    def test_rerun_title_shows_rerun(self) -> None:
        """Modal title shows 'Re-run' when from param is valid."""
        entry = _make_index_entry()
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        response = client.get(f"/partials/new-run?from={entry.run_id}")
        assert "Re-run" in response.text
        assert "Start New Run" not in response.text

    def test_rerun_project_select_disabled(self) -> None:
        """Project select is disabled when re-run context active."""
        entry = _make_index_entry()
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        response = client.get(f"/partials/new-run?from={entry.run_id}")
        assert "disabled" in response.text

    def test_rerun_project_preselected(self) -> None:
        """Project name is shown in disabled select."""
        entry = _make_index_entry(project_name="alpha-project")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["alpha-project"]),
            index_manager=im,
        )
        response = client.get(f"/partials/new-run?from={entry.run_id}")
        assert "alpha-project" in response.text

    def test_rerun_hidden_project_input(self) -> None:
        """Hidden input for project path is present when re-run active."""
        entry = _make_index_entry(project_path="/projects/alpha")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["alpha"]),
            index_manager=im,
        )
        response = client.get(f"/partials/new-run?from={entry.run_id}")
        assert 'name="project"' in response.text
        assert 'value="/projects/alpha"' in response.text

    def test_rerun_feature_prefilled(self) -> None:
        """Feature textarea is pre-filled with source run's feature."""
        entry = _make_index_entry(feature_description="Implement dark mode toggle")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        response = client.get(f"/partials/new-run?from={entry.run_id}")
        assert "Implement dark mode toggle" in response.text

    def test_rerun_csrf_token_present(self) -> None:
        """CSRF token is still included in re-run modal."""
        entry = _make_index_entry()
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        response = client.get(f"/partials/new-run?from={entry.run_id}")
        assert 'name="csrf_token"' in response.text

    def test_rerun_from_run_hidden_input(self) -> None:
        """Hidden from_run input is present in re-run modal."""
        entry = _make_index_entry()
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        response = client.get(f"/partials/new-run?from={entry.run_id}")
        assert 'name="from_run"' in response.text
        assert f'value="{entry.run_id}"' in response.text

    def test_invalid_from_falls_back_to_new_run(self) -> None:
        """Invalid from run_id falls back to standard new-run modal."""
        im = _mock_index_manager(entries=[])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        response = client.get("/partials/new-run?from=01NONEXISTENT000000000000")
        assert response.status_code == 200
        assert "Start New Run" in response.text
        assert "Re-run" not in response.text.split("Start New Run")[0]

    def test_empty_from_shows_standard_modal(self) -> None:
        """Empty from param shows standard new-run modal."""
        im = _mock_index_manager(entries=[])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        response = client.get("/partials/new-run?from=")
        assert "Start New Run" in response.text

    def test_no_from_param_shows_standard_modal(self) -> None:
        """No from param at all shows standard new-run modal."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
        )
        response = client.get("/partials/new-run")
        assert "Start New Run" in response.text


# ── Re-run Submission Tests ──────────────────────────────────────


class TestRerunSubmission:
    """Tests for POST /runs/start with re-run context."""

    def test_rerun_submission_creates_run(self) -> None:
        """Successful re-run submission creates a new run."""
        entry = _make_index_entry()
        im = _mock_index_manager(entries=[entry])
        rt = _mock_run_trigger(success=True, process_id=55)
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
            index_manager=im,
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add user authentication",
                "csrf_token": token,
                "from_run": entry.run_id,
            },
        )
        assert response.status_code == 200
        assert "Run Started" in response.text
        rt.start_run.assert_called_once()

    def test_rerun_modified_feature(self) -> None:
        """Re-run with modified feature uses updated text."""
        entry = _make_index_entry(feature_description="Original feature")
        im = _mock_index_manager(entries=[entry])
        rt = _mock_run_trigger(success=True, process_id=66)
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
            index_manager=im,
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Modified feature text",
                "csrf_token": token,
                "from_run": entry.run_id,
            },
        )
        assert response.status_code == 200
        assert "Run Started" in response.text
        rt.start_run.assert_called_once_with(
            project_path="/projects/my-project",
            feature="Modified feature text",
        )

    def test_rerun_validation_error_preserves_context(self) -> None:
        """Validation error on re-run preserves re-run context."""
        entry = _make_index_entry()
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "",
                "csrf_token": token,
                "from_run": entry.run_id,
            },
        )
        assert response.status_code == 200
        # Re-run title should be preserved
        assert "Re-run" in response.text
        # Project should still be locked (disabled select)
        assert "disabled" in response.text

    def test_rerun_csrf_still_enforced(self) -> None:
        """CSRF validation still enforced on re-run submissions."""
        entry = _make_index_entry()
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add login",
                "from_run": entry.run_id,
            },
        )
        assert response.status_code == 403

    def test_rerun_trigger_failure_preserves_context(self) -> None:
        """Trigger failure on re-run preserves re-run context."""
        entry = _make_index_entry()
        im = _mock_index_manager(entries=[entry])
        rt = _mock_run_trigger(success=False, error="spawn failed")
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
            index_manager=im,
        )
        token = _get_csrf_token(client)
        response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Add login",
                "csrf_token": token,
                "from_run": entry.run_id,
            },
        )
        assert response.status_code == 200
        assert "Failed to start run" in response.text
        # Re-run context preserved
        assert "Re-run" in response.text
        assert "disabled" in response.text


# ── Re-run Button Tests ──────────────────────────────────────────


class TestRerunButton:
    """Tests for the Re-run button on run detail page."""

    def _make_run_detail_client(self) -> tuple:
        """Create client with a mock run for detail page testing."""
        entry = _make_index_entry(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            project_path="/projects/my-project",
            project_name="my-project",
            feature_description="Test feature",
        )
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            index_manager=im,
        )
        return client, entry

    def test_rerun_button_not_disabled(self) -> None:
        """Run detail page has an enabled Re-run button."""
        client, entry = self._make_run_detail_client()
        response = client.get(
            f"/runs/{entry.run_id}",
            headers={"HX-Request": "true"},
        )
        # Find the Re-run button and verify it's not disabled
        text = response.text
        rerun_pos = text.find(">Re-run</button>")
        assert rerun_pos != -1, "Re-run button not found in response"
        # Look backwards to find the button opening tag
        button_start = text.rfind("<button", 0, rerun_pos)
        button_html = text[button_start:rerun_pos + len(">Re-run</button>")]
        assert "disabled" not in button_html

    def test_rerun_button_has_htmx_get(self) -> None:
        """Re-run button has hx-get attribute with from param."""
        client, entry = self._make_run_detail_client()
        response = client.get(
            f"/runs/{entry.run_id}",
            headers={"HX-Request": "true"},
        )
        assert f'hx-get="/partials/new-run?from={entry.run_id}"' in response.text

    def test_rerun_button_targets_modal_container(self) -> None:
        """Re-run button targets #modal-container."""
        client, entry = self._make_run_detail_client()
        response = client.get(
            f"/runs/{entry.run_id}",
            headers={"HX-Request": "true"},
        )
        text = response.text
        # Find the Re-run button context and verify hx-target
        rerun_pos = text.find(">Re-run</button>")
        assert rerun_pos != -1, "Re-run button not found in response"
        button_start = text.rfind("<button", 0, rerun_pos)
        button_html = text[button_start:rerun_pos]
        assert 'hx-target="#modal-container"' in button_html


# ── Re-run Full Flow Integration ─────────────────────────────────


class TestRerunFullFlow:
    """Integration test for the complete re-run flow."""

    def test_rerun_full_flow(self) -> None:
        """Open re-run modal → verify pre-population → modify → submit → success."""
        entry = _make_index_entry(
            project_path="/projects/my-project",
            project_name="my-project",
            feature_description="Original feature description",
        )
        im = _mock_index_manager(entries=[entry])
        rt = _mock_run_trigger(success=True, process_id=101)
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(["my-project"]),
            run_trigger=rt,
            index_manager=im,
        )

        # Step 1: Open re-run modal
        modal_response = client.get(f"/partials/new-run?from={entry.run_id}")
        assert modal_response.status_code == 200
        assert "Re-run" in modal_response.text
        assert "Original feature description" in modal_response.text
        assert "my-project" in modal_response.text

        # Step 2: Submit with modified feature
        token = _get_csrf_token(client)
        submit_response = client.post(
            "/runs/start",
            data={
                "project": "/projects/my-project",
                "feature": "Improved feature description",
                "csrf_token": token,
                "from_run": entry.run_id,
            },
        )
        assert submit_response.status_code == 200
        assert "Run Started" in submit_response.text
        rt.start_run.assert_called_once_with(
            project_path="/projects/my-project",
            feature="Improved feature description",
        )
