"""Global workflow execution index manager.

This module provides the IndexManager class for managing the global
workflow execution index at ~/.adw/index.jsonl.

The index stores metadata about all ADW runs across all projects,
enabling cross-project run discovery and historical queries.

Key features:
- JSONL format for append-only writes
- Concurrent access safety via append-only pattern
- Automatic archival when index exceeds threshold
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from adw.exceptions import StateError
from adw.models.index import IndexEntry

if TYPE_CHECKING:
    from adw.models import RunContext

logger = logging.getLogger(__name__)

__all__ = ["IndexManager"]

# Default threshold for archiving old entries
_DEFAULT_ARCHIVE_THRESHOLD: int = 10_000


class IndexManager:
    """Manages the global workflow execution index.

    The index is stored at ~/.adw/index.jsonl in JSONL format
    (one JSON object per line). This format supports:
    - Append-only writes (no locking needed for basic ops)
    - Streaming reads
    - Simple concurrent access

    Attributes:
        index_path: Path to the index.jsonl file.
        archive_dir: Path to the archive directory for old entries.

    Environment Variables:
        ADW_TEST_INDEX_PATH: If set, overrides the default index path.
            Used during testing to prevent test runs from polluting
            the user's global index.

    Example:
        >>> from pathlib import Path
        >>> manager = IndexManager()
        >>> manager.register_run(context, Path("/my/project"))
        >>> manager.update_run(context.run_id, status="completed")
        >>> runs = manager.get_recent_runs(limit=10)
    """

    def __init__(
        self,
        index_path: Path | None = None,
        archive_threshold: int = _DEFAULT_ARCHIVE_THRESHOLD,
    ) -> None:
        """Initialize the IndexManager.

        Args:
            index_path: Path to the index file. Defaults to ~/.adw/index.jsonl,
                or the path specified by ADW_TEST_INDEX_PATH environment variable.
            archive_threshold: Number of entries before triggering archive.
                              Defaults to 10,000.
        """
        import os

        # Allow environment variable to override default path (for testing)
        env_index_path = os.environ.get("ADW_TEST_INDEX_PATH")
        if index_path is not None:
            self.index_path = index_path
        elif env_index_path:
            self.index_path = Path(env_index_path)
        else:
            self.index_path = Path.home() / ".adw" / "index.jsonl"
        self.archive_dir = self.index_path.parent / "index-archive"
        self._archive_threshold = archive_threshold

    def register_run(self, context: "RunContext", project_path: Path) -> None:
        """Register a new run in the index.

        Creates a new index entry with status='running' and appends it
        to the index file. Creates the index file and parent directories
        if they don't exist. Triggers archival if index exceeds threshold.

        Args:
            context: The RunContext for the new run.
            project_path: Absolute path to the project directory.

        Example:
            >>> manager.register_run(context, Path("/path/to/project"))
        """
        # Ensure parent directories exist
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        # Create index entry from context
        entry = IndexEntry(
            run_id=context.run_id,
            project_path=str(project_path),
            project_name=project_path.name,
            feature_description=context.feature_description,
            started_at=context.started_at,
            completed_at=None,
            status="running",
            phase_reached=context.current_phase,
            phases_completed=list(context.phase_history),
        )

        # Append to index (JSONL format)
        self._append_entry(entry)

        # Check if archive is needed (AC5: archive when >10,000 entries)
        self._archive_old_entries()

    def update_run(self, run_id: str, **updates: Any) -> None:
        """Update an existing run entry.

        Reads all entries, finds the matching run_id, updates the fields,
        and rewrites the index file. This is safe because:
        1. Updates are infrequent (only on phase transitions and completion)
        2. Index file is relatively small (archived at 10k entries)

        Args:
            run_id: The run ID to update.
            **updates: Fields to update (status, completed_at, phase_reached,
                      phases_completed).

        Raises:
            StateError: If run_id is not found in the index (INDEX_ENTRY_NOT_FOUND).

        Example:
            >>> manager.update_run(run_id, status="completed", phase_reached="validate")
        """
        if not self.index_path.exists():
            raise StateError(
                code="INDEX_ENTRY_NOT_FOUND",
                message=f"Run not found in index: {run_id}",
                suggestion="Ensure the run was registered before updating",
                recoverable=False,
            )

        # Read all entries
        entries = self._read_all_entries()

        # Find and update the matching entry
        found = False
        for i, entry in enumerate(entries):
            if entry.run_id == run_id:
                # Create updated entry using model_copy
                entries[i] = entry.model_copy(update=updates)
                found = True
                break

        if not found:
            raise StateError(
                code="INDEX_ENTRY_NOT_FOUND",
                message=f"Run not found in index: {run_id}",
                suggestion="Ensure the run was registered before updating",
                recoverable=False,
            )

        # Rewrite the index file
        self._write_all_entries(entries)

    def get_recent_runs(
        self,
        limit: int = 10,
        project_path: Path | None = None,
        project_name: str | None = None,
        status: str | None = None,
        since: datetime | None = None,
    ) -> list[IndexEntry]:
        """Query recent runs with optional filters.

        Returns entries sorted by started_at (most recent first).

        Args:
            limit: Maximum number of entries to return.
            project_path: Filter to runs from this project path only.
            project_name: Filter to runs matching this project name.
            status: Filter to runs with this status.
            since: Filter to runs started on or after this time.

        Returns:
            List of IndexEntry objects matching the filters.

        Example:
            >>> runs = manager.get_recent_runs(limit=5, status="completed")
            >>> runs = manager.get_recent_runs(project_name="my-api", since=threshold)
        """
        if not self.index_path.exists():
            return []

        entries = self._read_all_entries()

        # Apply filters
        if project_path is not None:
            project_path_str = str(project_path)
            entries = [e for e in entries if e.project_path == project_path_str]

        if project_name is not None:
            entries = [e for e in entries if e.project_name == project_name]

        if status is not None:
            entries = [e for e in entries if e.status == status]

        if since is not None:
            entries = [e for e in entries if e.started_at >= since]

        # Sort by started_at (most recent first)
        entries.sort(key=lambda e: e.started_at, reverse=True)

        # Apply limit
        return entries[:limit]

    def _archive_old_entries(self) -> None:
        """Archive old entries when index exceeds threshold.

        Moves older entries to monthly archive files at:
        ~/.adw/index-archive/YYYY-MM.jsonl

        Keeps the newest entries (up to threshold / 2) in the main index.
        """
        if not self.index_path.exists():
            return

        entries = self._read_all_entries()

        if len(entries) <= self._archive_threshold:
            return

        # Sort by started_at (oldest first)
        entries.sort(key=lambda e: e.started_at)

        # Keep the newest half
        keep_count = self._archive_threshold // 2
        to_archive = entries[:-keep_count]
        to_keep = entries[-keep_count:]

        # Group archived entries by month
        by_month: dict[str, list[IndexEntry]] = {}
        for entry in to_archive:
            month_key = entry.started_at.strftime("%Y-%m")
            if month_key not in by_month:
                by_month[month_key] = []
            by_month[month_key].append(entry)

        # Write to archive files
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        for month_key, month_entries in by_month.items():
            archive_path = self.archive_dir / f"{month_key}.jsonl"
            # Append to existing archive file
            with open(archive_path, "a") as f:
                for entry in month_entries:
                    f.write(entry.model_dump_json() + "\n")

        # Rewrite main index with kept entries
        self._write_all_entries(to_keep)

    def _append_entry(self, entry: IndexEntry) -> None:
        """Append a single entry to the index file.

        Args:
            entry: The IndexEntry to append.
        """
        with open(self.index_path, "a") as f:
            f.write(entry.model_dump_json() + "\n")

    def _read_all_entries(self) -> list[IndexEntry]:
        """Read all entries from the index file.

        Skips corrupted lines (invalid JSON or validation errors) and logs warnings.

        Returns:
            List of IndexEntry objects.
        """
        entries: list[IndexEntry] = []

        with open(self.index_path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = IndexEntry.model_validate_json(line)
                    entries.append(entry)
                except Exception as e:
                    logger.warning(
                        "Skipping corrupted line in index",
                        extra={
                            "line_number": line_num,
                            "error": str(e),
                            "index_path": str(self.index_path),
                        },
                    )

        return entries

    def _write_all_entries(self, entries: list[IndexEntry]) -> None:
        """Write all entries to the index file (overwrite).

        Args:
            entries: List of IndexEntry objects to write.
        """
        with open(self.index_path, "w") as f:
            for entry in entries:
                f.write(entry.model_dump_json() + "\n")
