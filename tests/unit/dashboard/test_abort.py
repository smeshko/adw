"""Tests for Story 3.3: Abort Active Run.

Covers abort confirmation modal, GET /partials/abort/{run_id},
POST /runs/{run_id}/abort, CSRF validation, and abort flow.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from unittest.mock import MagicMock, patch

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


def _mock_index_manager(entries: list | None = None) -> MagicMock:
    """Build a minimal mock IndexManager."""
    mock = MagicMock()
    mock.get_recent_runs.return_value = entries or []
    return mock


def _make_index_entry(
    run_id: str = "01KDSG2VDHNK0W4HSCZWJZXWSQ",
    project_path: str = "/projects/my-project",
    project_name: str = "my-project",
    feature_description: str = "Add user authentication",
    status: Literal["running", "completed", "failed", "interrupted", "aborted"] = "running",
    phase_reached: str = "build",
) -> IndexEntry:
    """Build a mock IndexEntry for abort tests."""
    return IndexEntry(
        run_id=run_id,
        project_path=project_path,
        project_name=project_name,
        feature_description=feature_description,
        started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        completed_at=None if status == "running" else datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC),
        status=status,
        phase_reached=phase_reached,
        phases_completed=["plan"] if phase_reached == "build" else ["plan", "build", "validate", "document", "ship"],
    )


def _mock_stats_aggregator() -> MagicMock:
    """Build a minimal mock StatsAggregator."""
    from adw.models.stats import GlobalStatistics

    mock = MagicMock()
    mock.get_global_stats.return_value = GlobalStatistics(generated_at=datetime.now(UTC))
    mock.get_daily_token_counts.return_value = []
    return mock


def _mock_run_trigger() -> MagicMock:
    """Build a mock RunTrigger."""
    return MagicMock()


def _make_client_with_mocks(
    project_registry: MagicMock | None = None,
    index_manager: MagicMock | None = None,
) -> TestClient:
    """Create a TestClient with dependency overrides for abort testing."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    pr = project_registry or _mock_project_registry()
    im = index_manager or _mock_index_manager()
    sa = _mock_stats_aggregator()
    rt = _mock_run_trigger()

    app.dependency_overrides[dependencies.get_project_registry] = lambda: pr
    app.dependency_overrides[dependencies.get_index_manager] = lambda: im
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: sa
    app.dependency_overrides[dependencies.get_run_trigger] = lambda: rt

    return TestClient(app)


def _get_csrf_token() -> str:
    """Get a valid CSRF token."""
    from unittest.mock import MagicMock

    from fastapi import Request

    mock_request = MagicMock(spec=Request)
    mock_request.state = MagicMock()
    return generate_csrf_token(mock_request)


def _mock_run_context(
    run_id: str = "01KDSG2VDHNK0W4HSCZWJZXWSQ",
    status: str = "running",
    current_phase: str = "build",
) -> MagicMock:
    """Build a mock RunContext for abort tests."""
    ctx = MagicMock()
    ctx.run_id = run_id
    ctx.status = status
    ctx.current_phase = current_phase
    ctx.phase_history = ["plan"]
    ctx.branch_name = "feature/test"
    ctx.total_tokens = 1000
    ctx.phase_tokens = {"plan": 500, "build": 500}
    ctx.pr_url = None
    ctx.task_id = None
    ctx.task_manager = None
    ctx.worktree_path = None
    ctx.started_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    ctx.completed_at = None
    # model_copy returns an updated context
    def model_copy_side_effect(update=None):
        new_ctx = _mock_run_context(
            run_id=run_id,
            status=update.get("status", status) if update else status,
            current_phase=current_phase,
        )
        if update:
            for k, v in update.items():
                setattr(new_ctx, k, v)
        return new_ctx
    ctx.model_copy.side_effect = model_copy_side_effect
    return ctx


# ── GET /partials/abort/{run_id} Tests ────────────────────────────


class TestAbortModalPartialRoute:
    """Tests for GET /partials/abort/{run_id} modal route."""

    def test_returns_200_for_running_run(self) -> None:
        """Abort modal returns 200 for a running run."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert response.status_code == 200

    def test_returns_html(self) -> None:
        """Abort modal returns HTML content type."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert "text/html" in response.headers["content-type"]

    def test_contains_abort_dialog(self) -> None:
        """Response contains the DaisyUI abort modal dialog."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert 'id="abort-dialog"' in response.text
            assert "modal" in response.text

    def test_contains_abort_title(self) -> None:
        """Modal contains 'Abort Run?' title."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert "Abort Run?" in response.text

    def test_contains_warning_text(self) -> None:
        """Modal contains the abort warning text."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert "This will stop the current phase" in response.text
            assert "cannot be undone" in response.text

    def test_contains_run_id(self) -> None:
        """Modal displays the run ID."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            # Should contain truncated run ID
            assert entry.run_id[:8] in response.text

    def test_contains_current_phase(self) -> None:
        """Modal displays the current phase."""
        entry = _make_index_entry(status="running", phase_reached="build")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context(current_phase="build")
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert "build" in response.text

    def test_contains_csrf_token(self) -> None:
        """Modal includes a hidden CSRF token input."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert 'name="csrf_token"' in response.text
            assert 'type="hidden"' in response.text

    def test_form_posts_to_abort_endpoint(self) -> None:
        """Modal form posts to /runs/{run_id}/abort targeting #main."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert f'hx-post="/runs/{entry.run_id}/abort"' in response.text
            assert 'hx-target="#main"' in response.text

    def test_contains_cancel_button(self) -> None:
        """Modal has a Cancel button."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert "Cancel" in response.text
            assert "btn-ghost" in response.text

    def test_contains_abort_button_with_error_style(self) -> None:
        """Modal has an 'Abort Run' button with btn-error class."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert "Abort Run" in response.text
            assert "btn-error" in response.text

    def test_returns_404_for_nonexistent_run(self) -> None:
        """GET abort modal for non-existent run returns 404."""
        im = _mock_index_manager(entries=[])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get("/partials/abort/01NONEXISTENT000000000000")
        assert response.status_code == 404

    def test_returns_error_for_completed_run(self) -> None:
        """GET abort modal for completed run returns error."""
        entry = _make_index_entry(status="completed")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get(f"/partials/abort/{entry.run_id}")
        assert response.status_code == 400
        assert "not active" in response.text.lower() or "cannot be aborted" in response.text.lower()

    def test_returns_error_for_failed_run(self) -> None:
        """GET abort modal for failed run returns error."""
        entry = _make_index_entry(status="failed")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get(f"/partials/abort/{entry.run_id}")
        assert response.status_code == 400

    def test_returns_error_for_already_aborted_run(self) -> None:
        """GET abort modal for already-aborted run returns error."""
        entry = _make_index_entry(status="aborted")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get(f"/partials/abort/{entry.run_id}")
        assert response.status_code == 400

    def test_falls_back_to_index_entry_phase(self) -> None:
        """If RunContext is unavailable, falls back to IndexEntry phase_reached."""
        entry = _make_index_entry(status="running", phase_reached="plan")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            from adw.exceptions import StateError
            mock_cm = MagicMock()
            mock_cm.load.side_effect = StateError(
                code="CONTEXT_NOT_FOUND",
                message="Not found",
                suggestion="",
                recoverable=False,
            )
            mock_cm_cls.return_value = mock_cm

            response = client.get(f"/partials/abort/{entry.run_id}")
            assert response.status_code == 200
            assert "plan" in response.text


# ── POST /runs/{run_id}/abort Tests ───────────────────────────────


class TestAbortCSRFValidation:
    """Tests for CSRF protection on /runs/{run_id}/abort."""

    def test_missing_csrf_returns_403(self) -> None:
        """POST without CSRF token returns 403."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.post(f"/runs/{entry.run_id}/abort")
        assert response.status_code == 403

    def test_invalid_csrf_returns_403(self) -> None:
        """POST with invalid CSRF token returns 403."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.post(
            f"/runs/{entry.run_id}/abort",
            data={"csrf_token": "invalid:token"},
        )
        assert response.status_code == 403


class TestAbortMutation:
    """Tests for POST /runs/{run_id}/abort endpoint."""

    def test_successful_abort_returns_200(self) -> None:
        """Successful abort of running run returns 200."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        with (
            patch("adw.dashboard.mutations.ContextManager") as mock_cm_cls,
            patch("adw.dashboard.mutations.SnapshotManager") as mock_sm_cls,
            patch("adw.dashboard.mutations.InterruptionHandler") as mock_ih_cls,
        ):
            mock_cm = MagicMock()
            mock_ctx = _mock_run_context()
            mock_cm.load.return_value = mock_ctx
            mock_cm_cls.return_value = mock_cm

            mock_sm = MagicMock()
            mock_sm_cls.return_value = mock_sm

            mock_handler = MagicMock()
            aborted_ctx = _mock_run_context(status="aborted")
            mock_handler.abort_gracefully.return_value = aborted_ctx
            mock_ih_cls.return_value = mock_handler

            response = client.post(
                f"/runs/{entry.run_id}/abort",
                data={"csrf_token": token},
            )
            assert response.status_code == 200

    def test_successful_abort_calls_abort_gracefully(self) -> None:
        """Abort calls InterruptionHandler.abort_gracefully with dashboard_abort reason."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        with (
            patch("adw.dashboard.mutations.ContextManager") as mock_cm_cls,
            patch("adw.dashboard.mutations.SnapshotManager") as mock_sm_cls,
            patch("adw.dashboard.mutations.InterruptionHandler") as mock_ih_cls,
        ):
            mock_cm = MagicMock()
            mock_ctx = _mock_run_context()
            mock_cm.load.return_value = mock_ctx
            mock_cm_cls.return_value = mock_cm

            mock_sm = MagicMock()
            mock_sm_cls.return_value = mock_sm

            mock_handler = MagicMock()
            aborted_ctx = _mock_run_context(status="aborted")
            mock_handler.abort_gracefully.return_value = aborted_ctx
            mock_ih_cls.return_value = mock_handler

            client.post(
                f"/runs/{entry.run_id}/abort",
                data={"csrf_token": token},
            )

            mock_handler.abort_gracefully.assert_called_once_with(
                mock_ctx, reason="dashboard_abort",
            )

    def test_successful_abort_clears_modal_via_oob(self) -> None:
        """Successful abort includes OOB swap to clear modal."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        with (
            patch("adw.dashboard.mutations.ContextManager") as mock_cm_cls,
            patch("adw.dashboard.mutations.SnapshotManager") as mock_sm_cls,
            patch("adw.dashboard.mutations.InterruptionHandler") as mock_ih_cls,
        ):
            mock_cm = MagicMock()
            mock_ctx = _mock_run_context()
            mock_cm.load.return_value = mock_ctx
            mock_cm_cls.return_value = mock_cm

            mock_sm = MagicMock()
            mock_sm_cls.return_value = mock_sm

            mock_handler = MagicMock()
            aborted_ctx = _mock_run_context(status="aborted")
            mock_handler.abort_gracefully.return_value = aborted_ctx
            mock_ih_cls.return_value = mock_handler

            response = client.post(
                f"/runs/{entry.run_id}/abort",
                data={"csrf_token": token},
            )
            assert 'id="modal-container"' in response.text
            assert "hx-swap-oob" in response.text

    def test_successful_abort_shows_aborted_detail(self) -> None:
        """Successful abort returns run detail showing aborted state."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        with (
            patch("adw.dashboard.mutations.ContextManager") as mock_cm_cls,
            patch("adw.dashboard.mutations.SnapshotManager") as mock_sm_cls,
            patch("adw.dashboard.mutations.InterruptionHandler") as mock_ih_cls,
        ):
            mock_cm = MagicMock()
            mock_ctx = _mock_run_context()
            mock_cm.load.return_value = mock_ctx
            mock_cm_cls.return_value = mock_cm

            mock_sm = MagicMock()
            mock_sm_cls.return_value = mock_sm

            mock_handler = MagicMock()
            aborted_ctx = _mock_run_context(status="aborted")
            mock_handler.abort_gracefully.return_value = aborted_ctx
            mock_ih_cls.return_value = mock_handler

            response = client.post(
                f"/runs/{entry.run_id}/abort",
                data={"csrf_token": token},
            )
            assert "run-detail" in response.text

    def test_successful_abort_sets_push_url(self) -> None:
        """Successful abort sets HX-Push-Url to the run detail page."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        with (
            patch("adw.dashboard.mutations.ContextManager") as mock_cm_cls,
            patch("adw.dashboard.mutations.SnapshotManager") as mock_sm_cls,
            patch("adw.dashboard.mutations.InterruptionHandler") as mock_ih_cls,
        ):
            mock_cm = MagicMock()
            mock_ctx = _mock_run_context()
            mock_cm.load.return_value = mock_ctx
            mock_cm_cls.return_value = mock_cm

            mock_sm = MagicMock()
            mock_sm_cls.return_value = mock_sm

            mock_handler = MagicMock()
            aborted_ctx = _mock_run_context(status="aborted")
            mock_handler.abort_gracefully.return_value = aborted_ctx
            mock_ih_cls.return_value = mock_handler

            response = client.post(
                f"/runs/{entry.run_id}/abort",
                data={"csrf_token": token},
            )
            assert response.headers.get("hx-push-url") == f"/runs/{entry.run_id}"

    def test_abort_nonexistent_run_returns_404(self) -> None:
        """POST abort for non-existent run returns 404."""
        im = _mock_index_manager(entries=[])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        response = client.post(
            "/runs/01NONEXISTENT000000000000/abort",
            data={"csrf_token": token},
        )
        assert response.status_code == 404

    def test_abort_completed_run_returns_error(self) -> None:
        """POST abort for completed run returns error."""
        entry = _make_index_entry(status="completed")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        response = client.post(
            f"/runs/{entry.run_id}/abort",
            data={"csrf_token": token},
        )
        assert response.status_code == 400

    def test_abort_already_aborted_run_returns_error(self) -> None:
        """POST abort for already-aborted run returns error."""
        entry = _make_index_entry(status="aborted")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        response = client.post(
            f"/runs/{entry.run_id}/abort",
            data={"csrf_token": token},
        )
        assert response.status_code == 400

    def test_abort_failed_run_returns_error(self) -> None:
        """POST abort for failed run returns error."""
        entry = _make_index_entry(status="failed")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        response = client.post(
            f"/runs/{entry.run_id}/abort",
            data={"csrf_token": token},
        )
        assert response.status_code == 400

    def test_abort_no_abort_button_after_abort(self) -> None:
        """After abort, the returned detail view should not show Abort button."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        with (
            patch("adw.dashboard.mutations.ContextManager") as mock_cm_cls,
            patch("adw.dashboard.mutations.SnapshotManager") as mock_sm_cls,
            patch("adw.dashboard.mutations.InterruptionHandler") as mock_ih_cls,
        ):
            mock_cm = MagicMock()
            mock_ctx = _mock_run_context()
            mock_cm.load.return_value = mock_ctx
            mock_cm_cls.return_value = mock_cm

            mock_sm = MagicMock()
            mock_sm_cls.return_value = mock_sm

            mock_handler = MagicMock()
            aborted_ctx = _mock_run_context(status="aborted")
            mock_handler.abort_gracefully.return_value = aborted_ctx
            mock_ih_cls.return_value = mock_handler

            response = client.post(
                f"/runs/{entry.run_id}/abort",
                data={"csrf_token": token},
            )
            # The Abort button should not appear since is_active=False for aborted runs
            # Check that no abort button appears in the response
            text = response.text
            # The HTMX abort button should not be present
            assert 'hx-get="/partials/abort/' not in text

    def test_abort_lock_timeout_handled(self) -> None:
        """Lock timeout on abort is handled gracefully."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)
        token = _get_csrf_token()

        with (
            patch("adw.dashboard.mutations.ContextManager") as mock_cm_cls,
            patch("adw.dashboard.mutations.SnapshotManager") as mock_sm_cls,
            patch("adw.dashboard.mutations.InterruptionHandler") as mock_ih_cls,
        ):
            from adw.exceptions import StateError

            mock_cm = MagicMock()
            mock_ctx = _mock_run_context()
            mock_cm.load.return_value = mock_ctx
            mock_cm_cls.return_value = mock_cm

            mock_sm = MagicMock()
            mock_sm_cls.return_value = mock_sm

            mock_handler = MagicMock()
            mock_handler.abort_gracefully.side_effect = StateError(
                code="LOCK_TIMEOUT",
                message="Could not acquire lock",
                suggestion="Another process may be using this run",
                recoverable=True,
            )
            mock_ih_cls.return_value = mock_handler

            response = client.post(
                f"/runs/{entry.run_id}/abort",
                data={"csrf_token": token},
            )
            # Should return an error response, not crash
            assert response.status_code in (200, 500)


# ── Abort Button on Run Detail Tests ──────────────────────────────


class TestAbortButton:
    """Tests for the Abort button on run detail page."""

    def test_abort_button_shown_for_running_run(self) -> None:
        """Run detail page shows Abort button for active run."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get(
            f"/runs/{entry.run_id}",
            headers={"HX-Request": "true"},
        )
        assert "Abort" in response.text

    def test_abort_button_has_htmx_get(self) -> None:
        """Abort button has hx-get to load abort modal."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get(
            f"/runs/{entry.run_id}",
            headers={"HX-Request": "true"},
        )
        assert f'hx-get="/partials/abort/{entry.run_id}"' in response.text
        assert 'hx-target="#modal-container"' in response.text

    def test_abort_button_not_disabled(self) -> None:
        """Abort button is not disabled for running runs."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get(
            f"/runs/{entry.run_id}",
            headers={"HX-Request": "true"},
        )
        text = response.text
        # Find the Abort button
        abort_pos = text.find(">Abort</button>")
        assert abort_pos != -1, "Abort button not found"
        button_start = text.rfind("<button", 0, abort_pos)
        button_html = text[button_start:abort_pos + len(">Abort</button>")]
        assert "disabled" not in button_html

    def test_abort_button_hidden_for_completed_run(self) -> None:
        """Abort button not shown for completed runs."""
        entry = _make_index_entry(status="completed")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get(
            f"/runs/{entry.run_id}",
            headers={"HX-Request": "true"},
        )
        assert 'hx-get="/partials/abort/' not in response.text

    def test_abort_button_hidden_for_failed_run(self) -> None:
        """Abort button not shown for failed runs."""
        entry = _make_index_entry(status="failed")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get(
            f"/runs/{entry.run_id}",
            headers={"HX-Request": "true"},
        )
        assert 'hx-get="/partials/abort/' not in response.text

    def test_abort_button_hidden_for_aborted_run(self) -> None:
        """Abort button not shown for already-aborted runs."""
        entry = _make_index_entry(status="aborted")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        response = client.get(
            f"/runs/{entry.run_id}",
            headers={"HX-Request": "true"},
        )
        assert 'hx-get="/partials/abort/' not in response.text


# ── Full Flow Integration Test ────────────────────────────────────


class TestAbortFullFlow:
    """Integration test for the complete abort flow."""

    def test_open_modal_then_abort(self) -> None:
        """Open abort modal → verify content → submit abort → confirm aborted."""
        entry = _make_index_entry(status="running")
        im = _mock_index_manager(entries=[entry])
        client = _make_client_with_mocks(index_manager=im)

        # Step 1: Open abort modal
        with patch("adw.dashboard.partials.ContextManager") as mock_cm_cls:
            mock_cm = MagicMock()
            mock_cm.load.return_value = _mock_run_context()
            mock_cm_cls.return_value = mock_cm

            modal_response = client.get(f"/partials/abort/{entry.run_id}")
            assert modal_response.status_code == 200
            assert "Abort Run?" in modal_response.text

        # Step 2: Submit abort
        token = _get_csrf_token()
        with (
            patch("adw.dashboard.mutations.ContextManager") as mock_cm_cls,
            patch("adw.dashboard.mutations.SnapshotManager") as mock_sm_cls,
            patch("adw.dashboard.mutations.InterruptionHandler") as mock_ih_cls,
        ):
            mock_cm = MagicMock()
            mock_ctx = _mock_run_context()
            mock_cm.load.return_value = mock_ctx
            mock_cm_cls.return_value = mock_cm

            mock_sm = MagicMock()
            mock_sm_cls.return_value = mock_sm

            mock_handler = MagicMock()
            aborted_ctx = _mock_run_context(status="aborted")
            mock_handler.abort_gracefully.return_value = aborted_ctx
            mock_ih_cls.return_value = mock_handler

            abort_response = client.post(
                f"/runs/{entry.run_id}/abort",
                data={"csrf_token": token},
            )
            assert abort_response.status_code == 200
            assert "run-detail" in abort_response.text
            assert 'id="modal-container"' in abort_response.text
            mock_handler.abort_gracefully.assert_called_once()
