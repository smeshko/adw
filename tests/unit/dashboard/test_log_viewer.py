"""Tests for Story 2.3: Log Viewer.

Covers log search endpoint, log filtering by keyword/severity/phase,
log content template, and 300ms debounce integration.
"""

from __future__ import annotations

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


# ── Log Search Endpoint ─────────────────────────────────────────────


class TestLogSearchEndpoint:
    """Tests for GET /runs/{id}/logs endpoint (FR21, FR22, FR26)."""

    def test_logs_returns_200(self) -> None:
        """Log endpoint returns 200."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = []
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200

    def test_logs_run_not_found_returns_404(self) -> None:
        """Log endpoint for non-existent run returns 404."""
        client = _make_client_with_mocks(entries=[])
        response = client.get(
            "/runs/01HQXK5P3Z7V8R2M4N6T9W1Y00/logs",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 404

    def test_logs_shows_entries(self) -> None:
        """Log endpoint renders log entries."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "Phase started"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        assert "Phase started" in response.text

    def test_logs_uses_monospace_styling(self) -> None:
        """Log content uses font-mono text-xs styling."""
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

        assert "font-mono" in response.text
        assert "text-xs" in response.text

    def test_logs_warn_uses_warning_color(self) -> None:
        """WARN entries use text-warning class."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "WARN", "message": "Warning msg"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        assert "text-warning" in response.text

    def test_logs_error_uses_error_color(self) -> None:
        """ERROR entries use text-error class."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "ERROR", "message": "Error msg"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        assert "text-error" in response.text

    def test_logs_filters_by_query(self) -> None:
        """Query parameter filters log entries."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "Phase started"},
                {"timestamp": "2025-01-15 10:31:00", "level": "INFO", "message": "Token stream"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs?q=Token",
                headers={"HX-Request": "true"},
            )

        assert "Token stream" in response.text
        assert "Phase started" not in response.text

    def test_logs_filters_by_level(self) -> None:
        """Level parameter filters log entries by severity."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "Info msg"},
                {"timestamp": "2025-01-15 10:31:00", "level": "ERROR", "message": "Error msg"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs?level=ERROR",
                headers={"HX-Request": "true"},
            )

        assert "Error msg" in response.text
        assert "Info msg" not in response.text

    def test_logs_empty_shows_no_logs_message(self) -> None:
        """Empty log results show 'No log entries' message."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = []
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        assert "No log entries" in response.text

    def test_logs_scrollable_container(self) -> None:
        """Log container has max-h-80 overflow-y-auto for scrollability."""
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

    def test_logs_entry_format(self) -> None:
        """Each log line shows {timestamp} {level} {message}."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes._load_log_entries") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2025-01-15 10:30:00", "level": "INFO", "message": "Phase plan started"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/logs",
                headers={"HX-Request": "true"},
            )

        # All three parts should appear on the same line
        assert "2025-01-15 10:30:00" in response.text
        assert "INFO" in response.text
        assert "Phase plan started" in response.text


# ── Log Viewer Template in Phase Detail ────────────────────────────


class TestLogViewerInPhaseDetail:
    """Tests for log viewer controls in phase detail template."""

    def test_phase_detail_has_log_section(self) -> None:
        """Phase detail includes a Logs section."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = None
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert "Logs" in response.text

    def test_phase_detail_has_search_input(self) -> None:
        """Log viewer has a search input with debounce."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = None
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert "input input-bordered input-sm" in response.text
        assert "delay:300ms" in response.text

    def test_phase_detail_has_severity_filter(self) -> None:
        """Log viewer has severity filter dropdown."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = None
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert "select select-bordered select-sm" in response.text
        assert ">INFO<" in response.text
        assert ">WARN<" in response.text
        assert ">ERROR<" in response.text

    def test_phase_detail_log_viewer_prefiltered_to_phase(self) -> None:
        """Log viewer is pre-filtered to the current phase."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = None
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert f"/runs/{entry.run_id}/logs?phase=plan" in response.text

    def test_phase_detail_log_target_uses_phase_id(self) -> None:
        """Log content target div uses phase-specific ID."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_am.return_value.list_artifacts.return_value = []
            with patch("adw.dashboard.routes._load_llm_stats") as mock_llm:
                mock_llm.return_value = None
                response = client.get(
                    f"/runs/{entry.run_id}/phases/plan",
                    headers={"HX-Request": "true"},
                )

        assert 'id="log-content-plan"' in response.text


# ── Helper Function Tests ──────────────────────────────────────────


class TestLoadLogEntries:
    """Tests for _load_log_entries helper."""

    def test_parses_live_log_file(self, tmp_path: Path) -> None:
        """Parses entries from live.log file."""
        from adw.dashboard.routes import _load_log_entries

        run_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A"
        run_dir.mkdir(parents=True)

        log_content = (
            "[2025-01-15 10:30:00] [PHASE] Phase 'plan' started\n"
            "[2025-01-15 10:30:05] [LLM] Token stream begins\n"
            "[2025-01-15 10:31:00] [ERROR] Something went wrong\n"
        )
        (run_dir / "live.log").write_text(log_content)

        runs_dir = tmp_path / "runs"
        entries = _load_log_entries(runs_dir, "01TESTRUNID0000000000000A")
        assert len(entries) == 3
        assert entries[0]["level"] == "INFO"
        assert entries[2]["level"] == "ERROR"

    def test_returns_empty_when_no_log_file(self, tmp_path: Path) -> None:
        """Returns empty list when no log file exists."""
        from adw.dashboard.routes import _load_log_entries

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True)
        entries = _load_log_entries(runs_dir, "01TESTRUNID0000000000000A")
        assert entries == []

    def test_filters_by_phase(self, tmp_path: Path) -> None:
        """Filters entries containing the phase name."""
        from adw.dashboard.routes import _load_log_entries

        run_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A"
        run_dir.mkdir(parents=True)

        log_content = (
            "[2025-01-15 10:30:00] [PHASE] Phase 'plan' started\n"
            "[2025-01-15 10:31:00] [PHASE] Phase 'build' started\n"
        )
        (run_dir / "live.log").write_text(log_content)

        runs_dir = tmp_path / "runs"
        entries = _load_log_entries(runs_dir, "01TESTRUNID0000000000000A", phase="plan")
        assert len(entries) == 1
        assert "plan" in entries[0]["message"]

    def test_phase_filter_uses_word_boundary(self, tmp_path: Path) -> None:
        """Phase filter uses word-boundary match to avoid false positives."""
        from adw.dashboard.routes import _load_log_entries

        run_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A"
        run_dir.mkdir(parents=True)

        log_content = (
            "[2025-01-15 10:30:00] [PHASE] Phase 'plan' started\n"
            "[2025-01-15 10:30:05] [INFO] Let me explain the approach\n"
            "[2025-01-15 10:30:10] [LLM] Token stream begins(plan)\n"
        )
        (run_dir / "live.log").write_text(log_content)

        runs_dir = tmp_path / "runs"
        entries = _load_log_entries(runs_dir, "01TESTRUNID0000000000000A", phase="plan")
        # "explain" should NOT match, but "Phase 'plan'" and "(plan)" should
        assert len(entries) == 2
        assert all("plan" in e["message"] for e in entries)
        assert not any("explain" in e["message"] for e in entries)

    def test_handles_malformed_lines(self, tmp_path: Path) -> None:
        """Skips lines that don't match the expected format."""
        from adw.dashboard.routes import _load_log_entries

        run_dir = tmp_path / "runs" / "01TESTRUNID0000000000000A"
        run_dir.mkdir(parents=True)

        log_content = (
            "random text without brackets\n"
            "[2025-01-15 10:30:00] [INFO] Valid log line\n"
            "\n"
        )
        (run_dir / "live.log").write_text(log_content)

        runs_dir = tmp_path / "runs"
        entries = _load_log_entries(runs_dir, "01TESTRUNID0000000000000A")
        assert len(entries) == 1
        assert entries[0]["message"] == "Valid log line"
