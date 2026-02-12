"""Tests for Story 2.4: Active & Failed Run Variants with SSE.

Covers SSE endpoint registration, active run SSE wrapper, failed run error banner,
failed phase auto-expansion, severity pre-filter, streaming log viewer,
and OOB phase pipeline rendering.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from adw.dashboard.server import create_dashboard_app
from adw.models.index import IndexEntry


def _make_index_entry(
    run_id: str = "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
    project_name: str = "my-project",
    feature_description: str = "Add user authentication",
    status: str = "completed",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    project_path: str = "/tmp/my-project",
    phases_completed: list[str] | None = None,
    phase_reached: str | None = "build",
) -> IndexEntry:
    """Create a test IndexEntry."""
    now = datetime.now(UTC)
    return IndexEntry(
        run_id=run_id,
        project_name=project_name,
        feature_description=feature_description,
        status=status,
        started_at=started_at or now - timedelta(minutes=10),
        completed_at=completed_at or now - timedelta(minutes=2),
        project_path=project_path,
        phases_completed=phases_completed or ["plan", "build"],
        phase_reached=phase_reached,
    )


def _mock_index_manager(
    entries: list[IndexEntry] | None = None,
) -> MagicMock:
    """Build a mock IndexManager."""
    mock = MagicMock()
    all_entries = entries or []

    def get_recent_side_effect(**kwargs):
        if kwargs.get("status") == "running":
            return [e for e in all_entries if e.status == "running"]
        limit = kwargs.get("limit", 10)
        return all_entries[:limit]

    mock.get_recent_runs.side_effect = get_recent_side_effect
    return mock


def _mock_project_registry(project_names: list[str] | None = None) -> MagicMock:
    """Build a mock ProjectRegistryManager."""
    mock = MagicMock()
    projects = []
    for name in (project_names or []):
        p = MagicMock()
        p.name = name
        projects.append(p)
    mock.get_all.return_value = projects
    return mock


def _make_client_with_mocks(
    entries: list[IndexEntry] | None = None,
    project_names: list[str] | None = None,
) -> TestClient:
    """Create a TestClient with dependency overrides."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    im = _mock_index_manager(entries=entries or [])
    pr = _mock_project_registry(project_names or ["my-project"])
    sa = MagicMock()
    sa.get_global_stats.return_value = MagicMock(projects=[])

    app.dependency_overrides[dependencies.get_index_manager] = lambda: im
    app.dependency_overrides[dependencies.get_project_registry] = lambda: pr
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: sa

    return TestClient(app)


# ── Active Run SSE Wrapper ────────────────────────────────────────────


class TestActiveRunSSEWrapper:
    """Tests for SSE wrapper on active (running) runs."""

    def test_active_run_has_sse_wrapper(self) -> None:
        """Running run detail page includes hx-ext='sse' attribute."""
        entry = _make_index_entry(status="running", completed_at=None)
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        assert 'hx-ext="sse"' in response.text

    def test_active_run_has_sse_connect(self) -> None:
        """Running run connects to SSE events endpoint."""
        entry = _make_index_entry(status="running", completed_at=None)
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert f'sse-connect="/runs/{entry.run_id}/events"' in response.text

    def test_active_run_has_sse_close_events(self) -> None:
        """SSE wrapper includes sse-close for terminal events."""
        entry = _make_index_entry(status="running", completed_at=None)
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert 'sse-close="run-complete,run-failed"' in response.text

    def test_completed_run_has_no_sse(self) -> None:
        """Completed run detail page does NOT include SSE wrapper."""
        entry = _make_index_entry(status="completed")
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert 'hx-ext="sse"' not in response.text
        assert "sse-connect" not in response.text

    def test_active_run_shows_abort_button(self) -> None:
        """Running run shows the Abort button."""
        entry = _make_index_entry(status="running", completed_at=None)
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "Abort" in response.text

    def test_active_run_has_loading_animation(self) -> None:
        """Running run shows loading dots animation."""
        entry = _make_index_entry(
            status="running",
            completed_at=None,
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "loading loading-dots" in response.text

    def test_active_run_has_run_elapsed_id(self) -> None:
        """Running run has #run-elapsed span for OOB elapsed time updates."""
        entry = _make_index_entry(status="running", completed_at=None)
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert 'id="run-elapsed"' in response.text

    def test_active_run_has_phase_pipeline_id(self) -> None:
        """Running run has #run-phase-pipeline for OOB pipeline updates."""
        entry = _make_index_entry(status="running", completed_at=None)
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert 'id="run-phase-pipeline"' in response.text

    def test_active_run_shows_all_phases_including_pending(self) -> None:
        """Active run accordion shows all phases (even pending)."""
        entry = _make_index_entry(
            status="running",
            completed_at=None,
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # All phases should appear in the accordion
        assert "Plan" in response.text
        assert "Build" in response.text
        assert "Valid" in response.text
        assert "Doc" in response.text
        assert "Ship" in response.text
        # Pending phases should show "Waiting..." text
        assert "Waiting..." in response.text


# ── Failed Run Error Banner ──────────────────────────────────────────


class TestFailedRunErrorBanner:
    """Tests for the failed run error banner and auto-expansion."""

    def test_failed_run_shows_error_banner(self) -> None:
        """Failed run has alert-error banner."""
        entry = _make_index_entry(
            status="failed",
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "alert alert-error" in response.text
        assert "Run failed" in response.text

    def test_failed_run_banner_shows_phase_name(self) -> None:
        """Error banner names the phase where failure occurred."""
        entry = _make_index_entry(
            status="failed",
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # "Build" is the phase_reached label
        assert "Build" in response.text

    def test_failed_run_has_no_error_banner_for_completed(self) -> None:
        """Completed run does NOT have error banner."""
        entry = _make_index_entry(status="completed")
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "alert-error" not in response.text

    def test_failed_phase_accordion_auto_expanded(self) -> None:
        """Failed phase accordion is auto-expanded via checked checkbox."""
        entry = _make_index_entry(
            status="failed",
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # The failed phase accordion should have checked checkbox for auto-expand
        assert "checked" in response.text

    def test_failed_phase_preloads_content(self) -> None:
        """Failed phase uses hx-trigger='load' instead of 'click once'."""
        entry = _make_index_entry(
            status="failed",
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # Failed phase content should use hx-trigger="load" for immediate loading
        assert 'hx-trigger="load"' in response.text

    def test_failed_phase_prefilters_error_severity(self) -> None:
        """Failed phase loads with severity=ERROR query param."""
        entry = _make_index_entry(
            status="failed",
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # The hx-get for the failed phase should include severity=ERROR
        assert "severity=ERROR" in response.text

    def test_failed_run_pipeline_shows_error_step(self) -> None:
        """Failed run pipeline shows step-error class on failed phase."""
        entry = _make_index_entry(
            status="failed",
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "step-error" in response.text


# ── Phase Detail: Severity Pre-filter ─────────────────────────────────


class TestPhaseDetailSeverityFilter:
    """Tests for severity pre-filter on phase detail."""

    def test_phase_detail_accepts_severity_param(self) -> None:
        """Phase detail route accepts severity query param."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan?severity=ERROR",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200

    def test_phase_detail_severity_preselects_dropdown(self) -> None:
        """Severity param pre-selects the level dropdown in the template."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan?severity=ERROR",
                headers={"HX-Request": "true"},
            )

        # The ERROR option should have 'selected' attribute
        assert 'value="ERROR" selected' in response.text

    def test_phase_detail_severity_includes_level_in_initial_load(self) -> None:
        """Default severity is included in the initial log load URL."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan?severity=ERROR",
                headers={"HX-Request": "true"},
            )

        # The initial hx-get for logs should include &level=ERROR
        assert "&amp;level=ERROR" in response.text or "&level=ERROR" in response.text

    def test_phase_detail_no_severity_shows_all(self) -> None:
        """Without severity param, dropdown defaults to 'All'."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        # No 'selected' on any severity option (default is All)
        assert 'value="ERROR" selected' not in response.text
        assert 'value="WARN" selected' not in response.text


# ── Phase Detail: Active Phase SSE Streaming ──────────────────────────


class TestPhaseDetailSSEStreaming:
    """Tests for SSE streaming log viewer in active phase detail."""

    def test_active_phase_has_sse_log_stream(self) -> None:
        """Active phase detail uses SSE for log streaming."""
        entry = _make_index_entry(
            status="running",
            completed_at=None,
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.status = "running"
        mock_ctx.current_phase = "build"

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}/phases/build",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        assert 'sse-connect=' in response.text
        assert 'sse-swap="log-line"' in response.text
        assert 'hx-swap="beforeend"' in response.text

    def test_active_phase_streaming_label(self) -> None:
        """Active phase shows 'Streaming live logs...' message."""
        entry = _make_index_entry(
            status="running",
            completed_at=None,
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.status = "running"
        mock_ctx.current_phase = "build"

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}/phases/build",
                headers={"HX-Request": "true"},
            )

        assert "Streaming live logs" in response.text

    def test_completed_phase_has_static_log_viewer(self) -> None:
        """Completed phase uses static log viewer (not SSE)."""
        entry = _make_index_entry(
            status="completed",
            phases_completed=["plan", "build"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.status = "completed"
        mock_ctx.current_phase = "build"

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        # Should have static log viewer with search/filter
        assert "Search logs" in response.text
        # Should NOT have SSE streaming
        assert "sse-swap" not in response.text
        assert "Streaming live logs" not in response.text

    def test_active_phase_has_log_stream_container_class(self) -> None:
        """Active phase log viewer has log-stream-container class for auto-scroll."""
        entry = _make_index_entry(
            status="running",
            completed_at=None,
            phases_completed=["plan"],
            phase_reached="build",
        )
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.status = "running"
        mock_ctx.current_phase = "build"

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}/phases/build",
                headers={"HX-Request": "true"},
            )

        assert "log-stream-container" in response.text


# ── SSE Endpoint Registration ─────────────────────────────────────────


class TestSSEEndpointRegistration:
    """Tests that SSE endpoints are registered and respond."""

    def test_run_events_endpoint_exists(self) -> None:
        """GET /runs/{id}/events returns a response (not 404/405)."""
        entry = _make_index_entry(status="running", completed_at=None)
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            # Make it return a terminal state immediately so the stream ends
            mock_ctx = MagicMock()
            mock_ctx.status = "completed"
            mock_ctx.current_phase = "ship"
            mock_ctx.phase_history = ["plan", "build", "validate", "document", "ship"]
            mock_ctx.started_at = datetime.now(UTC) - timedelta(minutes=5)
            mock_cm.return_value.load.return_value = mock_ctx

            response = client.get(f"/runs/{entry.run_id}/events")

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")

    def test_run_events_404_for_missing_run(self) -> None:
        """GET /runs/{id}/events returns 404 for non-existent run."""
        client = _make_client_with_mocks(entries=[])
        response = client.get("/runs/01HQXK5P3Z7V8R2M4N6T9W1Y00/events")
        assert response.status_code == 404

    def test_log_stream_endpoint_exists(self) -> None:
        """GET /runs/{id}/logs/stream returns a response (not 404/405)."""
        entry = _make_index_entry(status="running", completed_at=None)
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_ctx = MagicMock()
            mock_ctx.status = "completed"
            mock_ctx.current_phase = "build"
            mock_ctx.phase_history = ["plan"]
            mock_cm.return_value.load.return_value = mock_ctx

            response = client.get(f"/runs/{entry.run_id}/logs/stream")

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")

    def test_log_stream_404_for_missing_run(self) -> None:
        """GET /runs/{id}/logs/stream returns 404 for non-existent run."""
        client = _make_client_with_mocks(entries=[])
        response = client.get("/runs/01HQXK5P3Z7V8R2M4N6T9W1Y00/logs/stream")
        assert response.status_code == 404


# ── SSE Helper Functions ──────────────────────────────────────────────


class TestFormatSSEEvent:
    """Tests for _format_sse_event helper."""

    def test_single_line_data(self) -> None:
        """Single line data is formatted correctly."""
        from adw.dashboard.routes import _format_sse_event

        result = _format_sse_event("test-event", "hello world")
        assert result == "event:test-event\ndata:hello world\n\n"

    def test_multi_line_data(self) -> None:
        """Multi-line data has each line prefixed with 'data:'."""
        from adw.dashboard.routes import _format_sse_event

        result = _format_sse_event("update", "line1\nline2\nline3")
        assert "data:line1\n" in result
        assert "data:line2\n" in result
        assert "data:line3\n" in result
        assert result.startswith("event:update\n")
        assert result.endswith("\n\n")


class TestRenderLogLineHTML:
    """Tests for _render_log_line_html helper."""

    def test_info_level_no_extra_class(self) -> None:
        """INFO level renders without extra color class."""
        from adw.dashboard.routes import _render_log_line_html

        result = _render_log_line_html("2024-01-15 10:30:00", "INFO", "test msg")
        assert "text-warning" not in result
        assert "text-error" not in result
        assert "INFO" in result
        assert "test msg" in result

    def test_warn_level_has_warning_class(self) -> None:
        """WARN level renders with text-warning class."""
        from adw.dashboard.routes import _render_log_line_html

        result = _render_log_line_html("2024-01-15 10:30:00", "WARN", "some warning")
        assert "text-warning" in result

    def test_error_level_has_error_class(self) -> None:
        """ERROR level renders with text-error class."""
        from adw.dashboard.routes import _render_log_line_html

        result = _render_log_line_html("2024-01-15 10:30:00", "ERROR", "something broke")
        assert "text-error" in result

    def test_html_escaping(self) -> None:
        """Message content is HTML-escaped to prevent XSS."""
        from adw.dashboard.routes import _render_log_line_html

        result = _render_log_line_html("2024-01-15 10:30:00", "INFO", '<script>alert("xss")</script>')
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestRenderPhasePipelineOOB:
    """Tests for _render_phase_pipeline_oob helper."""

    def test_oob_pipeline_has_swap_attribute(self) -> None:
        """Pipeline HTML has hx-swap-oob for OOB update."""
        from adw.dashboard.routes import _render_phase_pipeline_oob

        phases = [
            {"name": "Plan", "status": "completed", "duration": "1m 30s"},
            {"name": "Build", "status": "active", "duration": ""},
        ]
        result = _render_phase_pipeline_oob(phases, "5m 30s")
        assert 'hx-swap-oob="innerHTML"' in result
        assert 'id="run-phase-pipeline"' in result

    def test_oob_elapsed_has_swap_attribute(self) -> None:
        """Elapsed time HTML has hx-swap-oob for OOB update."""
        from adw.dashboard.routes import _render_phase_pipeline_oob

        phases = [{"name": "Plan", "status": "completed", "duration": ""}]
        result = _render_phase_pipeline_oob(phases, "2m 15s")
        assert 'id="run-elapsed"' in result
        assert "2m 15s" in result

    def test_oob_pipeline_shows_success_step(self) -> None:
        """Completed phase has step-success class."""
        from adw.dashboard.routes import _render_phase_pipeline_oob

        phases = [{"name": "Plan", "status": "completed", "duration": ""}]
        result = _render_phase_pipeline_oob(phases, "1m")
        assert "step-success" in result
        assert "step step-success" in result

    def test_oob_pipeline_shows_active_step(self) -> None:
        """Active phase has step-warning and loading dots."""
        from adw.dashboard.routes import _render_phase_pipeline_oob

        phases = [{"name": "Build", "status": "active", "duration": ""}]
        result = _render_phase_pipeline_oob(phases, "3m")
        assert "step-warning" in result
        assert "loading loading-dots" in result

    def test_oob_pipeline_shows_failed_step(self) -> None:
        """Failed phase has step-error class."""
        from adw.dashboard.routes import _render_phase_pipeline_oob

        phases = [{"name": "Build", "status": "failed", "duration": ""}]
        result = _render_phase_pipeline_oob(phases, "3m")
        assert "step-error" in result


# ── Build Detail Context for Active/Failed ────────────────────────────


class TestBuildRunDetailContextVariants:
    """Tests for _build_run_detail_context active/failed variants."""

    def test_active_run_context_is_active_true(self) -> None:
        """Active run sets is_active=True in context."""
        from adw.dashboard.routes import _build_run_detail_context

        entry = _make_index_entry(status="running", completed_at=None)
        request = MagicMock()
        request.query_params.get.return_value = ""
        request.headers.get.return_value = ""

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            result = _build_run_detail_context(entry, request)

        assert result["is_active"] is True

    def test_failed_run_context_is_active_false(self) -> None:
        """Failed run sets is_active=False in context."""
        from adw.dashboard.routes import _build_run_detail_context

        entry = _make_index_entry(status="failed")
        request = MagicMock()
        request.query_params.get.return_value = ""
        request.headers.get.return_value = ""

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            result = _build_run_detail_context(entry, request)

        assert result["is_active"] is False

    def test_failed_run_has_failed_phase_name(self) -> None:
        """Failed run has failed_phase_name in context."""
        from adw.dashboard.routes import _build_run_detail_context

        entry = _make_index_entry(
            status="failed",
            phases_completed=["plan"],
            phase_reached="build",
        )
        request = MagicMock()
        request.query_params.get.return_value = ""
        request.headers.get.return_value = ""

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            result = _build_run_detail_context(entry, request)

        assert result["failed_phase_name"] == "Build"

    def test_completed_run_has_no_failed_phase_name(self) -> None:
        """Completed run has failed_phase_name=None."""
        from adw.dashboard.routes import _build_run_detail_context

        entry = _make_index_entry(status="completed")
        request = MagicMock()
        request.query_params.get.return_value = ""
        request.headers.get.return_value = ""

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            result = _build_run_detail_context(entry, request)

        assert result["failed_phase_name"] is None

    def test_active_run_shows_all_phases_in_detail(self) -> None:
        """Active run accordion includes all 5 phases (even pending)."""
        from adw.dashboard.routes import _build_run_detail_context

        entry = _make_index_entry(
            status="running",
            completed_at=None,
            phases_completed=["plan"],
            phase_reached="build",
        )
        request = MagicMock()
        request.query_params.get.return_value = ""
        request.headers.get.return_value = ""

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            result = _build_run_detail_context(entry, request)

        phase_keys = [p["phase_key"] for p in result["phases_detail"]]
        assert len(phase_keys) == 5
        assert "validate" in phase_keys
        assert "document" in phase_keys
        assert "ship" in phase_keys

    def test_completed_run_only_shows_phases_with_data(self) -> None:
        """Completed run accordion only shows phases that have data."""
        from adw.dashboard.routes import _build_run_detail_context

        entry = _make_index_entry(
            status="completed",
            phases_completed=["plan", "build"],
            phase_reached="build",
        )
        request = MagicMock()
        request.query_params.get.return_value = ""
        request.headers.get.return_value = ""

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            result = _build_run_detail_context(entry, request)

        phase_keys = [p["phase_key"] for p in result["phases_detail"]]
        # Only phases with data (completed or current) should show
        assert "plan" in phase_keys
        assert "build" in phase_keys
        # Pending phases should NOT show
        assert "validate" not in phase_keys
        assert "document" not in phase_keys
        assert "ship" not in phase_keys
