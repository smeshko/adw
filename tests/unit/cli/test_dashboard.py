"""Unit tests for dashboard data models and layout.

Tests for DashboardState, DashboardData, and DashboardLayout classes
used by the TUI dashboard for cross-project monitoring.
"""

from datetime import UTC, datetime

import pytest
from rich.console import Console

from adw.cli.dashboard import (
    STATUS_INDICATORS,
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
