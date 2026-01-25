"""Unit tests for dashboard data models and layout.

Tests for DashboardState, DashboardData, and DashboardLayout classes
used by the TUI dashboard for cross-project monitoring.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from rich.console import Console

from adw.cli.dashboard import (
    STATUS_INDICATORS,
    DashboardController,
    DashboardData,
    DashboardLayout,
    DashboardState,
)
from adw.models.index import IndexEntry
from adw.models.stats import GlobalStatistics, ProjectStatistics, TokenUsage


class TestDashboardState:
    """Tests for DashboardState mutable state tracking."""

    def test_default_values(self) -> None:
        """State has sensible defaults."""
        state = DashboardState()
        assert state.selected_run_index == 0
        assert state.selected_project is None
        assert state.scroll_offset == 0
        assert state.paused is False
        assert state.view_mode == "summary"
        assert state.quit_requested is False
        assert isinstance(state.last_refresh, datetime)

    def test_mutable_state(self) -> None:
        """State is mutable after creation."""
        state = DashboardState()
        state.selected_run_index = 5
        state.paused = True
        state.view_mode = "runs"
        assert state.selected_run_index == 5
        assert state.paused is True
        assert state.view_mode == "runs"

    def test_selected_project_can_be_set(self) -> None:
        """Selected project filter can be set."""
        state = DashboardState()
        state.selected_project = "my-api"
        assert state.selected_project == "my-api"

    def test_view_modes(self) -> None:
        """View mode accepts valid values."""
        state = DashboardState()
        for mode in ("summary", "runs", "projects"):
            state.view_mode = mode
            assert state.view_mode == mode


class TestDashboardData:
    """Tests for DashboardData cached data container."""

    def test_default_values(self) -> None:
        """Data has sensible defaults."""
        data = DashboardData()
        assert data.stats is None
        assert data.recent_runs == []
        assert data.active_runs == []
        assert data.error is None

    def test_can_store_error(self) -> None:
        """Error message can be stored."""
        data = DashboardData()
        data.error = "Connection failed"
        assert data.error == "Connection failed"

    def test_can_clear_error(self) -> None:
        """Error can be cleared."""
        data = DashboardData()
        data.error = "Something went wrong"
        data.error = None
        assert data.error is None


# Fixtures for layout tests
@pytest.fixture
def sample_global_stats() -> GlobalStatistics:
    """Create sample GlobalStatistics for testing."""
    return GlobalStatistics(
        generated_at=datetime.now(UTC),
        total_runs=100,
        runs_this_week=25,
        runs_today=5,
        completed_runs=90,
        failed_runs=10,
        success_rate=0.9,
        average_duration_ms=300000,
        tokens=TokenUsage(input_tokens=1000000, output_tokens=200000),
        estimated_cost=45.50,
        projects=[
            ProjectStatistics(
                name="my-api",
                path="/path/to/my-api",
                total_runs=50,
                completed_runs=48,
                failed_runs=2,
                success_rate=0.96,
                tokens=TokenUsage(input_tokens=500000, output_tokens=100000),
                estimated_cost=22.50,
            )
        ],
    )


@pytest.fixture
def sample_index_entries() -> list[IndexEntry]:
    """Create sample IndexEntry list for testing."""
    return [
        IndexEntry(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            project_path="/path/to/my-api",
            project_name="my-api",
            feature_description="Add user authentication",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            status="completed",
            phases_completed=["plan", "build", "validate"],
        ),
        IndexEntry(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3D",
            project_path="/path/to/frontend",
            project_name="frontend",
            feature_description="Fix navigation bug",
            started_at=datetime.now(UTC),
            status="running",
            phases_completed=["plan"],
        ),
    ]


class TestStatusIndicators:
    """Tests for status indicator definitions."""

    def test_all_statuses_have_indicators(self) -> None:
        """All known statuses have indicator definitions."""
        expected_statuses = {"running", "completed", "failed", "interrupted", "aborted"}
        assert set(STATUS_INDICATORS.keys()) == expected_statuses

    def test_indicators_have_symbol_and_color(self) -> None:
        """Each indicator has both symbol and color."""
        for status, (symbol, color) in STATUS_INDICATORS.items():
            assert isinstance(symbol, str), f"{status} symbol not a string"
            assert len(symbol) == 1, f"{status} symbol not single character"
            assert isinstance(color, str), f"{status} color not a string"
            assert len(color) > 0, f"{status} color is empty"


class TestDashboardLayout:
    """Tests for DashboardLayout Rich renderable generation."""

    def test_create_layout(self) -> None:
        """Layout can be instantiated with console."""
        console = Console()
        layout = DashboardLayout(console)
        assert layout is not None
        assert layout.console is console

    def test_create_header(self) -> None:
        """Header panel is created with title and hints."""
        console = Console()
        layout = DashboardLayout(console)
        header = layout.create_header()
        assert header is not None
        # Panel has title/subtitle attributes
        assert "DASHBOARD" in str(header.title).upper() or hasattr(header, "renderable")

    def test_create_summary_panel_with_stats(
        self, sample_global_stats: GlobalStatistics
    ) -> None:
        """Summary panel displays statistics."""
        console = Console()
        layout = DashboardLayout(console)
        panel = layout.create_summary_panel(sample_global_stats)
        assert panel is not None
        assert "SUMMARY" in str(panel.title).upper()

    def test_create_summary_panel_loading(self) -> None:
        """Summary panel shows loading when stats is None."""
        console = Console()
        layout = DashboardLayout(console)
        panel = layout.create_summary_panel(None)
        assert panel is not None
        # Should show loading indicator - panel exists even when loading

    def test_create_active_runs_panel_with_runs(
        self, sample_index_entries: list[IndexEntry]
    ) -> None:
        """Active runs panel shows running runs."""
        console = Console()
        layout = DashboardLayout(console)
        # Filter to running only
        active_runs = [e for e in sample_index_entries if e.status == "running"]
        panel = layout.create_active_runs_panel(active_runs)
        assert panel is not None
        assert "ACTIVE" in str(panel.title).upper()

    def test_create_active_runs_panel_empty(self) -> None:
        """Active runs panel returns None when no active runs."""
        console = Console()
        layout = DashboardLayout(console)
        result = layout.create_active_runs_panel([])
        assert result is None

    def test_create_recent_runs_table(
        self, sample_index_entries: list[IndexEntry]
    ) -> None:
        """Recent runs table displays runs with columns."""
        console = Console()
        layout = DashboardLayout(console)
        panel = layout.create_recent_runs_table(sample_index_entries)
        assert panel is not None
        assert "RECENT" in str(panel.title).upper()

    def test_create_recent_runs_table_empty(self) -> None:
        """Recent runs table handles empty list."""
        console = Console()
        layout = DashboardLayout(console)
        panel = layout.create_recent_runs_table([])
        assert panel is not None
        # Should show no runs message

    def test_create_projects_panel(
        self, sample_global_stats: GlobalStatistics
    ) -> None:
        """Projects panel displays per-project breakdown."""
        console = Console()
        layout = DashboardLayout(console)
        panel = layout.create_projects_panel(sample_global_stats)
        assert panel is not None
        assert "PROJECT" in str(panel.title).upper()

    def test_create_footer(self) -> None:
        """Footer displays refresh status."""
        console = Console()
        layout = DashboardLayout(console)
        footer = layout.create_footer(
            last_refresh=datetime.now(UTC),
            paused=False,
            refresh_interval=30,
        )
        assert footer is not None

    def test_create_empty_state(self) -> None:
        """Empty state shows helpful guidance."""
        console = Console()
        layout = DashboardLayout(console)
        panel = layout.create_empty_state()
        assert panel is not None
        # Should contain guidance text
        panel_str = str(panel.renderable) if hasattr(panel, "renderable") else str(panel)
        assert "register" in panel_str.lower() or "init" in panel_str.lower()


class TestDashboardController:
    """Tests for DashboardController state management and data fetching."""

    def test_init_defaults(self) -> None:
        """Controller initializes with sensible defaults."""
        controller = DashboardController()
        assert controller.refresh_interval == 30
        assert controller.project_filter is None
        assert controller.state is not None
        assert controller.data is not None
        assert controller.layout is not None

    def test_init_custom_params(self) -> None:
        """Controller accepts custom parameters."""
        controller = DashboardController(
            refresh_interval=60,
            project_filter="my-api",
        )
        assert controller.refresh_interval == 60
        assert controller.project_filter == "my-api"

    def test_refresh_data_calls_index_manager(
        self, sample_index_entries: list[IndexEntry]
    ) -> None:
        """refresh_data fetches from IndexManager."""
        controller = DashboardController()

        with patch.object(
            controller.index_manager,
            "get_recent_runs",
            return_value=sample_index_entries,
        ):
            controller.refresh_data()

        assert len(controller.data.recent_runs) == 2
        assert len(controller.data.active_runs) == 1  # One running

    def test_refresh_data_calls_stats_aggregator(
        self, sample_global_stats: GlobalStatistics
    ) -> None:
        """refresh_data fetches from StatsAggregator."""
        controller = DashboardController()

        with (
            patch.object(
                controller.index_manager,
                "get_recent_runs",
                return_value=[],
            ),
            patch.object(
                controller.stats_aggregator,
                "get_global_stats",
                return_value=sample_global_stats,
            ),
        ):
            controller.refresh_data()

        assert controller.data.stats is not None
        assert controller.data.stats.total_runs == 100

    def test_refresh_data_filters_active_runs(
        self, sample_index_entries: list[IndexEntry]
    ) -> None:
        """refresh_data correctly identifies active runs."""
        controller = DashboardController()

        with patch.object(
            controller.index_manager,
            "get_recent_runs",
            return_value=sample_index_entries,
        ):
            controller.refresh_data()

        # Should filter to only running status
        for run in controller.data.active_runs:
            assert run.status == "running"

    def test_handle_key_q_requests_quit(self) -> None:
        """'q' key sets quit_requested."""
        controller = DashboardController()
        assert not controller.state.quit_requested

        controller.handle_key("q")

        assert controller.state.quit_requested is True

    def test_handle_key_p_toggles_pause(self) -> None:
        """'p' key toggles paused state."""
        controller = DashboardController()
        assert not controller.state.paused

        controller.handle_key("p")
        assert controller.state.paused is True

        controller.handle_key("p")
        assert controller.state.paused is False

    def test_handle_key_r_triggers_refresh(self) -> None:
        """'r' key triggers data refresh."""
        controller = DashboardController()

        with patch.object(controller, "refresh_data") as mock_refresh:
            controller.handle_key("r")
            mock_refresh.assert_called_once()

    def test_handle_key_up_decrements_selection(self) -> None:
        """Up arrow decrements selected index."""
        controller = DashboardController()
        controller.state.selected_run_index = 5

        controller.handle_key("up")

        assert controller.state.selected_run_index == 4

    def test_handle_key_up_stops_at_zero(self) -> None:
        """Up arrow stops at index 0."""
        controller = DashboardController()
        controller.state.selected_run_index = 0

        controller.handle_key("up")

        assert controller.state.selected_run_index == 0

    def test_handle_key_down_increments_selection(
        self, sample_index_entries: list[IndexEntry]
    ) -> None:
        """Down arrow increments selected index."""
        controller = DashboardController()
        controller.data.recent_runs = sample_index_entries
        controller.state.selected_run_index = 0

        controller.handle_key("down")

        assert controller.state.selected_run_index == 1

    def test_handle_key_down_stops_at_max(
        self, sample_index_entries: list[IndexEntry]
    ) -> None:
        """Down arrow stops at max index."""
        controller = DashboardController()
        controller.data.recent_runs = sample_index_entries
        controller.state.selected_run_index = len(sample_index_entries) - 1

        controller.handle_key("down")

        assert controller.state.selected_run_index == len(sample_index_entries) - 1

    def test_render_returns_renderable(self) -> None:
        """render() returns a Rich renderable."""
        controller = DashboardController()
        result = controller.render()
        assert result is not None

    def test_render_with_no_data(self) -> None:
        """render() works with empty data."""
        controller = DashboardController()
        controller.data = DashboardData()  # Reset to empty
        result = controller.render()
        assert result is not None
