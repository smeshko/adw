"""Ship Phase Extension.

This module provides the ShipExtension class that controls
ship phase execution based on PR creation state and handles
post-merge cleanup (worktree removal, branch deletion, checkout).
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import yaml

from adw.core.constants import project_runs_dir
from adw.git import HOOK_TIMEOUT, git
from adw.models.command import ShipCommandConfig, get_config_class

if TYPE_CHECKING:
    from adw.models import GitConfig, LLMResult, PhaseResult, RunContext

logger = logging.getLogger(__name__)


class ShipExtension:
    """Extension for ship phase that controls execution based on PR state.

    Skips the ship phase if PR creation was attempted but failed,
    since the ship phase relies on having a PR to merge.

    This extension:
    - Controls skip logic based on PR state
    - Provides hook environment variables from ship config and build_command
    - Uses context.pr_creation_attempted and pr_creation_failed

    Dependencies:
    - git_config: Base branch to check out after a merge whose record has none
    - project_root: For loading ship config from .adw/commands/ship/config.yaml
    - build_command: The project's build_command, from the loaded ProjectConfig

    Example:
        >>> from adw.core.extensions import ExtensionRegistry
        >>> registry = ExtensionRegistry()
        >>> registry.register(ShipExtension(GitConfig(), project_root=Path("/project")))
    """

    phase: ClassVar[str] = "ship"

    def __init__(
        self,
        git_config: "GitConfig",
        project_root: Path | None = None,
        build_command: str | None = None,
    ) -> None:
        """Initialize ShipExtension.

        Args:
            git_config: Git configuration; its base_branch is the fallback
                when the merge record carries no base branch.
            project_root: Path to project root for loading ship config.
                If None, hook environment variables won't be set from config.
            build_command: The project's build command, exported to the
                post-hook as ADW_SHIP_BUILD_CMD. If None, it is not exported.
        """
        self._git_config = git_config
        self._project_root = project_root
        self._build_command = build_command

    def _load_ship_config(self) -> ShipCommandConfig | None:
        """Load ship config from project's .adw/commands/ship/config.yaml.

        Returns:
            ShipCommandConfig if config exists and is valid, None otherwise.
        """
        if self._project_root is None:
            return None

        config_path = self._project_root / ".adw" / "commands" / "ship" / "config.yaml"
        if not config_path.exists():
            return None

        try:
            config_content = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(config_content)
            if data is None:
                data = {}
            config_class = get_config_class("ship")
            config = config_class.model_validate(data)
            if isinstance(config, ShipCommandConfig):
                return config
            return None
        except Exception as e:
            logger.warning(
                "Failed to load ship config for hook environment",
                extra={"error": str(e)},
            )
            return None

    def should_skip(self, context: "RunContext") -> tuple[bool, str | None]:
        """Check if ship phase should be skipped due to PR failure.

        Skips the ship phase if:
        - pr_creation_attempted is True AND
        - pr_creation_failed is True

        This prevents the ship phase from running when there's no
        PR to merge.

        Args:
            context: Current run context with PR state fields.

        Returns:
            Tuple of (should_skip, reason). Returns (True, reason) if
            PR creation failed, (False, None) otherwise.
        """
        if context.pr_creation_attempted and context.pr_creation_failed:
            reason = context.pr_failure_reason or "PR creation failed"
            logger.info(
                "Skipping ship phase due to PR failure",
                extra={
                    "run_id": context.run_id,
                    "reason": reason,
                },
            )
            return True, f"PR not available: {reason}"

        return False, None

    def on_complete(self, context: "RunContext", result: "PhaseResult") -> "RunContext":
        """Handle post-merge cleanup after ship phase completes.

        If the post-hook successfully merged a PR (merge_record.json exists),
        clean up the worktree, delete the local branch, checkout the base
        branch, and pull latest changes.

        Args:
            context: Current run context.
            result: Result from the completed phase.

        Returns:
            Updated context with worktree_path cleared if cleanup succeeded.
        """
        del result  # Unused

        if not (context.use_worktree and context.worktree_path and self._project_root):
            return context

        # Check if ship phase merged a PR
        merge_record_path = (
            project_runs_dir(context.worktree_path)
            / context.run_id
            / "artifacts"
            / "ship"
            / "merge_record.json"
        )
        if not merge_record_path.exists():
            return context

        try:
            merge_record = json.loads(merge_record_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return context

        if not merge_record.get("merged"):
            return context

        base_branch = merge_record.get("base_branch") or self._git_config.base_branch

        logger.info(
            "Post-merge cleanup: removing worktree and switching to base branch",
            extra={
                "run_id": context.run_id,
                "base_branch": base_branch,
                "branch_name": context.branch_name,
            },
        )

        # 1. Remove worktree + delete local branch
        from adw.worktree.manager import WorktreeManager

        worktree_manager = WorktreeManager(self._project_root)
        worktree_manager.remove_worktree(
            context.run_id,
            force=True,
            delete_branch=True,
            branch_name=context.branch_name,
            preserve=True,
        )

        # 2. Checkout base branch and pull latest (both run git hooks)
        git(
            "checkout",
            base_branch,
            cwd=self._project_root,
            check=True,
            timeout=HOOK_TIMEOUT,
        )
        git(
            "pull",
            "origin",
            base_branch,
            cwd=self._project_root,
            check=True,
            timeout=HOOK_TIMEOUT,
        )

        logger.info(
            "Post-merge cleanup complete",
            extra={
                "run_id": context.run_id,
                "base_branch": base_branch,
            },
        )

        # 3. Clear worktree_path so finalize_success skips "preserved" message
        return context.model_copy(update={"worktree_path": None})

    def extra_artifacts(
        self, context: "RunContext", llm_result: "LLMResult"
    ) -> list[tuple[str, str]]:
        """Ship phase produces no extra artifacts.

        Args:
            context: Current run context (unused).
            llm_result: Result from LLM execution (unused).

        Returns:
            Empty list.
        """
        del context, llm_result  # Unused
        return []

    def get_hook_env(self, context: "RunContext") -> dict[str, str]:
        """Get ship config values as environment variables for hooks.

        Returns the environment variables that the ship phase post-hook
        expects. These come from the ship config, when the project has one:
        - ADW_SHIP_BYPASS_CI: Whether to bypass CI checks
        - ADW_SHIP_WAIT_FOR_MERGE: Whether to wait for the PR to merge
        - ADW_SHIP_VERSION_BUMP_CMD: Version bump command (if configured)
        - ADW_SHIP_PUBLISH_CMD: Publish command (if configured)

        ADW_SHIP_BUILD_CMD comes from the project's build_command, and is set
        whether or not the ship config exists.

        Args:
            context: Current run context (unused).

        Returns:
            Dictionary of environment variable names to values.
        """
        del context  # Unused
        env: dict[str, str] = {}

        config = self._load_ship_config()
        if config is not None:
            env["ADW_SHIP_BYPASS_CI"] = str(config.bypass_ci).lower()
            env["ADW_SHIP_WAIT_FOR_MERGE"] = str(config.wait_for_merge).lower()

            # Expose deploy commands so post-hook can execute them deterministically
            if config.commands.version_bump:
                env["ADW_SHIP_VERSION_BUMP_CMD"] = config.commands.version_bump
            if config.commands.publish:
                env["ADW_SHIP_PUBLISH_CMD"] = config.commands.publish

        # build_command lives at project level (project.yaml), not ship config
        if self._build_command:
            env["ADW_SHIP_BUILD_CMD"] = self._build_command

        return env
