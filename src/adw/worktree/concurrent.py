"""Concurrent run management for ADW.

This module provides the ConcurrentRunManager class for tracking
and limiting concurrent ADW workflow executions.
"""

import contextlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from adw.exceptions import MaxConcurrentRunsError

logger = logging.getLogger(__name__)

# Default maximum concurrent runs
DEFAULT_MAX_CONCURRENT = 15


class ActiveRun(BaseModel):
    """Information about an active ADW run.

    Attributes:
        run_id: ULID identifier for the run.
        pid: Process ID of the running ADW instance.
        start_time: When the run was started.
        worktree_path: Absolute path to the worktree directory.
        backend_port: Allocated backend port (if any).
        frontend_port: Allocated frontend port (if any).

    Example:
        >>> run = ActiveRun(
        ...     run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        ...     pid=12345,
        ...     start_time=datetime.now(UTC),
        ...     worktree_path=Path("/project/trees/01HQXK5..."),
        ... )
        >>> run.is_pid_running()
        True
    """

    run_id: str = Field(description="ULID identifier for the run")
    pid: int = Field(description="Process ID of the running ADW instance")
    start_time: datetime = Field(description="When the run was started")
    worktree_path: Path = Field(description="Absolute path to the worktree directory")
    backend_port: int | None = Field(default=None, description="Allocated backend port")
    frontend_port: int | None = Field(
        default=None, description="Allocated frontend port"
    )

    def is_pid_running(self) -> bool:
        """Check if the process for this run is still running.

        Uses os.kill with signal 0 to check process existence
        without actually sending a signal.

        Returns:
            True if the process is running, False otherwise.
        """
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False


class ConcurrentRunManager:
    """Manages concurrent ADW run tracking and limiting.

    Tracks active runs via lock files in the `trees/.locks/` directory.
    Each lock file contains JSON metadata about the run including PID,
    start time, worktree path, and allocated ports.

    Automatically cleans up stale locks (where the PID is no longer running)
    when querying active runs.

    Attributes:
        project_root: Absolute path to the project root directory.
        max_concurrent: Maximum number of concurrent runs allowed.
        locks_dir: Path to the lock files directory (trees/.locks/).

    Example:
        >>> manager = ConcurrentRunManager(Path("/project"))
        >>> if manager.can_start_run():
        ...     manager.register_run(
        ...         run_id="01HQXK5...",
        ...         worktree_path=Path("/project/trees/01HQXK5..."),
        ...     )
        >>> # Run completes...
        >>> manager.unregister_run("01HQXK5...")
    """

    def __init__(
        self,
        project_root: Path,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        base_dir: str = "trees",
    ) -> None:
        """Initialize the ConcurrentRunManager.

        Args:
            project_root: Absolute path to the project root directory.
            max_concurrent: Maximum number of concurrent runs allowed.
                Defaults to 15.
            base_dir: Directory name for storing worktrees (relative to project_root).
                Defaults to "trees".
        """
        self.project_root = project_root.resolve()
        self.max_concurrent = max_concurrent
        self._base_dir = base_dir
        self.locks_dir = self.project_root / base_dir / ".locks"

    @property
    def base_dir(self) -> str:
        """Get the base directory name for worktrees.

        Returns:
            The directory name (relative to project_root) where worktrees are stored.
        """
        return self._base_dir

    def _lock_path(self, run_id: str) -> Path:
        """Get the lock file path for a given run ID.

        Args:
            run_id: ULID identifier for the run.

        Returns:
            Path to the lock file.
        """
        return self.locks_dir / f"{run_id}.lock"

    def get_active_runs(self) -> list[ActiveRun]:
        """Get all currently active runs, cleaning stale locks.

        Scans the locks directory for lock files, validates each one
        by checking if the PID is still running, and removes stale locks
        automatically.

        Returns:
            List of ActiveRun objects for currently running processes.
        """
        if not self.locks_dir.exists():
            return []

        active: list[ActiveRun] = []

        for lock_file in self.locks_dir.glob("*.lock"):
            try:
                data = json.loads(lock_file.read_text())

                # Parse the lock file data
                active_run = ActiveRun(
                    run_id=data["run_id"],
                    pid=data["pid"],
                    start_time=datetime.fromisoformat(data["start_time"]),
                    worktree_path=Path(data["worktree_path"]),
                    backend_port=data.get("backend_port"),
                    frontend_port=data.get("frontend_port"),
                )

                if active_run.is_pid_running():
                    active.append(active_run)
                    logger.debug(
                        "Found active run",
                        extra={
                            "run_id": active_run.run_id,
                            "pid": active_run.pid,
                        },
                    )
                else:
                    # Clean up stale lock
                    lock_file.unlink()
                    logger.info(
                        "Cleaned up stale lock",
                        extra={
                            "run_id": data["run_id"],
                            "pid": data["pid"],
                            "lock_file": str(lock_file),
                        },
                    )

            except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                # Corrupt or invalid lock file, remove it
                logger.warning(
                    "Removing corrupt lock file",
                    extra={
                        "lock_file": str(lock_file),
                        "error": str(e),
                    },
                )
                with contextlib.suppress(OSError):
                    lock_file.unlink(missing_ok=True)

        return active

    def can_start_run(self) -> bool:
        """Check if a new run can be started.

        Returns:
            True if under the max_concurrent limit, False otherwise.
        """
        active_count = len(self.get_active_runs())
        can_start = active_count < self.max_concurrent

        logger.debug(
            "Checking if run can start",
            extra={
                "active_count": active_count,
                "max_concurrent": self.max_concurrent,
                "can_start": can_start,
            },
        )

        return can_start

    def check_can_start_or_raise(self) -> None:
        """Check if a new run can be started, raising if not.

        Raises:
            MaxConcurrentRunsError: If at or over the max_concurrent limit.
        """
        active_runs = self.get_active_runs()

        if len(active_runs) >= self.max_concurrent:
            # Build a list of active run IDs for the error message
            active_ids = [run.run_id for run in active_runs[:5]]
            if len(active_runs) > 5:
                active_ids.append(f"... and {len(active_runs) - 5} more")

            raise MaxConcurrentRunsError(
                code="MAX_CONCURRENT_REACHED",
                message=f"Maximum concurrent runs reached ({self.max_concurrent})",
                suggestion="Use `adw list --running` to see active runs. "
                "Wait for a run to complete or abort one with `adw abort <run_id>`.",
                recoverable=False,
                context={
                    "max_concurrent": self.max_concurrent,
                    "active_count": len(active_runs),
                    "active_runs": active_ids,
                },
            )

    def register_run(
        self,
        run_id: str,
        worktree_path: Path,
        backend_port: int | None = None,
        frontend_port: int | None = None,
    ) -> None:
        """Register a new active run by creating a lock file.

        Creates the locks directory if it doesn't exist and writes
        a JSON lock file with run metadata.

        Args:
            run_id: ULID identifier for the run.
            worktree_path: Absolute path to the worktree directory.
            backend_port: Allocated backend port (if any).
            frontend_port: Allocated frontend port (if any).

        Raises:
            OSError: If the lock file cannot be created.
        """
        self.locks_dir.mkdir(parents=True, exist_ok=True)

        lock_data = {
            "run_id": run_id,
            "pid": os.getpid(),
            "start_time": datetime.now(UTC).isoformat(),
            "worktree_path": str(worktree_path),
            "backend_port": backend_port,
            "frontend_port": frontend_port,
        }

        lock_path = self._lock_path(run_id)
        lock_path.write_text(json.dumps(lock_data, indent=2))

        logger.info(
            "Registered active run",
            extra={
                "run_id": run_id,
                "pid": lock_data["pid"],
                "worktree_path": str(worktree_path),
                "lock_path": str(lock_path),
            },
        )

    def unregister_run(self, run_id: str) -> None:
        """Unregister a run by removing its lock file.

        Removes the lock file for the given run ID. Does not raise
        an error if the lock file doesn't exist.

        Args:
            run_id: ULID identifier for the run.
        """
        lock_path = self._lock_path(run_id)

        if lock_path.exists():
            try:
                lock_path.unlink()
                logger.info(
                    "Unregistered run",
                    extra={
                        "run_id": run_id,
                        "lock_path": str(lock_path),
                    },
                )
            except OSError as e:
                logger.warning(
                    "Failed to unregister run",
                    extra={
                        "run_id": run_id,
                        "lock_path": str(lock_path),
                        "error": str(e),
                    },
                )
        else:
            logger.debug(
                "Lock file not found for unregister",
                extra={
                    "run_id": run_id,
                    "lock_path": str(lock_path),
                },
            )

    def get_run_info(self, run_id: str) -> ActiveRun | None:
        """Get information about a specific run.

        Args:
            run_id: ULID identifier for the run.

        Returns:
            ActiveRun object if the run is active, None otherwise.
        """
        lock_path = self._lock_path(run_id)

        if not lock_path.exists():
            return None

        try:
            data = json.loads(lock_path.read_text())
            active_run = ActiveRun(
                run_id=data["run_id"],
                pid=data["pid"],
                start_time=datetime.fromisoformat(data["start_time"]),
                worktree_path=Path(data["worktree_path"]),
                backend_port=data.get("backend_port"),
                frontend_port=data.get("frontend_port"),
            )

            if active_run.is_pid_running():
                return active_run
            else:
                # Clean up stale lock
                lock_path.unlink(missing_ok=True)
                return None

        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            return None

    def get_orphaned_worktrees(self) -> list[Path]:
        """Find worktrees without corresponding active locks.

        Scans the worktree base directory for directories that don't have
        corresponding lock files with running processes. These are considered
        orphaned and safe to clean up.

        Returns:
            List of paths to orphaned worktree directories.

        Note:
            This method first calls get_active_runs() to clean up any stale
            locks before determining which worktrees are orphaned.
        """
        # First, clean up stale locks by getting active runs
        active_run_ids = {run.run_id for run in self.get_active_runs()}

        worktree_base = self.project_root / self._base_dir
        if not worktree_base.exists():
            return []

        orphaned: list[Path] = []

        for entry in worktree_base.iterdir():
            # Skip non-directories and special entries
            if not entry.is_dir():
                continue
            if entry.name.startswith("."):
                continue  # Skip .locks and other hidden directories

            run_id = entry.name

            # If this worktree has an active lock, it's not orphaned
            if run_id in active_run_ids:
                continue

            # Verify it looks like a git worktree (has .git file or directory)
            if (entry / ".git").exists():
                orphaned.append(entry)
                logger.debug(
                    "Found orphaned worktree",
                    extra={
                        "run_id": run_id,
                        "path": str(entry),
                    },
                )

        return orphaned
