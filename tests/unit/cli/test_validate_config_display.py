"""Tests for ValidateConfigDisplay."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from adw.cli.validate_config_display import ValidateConfigDisplay
from adw.config.checker import CheckReport, CheckResult, Severity


class TestValidateConfigDisplay:
    """Tests for ValidateConfigDisplay output formatting."""

    def _make_console(self) -> tuple[Console, StringIO]:
        """Create a Console that writes to a StringIO buffer."""
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, no_color=True, width=80)
        return console, buf

    def test_show_empty_report(self) -> None:
        """Empty report should show all OK."""
        console, buf = self._make_console()
        display = ValidateConfigDisplay(console)
        report = CheckReport()
        display.show(report)
        output = buf.getvalue()
        assert "Configuration Check" in output
        assert "0 errors" in output
        assert "0 warnings" in output

    def test_show_report_with_error(self) -> None:
        """Report with error should show error count."""
        console, buf = self._make_console()
        display = ValidateConfigDisplay(console)
        report = CheckReport()
        report.add(
            CheckResult(
                severity=Severity.ERROR,
                file_path=".adw/project.yaml",
                message="File not found",
                suggestion="Run adw init",
            )
        )
        display.show(report)
        output = buf.getvalue()
        assert "1 error" in output
        assert "File not found" in output

    def test_show_report_with_warning(self) -> None:
        """Report with warning should show warning count."""
        console, buf = self._make_console()
        display = ValidateConfigDisplay(console)
        report = CheckReport()
        report.add(
            CheckResult(
                severity=Severity.WARNING,
                file_path=".adw/project.yaml",
                message="'ruff' not found",
                field="lint_command",
                suggestion="Install ruff",
            )
        )
        display.show(report)
        output = buf.getvalue()
        assert "1 warning" in output

    def test_show_valid_status(self) -> None:
        """Valid config should show 'valid' in result."""
        console, buf = self._make_console()
        display = ValidateConfigDisplay(console)
        report = CheckReport()
        display.show(report)
        output = buf.getvalue()
        assert "valid" in output.lower()

    def test_show_suggestion(self) -> None:
        """Suggestions should be displayed."""
        console, buf = self._make_console()
        display = ValidateConfigDisplay(console)
        report = CheckReport()
        report.add(
            CheckResult(
                severity=Severity.ERROR,
                file_path=".adw/project.yaml",
                message="Missing",
                suggestion="Run adw init",
            )
        )
        display.show(report)
        output = buf.getvalue()
        assert "Run adw init" in output

    def test_show_field_path(self) -> None:
        """Field paths should be displayed with the message."""
        console, buf = self._make_console()
        display = ValidateConfigDisplay(console)
        report = CheckReport()
        report.add(
            CheckResult(
                severity=Severity.WARNING,
                file_path=".adw/project.yaml",
                message="not found",
                field="llm.path",
            )
        )
        display.show(report)
        output = buf.getvalue()
        assert "llm.path" in output
