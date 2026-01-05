"""Git branch manager for ADW worktree isolation.

This module provides the WorktreeBranchManager class for creating and managing
git branches associated with ADW worktrees. Branches follow the naming
convention `adw/<run_id>`.
"""

import logging
import subprocess
from pathlib import Path

from adw.exceptions import WorktreeError

logger = logging.getLogger(__name__)


class WorktreeBranchManager:
    """Manages git branches for ADW worktree isolation.

    Each ADW run uses a dedicated branch named `adw/<run_id>` to isolate
    its changes from other concurrent runs and from the user's working
    directory.

    Attributes:
        project_root: Absolute path to the project root directory.

    Example:
        >>> manager = WorktreeBranchManager(project_root=Path("/project"))
        >>> branch = manager.create_branch("01HQ1234567890ABCDEFGHIJK")
        >>> # Work happens on the branch...
        >>> manager.delete_branch("01HQ1234567890ABCDEFGHIJK", force=True)
    """

    def __init__(self, project_root: Path) -> None:
        """Initialize the WorktreeBranchManager.

        Args:
            project_root: Absolute path to the project root directory.
        """
        self.project_root = project_root.resolve()

    def get_branch_name(self, run_id: str) -> str:
        """Generate branch name for a run.

        Args:
            run_id: ULID identifier for the run.

        Returns:
            Branch name in format `adw/<run_id>`.
        """
        return f"adw/{run_id}"

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists locally.

        Args:
            branch_name: Name of the branch to check.

        Returns:
            True if the branch exists, False otherwise.
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--list", branch_name],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            return bool(result.stdout.strip())
        except FileNotFoundError:
            return False

    def create_branch(self, run_id: str, base_ref: str | None = None) -> str:
        """Create a worktree branch from base ref.

        Args:
            run_id: ULID identifier for this run.
            base_ref: Optional ref (branch, tag, commit) to create from.
                If None, uses HEAD.

        Returns:
            The created branch name.

        Raises:
            WorktreeError: If the branch already exists or creation fails.
        """
        branch_name = self.get_branch_name(run_id)
        base = base_ref or "HEAD"

        if self.branch_exists(branch_name):
            raise WorktreeError(
                code="BRANCH_EXISTS",
                message=f"Branch {branch_name} already exists",
                suggestion=f"Delete the branch with: git branch -D {branch_name}",
            )

        logger.info(
            "Creating branch",
            extra={
                "branch": branch_name,
                "base_ref": base,
                "run_id": run_id,
            },
        )

        result = subprocess.run(
            ["git", "branch", branch_name, base],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise WorktreeError(
                code="BRANCH_CREATE_FAILED",
                message=f"Failed to create branch: {result.stderr.strip()}",
                suggestion="Check that base ref exists and git is available",
            )

        logger.info(
            "Branch created successfully",
            extra={"branch": branch_name},
        )

        return branch_name
