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

import json
import logging
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from adw.exceptions import ConfigError, WorktreeError
from adw.worktree.branch import WorktreeBranchManager

logger = logging.getLogger(__name__)


# Default artifacts to preserve when cleaning up worktrees
DEFAULT_PRESERVE_ARTIFACTS = ["context.json", "logs", "artifacts", "llm"]


class PreservedArtifactInfo(TypedDict):
    """Information about a preserved artifact."""

    path: str
    size: int
    type: str  # "file" or "directory"


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

    def ensure_worktree_adw_structure(self, worktree_path: Path, run_id: str) -> Path:
        """Create the .adw/runs/<run_id>/ directory structure in a worktree.

        This creates the standard ADW run directory structure inside the worktree,
        allowing the run to store artifacts, logs, and state in an isolated location.

        Directory structure created:
            <worktree_path>/
            └── .adw/
                └── runs/
                    └── <run_id>/
                        ├── artifacts/   # Phase output artifacts
                        ├── logs/        # Log files
                        └── llm/         # LLM interaction logs

        Args:
            worktree_path: Absolute path to the worktree directory.
            run_id: ULID identifier for this run.

        Returns:
            Absolute path to the run directory (.adw/runs/<run_id>/).

        Example:
            >>> manager = WorktreeManager(project_root=Path("/project"))
            >>> worktree = Path("/project/trees/01HQ...")
            >>> run_dir = manager.ensure_worktree_adw_structure(worktree, "01HQ...")
            >>> run_dir.exists()
            True
        """
        run_dir = worktree_path / ".adw" / "runs" / run_id

        # Create the main run directory and subdirectories
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)
        (run_dir / "llm").mkdir(exist_ok=True)

        logger.debug(
            "Created ADW run structure in worktree",
            extra={
                "worktree_path": str(worktree_path),
                "run_id": run_id,
                "run_dir": str(run_dir),
            },
        )

        return run_dir

    def preserve_artifacts(
        self,
        worktree_path: Path,
        run_id: str,
        artifacts_to_preserve: list[str] | None = None,
        manifest_file: str = "worktree-artifacts.json",
    ) -> list[Path]:
        """Copy key artifacts from worktree to main project before worktree removal.

        This method copies specified artifacts from the worktree's .adw/runs/<run_id>/
        directory to the main project's .adw/runs/<run_id>/ directory, and creates
        a manifest file documenting what was preserved.

        Args:
            worktree_path: Absolute path to the worktree directory.
            run_id: ULID identifier for this run.
            artifacts_to_preserve: List of artifact names to preserve. If None,
                uses DEFAULT_PRESERVE_ARTIFACTS (context.json, logs, artifacts, llm).
            manifest_file: Name of the manifest file to create.

        Returns:
            List of paths to the preserved artifacts in the main project.

        Example:
            >>> manager = WorktreeManager(project_root=Path("/project"))
            >>> preserved = manager.preserve_artifacts(
            ...     Path("/project/trees/01HQ..."),
            ...     "01HQ...",
            ... )
            >>> len(preserved) > 0
            True
        """
        if artifacts_to_preserve is None:
            artifacts_to_preserve = DEFAULT_PRESERVE_ARTIFACTS

        source_run_dir = worktree_path / ".adw" / "runs" / run_id
        target_run_dir = self.project_root / ".adw" / "runs" / run_id

        # Ensure target directory exists
        target_run_dir.mkdir(parents=True, exist_ok=True)

        preserved_paths: list[Path] = []
        manifest_entries: list[PreservedArtifactInfo] = []

        for artifact_name in artifacts_to_preserve:
            source_path = source_run_dir / artifact_name
            target_path = target_run_dir / artifact_name

            if not source_path.exists():
                logger.debug(
                    "Artifact not found, skipping",
                    extra={"artifact": artifact_name, "source": str(source_path)},
                )
                continue

            try:
                if source_path.is_file():
                    # Copy single file
                    shutil.copy2(source_path, target_path)
                    size = target_path.stat().st_size
                    artifact_type = "file"
                else:
                    # Copy directory recursively
                    # Check if source has content - if empty, skip to preserve
                    # any existing content in target (artifacts may have been
                    # written directly to main project, not worktree)
                    source_has_content = (
                        any(source_path.iterdir()) if source_path.exists() else False
                    )
                    if not source_has_content and target_path.exists():
                        # Source is empty but target has content - preserve target
                        size = self._get_directory_size(target_path)
                        artifact_type = "directory"
                        logger.debug(
                            "Preserving existing target (source empty)",
                            extra={
                                "artifact": artifact_name,
                                "target": str(target_path),
                            },
                        )
                    else:
                        # Normal case: copy source to target
                        if target_path.exists():
                            shutil.rmtree(target_path)
                        shutil.copytree(source_path, target_path)
                        size = self._get_directory_size(target_path)
                        artifact_type = "directory"

                preserved_paths.append(target_path)
                manifest_entries.append(
                    PreservedArtifactInfo(
                        path=artifact_name,
                        size=size,
                        type=artifact_type,
                    )
                )

                logger.info(
                    "Preserved artifact",
                    extra={
                        "artifact": artifact_name,
                        "type": artifact_type,
                        "size": size,
                    },
                )

            except OSError as e:
                logger.warning(
                    "Failed to preserve artifact",
                    extra={"artifact": artifact_name, "error": str(e)},
                )

        # Create manifest
        manifest_path = target_run_dir / manifest_file
        manifest_data = {
            "run_id": run_id,
            "source_worktree": str(worktree_path),
            "preserved_at": datetime.now(UTC).isoformat(),
            "artifacts": manifest_entries,
        }

        try:
            manifest_path.write_text(json.dumps(manifest_data, indent=2))
            preserved_paths.append(manifest_path)
            logger.info(
                "Created artifact manifest",
                extra={"path": str(manifest_path)},
            )
        except OSError as e:
            logger.warning(
                "Failed to create artifact manifest",
                extra={"path": str(manifest_path), "error": str(e)},
            )

        return preserved_paths

    def _get_directory_size(self, path: Path) -> int:
        """Calculate total size of a directory recursively.

        Args:
            path: Path to the directory.

        Returns:
            Total size in bytes.
        """
        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
        return total

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
        branch_name: str | None = None,
    ) -> tuple[Path, str]:
        """Create a new worktree for the given run.

        Creates a git worktree at `<project_root>/<base_dir>/<run_id>/`
        with a new branch. The branch name can be specified explicitly
        (e.g., 'feature/add-auth') or defaults to 'adw/<run_id>'.

        Args:
            run_id: ULID identifier for this run.
            source_branch: Optional branch to create the worktree from.
                If None, uses the current HEAD.
            branch_name: Optional explicit branch name for the worktree.
                If None, defaults to 'adw/<run_id>'. Use this to create
                human-readable feature branches like 'feature/add-auth'.

        Returns:
            Tuple of (worktree_path, branch_name) where:
                - worktree_path: Absolute path to the created worktree directory.
                - branch_name: Name of the created git branch.

        Raises:
            ConfigError: If git is not available.
            WorktreeError: If the branch or worktree path already exists,
                or if branch creation fails.
        """
        worktree_path = self.worktree_base_path / run_id
        branch_name = branch_name or f"adw/{run_id}"

        # Check if worktree path already exists
        if worktree_path.exists():
            raise WorktreeError(
                code="WORKTREE_PATH_EXISTS",
                message=f"Worktree path already exists: {worktree_path}",
                suggestion=f"Remove the directory or use a different run ID: "
                f"rm -rf {worktree_path}",
            )

        # Check if branch already exists (using branch manager for consistency)
        if self._branch_manager.branch_exists(branch_name):
            raise WorktreeError(
                code="BRANCH_EXISTS",
                message=f"Branch '{branch_name}' already exists for run '{run_id}'",
                suggestion=f"Delete the branch: git branch -D {branch_name}",
            )

        # Ensure trees directory exists with proper gitignore setup
        self.ensure_trees_directory()

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

            # Create .adw/runs/<run_id>/ structure in the new worktree
            self.ensure_worktree_adw_structure(worktree_path, run_id)

            # Verify the branch was created (ISS-025)
            if not self._branch_manager.branch_exists(branch_name):
                raise WorktreeError(
                    code="BRANCH_NOT_CREATED",
                    message=(
                        f"Branch '{branch_name}' was not created during worktree setup"
                    ),
                    suggestion="Check git status and try again",
                    recoverable=False,
                )

            logger.info(
                "Worktree created successfully",
                extra={
                    "run_id": run_id,
                    "path": str(worktree_path),
                    "branch": branch_name,
                },
            )

            return worktree_path, branch_name

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
        preserve: bool = True,
        artifacts_to_preserve: list[str] | None = None,
        manifest_file: str = "worktree-artifacts.json",
        branch_name: str | None = None,
    ) -> tuple[bool, bool]:
        """Remove an existing worktree for the given run.

        Args:
            run_id: ULID identifier for this run.
            force: If True, remove even if there are uncommitted changes.
            delete_branch: If True, also delete the associated branch.
                Branch will be preserved if it has a PR or gh CLI is unavailable
                (unless force=True).
            preserve: If True, preserve artifacts before removal (default: True).
            artifacts_to_preserve: List of artifact names to preserve. If None,
                uses DEFAULT_PRESERVE_ARTIFACTS.
            manifest_file: Name of the manifest file to create.
            branch_name: Explicit branch name to delete. If None, falls back to
                deriving from run_id (adw/<run_id>). This should be used when
                git integration creates feature branches like feature/<name>.

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
        branch_name = branch_name or self._branch_manager.get_branch_name(run_id)

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

        # Preserve artifacts before removal
        if preserve:
            preserved = self.preserve_artifacts(
                worktree_path,
                run_id,
                artifacts_to_preserve=artifacts_to_preserve,
                manifest_file=manifest_file,
            )
            logger.info(
                "Artifacts preserved before worktree removal",
                extra={
                    "run_id": run_id,
                    "preserved_count": len(preserved),
                },
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

            logger.debug(
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
                        run_id, force=True, branch_name=branch_name
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
