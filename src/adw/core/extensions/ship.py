"""Ship Phase Extension.

This module provides the ShipExtension class that controls
ship phase execution based on PR creation state.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import yaml

from adw.commands.loader import get_config_class
from adw.models.command import ShipCommandConfig

if TYPE_CHECKING:
    from adw.models import LLMResult, PhaseResult, RunContext

logger = logging.getLogger(__name__)


class ShipExtension:
    """Extension for ship phase that controls execution based on PR state.

    Skips the ship phase if PR creation was attempted but failed,
    since the ship phase relies on having a PR to merge.

    This extension:
    - Controls skip logic based on PR state
    - Provides hook environment variables from ship config
    - Uses context.pr_creation_attempted and pr_creation_failed

    Dependencies:
    - project_root: For loading ship config from .adw/commands/ship/config.yaml

    Example:
        >>> from adw.core.extensions import ExtensionRegistry
        >>> registry = ExtensionRegistry()
        >>> registry.register(ShipExtension(project_root=Path("/project")))
    """

    phase: ClassVar[str] = "ship"

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize ShipExtension.

        Args:
            project_root: Path to project root for loading ship config.
                If None, hook environment variables won't be set from config.
        """
        self._project_root = project_root

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
        """No post-processing needed for ship phase.

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

        Loads the ship config and returns environment variables that
        the ship phase post-hook expects:
        - ADW_SHIP_BYPASS_CI: Whether to bypass CI checks

        Args:
            context: Current run context (unused).

        Returns:
            Dictionary of environment variable names to values.
        """
        del context  # Unused
        config = self._load_ship_config()
        if config is None:
            return {}

        return {
            "ADW_SHIP_BYPASS_CI": str(config.bypass_ci).lower(),
        }
