"""Phase Extension Protocol definition.

This module defines the Protocol for phase-specific extension behavior,
allowing phases to define custom lifecycle hooks without modifying core
orchestration files.
"""

from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from adw.models import LLMResult, PhaseResult, RunContext


@runtime_checkable
class PhaseExtension(Protocol):
    """Extension point for phase-specific behavior.

    Extensions provide lifecycle hooks that are called at specific points
    during phase execution:
    - should_skip(): Before phase execution, to conditionally skip
    - on_complete(): After phase completes successfully
    - extra_artifacts(): During artifact capture, to add additional artifacts

    Extensions are:
    - Stateless: Run-specific data flows through RunContext
    - Singletons: One instance per registry lifetime
    - Non-blocking: Failures log warnings, don't fail phases

    Example:
        >>> class MyExtension:
        ...     phase: ClassVar[str] = "build"
        ...
        ...     def should_skip(self, context: RunContext) -> tuple[bool, str | None]:
        ...         return False, None
        ...
        ...     def on_complete(
        ...         self, context: RunContext, result: PhaseResult
        ...     ) -> RunContext:
        ...         return context
        ...
        ...     def extra_artifacts(
        ...         self, context: RunContext, llm_result: LLMResult
        ...     ) -> list[tuple[str, str]]:
        ...         return []
    """

    phase: ClassVar[str]
    """The phase this extension applies to (e.g., 'build', 'document', 'ship')."""

    def should_skip(self, context: "RunContext") -> tuple[bool, str | None]:
        """Determine if the phase should be skipped.

        Called before phase execution. Return (True, reason) to skip the phase,
        or (False, None) to proceed with execution.

        Args:
            context: Current run context with state from previous phases.

        Returns:
            Tuple of (should_skip, reason). If should_skip is True, reason
            should explain why the phase is being skipped.

        Example:
            >>> def should_skip(self, context):
            ...     if context.pr_creation_failed:
            ...         return True, "PR creation failed"
            ...     return False, None
        """
        ...

    def on_complete(
        self, context: "RunContext", result: "PhaseResult"
    ) -> "RunContext":
        """Handle post-phase processing.

        Called after phase completes successfully. Can perform side effects
        (e.g., PR creation) and return an updated context with new state.

        Args:
            context: Current run context.
            result: Result from the completed phase.

        Returns:
            Updated RunContext (may be same instance if no changes).

        Example:
            >>> def on_complete(self, context, result):
            ...     # Create PR and update context
            ...     pr_url = self._create_pr(context)
            ...     return context.model_copy(update={"pr_url": pr_url})
        """
        ...

    def extra_artifacts(
        self, context: "RunContext", llm_result: "LLMResult"
    ) -> list[tuple[str, str]]:
        """Generate additional artifacts for the phase.

        Called during artifact capture. Return a list of (name, content) tuples
        for artifacts to store alongside the standard phase artifacts.

        Args:
            context: Current run context.
            llm_result: Result from LLM execution.

        Returns:
            List of (artifact_name, content) tuples. Empty list if no
            additional artifacts.

        Example:
            >>> def extra_artifacts(self, context, llm_result):
            ...     diff = capture_git_diff()
            ...     return [("diff.txt", diff), ("diff_stats.json", stats)]
        """
        ...
