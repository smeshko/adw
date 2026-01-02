"""Run directory management for ADW state persistence.

This module provides the RunDirectoryManager class that manages the directory
structure for ADW runs:

.adw/runs/<run_id>/
├── context.json          # RunContext - live updated
├── .lock                 # filelock for concurrency control
├── artifacts/            # Phase output artifacts
├── logs/                 # Logging output
├── llm/                  # LLM interaction capture
└── snapshots/            # State snapshots at key moments
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import filelock
from pydantic import BaseModel, ConfigDict
from ulid import ULID

from adw.exceptions import StateError

if TYPE_CHECKING:
    from adw.models import RunContext


class RunInfo(BaseModel):
    """Information about a run directory.

    Attributes:
        run_id: The ULID run identifier.
        path: Path to the run directory.
        created_at: When the run was created (extracted from ULID timestamp).
    """

    run_id: str
    path: Path
    created_at: datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)

# Subdirectories to create in each run directory
_SUBDIRECTORIES = ("artifacts", "logs", "llm", "snapshots")

# Default lock timeout in seconds
_DEFAULT_LOCK_TIMEOUT = 10


class RunDirectoryManager:
    """Manages run directory structure and lifecycle.

    Creates and manages the directory structure for ADW runs:
    .adw/runs/<run_id>/
    ├── context.json
    ├── .lock
    ├── artifacts/
    ├── logs/
    ├── llm/
    └── snapshots/

    Attributes:
        project_root: Path to the project root directory.
        runs_dir: Path to the .adw/runs directory.

    Example:
        >>> from pathlib import Path
        >>> manager = RunDirectoryManager(Path("/my/project"))
        >>> run_dir = manager.create(context)
    """

    def __init__(self, project_root: Path) -> None:
        """Initialize the RunDirectoryManager.

        Args:
            project_root: Path to the project root directory.
        """
        self.project_root = project_root
        self.runs_dir = project_root / ".adw" / "runs"

    def create(self, context: "RunContext") -> Path:
        """Create run directory structure and save initial context.

        Creates the directory structure:
        .adw/runs/<run_id>/
        ├── artifacts/
        ├── logs/
        ├── llm/
        └── snapshots/

        Args:
            context: Initial RunContext to serialize.

        Returns:
            Path to created run directory.

        Raises:
            StateError: If directory creation fails (e.g., already exists).
        """
        run_id = context.run_id
        run_dir = self.runs_dir / run_id

        try:
            # Create parent directories and run directory atomically
            # exist_ok=False ensures we fail if the directory already exists
            run_dir.mkdir(parents=True, exist_ok=False)

            # Create all subdirectories
            for subdir in _SUBDIRECTORIES:
                (run_dir / subdir).mkdir()

            # Acquire lock and write context.json atomically
            lock_path = run_dir / ".lock"
            with filelock.FileLock(lock_path, timeout=_DEFAULT_LOCK_TIMEOUT):
                context_path = run_dir / "context.json"
                context_path.write_text(context.model_dump_json(indent=2))

            return run_dir

        except FileExistsError as e:
            raise StateError(
                code="RUN_ALREADY_EXISTS",
                message=f"Run directory already exists: {run_id}",
                suggestion="Use a different run ID or delete existing run",
                recoverable=False,
            ) from e
        except OSError as e:
            raise StateError(
                code="DIR_CREATION_FAILED",
                message=f"Failed to create run directory: {e}",
                suggestion="Check filesystem permissions",
                recoverable=False,
            ) from e

    def acquire_lock(
        self, run_id: str, timeout: int = _DEFAULT_LOCK_TIMEOUT
    ) -> filelock.FileLock:
        """Acquire a lock for a run directory.

        This method returns a FileLock that can be used as a context manager
        to ensure exclusive access to a run's state files.

        Args:
            run_id: The run ID to lock.
            timeout: Lock acquisition timeout in seconds.

        Returns:
            A FileLock context manager for the run.

        Raises:
            StateError: If the run directory does not exist.

        Example:
            >>> with manager.acquire_lock(run_id):
            ...     # Safely modify run state
            ...     pass
        """
        run_dir = self.runs_dir / run_id
        lock_path = run_dir / ".lock"

        if not run_dir.exists():
            raise StateError(
                code="RUN_NOT_FOUND",
                message=f"Run directory does not exist: {run_id}",
                suggestion="Use 'adw list' to see available runs",
                recoverable=False,
            )

        return filelock.FileLock(lock_path, timeout=timeout)

    def list_runs(self) -> list[RunInfo]:
        """List all runs sorted by ULID (chronological order).

        Returns a list of RunInfo objects for all runs in the runs directory.
        Runs are sorted by ULID, which is chronological order since ULIDs
        encode creation time.

        Returns:
            List of RunInfo objects sorted by creation time.

        Example:
            >>> runs = manager.list_runs()
            >>> for run in runs:
            ...     print(f"{run.run_id}: {run.path} ({run.created_at})")
        """
        if not self.runs_dir.exists():
            return []

        runs = []
        for run_path in self.runs_dir.iterdir():
            # Skip hidden directories and non-directories
            if run_path.is_dir() and not run_path.name.startswith("."):
                # Extract timestamp from ULID
                try:
                    ulid = ULID.from_str(run_path.name)
                    created_at = ulid.datetime
                except (ValueError, AttributeError):
                    # Fallback for invalid ULIDs - use current time
                    created_at = datetime.now(UTC)

                runs.append(
                    RunInfo(
                        run_id=run_path.name,
                        path=run_path,
                        created_at=created_at,
                    )
                )

        # ULID sorting is lexicographic = chronological
        return sorted(runs, key=lambda r: r.run_id)
