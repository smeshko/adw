"""Document Phase Extension.

This module provides the DocumentExtension class that handles
PR description artifact creation and automatic PR creation.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from adw.core.pr import create_pr, load_pr_description
from adw.exceptions import ADWError
from adw.models import GitConfig

if TYPE_CHECKING:
    from adw.models import LLMResult, PhaseResult, RunContext

logger = logging.getLogger(__name__)


class DocumentExtension:
    """Extension for document phase that handles PR creation.

    Creates pr_description.md artifact and opens the run's PR.

    This extension:
    - Saves pr_description.md as an extra artifact
    - Opens the PR in on_complete() through core.pr.create_pr
    - Updates context with PR state fields

    Dependencies:
    - git_config: Supplies the PR's base branch
    - runs_dir: For artifact path resolution

    Example:
        >>> from adw.core.extensions import ExtensionRegistry
        >>> registry = ExtensionRegistry()
        >>> registry.register(
        ...     DocumentExtension(git_config=git_config, runs_dir=runs_dir)
        ... )
    """

    phase: ClassVar[str] = "document"

    def __init__(self, git_config: GitConfig, runs_dir: Path) -> None:
        """Initialize DocumentExtension.

        Args:
            git_config: Git configuration; its base_branch is the PR base.
            runs_dir: Path to .adw/runs directory.
        """
        self._git_config = git_config
        self._runs_dir = runs_dir

    def should_skip(self, context: "RunContext") -> tuple[bool, str | None]:
        """Document phase never skips via extension logic.

        Args:
            context: Current run context (unused).

        Returns:
            Always returns (False, None).
        """
        del context  # Unused
        return False, None

    def on_complete(self, context: "RunContext", result: "PhaseResult") -> "RunContext":
        """Open the run's PR after the document phase completes.

        Loads the PR description and calls ``create_pr``, recording the
        outcome on the context.

        Context fields updated:
        - pr_creation_attempted: Set to True
        - pr_url: Set to PR URL if successful
        - pr_creation_failed: Set to True if creation failed
        - pr_failure_reason: ``str(error)`` of the ADWError, if any

        Args:
            context: Current run context.
            result: Result from the completed phase (unused).

        Returns:
            Updated RunContext with PR state fields.
        """
        del result  # Unused
        logger.info(
            "Attempting PR creation after document phase",
            extra={"run_id": context.run_id},
        )

        context = context.model_copy(update={"pr_creation_attempted": True})

        try:
            body = load_pr_description(self._runs_dir / context.run_id)
            pr_url = create_pr(context, body, base=self._git_config.base_branch)
        except ADWError as e:
            logger.warning(
                "PR creation failed",
                extra={"run_id": context.run_id, "reason": str(e)},
            )
            return context.model_copy(
                update={"pr_creation_failed": True, "pr_failure_reason": str(e)}
            )

        logger.info(
            "PR created successfully",
            extra={"run_id": context.run_id, "pr_url": pr_url},
        )
        return context.model_copy(update={"pr_url": pr_url})

    def extra_artifacts(
        self, context: "RunContext", llm_result: "LLMResult"
    ) -> list[tuple[str, str]]:
        """Create pr_description.md artifact.

        Extracts the PR description from the LLM result and returns
        it as an artifact to be stored.

        Args:
            context: Current run context.
            llm_result: Result from LLM execution.

        Returns:
            List containing ("pr_description.md", content) tuple.
        """
        # Use final_output (last message only) for cleaner PR description
        # Falls back to full content if final_output is empty
        artifact_content = llm_result.final_output or llm_result.content

        logger.debug(
            "Creating pr_description artifact",
            extra={"run_id": context.run_id, "content_len": len(artifact_content)},
        )

        return [("pr_description.md", artifact_content)]

    def get_hook_env(self, context: "RunContext") -> dict[str, str]:
        """Document phase has no additional hook environment variables.

        Args:
            context: Current run context (unused).

        Returns:
            Empty dictionary.
        """
        del context  # Unused
        return {}
