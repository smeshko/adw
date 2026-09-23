"""Git branch manager for ADW worktree isolation.

This module provides the WorktreeBranchManager class for creating and managing
git branches associated with ADW worktrees. Branches follow the naming
convention `adw/<run_id>`.
"""

import logging
import subprocess
from pathlib import Path

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

    def has_unpushed_commits(self, branch_name: str) -> bool:
        """Check if branch has commits not pushed to upstream.

        Args:
            branch_name: Name of the branch to check.

        Returns:
            True if branch has unpushed commits, False otherwise.
            Returns False if no upstream is set (conservative - assumes safe).
        """
        try:
            result = subprocess.run(
                ["git", "log", f"{branch_name}@{{u}}..{branch_name}", "--oneline"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            # If command fails (no upstream), assume no unpushed
            if result.returncode != 0:
                return False
            return bool(result.stdout.strip())
        except FileNotFoundError:
            return False

    def delete_branch(
        self,
        run_id: str,
        force: bool = False,
        *,
        branch_name: str | None = None,
    ) -> bool:
        """Delete a worktree branch.

        Args:
            run_id: ULID identifier for the run.
            force: If True, use -D flag (force delete even if not merged).
                If False, use -d flag which fails on unmerged branches.
            branch_name: Explicit branch name to delete. If None, falls back to
                deriving from run_id using get_branch_name().

        Returns:
            True if branch was deleted or didn't exist, False if preserved
            due to unpushed commits (when force=False).
        """
        branch_name = branch_name or self.get_branch_name(run_id)

        if not self.branch_exists(branch_name):
            return True  # Already gone

        # Check for unpushed commits when not forcing
        if not force and self.has_unpushed_commits(branch_name):
            logger.warning(
                "Preserving branch with unpushed commits",
                extra={"branch": branch_name, "run_id": run_id},
            )
            return False  # Preserve by default

        delete_flag = "-D" if force else "-d"

        logger.info(
            "Deleting branch",
            extra={
                "branch": branch_name,
                "run_id": run_id,
                "force": force,
            },
        )

        result = subprocess.run(
            ["git", "branch", delete_flag, branch_name],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            logger.info(
                "Branch deleted successfully",
                extra={"branch": branch_name},
            )
            return True

        logger.warning(
            "Failed to delete branch",
            extra={"branch": branch_name, "error": result.stderr.strip()},
        )
        return False

    def check_pr_exists(self, branch_name: str) -> bool | None:
        """Check if a PR exists for the branch using gh CLI.

        Args:
            branch_name: Name of the branch to check.

        Returns:
            True if PR exists (OPEN or MERGED), False if no PR,
            None if gh CLI not available or not authenticated.
        """
        try:
            result = subprocess.run(
                ["gh", "pr", "view", branch_name, "--json", "state"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                # Could be: gh not installed, not authenticated, no PR
                return None

            return "OPEN" in result.stdout or "MERGED" in result.stdout

        except FileNotFoundError:
            # gh CLI not installed
            return None
