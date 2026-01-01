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

from pathlib import Path
from typing import TYPE_CHECKING

import filelock

from adw.exceptions import StateError

if TYPE_CHECKING:
    from adw.models import RunContext

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

            # Create the lock file
            lock_path = run_dir / ".lock"
            lock_path.touch()

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
