"""Build Phase Extension.

This module provides the BuildExtension class that handles git diff
artifact capture for the build phase.
"""

import json
import logging
import subprocess
from typing import TYPE_CHECKING, ClassVar

from adw.hooks.git_diff import (
    capture_diff,
    capture_staged_diff,
    get_diff_stats,
    has_commits,
    truncate_diff,
)

if TYPE_CHECKING:
    from adw.models import LLMResult, PhaseResult, RunContext

logger = logging.getLogger(__name__)


class BuildExtension:
    """Extension for build phase that captures git diff artifacts.

    Captures git diff since the last commit (or staged changes if no commits)
    and stores as diff.txt and diff_stats.json artifacts.

    This extension:
    - Is stateless (uses RunContext for working directory)
    - Returns artifacts via extra_artifacts() hook
    - Handles errors gracefully (returns empty list on failure)

    Example:
        >>> from adw.core.extensions import ExtensionRegistry
        >>> registry = ExtensionRegistry()
        >>> registry.register(BuildExtension())
    """

    phase: ClassVar[str] = "build"

    def should_skip(self, context: "RunContext") -> tuple[bool, str | None]:
        """Build phase never skips via extension logic.

        Args:
            context: Current run context (unused).

        Returns:
            Always returns (False, None).
        """
        del context  # Unused
        return False, None

    def on_complete(
        self, context: "RunContext", result: "PhaseResult"
    ) -> "RunContext":
        """No post-processing needed for build phase.

        Args:
            context: Current run context.
            result: Result from the completed phase (unused).

        Returns:
            Unchanged context.
        """
        del result  # Unused
        return context

    def extra_artifacts(
        self, context: "RunContext", llm_result: "LLMResult"
    ) -> list[tuple[str, str]]:
        """Capture git diff as build phase artifacts.

        Captures the git diff since the last commit and returns it as artifacts.
        If no commits were made during build, captures staged changes instead.
        Large diffs (>100KB) are truncated with a summary.

        Args:
            context: Current run context.
            llm_result: Result from LLM execution (unused).

        Returns:
            List of (artifact_name, content) tuples:
            - ("diff.txt", diff_content)
            - ("diff_stats.json", stats_json)
            Empty list if no changes to capture or on error.
        """
        del llm_result  # Unused
        artifacts: list[tuple[str, str]] = []
        diff_reference = "HEAD~1"

        try:
            # Check if repository has commits (handles initial commit edge case)
            if not has_commits(working_dir=context.worktree_path):
                logger.debug(
                    "No commits in repository, trying staged changes",
                    extra={"run_id": context.run_id},
                )
                diff_content = capture_staged_diff(working_dir=context.worktree_path)
                diff_reference = "--cached"
            else:
                # Try to capture diff since last commit
                diff_content = capture_diff(
                    since="HEAD~1", working_dir=context.worktree_path
                )

                # If no diff found, try staged changes
                if not diff_content.strip():
                    logger.debug(
                        "No commit diff found, trying staged changes",
                        extra={"run_id": context.run_id},
                    )
                    diff_content = capture_staged_diff(
                        working_dir=context.worktree_path
                    )
                    diff_reference = "--cached"

            # Handle empty diff case
            if not diff_content.strip():
                logger.debug(
                    "No git changes to capture",
                    extra={"run_id": context.run_id},
                )
                return artifacts

            # Store raw diff content for binary file detection
            raw_diff_content = diff_content

            # Truncate if too large (>100KB)
            original_size = len(diff_content.encode("utf-8"))
            diff_content = truncate_diff(diff_content, max_bytes=102400)

            # Add diff.txt artifact
            artifacts.append(("diff.txt", diff_content))

            # Capture and add diff statistics
            stats_content = self._capture_diff_stats(
                context, diff_reference, raw_diff_content, original_size
            )
            if stats_content:
                artifacts.append(("diff_stats.json", stats_content))

        except Exception as e:
            # Git diff errors are non-fatal - log and continue
            logger.warning(
                "Could not capture git diff (non-blocking)",
                extra={
                    "run_id": context.run_id,
                    "error": str(e),
                },
            )

        return artifacts

    def _capture_diff_stats(
        self,
        context: "RunContext",
        diff_reference: str,
        raw_diff_content: str,
        original_size: int,
    ) -> str | None:
        """Capture diff statistics as JSON string.

        Args:
            context: Current run context.
            diff_reference: Git reference used for diff (HEAD~1 or --cached).
            raw_diff_content: Raw diff content for binary file detection.
            original_size: Original diff size in bytes.

        Returns:
            JSON string with diff stats, or None on error.
        """
        try:
            stat_cmd = ["git", "diff", "--stat", "--no-color"]
            if diff_reference == "--cached":
                stat_cmd.append("--cached")
            else:
                stat_cmd.append(diff_reference)

            stat_result = subprocess.run(
                stat_cmd,
                capture_output=True,
                text=True,
                cwd=context.worktree_path if context.worktree_path else None,
            )

            if stat_result.returncode != 0:
                logger.debug(
                    "Git diff --stat failed",
                    extra={"returncode": stat_result.returncode},
                )
                return None

            stats = get_diff_stats(stat_result.stdout, raw_diff_content)

            # Log summary
            lines = stats.insertions + stats.deletions
            logger.info(
                "Captured diff",
                extra={
                    "run_id": context.run_id,
                    "lines": lines,
                    "original_bytes": original_size,
                    "files_changed": stats.files_changed,
                    "insertions": stats.insertions,
                    "deletions": stats.deletions,
                    "binary_files": stats.binary_files,
                },
            )

            return json.dumps(stats.model_dump(), indent=2)

        except Exception as stat_error:
            logger.debug(
                "Could not capture diff stats",
                extra={"error": str(stat_error)},
            )
            return None

    def get_hook_env(self, context: "RunContext") -> dict[str, str]:
        """Build phase has no additional hook environment variables.

        Args:
            context: Current run context (unused).

        Returns:
            Empty dictionary.
        """
        del context  # Unused
        return {}
