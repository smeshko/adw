"""Run lookup utilities for finding and loading runs.

This module provides the RunLookup class for finding runs by ID or
finding the most recent incomplete run for resume operations.
"""

from collections.abc import Callable
from pathlib import Path

from adw.core.context_manager import ContextManager
from adw.models import RunContext

__all__ = ["RunLookup"]


class RunLookup:
    """Find and load runs from the runs directory.

    This class provides methods to look up runs by their ID or find
    incomplete runs that can be resumed.

    Attributes:
        runs_dir: Path to the .adw/runs directory.
        context_manager: Manager for loading run contexts.

    Example:
        >>> from pathlib import Path
        >>> lookup = RunLookup(Path("/my/project/.adw/runs"))
        >>> context = lookup.find_by_id("01HQXK5P3Z7V8R2M4N6T9W1Y3C")
        >>> if context:
        ...     print(f"Found run: {context.status}")
    """

    def __init__(self, runs_dir: Path) -> None:
        """Initialize the RunLookup.

        Args:
            runs_dir: Path to the .adw/runs directory.
        """
        self.runs_dir = runs_dir
        self.context_manager = ContextManager(runs_dir)

    def find_by_id(self, run_id: str) -> RunContext | None:
        """Find a run by its ID.

        Args:
            run_id: The ULID of the run.

        Returns:
            RunContext if found, None otherwise.

        Example:
            >>> context = lookup.find_by_id("01HQXK5P3Z...")
            >>> if context:
            ...     print(context.feature_description)
        """
        run_path = self.runs_dir / run_id
        if not run_path.exists():
            return None

        try:
            return self.context_manager.load(run_id)
        except Exception:
            return None

    def find_most_recent(self) -> RunContext | None:
        """Find the most recent run regardless of status.

        Runs are sorted by their ULID which is lexicographically sortable
        and encodes the creation timestamp.

        Returns:
            Most recent RunContext, or None if none found.

        Example:
            >>> context = lookup.find_most_recent()
            >>> if context:
            ...     print(f"Most recent: {context.run_id}")
        """
        runs = self._list_runs()
        return runs[0] if runs else None

    def find_most_recent_incomplete(self) -> RunContext | None:
        """Find the most recent incomplete run.

        Incomplete runs have status: "running", "failed", or "interrupted".
        Runs are sorted by their ULID which is lexicographically sortable
        and encodes the creation timestamp.

        Returns:
            Most recent incomplete RunContext, or None if none found.

        Example:
            >>> context = lookup.find_most_recent_incomplete()
            >>> if context:
            ...     print(f"Resume: {context.run_id}")
        """
        incomplete_statuses = ("running", "failed", "interrupted")
        runs = self._list_runs(
            filter_fn=lambda ctx: ctx.status in incomplete_statuses
        )
        return runs[0] if runs else None

    def _list_runs(
        self,
        filter_fn: Callable[[RunContext], bool] | None = None,
    ) -> list[RunContext]:
        """List all runs, optionally filtered, sorted by most recent first.

        Args:
            filter_fn: Optional function to filter runs. Returns True to include.

        Returns:
            List of RunContext objects sorted by run_id (most recent first).
        """
        if not self.runs_dir.exists():
            return []

        runs: list[tuple[str, RunContext]] = []

        for run_dir in self.runs_dir.iterdir():
            if not run_dir.is_dir():
                continue

            try:
                context = self.context_manager.load(run_dir.name)
                if filter_fn is None or filter_fn(context):
                    runs.append((context.run_id, context))
            except Exception:
                continue

        # Sort by run_id (ULID) descending - most recent first
        runs.sort(key=lambda x: x[0], reverse=True)
        return [ctx for _, ctx in runs]

    def list_runs(
        self,
        limit: int = 10,
        status: str | None = None,
    ) -> list[RunContext]:
        """List runs with optional filtering.

        Returns runs sorted by creation time (newest first). ULID provides
        natural lexicographic sorting by timestamp.

        Args:
            limit: Maximum number of runs to return.
            status: Filter by status (optional).

        Returns:
            List of RunContext objects, sorted newest first.

        Example:
            >>> lookup = RunLookup(runs_dir)
            >>> # Get 10 most recent runs
            >>> runs = lookup.list_runs()
            >>> # Get failed runs only
            >>> failed = lookup.list_runs(status="failed")
        """
        def status_filter(ctx: RunContext) -> bool:
            return ctx.status == status

        runs = self._list_runs(filter_fn=status_filter if status else None)
        return runs[:limit]
