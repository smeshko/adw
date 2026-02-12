"""Tests for Story 2.1: Run Detail Page Layout & Metadata.

Covers run detail route, dual-response pattern, context-aware back link,
title section, phase pipeline, metadata card, action buttons, and clipboard copy.
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
    has_runs: bool = True,
) -> MagicMock:
    """Build a mock IndexManager with configurable run data."""
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
    """Build a mock ProjectRegistryManager with project list."""
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
    """Create a TestClient with dependency overrides for run detail testing."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    im = _mock_index_manager(entries=entries or [])
    pr = _mock_project_registry(project_names or ["my-project"])
    # Stats aggregator needed for _build_page_context calls
    sa = MagicMock()
    sa.get_global_stats.return_value = MagicMock(projects=[])

    app.dependency_overrides[dependencies.get_index_manager] = lambda: im
    app.dependency_overrides[dependencies.get_project_registry] = lambda: pr
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: sa

    return TestClient(app)


# ── Route / Dual Response Pattern ───────────────────────────────────


class TestRunDetailRoute:
    """Tests for the /runs/{run_id} route."""

    def test_full_page_returns_html_with_base_layout(self) -> None:
        """Full page response wraps run detail in base.html layout."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(f"/runs/{entry.run_id}")

        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text
        assert "<header" in response.text
        assert '<main id="main"' in response.text

    def test_htmx_returns_partial_fragment(self) -> None:
        """HTMX request returns partial without full HTML wrapper."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        assert "<!DOCTYPE" not in response.text
        assert '<div id="run-detail"' in response.text

    def test_not_found_returns_404(self) -> None:
        """Non-existent run_id returns 404."""
        client = _make_client_with_mocks(entries=[])
        response = client.get("/runs/01HQXK5P3Z7V8R2M4N6T9W1Y00")
        assert response.status_code == 404

    def test_htmx_not_found_returns_fragment(self) -> None:
        """HTMX request for non-existent run returns 404 fragment."""
        client = _make_client_with_mocks(entries=[])
        response = client.get(
            "/runs/01HQXK5P3Z7V8R2M4N6T9W1Y00",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 404
        assert "Run not found" in response.text
        assert "<!DOCTYPE" not in response.text

    def test_url_is_bookmarkable(self) -> None:
        """Direct URL access returns a full page (bookmarkable)."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(f"/runs/{entry.run_id}")

        assert response.status_code == 200
        assert "ADW Dashboard" in response.text

    def test_page_title_includes_project_and_feature(self) -> None:
        """Page <title> includes project and feature names."""
        entry = _make_index_entry(
            project_name="my-app",
            feature_description="Add dark mode",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(f"/runs/{entry.run_id}")

        assert "my-app" in response.text
        assert "Add dark mode" in response.text


# ── Context-Aware Back Link ─────────────────────────────────────────


class TestBackLink:
    """Tests for the context-aware back link."""

    def test_default_back_to_overview(self) -> None:
        """Default back link goes to overview."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(f"/runs/{entry.run_id}")

        assert "Back to Overview" in response.text
        assert 'hx-get="/"' in response.text

    def test_from_runs_param_shows_back_to_runs(self) -> None:
        """?from=runs shows 'Back to Runs' link."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(f"/runs/{entry.run_id}?from=runs")

        assert "Back to Runs" in response.text
        assert 'hx-get="/runs"' in response.text

    def test_back_link_uses_htmx_navigation(self) -> None:
        """Back link uses hx-get, hx-target, and hx-push-url."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(f"/runs/{entry.run_id}")

        assert 'hx-target="#main"' in response.text
        assert "hx-push-url" in response.text


# ── Title Section ───────────────────────────────────────────────────


class TestTitleSection:
    """Tests for the title section with project, feature, status badge, meta."""

    def test_title_shows_project_and_feature(self) -> None:
        """Title shows 'project / feature' format."""
        entry = _make_index_entry(
            project_name="alpha",
            feature_description="Add login page",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "alpha" in response.text
        assert "Add login page" in response.text

    def test_project_name_is_semibold(self) -> None:
        """Project name uses font-semibold class."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "font-semibold" in response.text

    def test_status_badge_displayed(self) -> None:
        """Status badge is shown with correct status."""
        entry = _make_index_entry(status="completed")
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "badge-lg" in response.text
        assert "completed" in response.text

    def test_meta_line_shows_run_id_short(self) -> None:
        """Meta line shows truncated run ID."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # Truncated run ID (first 8 chars + ellipsis)
        assert entry.run_id[:8] in response.text

    def test_meta_line_shows_duration(self) -> None:
        """Meta line includes duration display."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # Duration should be some format like "Xm Ys"
        assert "m " in response.text

    def test_meta_line_shows_relative_time(self) -> None:
        """Meta line includes relative time (e.g. '10m ago')."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "ago" in response.text

    def test_meta_line_uses_font_mono(self) -> None:
        """Meta line uses font-mono styling."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "font-mono" in response.text


# ── Phase Pipeline ──────────────────────────────────────────────────


class TestPhasePipeline:
    """Tests for the full-width horizontal phase pipeline."""

    def test_pipeline_rendered(self) -> None:
        """Phase pipeline is rendered on the detail page."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "steps steps-horizontal" in response.text

    def test_pipeline_has_all_phases(self) -> None:
        """Pipeline shows all 5 phases."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "Plan" in response.text
        assert "Build" in response.text
        assert "Valid" in response.text
        assert "Doc" in response.text
        assert "Ship" in response.text

    def test_pipeline_is_full_width(self) -> None:
        """Pipeline uses w-full class."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "w-full" in response.text

    def test_completed_phases_have_success_class(self) -> None:
        """Completed phases get step-success class."""
        entry = _make_index_entry(
            phases_completed=["plan", "build"],
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "step-success" in response.text


# ── Metadata Card ───────────────────────────────────────────────────


class TestMetadataCard:
    """Tests for the metadata card with 2-column grid layout."""

    def test_metadata_card_rendered(self) -> None:
        """Metadata card is rendered."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "Metadata" in response.text

    def test_metadata_uses_card_bordered(self) -> None:
        """Metadata card uses card-bordered bg-base-200 classes."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "card-bordered" in response.text
        assert "bg-base-200" in response.text

    def test_metadata_shows_full_run_id(self) -> None:
        """Metadata shows the full ULID run ID."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert entry.run_id in response.text

    def test_metadata_has_two_column_grid(self) -> None:
        """Metadata uses CSS grid with 2 columns on medium screens."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "md:grid-cols-2" in response.text

    def test_metadata_shows_project(self) -> None:
        """Metadata card shows project name."""
        entry = _make_index_entry(project_name="test-proj")
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "test-proj" in response.text

    def test_metadata_shows_feature(self) -> None:
        """Metadata card shows feature description."""
        entry = _make_index_entry(feature_description="Dark mode toggle")
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "Dark mode toggle" in response.text

    def test_metadata_shows_timestamps(self) -> None:
        """Metadata card shows started and completed timestamps."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "Started" in response.text
        assert "Completed" in response.text
        assert "UTC" in response.text

    def test_metadata_copy_button_for_run_id(self) -> None:
        """Metadata card has copy button for run ID."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "copy-btn" in response.text
        assert f'data-copy="{entry.run_id}"' in response.text

    def test_metadata_no_branch_shows_dash(self) -> None:
        """Branch field shows dash when not available."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # Should show dash for branch when RunContext not available
        text = response.text
        assert "Branch" in text


# ── Action Buttons ──────────────────────────────────────────────────


class TestActionButtons:
    """Tests for the action buttons (Abort, Re-run)."""

    def test_rerun_button_shown_for_completed(self) -> None:
        """Re-run button is shown for completed runs."""
        entry = _make_index_entry(status="completed")
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "Re-run" in response.text

    def test_abort_button_shown_for_active_run(self) -> None:
        """Abort button is shown for running runs."""
        entry = _make_index_entry(status="running")
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "Abort" in response.text

    def test_abort_button_not_shown_for_completed(self) -> None:
        """Abort button is NOT shown for completed runs."""
        entry = _make_index_entry(status="completed")
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "Abort" not in response.text

    def test_rerun_button_uses_correct_style(self) -> None:
        """Re-run button uses btn-primary btn-outline btn-sm."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "btn-primary" in response.text
        assert "btn-outline" in response.text


# ── Clipboard Copy ──────────────────────────────────────────────────


class TestClipboardCopy:
    """Tests for clipboard copy functionality."""

    def test_clipboard_script_present(self) -> None:
        """Clipboard copy JavaScript is included in the page."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "navigator.clipboard" in response.text

    def test_copy_button_has_data_copy_attribute(self) -> None:
        """Copy button has data-copy attribute with run ID."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert f'data-copy="{entry.run_id}"' in response.text


# ── RunContext Enrichment ───────────────────────────────────────────


class TestRunContextEnrichment:
    """Tests for loading enriched data from RunContext."""

    def test_graceful_fallback_when_context_unavailable(self) -> None:
        """Page renders successfully when RunContext cannot be loaded."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        assert "run-detail" in response.text

    def test_branch_shown_when_context_available(self) -> None:
        """Branch name from RunContext is displayed."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.branch_name = "feature/auth-flow"
        mock_ctx.total_tokens = 50000
        mock_ctx.phase_tokens = {"plan": 30000, "build": 20000}
        mock_ctx.pr_url = None
        mock_ctx.task_id = None
        mock_ctx.task_manager = None
        mock_ctx.worktree_path = None

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "feature/auth-flow" in response.text

    def test_pr_link_shown_when_available(self) -> None:
        """PR link is displayed when RunContext has pr_url."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "document"
        mock_ctx.phase_history = ["plan", "build", "validate"]
        mock_ctx.branch_name = "feature/test"
        mock_ctx.total_tokens = 100000
        mock_ctx.phase_tokens = {}
        mock_ctx.pr_url = "https://github.com/org/repo/pull/42"
        mock_ctx.task_id = None
        mock_ctx.task_manager = None
        mock_ctx.worktree_path = None

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "https://github.com/org/repo/pull/42" in response.text

    def test_pr_link_hidden_when_not_available(self) -> None:
        """PR section is not shown when pr_url is None."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # PR row should not appear at all
        assert "github.com" not in response.text

    def test_linear_link_shown_when_available(self) -> None:
        """Linear link is displayed when task_id and task_manager are set."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.branch_name = "feature/test"
        mock_ctx.total_tokens = 50000
        mock_ctx.phase_tokens = {}
        mock_ctx.pr_url = None
        mock_ctx.task_id = "ADW-17"
        mock_ctx.task_manager = "linear"
        mock_ctx.worktree_path = None

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "ADW-17" in response.text
        assert "linear.app" in response.text


# ── Helper Function Tests ───────────────────────────────────────────


class TestBuildDetailPhasePipeline:
    """Tests for _build_detail_phase_pipeline helper."""

    def test_all_phases_present(self) -> None:
        """Pipeline includes all 5 phases."""
        from adw.dashboard.routes import _build_detail_phase_pipeline

        result = _build_detail_phase_pipeline(
            phases_completed=[], current_phase="plan", status="running",
        )
        assert len(result) == 5
        names = [p["name"] for p in result]
        assert names == ["Plan", "Build", "Valid", "Doc", "Ship"]

    def test_completed_phases_marked(self) -> None:
        """Completed phases have status='completed'."""
        from adw.dashboard.routes import _build_detail_phase_pipeline

        result = _build_detail_phase_pipeline(
            phases_completed=["plan", "build"],
            current_phase="validate",
            status="running",
        )
        assert result[0]["status"] == "completed"
        assert result[1]["status"] == "completed"
        assert result[2]["status"] == "active"
        assert result[3]["status"] == "pending"

    def test_failed_run_shows_failed_phase(self) -> None:
        """Failed run marks current phase as 'failed'."""
        from adw.dashboard.routes import _build_detail_phase_pipeline

        result = _build_detail_phase_pipeline(
            phases_completed=["plan"],
            current_phase="build",
            status="failed",
        )
        assert result[0]["status"] == "completed"
        assert result[1]["status"] == "failed"

    def test_duration_included_when_available(self) -> None:
        """Duration string populated when phase_durations provided."""
        from adw.dashboard.routes import _build_detail_phase_pipeline

        result = _build_detail_phase_pipeline(
            phases_completed=["plan"],
            current_phase="build",
            status="running",
            phase_durations={"plan": 90000},  # 1m 30s
        )
        assert result[0]["duration"] == "1m 30s"
        assert result[1]["duration"] == ""


# ── Phase Accordion Context ─────────────────────────────────────────


class TestPhaseAccordionContext:
    """Tests for per-phase data in run detail context (Task 1)."""

    def test_phases_detail_present_when_context_available(self) -> None:
        """phases_detail list is present in template context."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.branch_name = "feature/test"
        mock_ctx.total_tokens = 80000
        mock_ctx.phase_tokens = {"plan": 50000, "build": 30000}
        mock_ctx.pr_url = None
        mock_ctx.task_id = None
        mock_ctx.task_manager = None
        mock_ctx.worktree_path = None

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # phases_detail data should populate accordion section
        assert response.status_code == 200
        # Check that phase names appear in accordion context
        assert "Plan" in response.text
        assert "Build" in response.text

    def test_phases_detail_shows_token_counts(self) -> None:
        """Per-phase token counts are displayed."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.branch_name = "feature/test"
        mock_ctx.total_tokens = 80000
        mock_ctx.phase_tokens = {"plan": 50000, "build": 30000}
        mock_ctx.pr_url = None
        mock_ctx.task_id = None
        mock_ctx.task_manager = None
        mock_ctx.worktree_path = None

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # Token counts should appear in accordion (50000 → "50K", 30000 → "30K")
        assert "50K" in response.text  # plan tokens
        assert "30K" in response.text  # build tokens

    def test_phases_detail_shows_cost_estimates(self) -> None:
        """Per-phase cost estimates are displayed."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.branch_name = "feature/test"
        mock_ctx.total_tokens = 80000
        mock_ctx.phase_tokens = {"plan": 50000, "build": 30000}
        mock_ctx.pr_url = None
        mock_ctx.task_id = None
        mock_ctx.task_manager = None
        mock_ctx.worktree_path = None

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # Cost estimates should appear (50000 * 0.000009 = $0.45)
        assert "$0.45" in response.text
        assert "$0.27" in response.text

    def test_phases_detail_includes_phase_key(self) -> None:
        """Phase accordion uses phase_key for HTMX URLs."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.branch_name = "feature/test"
        mock_ctx.total_tokens = 80000
        mock_ctx.phase_tokens = {"plan": 50000, "build": 30000}
        mock_ctx.pr_url = None
        mock_ctx.task_id = None
        mock_ctx.task_manager = None
        mock_ctx.worktree_path = None

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # HTMX URLs should use lowercase phase keys
        assert f"/runs/{entry.run_id}/phases/plan" in response.text
        assert f"/runs/{entry.run_id}/phases/build" in response.text

    def test_phases_detail_fallback_when_no_context(self) -> None:
        """phases_detail works with fallback data when RunContext unavailable."""
        entry = _make_index_entry(
            phases_completed=["plan", "build"],
            phase_reached="validate",
        )
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        # Should still render accordion with phase names
        assert response.status_code == 200
        # Accordion section should be present
        assert "collapse collapse-arrow" in response.text

    def test_accordion_has_collapse_classes(self) -> None:
        """Phase accordion uses collapse collapse-arrow bg-base-200."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "collapse collapse-arrow bg-base-200" in response.text

    def test_accordion_has_htmx_lazy_loading(self) -> None:
        """Phase accordion uses hx-trigger='change once' for lazy loading."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert 'hx-trigger="change once"' in response.text
        assert 'hx-swap="innerHTML"' in response.text

    def test_accordion_has_loading_indicator(self) -> None:
        """Phase accordion includes loading-dots indicator."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert "loading loading-dots" in response.text

    def test_artifact_viewer_panel_present(self) -> None:
        """Artifact viewer target div is present on the page."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}",
                headers={"HX-Request": "true"},
            )

        assert 'id="artifact-viewer"' in response.text


# ── Phase Detail Route ──────────────────────────────────────────────


class TestPhaseDetailRoute:
    """Tests for GET /runs/{id}/phases/{phase} route (Task 3)."""

    def test_phase_detail_returns_200(self) -> None:
        """Phase detail route returns 200 for a valid phase."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.artifacts = {"plan": ["plan_output.md"]}
        mock_ctx.phase_tokens = {"plan": 50000}

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200

    def test_phase_detail_shows_hooks_section(self) -> None:
        """Phase detail includes a hooks section."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.artifacts = {}
        mock_ctx.phase_tokens = {}

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert "Hooks" in response.text

    def test_phase_detail_shows_artifacts_section(self) -> None:
        """Phase detail includes an artifacts section."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.artifacts = {"plan": ["plan_output.md"]}
        mock_ctx.phase_tokens = {}

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = mock_ctx
            mock_am.return_value.list_artifacts.return_value = [
                {"phase": "plan", "name": "plan_output.md", "size": 1234, "path": "/tmp/a"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert "Artifacts" in response.text
        assert "plan_output.md" in response.text

    def test_phase_detail_no_hooks_message(self) -> None:
        """Phase detail shows 'no hooks' message when none configured."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.artifacts = {}
        mock_ctx.phase_tokens = {}

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert "No hooks configured" in response.text

    def test_phase_detail_no_artifacts_message(self) -> None:
        """Phase detail shows 'no artifacts' message when none exist."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.artifacts = {}
        mock_ctx.phase_tokens = {}

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = mock_ctx
            mock_am.return_value.list_artifacts.return_value = []
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert "No artifacts produced" in response.text

    def test_phase_detail_artifact_has_view_button(self) -> None:
        """Each artifact has a [View] button with hx-get."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.artifacts = {"plan": ["output.md"]}
        mock_ctx.phase_tokens = {}

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = mock_ctx
            mock_am.return_value.list_artifacts.return_value = [
                {"phase": "plan", "name": "output.md", "size": 500, "path": "/tmp/a"},
            ]
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert "View" in response.text
        assert f'hx-get="/runs/{entry.run_id}/artifacts/plan/output.md"' in response.text
        assert 'hx-target="#artifact-viewer"' in response.text

    def test_phase_detail_uses_card_classes(self) -> None:
        """Phase detail sections use card card-compact bg-base-300."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        mock_ctx = MagicMock()
        mock_ctx.current_phase = "build"
        mock_ctx.phase_history = ["plan"]
        mock_ctx.artifacts = {}
        mock_ctx.phase_tokens = {}

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = mock_ctx
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        assert "card card-compact bg-base-300" in response.text

    def test_phase_detail_context_unavailable_returns_error(self) -> None:
        """Phase detail gracefully handles unavailable RunContext."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm:
            mock_cm.return_value.load.side_effect = OSError("not found")
            response = client.get(
                f"/runs/{entry.run_id}/phases/plan",
                headers={"HX-Request": "true"},
            )

        # Should return 200 with fallback content
        assert response.status_code == 200

    def test_phase_detail_run_not_found(self) -> None:
        """Phase detail for non-existent run returns 404."""
        client = _make_client_with_mocks(entries=[])
        response = client.get(
            "/runs/01HQXK5P3Z7V8R2M4N6T9W1Y00/phases/plan",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 404


# ── Artifact Viewer Route ───────────────────────────────────────────


class TestArtifactViewerRoute:
    """Tests for GET /runs/{id}/artifacts/{phase}/{filename} route (Task 5)."""

    def test_artifact_viewer_returns_200(self) -> None:
        """Artifact viewer returns 200 for existing artifact."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.return_value = "# Plan Output\nSome content here"
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/plan_output.md",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200

    def test_artifact_viewer_shows_filename(self) -> None:
        """Artifact viewer shows the filename in header."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.return_value = "content"
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/output.txt",
                headers={"HX-Request": "true"},
            )

        assert "output.txt" in response.text

    def test_artifact_viewer_shows_content(self) -> None:
        """Artifact viewer displays the file content."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.return_value = "Hello World Content"
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/test.txt",
                headers={"HX-Request": "true"},
            )

        assert "Hello World Content" in response.text

    def test_artifact_viewer_uses_card_classes(self) -> None:
        """Artifact viewer uses card bg-base-300 styling."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.return_value = "content"
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/test.txt",
                headers={"HX-Request": "true"},
            )

        assert "card bg-base-300" in response.text

    def test_artifact_viewer_has_close_button(self) -> None:
        """Artifact viewer has a close button."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.return_value = "content"
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/test.txt",
                headers={"HX-Request": "true"},
            )

        assert "Close" in response.text or "close" in response.text.lower()

    def test_artifact_viewer_pre_block_for_text(self) -> None:
        """Non-markdown files render in pre block."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.return_value = "plain text content"
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/output.txt",
                headers={"HX-Request": "true"},
            )

        assert "<pre" in response.text

    def test_artifact_viewer_404_for_missing_artifact(self) -> None:
        """Missing artifact returns 404 fragment."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.return_value = None
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/nonexistent.txt",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 404

    def test_artifact_viewer_404_for_missing_run(self) -> None:
        """Artifact viewer for non-existent run returns 404."""
        client = _make_client_with_mocks(entries=[])
        response = client.get(
            "/runs/01HQXK5P3Z7V8R2M4N6T9W1Y00/artifacts/plan/test.txt",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 404

    def test_artifact_viewer_markdown_rendered(self) -> None:
        """Markdown files are rendered as HTML with prose class."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.return_value = "# Heading\n\nParagraph text"
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/output.md",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        # Should have prose class for markdown rendering
        assert "prose" in response.text


# ── Security Tests (Path Traversal & XSS) ──────────────────────────


class TestPathTraversalProtection:
    """Tests for path traversal and input validation (NFR10)."""

    def test_phase_detail_rejects_invalid_phase(self) -> None:
        """Phase detail returns 400 for phase not in PHASE_SEQUENCE."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])
        response = client.get(
            f"/runs/{entry.run_id}/phases/notaphase",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 400

    def test_phase_detail_rejects_dotdot_phase(self) -> None:
        """Phase detail returns 400 for '..' as phase value."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])
        # Use %2e%2e to bypass URL normalization
        response = client.get(
            f"/runs/{entry.run_id}/phases/%2e%2e",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 400

    def test_artifact_viewer_rejects_invalid_phase(self) -> None:
        """Artifact viewer returns 400 for invalid phase."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])
        response = client.get(
            f"/runs/{entry.run_id}/artifacts/badphase/test.txt",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 400

    def test_artifact_viewer_rejects_dotdot_filename(self) -> None:
        """Artifact viewer returns 400 for '..' in filename."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])
        response = client.get(
            f"/runs/{entry.run_id}/artifacts/plan/%2e%2e%2fetc%2fpasswd",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 400

    def test_artifact_viewer_rejects_absolute_filename(self) -> None:
        """Artifact viewer returns 400 for filename starting with /."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])
        response = client.get(
            f"/runs/{entry.run_id}/artifacts/plan//etc/passwd",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 400

    def test_artifact_viewer_markdown_xss_prevention(self) -> None:
        """Markdown rendering escapes script tags to prevent XSS."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.return_value = '<script>alert("xss")</script>\n# Hello'
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/evil.md",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 200
        assert "<script>" not in response.text
        assert "&lt;script&gt;" in response.text


class TestBinaryArtifactHandling:
    """Tests for handling binary/non-UTF8 artifacts gracefully."""

    def test_artifact_viewer_handles_unicode_error(self) -> None:
        """Binary files that cause UnicodeDecodeError return 404."""
        entry = _make_index_entry()
        client = _make_client_with_mocks(entries=[entry])

        with patch("adw.dashboard.routes.ContextManager") as mock_cm, \
             patch("adw.dashboard.routes.ArtifactManager") as mock_am:
            mock_cm.return_value.load.return_value = MagicMock()
            mock_am.return_value.get.side_effect = UnicodeDecodeError(
                "utf-8", b"\xff\xfe", 0, 1, "invalid start byte",
            )
            response = client.get(
                f"/runs/{entry.run_id}/artifacts/plan/binary.bin",
                headers={"HX-Request": "true"},
            )

        assert response.status_code == 404


# ── Helper Function Tests (New) ─────────────────────────────────────


class TestFormatFileSize:
    """Tests for _format_file_size helper."""

    def test_bytes(self) -> None:
        """Small files show bytes."""
        from adw.dashboard.routes import _format_file_size

        assert _format_file_size(512) == "512 B"

    def test_kilobytes(self) -> None:
        """Medium files show KB."""
        from adw.dashboard.routes import _format_file_size

        assert _format_file_size(2048) == "2.0 KB"

    def test_megabytes(self) -> None:
        """Large files show MB."""
        from adw.dashboard.routes import _format_file_size

        assert _format_file_size(1048576) == "1.0 MB"


class TestFindRunEntry:
    """Tests for _find_run_entry helper."""

    def test_finds_existing_run(self) -> None:
        """Returns entry when run exists."""
        from adw.dashboard.routes import _find_run_entry

        entry = _make_index_entry()
        mock_im = _mock_index_manager(entries=[entry])
        result = _find_run_entry(mock_im, entry.run_id)
        assert result is not None
        assert result.run_id == entry.run_id

    def test_returns_none_for_missing_run(self) -> None:
        """Returns None when run not found."""
        from adw.dashboard.routes import _find_run_entry

        mock_im = _mock_index_manager(entries=[])
        result = _find_run_entry(mock_im, "01HQXK5P3Z7V8R2M4N6T9W1Y00")
        assert result is None

    def test_handles_exception_gracefully(self) -> None:
        """Returns None when index manager throws."""
        from adw.dashboard.routes import _find_run_entry

        mock_im = MagicMock()
        mock_im.get_recent_runs.side_effect = RuntimeError("db error")
        result = _find_run_entry(mock_im, "test-id")
        assert result is None


class TestFormatDurationFromSeconds:
    """Tests for _format_duration_from_seconds helper."""

    def test_seconds_only(self) -> None:
        """Under 60 seconds shows Xs."""
        from adw.dashboard.routes import _format_duration_from_seconds

        assert _format_duration_from_seconds(45) == "45s"

    def test_minutes_and_seconds(self) -> None:
        """Minutes and seconds format."""
        from adw.dashboard.routes import _format_duration_from_seconds

        assert _format_duration_from_seconds(125) == "2m 5s"

    def test_hours_and_minutes(self) -> None:
        """Large duration shows hours."""
        from adw.dashboard.routes import _format_duration_from_seconds

        assert _format_duration_from_seconds(3725) == "1h 2m"
