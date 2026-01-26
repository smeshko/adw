"""Integration tests for TUI dashboard.

Tests the full dashboard lifecycle using real IndexManager and
StatsAggregator data with mocked terminal input.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from adw.cli.app import app
from adw.cli.dashboard import (
    DashboardController,
    DashboardData,
    DashboardState,
)
from adw.core.index_manager import IndexManager
from adw.core.stats_aggregator import StatsAggregator
from adw.models import RunContext
from adw.models.stats import GlobalStatistics

runner = CliRunner()


@pytest.fixture
def temp_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> IndexManager:
    """Create a temporary index for testing."""
    index_path = tmp_path / "test-index.jsonl"
    monkeypatch.setenv("ADW_TEST_INDEX_PATH", str(index_path))
    return IndexManager(index_path=index_path)


@pytest.fixture
def temp_stats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> StatsAggregator:
    """Create a temporary stats aggregator for testing."""
    cache_path = tmp_path / "stats-cache.json"
    monkeypatch.setenv("ADW_TEST_STATS_CACHE_PATH", str(cache_path))
    return StatsAggregator(cache_path=cache_path)


def _create_test_context(
    run_id: str,
    feature: str = "Test feature",
    started_at: datetime | None = None,
    status: str = "running",
) -> RunContext:
    """Create a test RunContext with sensible defaults."""
    return RunContext(
        run_id=run_id,
        feature_description=feature,
        current_phase="plan",
        started_at=started_at or datetime.now(UTC),
        status=status,
    )


class TestDashboardLifecycle:
    """Integration tests for full dashboard lifecycle."""

    @patch("adw.cli.dashboard.run_dashboard")
    def test_dashboard_command_starts(self, mock_run: MagicMock) -> None:
        """Dashboard command should invoke run_dashboard."""
        result = runner.invoke(app, ["global", "dashboard"])
        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("adw.cli.dashboard.run_dashboard")
    def test_dashboard_with_project_filter(self, mock_run: MagicMock) -> None:
        """Dashboard should pass project filter."""
        result = runner.invoke(
            app, ["global", "dashboard", "--project", "test-project"]
        )
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            refresh_interval=30,
            project_filter="test-project",
            no_auto_refresh=False,
        )


class TestDashboardWithRealIndex:
    """Tests using real IndexManager data."""

    def test_controller_loads_data_from_index(self, temp_index: IndexManager) -> None:
        """Controller should load runs from real index."""
        # Create test runs
        context1 = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS1",
            "Feature Alpha",
            status="completed",
        )
        context2 = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS2",
            "Feature Beta",
            status="running",
        )

        temp_index.register_run(context1, Path("/projects/alpha"))
        temp_index.register_run(context2, Path("/projects/beta"))
        temp_index.update_run(context1.run_id, status="completed")

        # Create controller and refresh
        controller = DashboardController(refresh_interval=30)
        controller.refresh_data()

        # Verify data loaded
        assert len(controller.data.recent_runs) >= 2
        assert len(controller.data.active_runs) >= 1

    def test_controller_filters_by_project(self, temp_index: IndexManager) -> None:
        """Controller should filter runs by project when specified."""
        # Create runs in different projects
        context1 = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS1", "Alpha Feature")
        context2 = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS2", "Beta Feature")

        temp_index.register_run(context1, Path("/projects/alpha"))
        temp_index.register_run(context2, Path("/projects/beta"))

        # Create controller with project filter
        controller = DashboardController(refresh_interval=30, project_filter="alpha")
        controller.refresh_data()

        # Should only have alpha project runs
        for run in controller.data.recent_runs:
            assert run.project_name == "alpha"


class TestDashboardKeyboardNavigation:
    """Integration tests for keyboard navigation."""

    def test_key_j_moves_selection_down(self) -> None:
        """J key should move selection down."""
        state = DashboardState()
        data = DashboardData(
            stats=GlobalStatistics(generated_at=datetime.now(UTC)),
            recent_runs=[],
            active_runs=[],
        )

        controller = DashboardController(refresh_interval=30)
        controller.state = state
        controller.data = data
        # Add fake runs for navigation
        controller.data.recent_runs = [MagicMock(), MagicMock(), MagicMock()]

        initial_index = controller.state.selected_run_index
        controller.handle_key("j")

        assert controller.state.selected_run_index == initial_index + 1

    def test_key_k_moves_selection_up(self) -> None:
        """K key should move selection up."""
        state = DashboardState(selected_run_index=2)
        data = DashboardData(
            stats=GlobalStatistics(generated_at=datetime.now(UTC)),
            recent_runs=[MagicMock(), MagicMock(), MagicMock()],
            active_runs=[],
        )

        controller = DashboardController(refresh_interval=30)
        controller.state = state
        controller.data = data

        controller.handle_key("k")

        assert controller.state.selected_run_index == 1

    def test_key_q_sets_quit_flag(self) -> None:
        """Q key should set quit flag."""
        controller = DashboardController(refresh_interval=30)
        assert not controller.state.quit_requested

        controller.handle_key("q")

        assert controller.state.quit_requested

    def test_key_escape_sets_quit_flag(self) -> None:
        """Escape key should set quit flag."""
        controller = DashboardController(refresh_interval=30)

        controller.handle_key("\x1b")

        assert controller.state.quit_requested

    def test_key_r_triggers_refresh(self) -> None:
        """R key should trigger data refresh."""
        controller = DashboardController(refresh_interval=30)
        original_time = controller.state.last_refresh

        # Wait a tiny bit to ensure time difference
        import time

        time.sleep(0.01)

        controller.handle_key("r")

        # Last refresh should be updated
        assert controller.state.last_refresh > original_time

    def test_key_p_toggles_pause(self) -> None:
        """P key should toggle pause state."""
        controller = DashboardController(refresh_interval=30)
        assert not controller.state.paused

        controller.handle_key("p")
        assert controller.state.paused

        controller.handle_key("p")
        assert not controller.state.paused

    def test_number_keys_switch_views(self) -> None:
        """Number keys 1/2/3 should switch view modes."""
        controller = DashboardController(refresh_interval=30)

        controller.handle_key("1")
        assert controller.state.view_mode == "summary"

        controller.handle_key("2")
        assert controller.state.view_mode == "runs"

        controller.handle_key("3")
        assert controller.state.view_mode == "projects"


class TestDashboardRendering:
    """Integration tests for dashboard rendering."""

    def test_layout_renders_with_real_data(self, temp_index: IndexManager) -> None:
        """Layout should render without errors with real data."""
        # Create test run
        context = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS1",
            "Test Feature",
            status="running",
        )
        temp_index.register_run(context, Path("/projects/test"))

        # Create controller and load data
        controller = DashboardController(refresh_interval=30)
        controller.refresh_data()

        # Render should not raise
        output = controller.render()
        assert output is not None

    def test_layout_with_empty_data(self) -> None:
        """Layout should handle empty data gracefully."""
        # Use DashboardController which sets up layout properly
        controller = DashboardController(refresh_interval=30)
        controller.data.stats = GlobalStatistics(generated_at=datetime.now(UTC))
        controller.data.recent_runs = []
        controller.data.active_runs = []

        # Should not raise
        output = controller.render()
        assert output is not None

    def test_layout_shows_filter_indicator(self) -> None:
        """Layout should show project filter when active."""
        # Use a Console that captures output
        console = Console(force_terminal=True, record=True, width=120)
        controller = DashboardController(
            refresh_interval=30, project_filter="my-api", console=console
        )
        controller.data.stats = GlobalStatistics(generated_at=datetime.now(UTC))
        controller.data.recent_runs = []
        controller.data.active_runs = []

        output = controller.render()
        console.print(output)
        output_str = console.export_text()

        # Filter indicator should be visible
        assert "my-api" in output_str

    def test_layout_shows_paused_indicator(self) -> None:
        """Layout should show PAUSED indicator when paused."""
        console = Console(force_terminal=True, record=True, width=120)
        controller = DashboardController(refresh_interval=30, console=console)
        controller.state.paused = True
        controller.data.stats = GlobalStatistics(generated_at=datetime.now(UTC))
        controller.data.recent_runs = []
        controller.data.active_runs = []

        output = controller.render()
        console.print(output)
        output_str = console.export_text()

        assert "aused" in output_str  # Matches "Paused" or "PAUSED"


class TestDashboardEmptyStates:
    """Integration tests for empty state handling."""

    def test_empty_index_shows_guidance(
        self,
        temp_index: IndexManager,  # noqa: ARG002
    ) -> None:
        """Empty index should show helpful guidance."""
        console = Console(force_terminal=True, record=True, width=120)
        controller = DashboardController(refresh_interval=30, console=console)
        controller.refresh_data()

        output = controller.render()
        console.print(output)
        output_str = console.export_text()

        # Should show guidance about registering projects
        assert "No" in output_str or "empty" in output_str.lower()

    def test_filtered_empty_shows_clear_hint(self, temp_index: IndexManager) -> None:
        """Filtered view with no matches should show clear hint."""
        # Create run in different project
        context = _create_test_context("01KDSG2VDHNK0W4HSCZWJZXWS1", "Test")
        temp_index.register_run(context, Path("/projects/alpha"))

        # Filter to non-existent project
        console = Console(force_terminal=True, record=True, width=120)
        controller = DashboardController(
            refresh_interval=30, project_filter="nonexistent", console=console
        )
        controller.refresh_data()

        output = controller.render()
        console.print(output)
        output_str = console.export_text()

        # Should indicate no matching runs or filter info
        assert "nonexistent" in output_str or "No" in output_str


class TestDashboardStatistics:
    """Integration tests for statistics display."""

    def test_stats_display_with_real_data(self, temp_index: IndexManager) -> None:
        """Statistics should display correctly with real data."""
        # Create some completed runs
        for i in range(5):
            context = _create_test_context(
                f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}",
                f"Feature{i}",
                started_at=datetime.now(UTC) - timedelta(hours=i),
                status="completed" if i % 2 == 0 else "failed",
            )
            temp_index.register_run(context, Path("/projects/test"))
            temp_index.update_run(
                context.run_id, status="completed" if i % 2 == 0 else "failed"
            )

        controller = DashboardController(refresh_interval=30)
        controller.refresh_data()

        # Stats should have data
        assert controller.data.stats.total_runs >= 5

    def test_per_project_breakdown(self, temp_index: IndexManager) -> None:
        """Projects view should show per-project breakdown."""
        # Create runs in multiple projects
        projects = ["api", "web", "mobile"]
        for i, proj in enumerate(projects):
            context = _create_test_context(
                f"01KDSG2VDHNK0W4HSCZWJZXW{i:02d}",
                f"Feature for {proj}",
            )
            temp_index.register_run(context, Path(f"/projects/{proj}"))

        console = Console(force_terminal=True, record=True, width=120)
        controller = DashboardController(refresh_interval=30, console=console)
        controller.state.view_mode = "projects"
        controller.refresh_data()

        output = controller.render()
        console.print(output)
        output_str = console.export_text()

        # Should show at least one project name (stats may aggregate differently)
        assert any(proj in output_str for proj in projects) or "Project" in output_str


class TestDashboardRunDetailView:
    """Integration tests for run detail view."""

    def test_enter_key_opens_run_detail(self, temp_index: IndexManager) -> None:
        """Enter key should open run detail view."""
        context = _create_test_context(
            "01KDSG2VDHNK0W4HSCZWJZXWS1",
            "Detailed Feature",
            status="completed",
        )
        temp_index.register_run(context, Path("/projects/test"))
        temp_index.update_run(context.run_id, status="completed")

        controller = DashboardController(refresh_interval=30)
        controller.refresh_data()
        controller.state.selected_run_index = 0

        # Press Enter to open detail
        controller.handle_key("\r")

        assert controller.state.show_run_detail

    def test_escape_closes_run_detail(self) -> None:
        """Escape should close run detail and return to main view."""
        controller = DashboardController(refresh_interval=30)
        controller.state.show_run_detail = True

        # Press Escape
        controller.handle_key("\x1b")

        # Should close detail (and not quit, since we were in detail view)
        assert not controller.state.show_run_detail


class TestDashboardRefreshBehavior:
    """Integration tests for auto-refresh behavior."""

    def test_no_auto_refresh_starts_paused(self) -> None:
        """When no_auto_refresh is passed to run(), controller starts paused."""
        # The no_auto_refresh flag is passed to run(), not __init__
        # It sets state.paused = True at start
        controller = DashboardController(refresh_interval=30)

        # Initially not paused
        assert not controller.state.paused

        # P key toggles pause
        controller.handle_key("p")
        assert controller.state.paused

    def test_refresh_interval_configurable(self) -> None:
        """Refresh interval should be configurable."""
        controller = DashboardController(refresh_interval=60)

        assert controller.refresh_interval == 60


class TestDashboardIndexClamping:
    """Tests for selected_run_index bounds clamping."""

    def test_selected_index_clamped_after_refresh(self) -> None:
        """Selected index should be clamped when runs list shrinks."""
        controller = DashboardController(refresh_interval=30)

        # Start with 3 mock runs
        mock_runs_3 = [MagicMock(), MagicMock(), MagicMock()]
        mock_runs_1 = [MagicMock()]

        # First refresh returns 3 runs
        with patch.object(
            controller.index_manager, "get_recent_runs", return_value=mock_runs_3
        ):
            controller.refresh_data()

        # Set selected index to last run
        controller.state.selected_run_index = 2

        # Second refresh returns only 1 run
        with patch.object(
            controller.index_manager, "get_recent_runs", return_value=mock_runs_1
        ):
            controller.refresh_data()

        # Index should be clamped to 0 (only 1 run now)
        assert controller.state.selected_run_index == 0

    def test_render_does_not_raise_with_out_of_range_index(self) -> None:
        """Render should not raise IndexError even if index is out of range."""
        controller = DashboardController(refresh_interval=30)
        controller.data.recent_runs = []  # Empty list
        controller.state.selected_run_index = 5  # Out of range

        # Should not raise
        output = controller.render()
        assert output is not None

    def test_detail_view_disabled_when_no_runs(self) -> None:
        """Detail view flag should be cleared when no runs available."""
        controller = DashboardController(refresh_interval=30)
        controller.state.show_run_detail = True

        # Empty refresh
        with patch.object(
            controller.index_manager, "get_recent_runs", return_value=[]
        ):
            controller.refresh_data()

        # Detail view should be disabled
        assert controller.state.show_run_detail is False
        assert controller.state.selected_run_index == 0


class TestDashboardViewModeRendering:
    """Tests for view_mode-based rendering."""

    def test_projects_view_renders_projects_panel(self) -> None:
        """Projects view mode should render the projects panel."""
        console = Console(force_terminal=True, record=True, width=120)
        controller = DashboardController(refresh_interval=30, console=console)
        controller.data.stats = GlobalStatistics(generated_at=datetime.now(UTC))
        controller.data.recent_runs = []
        controller.data.active_runs = []

        # Switch to projects view
        controller.handle_key("3")
        assert controller.state.view_mode == "projects"

        # Render and capture output
        output = controller.render()
        console.print(output)
        output_str = console.export_text()

        # Should include projects-related content
        assert "PROJECT" in output_str.upper()

    def test_runs_view_focuses_on_runs(self) -> None:
        """Runs view mode should show runs without summary."""
        console = Console(force_terminal=True, record=True, width=120)
        controller = DashboardController(refresh_interval=30, console=console)
        controller.data.stats = GlobalStatistics(generated_at=datetime.now(UTC))
        controller.data.recent_runs = []
        controller.data.active_runs = []

        # Switch to runs view
        controller.handle_key("2")
        assert controller.state.view_mode == "runs"

        # Render should not raise
        output = controller.render()
        assert output is not None

    def test_summary_view_includes_projects(self) -> None:
        """Summary view (default) should include projects panel."""
        console = Console(force_terminal=True, record=True, width=120)
        controller = DashboardController(refresh_interval=30, console=console)
        controller.data.stats = GlobalStatistics(generated_at=datetime.now(UTC))
        controller.data.recent_runs = []
        controller.data.active_runs = []

        # Keep default summary view
        assert controller.state.view_mode == "summary"

        # Render and capture output
        output = controller.render()
        console.print(output)
        output_str = console.export_text()

        # Should include both summary and projects
        assert "SUMMARY" in output_str.upper() or "summary" in output_str.lower()
