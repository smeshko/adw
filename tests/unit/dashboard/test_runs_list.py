"""Tests for the runs list page.

Covers the /runs route with dual-response pattern, runs table rendering,
pagination, sort dropdown, empty state, and query parameter forwarding.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from adw.dashboard.server import create_dashboard_app


# ── Helpers ────────────────────────────────────────────────────────


def _make_entry(
    run_id: str = "01KDSG2VDHNK0W4HSCZWJZXWSQ",
    project_name: str = "test-project",
    feature_description: str = "Add auth feature",
    status: str = "completed",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    duration_minutes: int = 5,
) -> MagicMock:
    """Build a mock IndexEntry."""
    entry = MagicMock()
    entry.run_id = run_id
    entry.project_name = project_name
    entry.feature_description = feature_description
    entry.status = status
    entry.started_at = started_at or (datetime.now(UTC) - timedelta(minutes=25))
    if status == "running":
        entry.completed_at = None
    else:
        entry.completed_at = completed_at or (
            entry.started_at + timedelta(minutes=duration_minutes)
        )
    return entry


def _mock_index_manager(
    entries: list[MagicMock] | None = None,
    active_count: int = 0,
    total_count: int | None = None,
    total_pages: int | None = None,
    page: int = 1,
) -> MagicMock:
    """Build a mock IndexManager with paginated runs support."""
    mock = MagicMock()
    running_runs = [MagicMock() for _ in range(active_count)]
    recent_entries = entries or []

    # get_recent_runs (used by _build_page_context)
    def get_recent_side_effect(**kwargs):
        if kwargs.get("status") == "running":
            return running_runs
        limit = kwargs.get("limit", 10)
        project_name = kwargs.get("project_name")
        filtered = recent_entries
        if project_name:
            filtered = [e for e in filtered if e.project_name == project_name]
        return filtered[:limit]

    mock.get_recent_runs.side_effect = get_recent_side_effect

    # get_paginated_runs (used by runs_list route)
    count = total_count if total_count is not None else len(recent_entries)
    pages = total_pages if total_pages is not None else max(1, (count + 14) // 15) if count else 0

    def get_paginated_side_effect(**kwargs):
        pg = kwargs.get("page", 1)
        pg_size = kwargs.get("page_size", 15)
        status_filter = kwargs.get("status")
        proj = kwargs.get("project_name")
        filtered = recent_entries
        if status_filter:
            filtered = [e for e in filtered if e.status == status_filter]
        if proj:
            filtered = [e for e in filtered if e.project_name == proj]
        c = len(filtered)
        tp = max(1, (c + pg_size - 1) // pg_size) if c else 0
        start = (pg - 1) * pg_size
        end = start + pg_size
        return {
            "entries": filtered[start:end],
            "total_count": c,
            "page": pg,
            "page_size": pg_size,
            "total_pages": tp,
        }

    mock.get_paginated_runs.side_effect = get_paginated_side_effect
    return mock


def _mock_stats_aggregator() -> MagicMock:
    """Build a minimal mock StatsAggregator."""
    from adw.models.stats import GlobalStatistics, TokenUsage

    mock = MagicMock()
    stats = GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=42,
        runs_this_week=10,
        runs_today=2,
        completed_runs=35,
        failed_runs=7,
        success_rate=0.83,
        average_duration_ms=120000,
        tokens=TokenUsage(input_tokens=500_000, output_tokens=100_000),
        estimated_cost=5.0,
        previous_week_total_runs=8,
        previous_week_success_rate=0.8,
        previous_week_average_duration_ms=130000,
        tokens_this_week=TokenUsage(input_tokens=200_000, output_tokens=50_000),
        cost_this_week=2.0,
        projects=[],
    )
    mock.get_global_stats.return_value = stats
    return mock


def _mock_project_registry(
    project_names: list[str] | None = None,
) -> MagicMock:
    """Build a mock ProjectRegistryManager."""
    mock = MagicMock()
    projects = []
    for name in project_names or []:
        p = MagicMock()
        p.name = name
        projects.append(p)
    mock.get_all.return_value = projects
    return mock


def _make_client_with_mocks(
    index_manager: MagicMock | None = None,
    stats_aggregator: MagicMock | None = None,
    project_registry: MagicMock | None = None,
) -> TestClient:
    """Create a TestClient with dependency overrides."""
    from adw.dashboard import dependencies

    app = create_dashboard_app()
    im = index_manager or _mock_index_manager()
    sa = stats_aggregator or _mock_stats_aggregator()
    pr = project_registry or _mock_project_registry()

    app.dependency_overrides[dependencies.get_index_manager] = lambda: im
    app.dependency_overrides[dependencies.get_stats_aggregator] = lambda: sa
    app.dependency_overrides[dependencies.get_project_registry] = lambda: pr

    return TestClient(app)


# ── Basic Route Tests ─────────────────────────────────────────────


class TestRunsListRoute:
    """Tests for GET /runs basic behavior."""

    def test_returns_200(self) -> None:
        """Runs list returns HTTP 200."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert response.status_code == 200

    def test_returns_html(self) -> None:
        """Runs list returns HTML content type."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert "text/html" in response.headers["content-type"]

    def test_full_page_has_title(self) -> None:
        """Full page response includes 'All Runs' title."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert "All Runs" in response.text


# ── Dual-Response Pattern ─────────────────────────────────────────


class TestRunsListDualResponse:
    """Tests for dual-response pattern on /runs."""

    def test_full_page_without_hx_header(self) -> None:
        """Without HX-Request, renders full page with base layout."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert "<!DOCTYPE html>" in response.text or "<html" in response.text

    def test_partial_with_hx_header(self) -> None:
        """With HX-Request, renders partial without base layout."""
        client = _make_client_with_mocks()
        response = client.get("/runs", headers={"HX-Request": "true"})
        assert "<!DOCTYPE html>" not in response.text
        assert 'id="runs-list"' in response.text

    def test_runs_content_target_present(self) -> None:
        """Response contains #runs-content div as swap target."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert 'id="runs-content"' in response.text

    def test_table_partial_with_runs_content_target(self) -> None:
        """HX-Target=runs-content returns only table partial."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get(
            "/runs",
            headers={"HX-Request": "true", "HX-Target": "runs-content"},
        )
        # Should NOT include the page header
        assert 'id="runs-list"' not in response.text
        # Should include the table
        assert "table" in response.text


# ── Page Header ───────────────────────────────────────────────────


class TestRunsListHeader:
    """Tests for page header elements."""

    def test_page_title(self) -> None:
        """Page shows 'All Runs' heading."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert "All Runs" in response.text

    def test_new_run_button(self) -> None:
        """'+ New Run' button is present."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert "+ New Run" in response.text

    def test_new_run_button_style(self) -> None:
        """'+ New Run' button uses btn-primary btn-sm classes."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert "btn btn-primary btn-sm" in response.text


# ── Table Rendering ───────────────────────────────────────────────


class TestRunsTable:
    """Tests for the runs data table."""

    def test_table_classes(self) -> None:
        """Table has table-zebra table-sm hover classes."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "table table-zebra table-sm hover" in response.text

    def test_overflow_wrapper(self) -> None:
        """Table has overflow-x-auto wrapper."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "overflow-x-auto" in response.text

    def test_displays_project_name(self) -> None:
        """Run row shows project name."""
        entries = [_make_entry(project_name="my-api")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "my-api" in response.text

    def test_displays_feature_description(self) -> None:
        """Run row shows feature description."""
        entries = [_make_entry(feature_description="Add user auth")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "Add user auth" in response.text

    def test_displays_status_badge(self) -> None:
        """Run row shows status badge."""
        entries = [_make_entry(status="completed")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "badge" in response.text
        assert "completed" in response.text

    def test_displays_duration(self) -> None:
        """Completed run shows duration in Xm Ys format."""
        entries = [_make_entry(duration_minutes=3)]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "3m 0s" in response.text

    def test_displays_relative_time(self) -> None:
        """Started column shows relative time."""
        entries = [_make_entry(started_at=datetime.now(UTC) - timedelta(minutes=25))]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "25m ago" in response.text

    def test_rows_are_clickable(self) -> None:
        """Each row has hx-get and cursor-pointer for click navigation."""
        entries = [_make_entry(run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "cursor-pointer" in response.text
        assert 'hx-get="/runs/01KDSG2VDHNK0W4HSCZWJZXWSQ"' in response.text

    def test_row_targets_main(self) -> None:
        """Row click targets #main for full page navigation."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert 'hx-target="#main"' in response.text

    def test_row_pushes_url(self) -> None:
        """Row click pushes run detail URL."""
        entries = [_make_entry(run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ")]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert 'hx-push-url="/runs/01KDSG2VDHNK0W4HSCZWJZXWSQ"' in response.text


# ── Sort Dropdown ─────────────────────────────────────────────────


class TestRunsListSortDropdown:
    """Tests for the sort dropdown."""

    def test_sort_dropdown_present(self) -> None:
        """Sort dropdown select element is present."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert "select select-bordered select-xs" in response.text

    def test_sort_options(self) -> None:
        """All five sort options are present."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert "Newest" in response.text
        assert "Oldest" in response.text
        assert "Duration (longest)" in response.text
        assert "Duration (shortest)" in response.text
        assert "Project (A-Z)" in response.text

    def test_default_sort_selected(self) -> None:
        """Newest is selected by default."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        # Check that newest option has selected attribute in the sort dropdown
        text = response.text
        # Find the sort select element (select-xs class distinguishes it from filter bar selects)
        sort_select_pos = text.find("select-xs")
        assert sort_select_pos > 0
        newest_pos = text.find('value="newest"', sort_select_pos)
        assert newest_pos > 0
        option_start = text.rfind("<option", 0, newest_pos)
        option_chunk = text[option_start:newest_pos + 30]
        assert "selected" in option_chunk


# ── Summary Line ──────────────────────────────────────────────────


class TestRunsListSummary:
    """Tests for the summary line above the table."""

    def test_shows_run_count(self) -> None:
        """Summary shows count of matching runs."""
        entries = [_make_entry(run_id=f"01KDSG2VDHNK0W4HSCZWJZXWS{chr(65 + i)}") for i in range(3)]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "Showing 3 runs" in response.text

    def test_singular_run_count(self) -> None:
        """Summary uses singular 'run' for count of 1."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "Showing 1 run" in response.text

    def test_zero_runs_count(self) -> None:
        """Summary shows 0 runs when empty."""
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=[]),
        )
        response = client.get("/runs")
        assert "Showing 0 runs" in response.text


# ── Pagination ────────────────────────────────────────────────────


class TestRunsListPagination:
    """Tests for pagination controls."""

    def test_no_pagination_when_single_page(self) -> None:
        """Pagination doesn't render when total_pages <= 1."""
        entries = [_make_entry(run_id=f"01KDSG2VDHNK0W4HSCZWJZXWS{chr(65 + i)}") for i in range(5)]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "join-item" not in response.text

    def test_pagination_renders_when_multiple_pages(self) -> None:
        """Pagination renders when total_pages > 1."""
        entries = [
            _make_entry(run_id=f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}")
            for i in range(20)
        ]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "join-item" in response.text

    def test_current_page_has_btn_active(self) -> None:
        """Current page button has btn-active class."""
        entries = [
            _make_entry(run_id=f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}")
            for i in range(20)
        ]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert "btn-active" in response.text

    def test_pagination_preserves_sort(self) -> None:
        """Pagination links include sort parameter."""
        entries = [
            _make_entry(run_id=f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}")
            for i in range(20)
        ]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs?sort=oldest")
        assert "sort=oldest" in response.text

    def test_pagination_uses_join_component(self) -> None:
        """Pagination uses DaisyUI join component."""
        entries = [
            _make_entry(run_id=f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}")
            for i in range(20)
        ]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert 'class="join"' in response.text

    def test_pagination_targets_runs_content(self) -> None:
        """Pagination links target #runs-content."""
        entries = [
            _make_entry(run_id=f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}")
            for i in range(20)
        ]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get("/runs")
        assert 'hx-target="#runs-content"' in response.text


# ── Empty State ───────────────────────────────────────────────────


class TestRunsListEmptyState:
    """Tests for empty state when no runs match."""

    def test_empty_state_message(self) -> None:
        """Shows enhanced empty state message with filter suggestion."""
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=[]),
        )
        response = client.get("/runs")
        assert "No runs match your filters." in response.text
        assert "Try adjusting the status or date range." in response.text

    def test_clear_filters_link(self) -> None:
        """Empty state includes clear filters link."""
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=[]),
        )
        response = client.get("/runs")
        assert "Clear filters" in response.text


# ── Query Parameter Forwarding ────────────────────────────────────


class TestRunsListQueryParams:
    """Tests for query parameter handling."""

    def test_sort_param_forwarded(self) -> None:
        """Sort parameter is forwarded to IndexManager."""
        entries = [_make_entry()]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        client.get("/runs?sort=oldest")
        call_kwargs = im.get_paginated_runs.call_args.kwargs
        assert call_kwargs["sort"] == "oldest"

    def test_status_filter_forwarded(self) -> None:
        """Status filter is forwarded to IndexManager."""
        entries = [_make_entry()]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        client.get("/runs?status=completed")
        call_kwargs = im.get_paginated_runs.call_args.kwargs
        assert call_kwargs["status"] == "completed"

    def test_project_filter_forwarded(self) -> None:
        """Project filter is forwarded to IndexManager."""
        entries = [_make_entry()]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        client.get("/runs?project=my-api")
        call_kwargs = im.get_paginated_runs.call_args.kwargs
        assert call_kwargs["project_name"] == "my-api"

    def test_page_param_forwarded(self) -> None:
        """Page parameter is forwarded to IndexManager."""
        entries = [_make_entry()]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        client.get("/runs?page=3")
        call_kwargs = im.get_paginated_runs.call_args.kwargs
        assert call_kwargs["page"] == 3

    def test_default_params(self) -> None:
        """Default parameters are page=1 and sort=newest."""
        entries = [_make_entry()]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        client.get("/runs")
        call_kwargs = im.get_paginated_runs.call_args.kwargs
        assert call_kwargs["page"] == 1
        assert call_kwargs["sort"] == "newest"
        assert call_kwargs["status"] is None
        assert call_kwargs["project_name"] is None

    def test_from_date_forwarded(self) -> None:
        """From date filter is forwarded as since parameter."""
        entries = [_make_entry()]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        client.get("/runs?from=2024-06-01")
        call_kwargs = im.get_paginated_runs.call_args.kwargs
        assert call_kwargs["since"] is not None

    def test_to_date_forwarded(self) -> None:
        """To date filter is forwarded as until parameter."""
        entries = [_make_entry()]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        client.get("/runs?to=2024-12-31")
        call_kwargs = im.get_paginated_runs.call_args.kwargs
        assert call_kwargs["until"] is not None

    def test_empty_status_treated_as_none(self) -> None:
        """Empty status parameter is treated as None (no filter)."""
        entries = [_make_entry()]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        client.get("/runs?status=")
        call_kwargs = im.get_paginated_runs.call_args.kwargs
        assert call_kwargs["status"] is None


# ── Filter Bar ────────────────────────────────────────────────────


class TestRunsFilterBar:
    """Tests for the filter bar with status, project & date range."""

    def test_filter_bar_container_renders(self) -> None:
        """Filter bar renders with card card-compact bg-base-200 classes."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert "card card-compact bg-base-200" in response.text

    def test_status_select_renders(self) -> None:
        """Status dropdown renders with all 6 options."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert 'name="status"' in response.text
        assert "All Statuses" in response.text
        assert ">Running<" in response.text
        assert ">Completed<" in response.text
        assert ">Failed<" in response.text
        assert ">Interrupted<" in response.text
        assert ">Aborted<" in response.text

    def test_project_select_renders(self) -> None:
        """Project dropdown renders with 'All Projects' + registered names."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(project_names=["my-api", "web-app"]),
        )
        response = client.get("/runs")
        text = response.text
        # Find the filter bar's project select (name="project")
        # The header also has a project filter, so we check the filter bar section
        assert "All Projects" in text
        assert "my-api" in text
        assert "web-app" in text

    def test_date_from_input_renders(self) -> None:
        """Date From input renders with type=date."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert 'name="from"' in response.text
        assert 'type="date"' in response.text

    def test_date_to_input_renders(self) -> None:
        """Date To input renders with type=date."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        assert 'name="to"' in response.text

    def test_filter_controls_have_htmx_attributes(self) -> None:
        """Filter controls have correct HTMX attributes."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        text = response.text
        assert 'hx-get="/runs"' in text
        assert 'hx-trigger="change"' in text
        assert 'hx-target="#runs-content"' in text

    def test_status_preselects_from_url(self) -> None:
        """Status filter pre-selects from URL param."""
        client = _make_client_with_mocks()
        response = client.get("/runs?status=failed")
        text = response.text
        # The filter bar's status select should have "failed" selected
        failed_pos = text.find('value="failed"')
        assert failed_pos > 0
        option_start = text.rfind("<option", 0, failed_pos)
        option_chunk = text[option_start:failed_pos + 30]
        assert "selected" in option_chunk

    def test_project_preselects_from_url(self) -> None:
        """Project filter pre-selects from URL param."""
        client = _make_client_with_mocks(
            project_registry=_mock_project_registry(project_names=["my-api", "web-app"]),
        )
        response = client.get("/runs?project=my-api")
        text = response.text
        # Find "my-api" option in the filter bar and check it's selected
        # The filter bar project select has name="project" inside the filter-bar div
        my_api_pos = text.find('value="my-api"')
        assert my_api_pos > 0
        option_start = text.rfind("<option", 0, my_api_pos)
        option_chunk = text[option_start:my_api_pos + 30]
        assert "selected" in option_chunk

    def test_date_inputs_prefill_from_url(self) -> None:
        """Date inputs pre-fill from URL params."""
        client = _make_client_with_mocks()
        response = client.get("/runs?from=2026-01-01&to=2026-02-01")
        text = response.text
        assert 'value="2026-01-01"' in text
        assert 'value="2026-02-01"' in text

    def test_clear_all_link_when_filter_active(self) -> None:
        """'Clear all' link appears when any filter is active."""
        client = _make_client_with_mocks()
        response = client.get("/runs?status=failed")
        assert "Clear all" in response.text

    def test_no_clear_all_link_when_no_filters(self) -> None:
        """'Clear all' link does NOT appear when no filters are active."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        # "Clear all" should not appear (note: "Clear filters" is in empty state, different)
        assert "Clear all" not in response.text

    def test_table_partial_excludes_filter_bar(self) -> None:
        """Table-only response (HX-Target=runs-content) does NOT include filter bar."""
        entries = [_make_entry()]
        client = _make_client_with_mocks(
            index_manager=_mock_index_manager(entries=entries),
        )
        response = client.get(
            "/runs",
            headers={"HX-Request": "true", "HX-Target": "runs-content"},
        )
        assert "card card-compact bg-base-200" not in response.text

    def test_page_partial_includes_filter_bar(self) -> None:
        """Page partial response (HX-Request without runs-content target) includes filter bar."""
        client = _make_client_with_mocks()
        response = client.get("/runs", headers={"HX-Request": "true"})
        assert "card card-compact bg-base-200" in response.text

    def test_filter_bar_outside_runs_content(self) -> None:
        """Filter bar is NOT inside #runs-content div."""
        client = _make_client_with_mocks()
        response = client.get("/runs")
        text = response.text
        # Find #runs-content div
        runs_content_pos = text.find('id="runs-content"')
        # Find filter bar
        filter_bar_pos = text.find("card card-compact bg-base-200")
        # Filter bar should appear BEFORE #runs-content
        assert filter_bar_pos < runs_content_pos

    def test_combined_filters_work(self) -> None:
        """Combined filters produce correct response."""
        entries = [
            _make_entry(run_id="run1", status="failed", project_name="my-api"),
            _make_entry(run_id="run2", status="completed", project_name="web-app"),
        ]
        im = _mock_index_manager(entries=entries)
        client = _make_client_with_mocks(index_manager=im)
        response = client.get("/runs?status=failed&project=my-api&from=2026-01-01")
        assert response.status_code == 200

    def test_hidden_sort_input_in_filter_bar(self) -> None:
        """Filter bar includes a hidden sort input to preserve sort on filter changes."""
        client = _make_client_with_mocks()
        response = client.get("/runs?sort=oldest")
        text = response.text
        assert 'name="sort"' in text
        assert 'value="oldest"' in text
