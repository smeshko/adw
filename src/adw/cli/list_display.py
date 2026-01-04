"""Display utilities for run listing.

This module provides the ListDisplay class for rendering run lists
as formatted Rich tables.
"""

from rich.console import Console
from rich.table import Table

from adw.models import RunContext

__all__ = ["ListDisplay"]


class ListDisplay:
    """Display run list using Rich.

    This class provides methods to render lists of runs as formatted
    tables with color-coded status columns.

    Attributes:
        console: Rich Console instance for output.

    Example:
        >>> from rich.console import Console
        >>> display = ListDisplay(Console())
        >>> display.show_runs(runs)
    """

    STATUS_COLORS: dict[str, str] = {
        "running": "yellow",
        "completed": "green",
        "failed": "red",
        "interrupted": "orange1",
        "aborted": "bright_black",
    }

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the ListDisplay.

        Args:
            console: Optional Rich Console instance. If not provided,
                a new Console will be created.
        """
        self.console = console or Console()

    def show_runs(self, runs: list[RunContext]) -> None:
        """Display list of runs as a table.

        Args:
            runs: List of RunContext objects to display.
        """
        table = Table(title=f"Recent Runs ({len(runs)})")

        table.add_column("Run ID", style="cyan", no_wrap=True)
        table.add_column("Feature", max_width=30)
        table.add_column("Status", justify="center")
        table.add_column("Started", style="dim")

        for run in runs:
            # Full run_id for display (allows copy/paste for other commands)
            short_id = self._truncate_id(run.run_id)

            # Truncate feature description
            feature = self._truncate_text(run.feature_description, max_length=27)

            # Color-code status
            color = self.STATUS_COLORS.get(run.status, "white")
            status = f"[{color}]{run.status}[/]"

            # Format timestamp
            started = self._format_timestamp(run.started_at)

            table.add_row(short_id, feature, status, started)

        self.console.print()
        self.console.print(table)
        self.console.print()

    def _truncate_id(self, run_id: str) -> str:
        """Return run ID for display.

        Note: Full ID is returned to allow copying for use with other commands.

        Args:
            run_id: Full ULID run ID.

        Returns:
            Full run ID without truncation.
        """
        return run_id

    def _truncate_text(self, text: str, max_length: int = 37) -> str:
        """Truncate text with ellipsis if too long.

        Args:
            text: Text to truncate.
            max_length: Maximum length before truncation.

        Returns:
            Truncated text with ellipsis if needed.
        """
        if len(text) > max_length:
            return f"{text[: max_length - 3]}..."
        return text

    def _format_timestamp(self, dt: object) -> str:
        """Format datetime for display.

        Args:
            dt: datetime object or None.

        Returns:
            Formatted timestamp string or "—" if None.
        """
        from datetime import datetime

        if dt is None:
            return "—"

        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M")

        return "—"
