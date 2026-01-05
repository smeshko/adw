"""Git worktree manager for ADW run isolation.

This module provides the WorktreeManager class for creating and managing
git worktrees that isolate concurrent ADW runs from each other and from
the user's working directory.
"""

import logging
import subprocess
from pathlib import Path

from adw.exceptions import ConfigError, WorktreeError

logger = logging.getLogger(__name__)


class WorktreeManager:
    """Manages git worktrees for isolated ADW run execution.

    Each ADW run can execute in its own git worktree, preventing
    concurrent runs from interfering with each other or with the
    user's working directory.

    Attributes:
        project_root: Absolute path to the project root directory.
        base_dir: Directory name for storing worktrees (relative to project_root).

    Example:
        >>> manager = WorktreeManager(project_root=Path("/project"))
        >>> worktree_path = manager.create_worktree("01HQ1234567890ABCDEFGHIJK")
        >>> # Run completes...
        >>> manager.remove_worktree("01HQ1234567890ABCDEFGHIJK")
    """

    def __init__(
        self,
        project_root: Path,
        base_dir: str = "trees",
    ) -> None:
        """Initialize the WorktreeManager.

        Args:
            project_root: Absolute path to the project root directory.
            base_dir: Directory name for storing worktrees (relative to project_root).
                Defaults to "trees".
        """
        self.project_root = project_root.resolve()
        self.base_dir = base_dir

    @property
    def worktree_base_path(self) -> Path:
        """Get the absolute path to the worktree base directory.

        Returns:
            Absolute path to the base directory for worktrees.
        """
        return self.project_root / self.base_dir

    def create_worktree(
        self,
        run_id: str,
        source_branch: str | None = None,
    ) -> Path:
        """Create a new worktree for the given run.

        Creates a git worktree at `<project_root>/<base_dir>/<run_id>/`
        with a new branch named `adw/<run_id>`.

        Args:
            run_id: ULID identifier for this run.
            source_branch: Optional branch to create the worktree from.
                If None, uses the current HEAD.

        Returns:
            Absolute path to the created worktree directory.

        Raises:
            ConfigError: If git is not available.
            WorktreeError: If the branch or worktree path already exists.
        """
        worktree_path = self.worktree_base_path / run_id
        branch_name = f"adw/{run_id}"

        # Check if worktree path already exists
        if worktree_path.exists():
            raise WorktreeError(
                code="WORKTREE_PATH_EXISTS",
                message=f"Worktree path already exists: {worktree_path}",
                suggestion=f"Remove the directory or use a different run ID: rm -rf {worktree_path}",
            )

        # Check if branch already exists
        if self._branch_exists(branch_name):
            raise WorktreeError(
                code="BRANCH_EXISTS",
                message=f"Branch '{branch_name}' already exists for run '{run_id}'",
                suggestion=f"Delete the branch: git branch -D {branch_name}",
            )

        # Ensure base directory exists
        self.worktree_base_path.mkdir(parents=True, exist_ok=True)

        # Build the git worktree add command
        cmd = ["git", "worktree", "add", str(worktree_path), "-b", branch_name]

        if source_branch:
            cmd.append(source_branch)

        logger.info(
            "Creating worktree",
            extra={
                "run_id": run_id,
                "path": str(worktree_path),
                "branch": branch_name,
                "source_branch": source_branch,
            },
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                # Clean up any partial state
                self._cleanup_partial_worktree(worktree_path, branch_name)

                raise WorktreeError(
                    code="WORKTREE_CREATE_FAILED",
                    message=f"Failed to create worktree: {result.stderr.strip()}",
                    suggestion="Check git status and try again",
                )

            logger.info(
                "Worktree created successfully",
                extra={
                    "run_id": run_id,
                    "path": str(worktree_path),
                },
            )

            return worktree_path

        except FileNotFoundError as e:
            raise ConfigError(
                code="GIT_NOT_FOUND",
                message="Git is not installed or not in PATH",
                suggestion="Install git and ensure it's in your PATH",
            ) from e

    def _branch_exists(self, branch_name: str) -> bool:
        """Check if a branch already exists.

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

    def _cleanup_partial_worktree(
        self,
        worktree_path: Path,
        branch_name: str,
    ) -> None:
        """Clean up partial worktree state after a failed creation.

        Args:
            worktree_path: Path to the worktree directory.
            branch_name: Name of the branch that may have been created.
        """
        # Try to remove the directory if it was created
        if worktree_path.exists():
            try:
                import shutil

                shutil.rmtree(worktree_path)
                logger.debug(
                    "Cleaned up partial worktree directory",
                    extra={"path": str(worktree_path)},
                )
            except OSError as e:
                logger.warning(
                    "Failed to clean up partial worktree directory",
                    extra={"path": str(worktree_path), "error": str(e)},
                )

        # Try to remove the branch if it was created
        try:
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            pass
