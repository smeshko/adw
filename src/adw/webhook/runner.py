"""Async run triggering for webhook events.

This module provides functionality to trigger ADW runs asynchronously
from webhook handlers, allowing non-blocking webhook responses.

The core subprocess logic lives in ``adw.core.run_trigger``. This
module adds webhook-specific concerns (correlation IDs, source info
logging, sync convenience wrappers).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from adw.core.run_trigger import RunTrigger, RunTriggerResult

if TYPE_CHECKING:
    from adw.models.webhook import RunParams

logger = logging.getLogger(__name__)

# Re-export so existing consumers of `from adw.webhook.runner import RunTriggerResult`
# continue to work without changes.
__all__ = ["RunTriggerResult", "WebhookRunTrigger", "trigger_run_async",
           "trigger_from_params_async", "trigger_from_params"]


class WebhookRunTrigger:
    """Triggers ADW runs from webhook events.

    Thin wrapper around :class:`adw.core.run_trigger.RunTrigger` that
    adds webhook-specific logging (correlation IDs, source info).

    Attributes:
        _trigger: The core RunTrigger instance.
        _project_dir: The project directory to run ADW in.

    Example:
        >>> trigger = WebhookRunTrigger(project_dir="/my/project")
        >>> result = await trigger.trigger_async(
        ...     feature_request="Add dark mode",
        ...     phases=["plan"],
        ...     source_info={"provider": "linear"},
        ... )
        >>> if result.success:
        ...     print(f"Run started: {result.run_id}")
    """

    def __init__(
        self,
        project_dir: Path | str | None = None,
        adw_command: str = "adw",
    ) -> None:
        """Initialize the run trigger.

        Args:
            project_dir: Directory to run ADW in. Defaults to cwd.
            adw_command: The ADW CLI command to execute.
        """
        self._project_dir = Path(project_dir) if project_dir else Path.cwd()
        self._trigger = RunTrigger(
            project_dir=self._project_dir,
            adw_command=adw_command,
        )

    async def trigger_async(
        self,
        feature_request: str,
        phases: list[str] | None = None,
        source_info: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunTriggerResult:
        """Trigger an ADW run asynchronously.

        Starts the ADW run as a background subprocess and returns
        immediately with the result. The run continues in the background.

        Args:
            feature_request: The feature description to implement.
            phases: Optional list of phases to run. None = all phases.
            source_info: Information about the webhook source (for logging).
            metadata: Additional metadata (for logging).

        Returns:
            RunTriggerResult with success status and run details.

        Example:
            >>> result = await trigger.trigger_async(
            ...     feature_request="Add login feature",
            ...     phases=["plan", "build"],
            ... )
        """
        # Generate a correlation ID for tracking
        correlation_id = str(uuid.uuid4())[:8]

        logger.info(
            "Triggering ADW run",
            extra={
                "correlation_id": correlation_id,
                "feature_request": feature_request[:100],  # Truncate for logs
                "phases": phases,
                "source_info": source_info,
                "metadata": metadata,
            },
        )

        try:
            result = await self._trigger.start_run(
                project_path=str(self._project_dir),
                feature=feature_request,
                phases=phases,
            )

            if result.success:
                logger.info(
                    "ADW run triggered successfully",
                    extra={
                        "correlation_id": correlation_id,
                        "run_id": result.run_id,
                        "process_id": result.process_id,
                    },
                )
            else:
                logger.error(
                    "Failed to trigger ADW run",
                    extra={
                        "correlation_id": correlation_id,
                        "error": result.error,
                    },
                )

            return result

        except (OSError, ValueError, RuntimeError) as e:
            # OSError: subprocess/file operation errors
            # ValueError: invalid input or configuration
            # RuntimeError: asyncio or event loop issues
            logger.exception(
                "Exception while triggering ADW run",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return RunTriggerResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
            )

    def trigger_sync(
        self,
        feature_request: str,
        phases: list[str] | None = None,
        source_info: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunTriggerResult:
        """Trigger an ADW run synchronously (blocking).

        Convenience method for triggering runs from synchronous code.
        Uses asyncio.run() internally.

        Args:
            feature_request: The feature description to implement.
            phases: Optional list of phases to run.
            source_info: Information about the webhook source.
            metadata: Additional metadata.

        Returns:
            RunTriggerResult with success status and run details.
        """
        return asyncio.run(
            self.trigger_async(
                feature_request=feature_request,
                phases=phases,
                source_info=source_info,
                metadata=metadata,
            )
        )


async def trigger_run_async(
    feature_request: str,
    phases: list[str] | None = None,
    source_info: dict[str, Any] | None = None,
    project_dir: Path | str | None = None,
) -> RunTriggerResult:
    """Convenience function to trigger an ADW run asynchronously.

    This is a module-level function for simple use cases. For more
    control, use WebhookRunTrigger class directly.

    Args:
        feature_request: The feature to implement.
        phases: Optional phases to run.
        source_info: Information about the trigger source.
        project_dir: Directory to run in (defaults to cwd).

    Returns:
        RunTriggerResult with trigger status.

    Example:
        >>> result = await trigger_run_async(
        ...     feature_request="Add login feature",
        ...     phases=["plan"],
        ...     source_info={"provider": "linear", "issue": "ENG-42"},
        ... )
    """
    trigger = WebhookRunTrigger(project_dir=project_dir)
    return await trigger.trigger_async(
        feature_request=feature_request,
        phases=phases,
        source_info=source_info,
    )


async def trigger_from_params_async(
    params: RunParams,
    project_dir: Path | str | None = None,
) -> RunTriggerResult:
    """Trigger an ADW run from extracted RunParams asynchronously.

    Convenience function to trigger a run using the RunParams model
    extracted from a webhook event. This async version should be used
    from within FastAPI route handlers or other async contexts.

    Args:
        params: The run parameters extracted from webhook event.
        project_dir: Directory to run in (defaults to cwd).

    Returns:
        RunTriggerResult with trigger status.

    Example:
        >>> params = provider.extract_run_params(event)
        >>> result = await trigger_from_params_async(params)
    """
    trigger = WebhookRunTrigger(project_dir=project_dir)
    return await trigger.trigger_async(
        feature_request=params.feature_request,
        phases=params.phases,
        source_info=params.source_info,
        metadata=params.metadata,
    )


def trigger_from_params(
    params: RunParams,
    project_dir: Path | str | None = None,
) -> RunTriggerResult:
    """Trigger an ADW run from extracted RunParams synchronously.

    Convenience function to trigger a run using the RunParams model
    extracted from a webhook event. This sync version should only be
    used from synchronous code outside an event loop. For FastAPI
    routes or async contexts, use trigger_from_params_async() instead.

    Args:
        params: The run parameters extracted from webhook event.
        project_dir: Directory to run in (defaults to cwd).

    Returns:
        RunTriggerResult with trigger status.

    Example:
        >>> params = provider.extract_run_params(event)
        >>> result = trigger_from_params(params)
    """
    trigger = WebhookRunTrigger(project_dir=project_dir)
    return trigger.trigger_sync(
        feature_request=params.feature_request,
        phases=params.phases,
        source_info=params.source_info,
        metadata=params.metadata,
    )
