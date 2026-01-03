"""Run lookup utilities for finding and loading runs.

This module provides the RunLookup class for finding runs by ID or
finding the most recent incomplete run for resume operations.
"""

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
        if not self.runs_dir.exists():
            return None

        incomplete_runs: list[tuple[str, RunContext]] = []

        for run_dir in self.runs_dir.iterdir():
            if not run_dir.is_dir():
                continue

            try:
                context = self.context_manager.load(run_dir.name)
                if context.status in ("running", "failed", "interrupted"):
                    # Use run_id (ULID) for sorting - lexicographically sortable
                    incomplete_runs.append((context.run_id, context))
            except Exception:
                continue

        if not incomplete_runs:
            return None

        # Sort by run_id (ULID) descending - most recent first
        incomplete_runs.sort(key=lambda x: x[0], reverse=True)
        return incomplete_runs[0][1]
