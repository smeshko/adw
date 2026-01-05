"""Git worktree manager for ADW run isolation.

This module provides the WorktreeManager class for creating and managing
git worktrees that isolate concurrent ADW runs from each other and from
the user's working directory.
"""

import logging
import subprocess
from pathlib import Path

from adw.exceptions import ConfigError, WorktreeError
from adw.worktree.branch import WorktreeBranchManager

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
        self._branch_manager = WorktreeBranchManager(self.project_root)

    @property
    def branch_manager(self) -> WorktreeBranchManager:
        """Get the branch manager for this worktree manager.

        Returns:
            The WorktreeBranchManager instance used by this manager.
        """
        return self._branch_manager

    def get_branch_name(self, run_id: str) -> str:
        """Get the branch name for a given run ID.

        Args:
            run_id: ULID identifier for the run.

        Returns:
            Branch name in format `adw/<run_id>`.
        """
        return self._branch_manager.get_branch_name(run_id)

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

        # Check if branch already exists (using branch manager for consistency)
        if self._branch_manager.branch_exists(branch_name):
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

    def remove_worktree(
        self,
        run_id: str,
        *,
        force: bool = False,
        delete_branch: bool = False,
    ) -> tuple[bool, bool]:
        """Remove an existing worktree for the given run.

        Args:
            run_id: ULID identifier for this run.
            force: If True, remove even if there are uncommitted changes.
            delete_branch: If True, also delete the `adw/<run_id>` branch.
                Branch will be preserved if it has a PR or unpushed commits
                (unless force=True).

        Returns:
            Tuple of (worktree_removed, branch_deleted).
            worktree_removed is True if the worktree was successfully removed.
            branch_deleted is True if the branch was deleted, False if preserved
            or if delete_branch was False.

        Raises:
            WorktreeError: If the worktree doesn't exist or has uncommitted changes
                and force=False.
        """
        worktree_path = self.worktree_base_path / run_id
        branch_name = self._branch_manager.get_branch_name(run_id)

        # Check if worktree exists
        if not worktree_path.exists():
            raise WorktreeError(
                code="WORKTREE_NOT_FOUND",
                message=f"Worktree not found at: {worktree_path}",
                suggestion=f"Check if the run ID '{run_id}' is correct",
            )

        # Check for uncommitted changes if not forcing
        if not force and self._has_uncommitted_changes(worktree_path):
            raise WorktreeError(
                code="WORKTREE_HAS_CHANGES",
                message=f"Worktree has uncommitted changes: {worktree_path}",
                suggestion="Commit or discard changes, or use force=True",
            )

        logger.info(
            "Removing worktree",
            extra={
                "run_id": run_id,
                "path": str(worktree_path),
                "force": force,
                "delete_branch": delete_branch,
            },
        )

        # Build the git worktree remove command
        cmd = ["git", "worktree", "remove", str(worktree_path)]
        if force:
            cmd.insert(3, "--force")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise WorktreeError(
                    code="WORKTREE_REMOVE_FAILED",
                    message=f"Failed to remove worktree: {result.stderr.strip()}",
                    suggestion="Check git status and try again",
                )

            logger.info(
                "Worktree removed successfully",
                extra={"run_id": run_id},
            )

            # Optionally delete the branch
            branch_deleted = False
            if delete_branch:
                # Check for PR before deletion (optional - graceful if gh not available)
                pr_exists = self._branch_manager.check_pr_exists(branch_name)
                if pr_exists is True and not force:
                    logger.info(
                        "Preserving branch with existing PR",
                        extra={"branch": branch_name, "run_id": run_id},
                    )
                elif pr_exists is None and not force:
                    # gh CLI unavailable - preserve branch to be safe
                    logger.info(
                        "Preserving branch (PR status unknown - gh CLI unavailable)",
                        extra={"branch": branch_name, "run_id": run_id},
                    )
                else:
                    # User explicitly requested deletion with --delete-branch
                    # Use force=True since ADW branches always have unmerged commits
                    # PR check above is the safety guard, not unmerged commits
                    branch_deleted = self._branch_manager.delete_branch(
                        run_id, force=True
                    )
                    if not branch_deleted:
                        logger.warning(
                            "Failed to delete branch",
                            extra={"branch": branch_name, "run_id": run_id},
                        )

            return (True, branch_deleted)

        except FileNotFoundError as e:
            raise WorktreeError(
                code="GIT_NOT_FOUND",
                message="Git is not installed or not in PATH",
                suggestion="Install git and ensure it's in your PATH",
            ) from e

    def _has_uncommitted_changes(self, worktree_path: Path) -> bool:
        """Check if the worktree has uncommitted changes.

        Args:
            worktree_path: Path to the worktree directory.

        Returns:
            True if there are uncommitted changes, False otherwise.
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return bool(result.stdout.strip())
        except (FileNotFoundError, OSError):
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
