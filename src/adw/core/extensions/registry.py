"""Extension Registry for phase-specific behavior.

This module provides the ExtensionRegistry class that manages registration
and invocation of phase extensions.
"""

import logging
from typing import TYPE_CHECKING

from adw.core.extensions.base import PhaseExtension

if TYPE_CHECKING:
    from adw.models import LLMResult, PhaseResult, RunContext

logger = logging.getLogger(__name__)


class ExtensionRegistry:
    """Registry for phase extensions.

    Manages registration of PhaseExtension instances and provides methods
    to query and invoke extensions for specific phases.

    Extensions are stored by phase name, allowing multiple extensions per
    phase (though typically there's one). All extension invocations are
    non-blocking - failures are logged but don't propagate.

    Example:
        >>> registry = ExtensionRegistry()
        >>> registry.register(BuildExtension(artifact_manager))
        >>> registry.register(DocumentExtension(...))
        >>>
        >>> # Check if phase should skip
        >>> should_skip, reason = registry.should_skip_phase("ship", context)
        >>>
        >>> # Call lifecycle hooks
        >>> context = registry.call_on_complete("document", context, result)
        >>> artifacts = registry.call_extra_artifacts("build", context, llm_result)
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._extensions: dict[str, list[PhaseExtension]] = {}

    def register(self, extension: PhaseExtension) -> None:
        """Register an extension for its phase.

        Args:
            extension: Extension instance to register. Must have a `phase`
                class variable indicating which phase it applies to.

        Example:
            >>> registry.register(BuildExtension(artifact_manager))
        """
        phase = extension.phase
        if phase not in self._extensions:
            self._extensions[phase] = []
        self._extensions[phase].append(extension)
        logger.debug(
            "Registered extension",
            extra={"phase": phase, "extension": type(extension).__name__},
        )

    def get_extensions(self, phase: str) -> list[PhaseExtension]:
        """Get all extensions registered for a phase.

        Args:
            phase: Phase name to query.

        Returns:
            List of extensions for the phase. Empty list if none registered.
        """
        return self._extensions.get(phase, [])

    def should_skip_phase(
        self, phase: str, context: "RunContext"
    ) -> tuple[bool, str | None]:
        """Check if any extension wants to skip the phase.

        Iterates through all extensions for the phase. Returns skip=True
        if any extension returns skip=True.

        Args:
            phase: Phase name to check.
            context: Current run context.

        Returns:
            Tuple of (should_skip, reason). If multiple extensions want to
            skip, returns the first reason.
        """
        extensions = self.get_extensions(phase)
        for ext in extensions:
            try:
                should_skip, reason = ext.should_skip(context)
                if should_skip:
                    logger.info(
                        "Extension requested phase skip",
                        extra={
                            "phase": phase,
                            "extension": type(ext).__name__,
                            "reason": reason,
                        },
                    )
                    return True, reason
            except Exception as e:
                logger.warning(
                    "Extension should_skip failed (non-blocking)",
                    extra={
                        "phase": phase,
                        "extension": type(ext).__name__,
                        "error": str(e),
                    },
                )
        return False, None

    def call_on_complete(
        self, phase: str, context: "RunContext", result: "PhaseResult"
    ) -> "RunContext":
        """Call on_complete hooks for all phase extensions.

        Chains context through all extensions - each extension receives
        the context returned by the previous one.

        Args:
            phase: Phase that completed.
            context: Current run context.
            result: Result from the completed phase.

        Returns:
            Updated RunContext after all extensions have processed.
        """
        extensions = self.get_extensions(phase)
        current_context = context

        for ext in extensions:
            try:
                current_context = ext.on_complete(current_context, result)
                logger.debug(
                    "Extension on_complete succeeded",
                    extra={"phase": phase, "extension": type(ext).__name__},
                )
            except Exception as e:
                logger.warning(
                    "Extension on_complete failed (non-blocking)",
                    extra={
                        "phase": phase,
                        "extension": type(ext).__name__,
                        "error": str(e),
                    },
                )

        return current_context

    def call_extra_artifacts(
        self, phase: str, context: "RunContext", llm_result: "LLMResult"
    ) -> list[tuple[str, str]]:
        """Collect extra artifacts from all phase extensions.

        Args:
            phase: Current phase.
            context: Current run context.
            llm_result: Result from LLM execution.

        Returns:
            Combined list of (artifact_name, content) tuples from all
            extensions. Empty list if no extensions or no artifacts.
        """
        extensions = self.get_extensions(phase)
        all_artifacts: list[tuple[str, str]] = []

        for ext in extensions:
            try:
                artifacts = ext.extra_artifacts(context, llm_result)
                all_artifacts.extend(artifacts)
                if artifacts:
                    logger.debug(
                        "Extension provided extra artifacts",
                        extra={
                            "phase": phase,
                            "extension": type(ext).__name__,
                            "artifact_count": len(artifacts),
                        },
                    )
            except Exception as e:
                logger.warning(
                    "Extension extra_artifacts failed (non-blocking)",
                    extra={
                        "phase": phase,
                        "extension": type(ext).__name__,
                        "error": str(e),
                    },
                )

        return all_artifacts
