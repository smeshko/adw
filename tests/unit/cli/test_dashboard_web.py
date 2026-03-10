"""Unit tests for dashboard web CLI command (adw dashboard web)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from adw.cli.dashboard_web import dashboard_web_app

runner = CliRunner()


class TestDashboardWebCommand:
    """Tests for the ``adw dashboard web`` CLI command."""

    def test_web_command_starts_server(self) -> None:
        """web command calls uvicorn.run with correct defaults."""
        mock_app = MagicMock()
        with (
            patch("adw.cli.dashboard_web.webbrowser.open") as mock_browser,
            patch(
                "adw.dashboard.server.create_dashboard_app",
                return_value=mock_app,
            ) as mock_factory,
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            result = runner.invoke(dashboard_web_app, ["web"])

        assert result.exit_code == 0
        mock_factory.assert_called_once_with(host="127.0.0.1", port=8100)
        mock_uvicorn_run.assert_called_once_with(mock_app, host="127.0.0.1", port=8100)
        mock_browser.assert_called_once_with("http://127.0.0.1:8100")

    def test_web_command_custom_port(self) -> None:
        """web command accepts --port flag."""
        mock_app = MagicMock()
        with (
            patch("adw.cli.dashboard_web.webbrowser.open"),
            patch(
                "adw.dashboard.server.create_dashboard_app",
                return_value=mock_app,
            ) as mock_factory,
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            result = runner.invoke(dashboard_web_app, ["web", "--port", "9000"])

        assert result.exit_code == 0
        mock_factory.assert_called_once_with(host="127.0.0.1", port=9000)
        mock_uvicorn_run.assert_called_once_with(mock_app, host="127.0.0.1", port=9000)

    def test_web_command_custom_host(self) -> None:
        """web command accepts --host flag."""
        mock_app = MagicMock()
        with (
            patch("adw.cli.dashboard_web.webbrowser.open"),
            patch(
                "adw.dashboard.server.create_dashboard_app",
                return_value=mock_app,
            ) as mock_factory,
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            result = runner.invoke(dashboard_web_app, ["web", "--host", "0.0.0.0"])

        assert result.exit_code == 0
        mock_factory.assert_called_once_with(host="0.0.0.0", port=8100)
        mock_uvicorn_run.assert_called_once_with(mock_app, host="0.0.0.0", port=8100)

    def test_web_command_no_browser_flag(self) -> None:
        """--no-browser flag prevents browser from opening."""
        mock_app = MagicMock()
        with (
            patch("adw.cli.dashboard_web.webbrowser.open") as mock_browser,
            patch(
                "adw.dashboard.server.create_dashboard_app",
                return_value=mock_app,
            ),
            patch("uvicorn.run"),
        ):
            result = runner.invoke(dashboard_web_app, ["web", "--no-browser"])

        assert result.exit_code == 0
        mock_browser.assert_not_called()

    def test_web_command_reload_mode(self) -> None:
        """--reload flag uses uvicorn string import with factory=True."""
        with (
            patch("adw.cli.dashboard_web.webbrowser.open"),
            patch("uvicorn.run") as mock_uvicorn_run,
        ):
            result = runner.invoke(dashboard_web_app, ["web", "--reload"])

        assert result.exit_code == 0
        mock_uvicorn_run.assert_called_once_with(
            "adw.dashboard.server:create_dashboard_app",
            host="127.0.0.1",
            port=8100,
            reload=True,
            factory=True,
        )

    def test_web_command_short_flags(self) -> None:
        """Short flags -p, -H work correctly."""
        mock_app = MagicMock()
        with (
            patch("adw.cli.dashboard_web.webbrowser.open"),
            patch(
                "adw.dashboard.server.create_dashboard_app",
                return_value=mock_app,
            ) as mock_factory,
            patch("uvicorn.run"),
        ):
            result = runner.invoke(
                dashboard_web_app,
                ["web", "-p", "3000", "-H", "0.0.0.0"],
            )

        assert result.exit_code == 0
        mock_factory.assert_called_once_with(host="0.0.0.0", port=3000)

    def test_web_command_lan_warning_shown(self) -> None:
        """LAN warning is shown when host is 0.0.0.0."""
        mock_app = MagicMock()
        with (
            patch("adw.cli.dashboard_web.webbrowser.open"),
            patch(
                "adw.dashboard.server.create_dashboard_app",
                return_value=mock_app,
            ),
            patch("uvicorn.run"),
        ):
            result = runner.invoke(dashboard_web_app, ["web", "--host", "0.0.0.0"])

        assert result.exit_code == 0
        assert "WARNING" in result.output
        assert "network interfaces" in result.output

    def test_web_command_browser_uses_localhost_for_0000(self) -> None:
        """Browser opens 127.0.0.1 even when binding to 0.0.0.0."""
        mock_app = MagicMock()
        with (
            patch("adw.cli.dashboard_web.webbrowser.open") as mock_browser,
            patch(
                "adw.dashboard.server.create_dashboard_app",
                return_value=mock_app,
            ),
            patch("uvicorn.run"),
        ):
            result = runner.invoke(dashboard_web_app, ["web", "--host", "0.0.0.0"])

        assert result.exit_code == 0
        mock_browser.assert_called_once_with("http://127.0.0.1:8100")

    def test_web_command_browser_error_handled(self) -> None:
        """Browser open failure is handled gracefully."""
        mock_app = MagicMock()
        with (
            patch(
                "adw.cli.dashboard_web.webbrowser.open",
                side_effect=Exception("No browser"),
            ),
            patch(
                "adw.dashboard.server.create_dashboard_app",
                return_value=mock_app,
            ),
            patch("uvicorn.run"),
        ):
            result = runner.invoke(dashboard_web_app, ["web"])

        assert result.exit_code == 0
        assert "Could not open browser" in result.output

    def test_web_command_shows_startup_info(self) -> None:
        """Startup info shows host, port, and URL."""
        mock_app = MagicMock()
        with (
            patch("adw.cli.dashboard_web.webbrowser.open"),
            patch(
                "adw.dashboard.server.create_dashboard_app",
                return_value=mock_app,
            ),
            patch("uvicorn.run"),
        ):
            result = runner.invoke(dashboard_web_app, ["web"])

        assert result.exit_code == 0
        assert "127.0.0.1" in result.output
        assert "8100" in result.output
        assert "Starting ADW Web Dashboard" in result.output


class TestDashboardCallback:
    """Tests for the dashboard subcommand callback."""

    def test_no_subcommand_shows_help_message(self) -> None:
        """Running ``adw dashboard`` without subcommand shows help hint."""
        result = runner.invoke(dashboard_web_app, [])

        assert result.exit_code == 0
        assert "adw dashboard --help" in result.output
