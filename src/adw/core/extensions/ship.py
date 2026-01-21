"""Ship Phase Extension.

This module provides the ShipExtension class that controls
ship phase execution based on PR creation state.
"""

import logging
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from adw.models import LLMResult, PhaseResult, RunContext

logger = logging.getLogger(__name__)


class ShipExtension:
    """Extension for ship phase that controls execution based on PR state.

    Skips the ship phase if PR creation was attempted but failed,
    since the ship phase relies on having a PR to merge.

    This extension:
    - Is stateless (no dependencies)
    - Uses context.pr_creation_attempted and pr_creation_failed
    - Returns skip reason for user feedback

    Example:
        >>> from adw.core.extensions import ExtensionRegistry
        >>> registry = ExtensionRegistry()
        >>> registry.register(ShipExtension())
    """

    phase: ClassVar[str] = "ship"

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

    def on_complete(
        self, context: "RunContext", _result: "PhaseResult"
    ) -> "RunContext":
        """No post-processing needed for ship phase.

        Args:
            context: Current run context.
            _result: Result from the completed phase (unused).

        Returns:
            Unchanged context.
        """
        return context

    def extra_artifacts(
        self, _context: "RunContext", _llm_result: "LLMResult"
    ) -> list[tuple[str, str]]:
        """Ship phase produces no extra artifacts.

        Args:
            _context: Current run context (unused).
            _llm_result: Result from LLM execution (unused).

        Returns:
            Empty list.
        """
        return []
