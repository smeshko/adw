"""Integration tests for Story 2.3: LLM Interaction Viewer & Log Viewer.

Validates all acceptance criteria across the full request lifecycle,
ensuring templates, routes, and data layer work together correctly.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
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


def _mock_project_registry() -> MagicMock:
    """Build a mock ProjectRegistryManager."""
    mock = MagicMock()
    p = MagicMock()
    p.name = "my-project"
    mock.get_all.return_value = [p]
    return mock


def _make_client_with_mocks(
    entries: list[IndexEntry] | None = None,
) -> TestClient:
    """Create a TestClient with dependency overrides."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    im = _mock_index_manager(entries=entries or [])
    pr = _mock_project_registry()
    sa = MagicMock()
    sa.get_global_stats.return_value = MagicMock(projects=[])

    app.dependency_overrides[dependencies.get_index_manager] = lambda: im
    app.dependency_overrides[dependencies.get_project_registry] = lambda: pr
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: sa

    return TestClient(app)


# ── AC: LLM Interaction Summary (FR25) ─────────────────────────────


class TestACLLMSummary:
    """Acceptance criteria: LLM interaction sub-section renders with token counts."""

    def test_summary_shows_token_counts_with_view_buttons(self) -> None:
        """Given phase accordion expanded, LLM section shows token counts
        for prompt and response with View buttons (FR25)."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am, \
             patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
            mock_am.return_value.list_artifacts.return_value = []
            mock_llm.return_value = {
                "input_tokens": 5000,
                "output_tokens": 12000,
            }
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        assert "LLM Interaction" in response.text
        assert "5,000" in response.text
        assert "12,000" in response.text
        # View buttons for both prompt and response
        assert f"/runs/{entry.run_id}/phases/plan/prompt" in response.text
        assert f"/runs/{entry.run_id}/phases/plan/response" in response.text


# ── AC: LLM Content Viewer (FR25) ──────────────────────────────────


class TestACLLMContentViewer:
    """Acceptance criteria: Full text loads in scrollable pre block."""

    def test_response_content_in_scrollable_pre(self) -> None:
        """Given user clicks View on response, full text loads in
        scrollable pre block with max-h-96 overflow-y-auto font-mono text-xs."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = "Generated plan:\n1. Design API\n2. Implement endpoints"
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/response",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        assert "<pre" in response.text
        assert "max-h-96" in response.text
        assert "overflow-y-auto" in response.text
        assert "font-mono" in response.text
        assert "text-xs" in response.text
        assert "Generated plan:" in response.text

    def test_prompt_content_escapes_html(self) -> None:
        """Prompt content escapes HTML to prevent XSS."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_llm_content") as mock_load:
            mock_load.return_value = '<script>alert("xss")</script>'
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan/prompt",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        assert "<script>" not in response.text
        assert "&lt;script&gt;" in response.text


# ── AC: Log Viewer Pre-filtered (FR26) ─────────────────────────────


class TestACLogViewerPrefiltered:
    """Acceptance criteria: Log viewer pre-filtered to current phase."""

    def test_log_viewer_prefiltered_to_phase(self) -> None:
        """Given phase accordion expanded, log viewer is pre-filtered
        to the current phase (FR26)."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am, \
             patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
            mock_am.return_value.list_artifacts.return_value = []
            mock_llm.return_value = None
            response = client.get(
                f"/runs/{entry.run_id}/phases/build",
                headers={"HX-Request": "true"},
            )

        # Log viewer should auto-load with phase=build
        assert f"/runs/{entry.run_id}/logs?phase=build" in response.text
        # Hidden input passes phase to HTMX requests
        assert 'name="phase" value="build"' in response.text

    def test_log_controls_bar_present(self) -> None:
        """Given log viewer displayed, controls bar shows search, severity,
        and phase filter (FR20, FR22, FR26)."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am, \
             patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
            mock_am.return_value.list_artifacts.return_value = []
            mock_llm.return_value = None
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        # Search input
        assert "input input-bordered input-sm" in response.text
        assert 'placeholder="Search logs..."' in response.text
        # Severity filter
        assert "select select-bordered select-sm" in response.text
        assert ">All<" in response.text
        assert ">INFO<" in response.text
        assert ">WARN<" in response.text
        assert ">ERROR<" in response.text


# ── AC: Log Entry Display ──────────────────────────────────────────


class TestACLogEntryDisplay:
    """Acceptance criteria: Log entries display with proper formatting."""

    def test_log_entries_show_timestamp_level_message(self) -> None:
        """Given log viewer displayed, each line shows
        {timestamp} {level} {message}."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "Phase plan started"},
                {"timestamp": "2025-01-15 10:31:00", "level": "WARN", "message": "Token limit approaching"},
                {"timestamp": "2025-01-15 10:32:00", "level": "ERROR", "message": "Execution failed"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        text = response.text
        assert "2025-01-15 10:30:00" in text
        assert "INFO" in text
        assert "Phase plan started" in text

    def test_log_level_coloring(self) -> None:
        """Level coloring: INFO = default, WARN = text-warning, ERROR = text-error."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "info msg"},
                {"timestamp": "2025-01-15 10:30:01", "level": "WARN", "message": "warn msg"},
                {"timestamp": "2025-01-15 10:30:02", "level": "ERROR", "message": "error msg"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        assert "text-warning" in response.text
        assert "text-error" in response.text

    def test_log_container_styling(self) -> None:
        """Logs show in bg-base-300 rounded-lg p-4 font-mono text-xs."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "test"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        assert "bg-base-300" in response.text
        assert "rounded-lg" in response.text
        assert "p-4" in response.text
        assert "font-mono" in response.text
        assert "text-xs" in response.text

    def test_log_container_scrollable(self) -> None:
        """Container is scrollable with max-h-80 overflow-y-auto."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "test"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        assert "max-h-80" in response.text
        assert "overflow-y-auto" in response.text


# ── AC: Log Search Debounce (FR21) ─────────────────────────────────


class TestACLogSearchDebounce:
    """Acceptance criteria: Search with 300ms debounce."""

    def test_search_input_has_debounce_trigger(self) -> None:
        """Given user types in search input, 300ms debounce via
        hx-trigger='keyup changed delay:300ms'."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am, \
             patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
            mock_am.return_value.list_artifacts.return_value = []
            mock_llm.return_value = None
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert "keyup changed delay:300ms" in response.text

    def test_search_filter_uses_htmx(self) -> None:
        """Search filter targets log content div via hx-get."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am, \
             patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
            mock_am.return_value.list_artifacts.return_value = []
            mock_llm.return_value = None
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert f'hx-get="/runs/{entry.run_id}/logs"' in response.text
        assert '#log-content-plan' in response.text


# ── AC: Severity Filter (FR22) ────────────────────────────────────


class TestACSeverityFilter:
    """Acceptance criteria: Severity filter reloads logs."""

    def test_severity_filter_changes_reload_logs(self) -> None:
        """Given user changes severity filter, logs reload filtered."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        # Request with ERROR level
        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "Info"},
                {"timestamp": "2025-01-15 10:30:01", "level": "ERROR", "message": "Error occurred"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs?level=ERROR",
                headers={"HX-Request": "true"},
            )

        assert "Error occurred" in response.text
        assert "Info" not in response.text


# ── AC: Phase Filter (FR26) ───────────────────────────────────────


class TestACPhaseFilter:
    """Acceptance criteria: Phase filter reloads logs for selected phase."""

    def test_phase_filter_reloads_logs(self) -> None:
        """Given user changes phase filter, logs reload filtered."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            # _load_log_entries receives phase parameter
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "Phase build started"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs?phase=build",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        # Verify the helper was called with phase parameter
        mock_load.assert_called_once()
        call_kwargs = mock_load.call_args
        assert call_kwargs[1].get("phase") == "build" or (
            len(call_kwargs[0]) >= 3 and call_kwargs[0][2] == "build"
        )


# ── Security Tests ─────────────────────────────────────────────────


class TestSecurityLLMLogViewer:
    """Security tests for LLM and log viewer endpoints."""

    def test_prompt_endpoint_rejects_invalid_phase(self) -> None:
        """Prompt endpoint rejects phase not in PHASE_SEQUENCE."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])
        response = client.get(
            f"/runs/{entry.run_id}/phases/../../etc/prompt",
            headers={"HX-Request": "true"},
        )
        assert response.status_code in (400, 404)

    def test_response_endpoint_rejects_invalid_phase(self) -> None:
        """Response endpoint rejects invalid phase."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])
        response = client.get(
            f"/runs/{entry.run_id}/phases/notreal/response",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 400

    def test_log_endpoint_xss_prevention(self) -> None:
        """Log entries with HTML are escaped."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {
                    "timestamp": "2025-01-15 10:30:00",
                    "level": "INFO",
                    "message": '<script>alert("xss")</script>',
                },
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        assert "<script>" not in response.text
        assert "&lt;script&gt;" in response.text


# ── Data Layer Integration ─────────────────────────────────────────


class TestDataLayerIntegration:
    """Tests for real file-based data loading."""

    def test_llm_stats_loads_from_real_file(self, tmp_path: Path) -> None:
        """_load_llm_stats reads actual JSON response files."""
        from adw.dashboard.routes import _load_llm_stats

        llm_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A" / "llm"
        llm_dir.mkdir(parents=True)

        data = {
            "timestamp": "2025-01-15T10:32:00+00:00",
            "phase": "build",
            "stats": {
                "input_tokens": 8000,
                "output_tokens": 15000,
                "duration_ms": 12000,
            },
        }
        (llm_dir / "002_build_response.json").write_text(json.dumps(data))

        result = _load_llm_stats(tmp_path / "runs", "01TESTRUNID0000000000000A", "build")
        assert result is not None
        assert result["input_tokens"] == 8000
        assert result["output_tokens"] == 15000

    def test_llm_content_loads_response_from_artifact(self, tmp_path: Path) -> None:
        """_load_llm_content reads the {phase}_output.md artifact."""
        from adw.dashboard.routes import _load_llm_content

        artifacts_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A" / "artifacts" / "build"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "build_output.md").write_text("# Build Output\n\nGenerated code here")

        result = _load_llm_content(
            tmp_path / "runs", "01TESTRUNID0000000000000A", "build", "response"
        )
        assert result is not None
        assert "Build Output" in result

    def test_log_entries_parses_real_log_with_ansi(self, tmp_path: Path) -> None:
        """_load_log_entries strips ANSI codes from live.log."""
        from adw.dashboard.routes import _load_log_entries

        logs_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A" / "logs"
        logs_dir.mkdir(parents=True)

        # Simulate ANSI-colored log output
        log_content = (
            "\x1b[35m[2025-01-15 10:30:00] [PHASE] \x1b[0mPhase 'plan' started\n"
            "\x1b[36m[2025-01-15 10:30:01] [LLM] \x1b[0m\x1b[36mToken stream begins(plan)\x1b[0m\n"
            "\x1b[31m[2025-01-15 10:31:00] [ERROR] \x1b[0mExecution timeout\n"
        )
        (logs_dir / "live.log").write_text(log_content)

        entries = _load_log_entries(tmp_path / "runs", "01TESTRUNID0000000000000A")
        assert len(entries) == 3
        assert entries[0]["level"] == "INFO"
        assert entries[0]["message"] == "Phase 'plan' started"
        assert entries[2]["level"] == "ERROR"
        assert entries[2]["message"] == "Execution timeout"
        # No ANSI codes in output
        assert "\x1b" not in entries[0]["message"]
        assert "\x1b" not in entries[1]["message"]

    def test_log_entries_multiple_phases(self, tmp_path: Path) -> None:
        """Phase filter correctly isolates entries for a specific phase."""
        from adw.dashboard.routes import _load_log_entries

        logs_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A" / "logs"
        logs_dir.mkdir(parents=True)

        log_content = (
            "[2025-01-15 10:30:00] [PHASE] Phase 'plan' started\n"
            "[2025-01-15 10:30:30] [LLM] Token stream begins(plan)\n"
            "[2025-01-15 10:31:00] [PHASE] Phase 'plan' completed\n"
            "[2025-01-15 10:31:01] [PHASE] Phase 'build' started\n"
            "[2025-01-15 10:31:30] [LLM] Token stream begins(build)\n"
            "[2025-01-15 10:32:00] [PHASE] Phase 'build' completed\n"
        )
        (logs_dir / "live.log").write_text(log_content)

        plan_entries = _load_log_entries(
            tmp_path / "runs", "01TESTRUNID0000000000000A", phase="plan"
        )
        build_entries = _load_log_entries(
            tmp_path / "runs", "01TESTRUNID0000000000000A", phase="build"
        )

        assert len(plan_entries) == 3  # plan started, stream(plan), plan completed
        assert len(build_entries) == 3  # build started, stream(build), build completed
