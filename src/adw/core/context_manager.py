"""Context manager for atomic RunContext persistence.

This module provides the ContextManager class that handles atomic saves and loads
of RunContext with fsync, temp file pattern, and lock integration.

Key features:
- Atomic writes using temp file + rename pattern
- fsync for data durability guarantee
- Filelock for concurrent access prevention
- Proper validation and error handling on load
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING

import filelock
from pydantic import ValidationError

from adw.exceptions import StateError

if TYPE_CHECKING:
    from adw.models import RunContext

__all__ = ["ContextManager"]

# Default lock timeout in seconds
_DEFAULT_LOCK_TIMEOUT: int = 10


class ContextManager:
    """Manages RunContext persistence with atomic writes.

    Ensures data durability through:
    - Atomic writes (temp file + rename)
    - fsync before rename
    - Filelock for concurrent access prevention

    Attributes:
        runs_dir: Path to the .adw/runs directory.

    Example:
        >>> from pathlib import Path
        >>> manager = ContextManager(Path("/my/project/.adw/runs"))
        >>> manager.save(context)
        >>> loaded = manager.load(context.run_id)
    """

    def __init__(self, runs_dir: Path) -> None:
        """Initialize the ContextManager.

        Args:
            runs_dir: Path to the .adw/runs directory.
        """
        self.runs_dir = runs_dir

    def save(self, context: "RunContext") -> None:
        """Save context atomically with fsync.

        Uses the write-to-temp-then-rename pattern for atomic writes.
        Calls fsync before rename to guarantee data durability.

        Args:
            context: RunContext to persist.

        Raises:
            StateError: If run directory doesn't exist (RUN_DIR_NOT_FOUND),
                       write fails (CONTEXT_WRITE_FAILED), or
                       lock cannot be acquired (LOCK_TIMEOUT).
        """
        run_dir = self.runs_dir / context.run_id
        context_path = run_dir / "context.json"
        temp_path = run_dir / ".context.json.tmp"
        lock_path = run_dir / ".lock"

        if not run_dir.exists():
            raise StateError(
                code="RUN_DIR_NOT_FOUND",
                message=f"Run directory not found: {run_dir}",
                suggestion="Ensure run directory is created before saving context",
                recoverable=False,
            )

        try:
            with filelock.FileLock(lock_path, timeout=_DEFAULT_LOCK_TIMEOUT):
                # Write to temp file with fsync for durability
                with open(temp_path, "w") as f:
                    f.write(context.model_dump_json(indent=2))
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic rename (POSIX guarantee)
                temp_path.rename(context_path)

        except filelock.Timeout as e:
            raise StateError(
                code="LOCK_TIMEOUT",
                message=f"Could not acquire lock for run {context.run_id}",
                suggestion="Another process may be using this run",
                recoverable=True,
            ) from e
        except OSError as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise StateError(
                code="CONTEXT_WRITE_FAILED",
                message=f"Failed to write context: {e}",
                suggestion="Check filesystem permissions and disk space",
                recoverable=False,
            ) from e

    def load(self, run_id: str) -> "RunContext":
        """Load context with validation.

        Reads the context.json file, parses JSON, and validates against
        the RunContext Pydantic model.

        Args:
            run_id: The run ID to load.

        Returns:
            Validated RunContext instance.

        Raises:
            StateError: If file is missing (CONTEXT_NOT_FOUND),
                       corrupted (CONTEXT_CORRUPTED), or
                       lock cannot be acquired (LOCK_TIMEOUT).
        """
        from adw.models import RunContext

        run_dir = self.runs_dir / run_id
        context_path = run_dir / "context.json"
        lock_path = run_dir / ".lock"

        if not context_path.exists():
            raise StateError(
                code="CONTEXT_NOT_FOUND",
                message=f"Context not found for run {run_id}",
                suggestion="Check if run ID is correct",
                recoverable=False,
            )

        try:
            with filelock.FileLock(lock_path, timeout=_DEFAULT_LOCK_TIMEOUT):
                content = context_path.read_text()
                return RunContext.model_validate_json(content)

        except ValidationError as e:
            raise StateError(
                code="CONTEXT_CORRUPTED",
                message=f"Context file is corrupted or invalid: {e}",
                suggestion="Check snapshots directory for recoverable state",
                recoverable=True,
            ) from e
        except filelock.Timeout as e:
            raise StateError(
                code="LOCK_TIMEOUT",
                message=f"Could not acquire lock for run {run_id}",
                suggestion="Another process may be using this run",
                recoverable=True,
            ) from e
