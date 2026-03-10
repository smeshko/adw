"""Display formatting for config validation results.

This module provides the ValidateConfigDisplay class that renders
CheckReport results using Rich tables and panels.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from adw.config.checker import CheckReport, CheckResult, Severity
from adw.core.constants import PHASE_SEQUENCE

__all__ = ["ValidateConfigDisplay"]


class ValidateConfigDisplay:
    """Renders config validation results with Rich formatting.

    Displays a summary line per file and detailed findings for
    files with issues.

    Example:
        >>> from rich.console import Console
        >>> display = ValidateConfigDisplay(Console())
        >>> display.show(report)
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def show(self, report: CheckReport, *, verbose: bool = False) -> None:
        """Display the full validation report.

        Args:
            report: The CheckReport to display.
            verbose: If True, show details for all files (not just those with issues).
        """
        self.console.print()
        self.console.print(
            Panel(
                "[bold]Configuration Check[/]",
                border_style="blue",
                expand=False,
            )
        )
        self.console.print()

        # Group results by file
        files_seen: list[str] = []
        results_by_file: dict[str, list[CheckResult]] = {}
        for result in report.results:
            if result.file_path not in results_by_file:
                results_by_file[result.file_path] = []
                files_seen.append(result.file_path)
            results_by_file[result.file_path].append(result)

        # Always show project.yaml first
        project_path = ".adw/project.yaml"
        self._show_file_status(project_path, results_by_file.get(project_path, []))

        # Show phase configs in phase order
        for phase in PHASE_SEQUENCE:
            # Find results for this phase (any file path containing the phase name)
            phase_results: list[CheckResult] = []
            for file_path, results in results_by_file.items():
                if f"/{phase}/" in file_path or file_path == phase:
                    phase_results = results
                    break

            self._show_file_status(phase, phase_results)

            # Show details for files with issues
            if phase_results:
                self._show_file_details(phase_results)

        # Show details for project.yaml if it has issues
        project_results = results_by_file.get(project_path, [])
        if project_results:
            self._show_file_details(project_results)

        # Summary
        self.console.print()
        error_count = len(report.errors)
        warning_count = len(report.warnings)

        if error_count == 0 and warning_count == 0:
            status = "[green]configuration is valid[/]"
        elif error_count == 0:
            status = "[green]configuration is valid[/]"
        else:
            status = "[red]configuration has errors[/]"

        self.console.print(
            f"  [bold]Result:[/] {error_count} error{'s' if error_count != 1 else ''}, "
            f"{warning_count} warning{'s' if warning_count != 1 else ''} — {status}"
        )
        self.console.print()

    def _show_file_status(self, label: str, results: list[CheckResult]) -> None:
        """Show a single-line status for a file.

        Args:
            label: Display label for the file.
            results: Check results for this file.
        """
        errors = [r for r in results if r.severity == Severity.ERROR]
        warnings = [r for r in results if r.severity == Severity.WARNING]

        # Build status text
        if errors:
            count = len(errors)
            status = f"[red]{count} error{'s' if count != 1 else ''}[/]"
        elif warnings:
            count = len(warnings)
            status = f"[yellow]{count} warning{'s' if count != 1 else ''}[/]"
        else:
            status = "[green]OK[/]"

        # Pad label with dots
        dots = "." * max(1, 40 - len(label))
        self.console.print(f"  {label} {dots} {status}")

    def _show_file_details(self, results: list[CheckResult]) -> None:
        """Show detailed findings for a file.

        Args:
            results: Check results to display.
        """
        for result in results:
            icon = "[red]✗[/]" if result.severity == Severity.ERROR else "[yellow]⚠[/]"
            field_str = f" {result.field}:" if result.field else ""
            self.console.print(f"    {icon}{field_str} {result.message}")
            if result.suggestion:
                self.console.print(
                    f"      [dim]Suggestion: {result.suggestion}[/]"
                )
