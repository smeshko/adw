"""Git worktree manager for ADW run isolation.

This module provides the WorktreeManager class for creating and managing
git worktrees that isolate concurrent ADW runs from each other and from
the user's working directory.

Worktree Directory Structure:
    <project-root>/
    ├── trees/                      # Worktrees base directory
    │   ├── .gitignore             # Contains: *
    │   ├── 01HQXK5.../            # Active worktree
    │   │   ├── (full project copy)
    │   │   ├── .adw/
    │   │   │   └── runs/01HQXK5.../
    │   │   │       ├── context.json
    │   │   │       ├── logs/
    │   │   │       ├── artifacts/
    │   │   │       └── llm/
    │   └── 01HQXK6.../             # Another concurrent run
    └── .adw/
        └── runs/
            └── 01HQXK5.../         # Preserved artifacts after worktree removal
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

    def ensure_trees_directory(self) -> Path:
        """Ensure the trees directory exists with proper gitignore setup.

        Creates the trees directory if it doesn't exist, adds a .gitignore
        file inside it to ignore all contents, and ensures the trees directory
        itself is listed in the project's root .gitignore.

        Returns:
            Absolute path to the trees directory.

        Example:
            >>> manager = WorktreeManager(project_root=Path("/project"))
            >>> trees_path = manager.ensure_trees_directory()
            >>> trees_path.exists()
            True
            >>> (trees_path / ".gitignore").read_text()
            '# Ignore all worktree contents\\n*\\n'
        """
        trees_path = self.worktree_base_path

        # Create trees/ directory if it doesn't exist
        trees_path.mkdir(parents=True, exist_ok=True)
        logger.debug(
            "Trees directory ensured",
            extra={"path": str(trees_path)},
        )

        # Create trees/.gitignore with '*' to ignore all worktree contents
        trees_gitignore = trees_path / ".gitignore"
        if not trees_gitignore.exists():
            trees_gitignore.write_text("# Ignore all worktree contents\n*\n")
            logger.debug(
                "Created trees gitignore",
                extra={"path": str(trees_gitignore)},
            )

        # Add trees/ entry to project's root .gitignore if not present
        self._ensure_root_gitignore_entry()

        return trees_path

    def _ensure_root_gitignore_entry(self) -> None:
        """Ensure the trees directory is listed in the project's root .gitignore.

        Checks if the trees directory entry already exists in .gitignore and
        adds it with a newline if not present. Creates the .gitignore file if
        it doesn't exist.
        """
        root_gitignore = self.project_root / ".gitignore"
        entry = f"{self.base_dir}/"

        if root_gitignore.exists():
            content = root_gitignore.read_text()
            # Check if entry already exists (as exact line or with comment)
            lines = content.splitlines()
            for line in lines:
                # Strip comments and whitespace for comparison
                stripped = line.split("#")[0].strip()
                if stripped == entry or stripped == self.base_dir:
                    logger.debug(
                        "Trees directory already in root gitignore",
                        extra={"entry": entry},
                    )
                    return

            # Entry not found, append it with proper newline handling
            if content and not content.endswith("\n"):
                content += "\n"
            content += f"\n# ADW worktree directory\n{entry}\n"
            root_gitignore.write_text(content)
            logger.info(
                "Added trees directory to root gitignore",
                extra={"entry": entry},
            )
        else:
            # Create new .gitignore with the entry
            root_gitignore.write_text(f"# ADW worktree directory\n{entry}\n")
            logger.info(
                "Created root gitignore with trees directory",
                extra={"entry": entry},
            )

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
                suggestion=f"Remove the directory or use a different run ID: "
                f"rm -rf {worktree_path}",
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

    def remove_worktree(
        self,
        run_id: str,
        *,
        force: bool = False,
        cleanup_branch: bool = False,
    ) -> bool:
        """Remove an existing worktree for the given run.

        Args:
            run_id: ULID identifier for this run.
            force: If True, remove even if there are uncommitted changes.
            cleanup_branch: If True, also delete the `adw/<run_id>` branch.

        Returns:
            True if the worktree was successfully removed.

        Raises:
            WorktreeError: If the worktree doesn't exist or has uncommitted changes
                and force=False.
        """
        worktree_path = self.worktree_base_path / run_id
        branch_name = f"adw/{run_id}"

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
                "cleanup_branch": cleanup_branch,
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

            # Optionally clean up the branch
            if cleanup_branch:
                self._delete_branch(branch_name)

            return True

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

    def _delete_branch(self, branch_name: str) -> None:
        """Delete a branch.

        Args:
            branch_name: Name of the branch to delete.
        """
        try:
            result = subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                logger.info(
                    "Branch deleted",
                    extra={"branch": branch_name},
                )
            else:
                logger.warning(
                    "Failed to delete branch",
                    extra={"branch": branch_name, "error": result.stderr.strip()},
                )
        except OSError as e:
            logger.warning(
                "Failed to delete branch",
                extra={"branch": branch_name, "error": str(e)},
            )

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
        import contextlib

        with contextlib.suppress(OSError):
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
