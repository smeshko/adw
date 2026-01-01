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

if TYPE_CHECKING:
    from adw.models import RunContext


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

        Args:
            context: Initial RunContext to serialize.

        Returns:
            Path to created run directory.

        Raises:
            StateError: If directory creation fails.
        """
        # Placeholder - will be implemented in Task 3
        raise NotImplementedError("create() will be implemented in Task 3")
