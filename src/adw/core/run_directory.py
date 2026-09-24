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

from adw.core.constants import CONTEXT_FILE
from adw.exceptions import StateError
from adw.fs import atomic_write

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
            # Check if this is a true duplicate (context.json already exists)
            # vs. a directory created by early logging (only logs/ subdirectory)
            context_path = run_dir / CONTEXT_FILE
            if run_dir.exists() and context_path.exists():
                raise StateError(
                    code="RUN_ALREADY_EXISTS",
                    message=f"Run directory already exists: {run_id}",
                    suggestion="Use a different run ID or delete existing run",
                    recoverable=False,
                )

            # Create parent directories and run directory
            # exist_ok=True because logging may have created the directory early
            run_dir.mkdir(parents=True, exist_ok=True)

            # Create all subdirectories (exist_ok=True for same reason)
            for subdir in _SUBDIRECTORIES:
                (run_dir / subdir).mkdir(exist_ok=True)

            # Acquire lock and write context.json atomically
            lock_path = run_dir / ".lock"
            with filelock.FileLock(lock_path, timeout=_DEFAULT_LOCK_TIMEOUT):
                atomic_write(context_path, context.model_dump_json(indent=2))

            return run_dir

        except OSError as e:
            raise StateError(
                code="DIR_CREATION_FAILED",
                message=f"Failed to create run directory: {e}",
                suggestion="Check filesystem permissions",
                recoverable=False,
            ) from e
