"""Unit tests for dashboard data models.

Tests for DashboardState and DashboardData classes used by
the TUI dashboard for cross-project monitoring.
"""

from datetime import datetime

from adw.cli.dashboard import (
    DashboardData,
    DashboardState,
)


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
