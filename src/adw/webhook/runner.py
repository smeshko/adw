"""Async run triggering for webhook events.

This module provides functionality to trigger ADW runs asynchronously
from webhook handlers, allowing non-blocking webhook responses.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from adw.models.webhook import RunParams

logger = logging.getLogger(__name__)


@dataclass
class RunTriggerResult:
    """Result of triggering an ADW run.

    Attributes:
        success: Whether the run was successfully triggered.
        run_id: The ADW run ID if successful.
        error: Error message if not successful.
        process_id: The subprocess PID if launched in background.
    """

    success: bool
    run_id: str | None = None
    error: str | None = None
    process_id: int | None = None


class WebhookRunTrigger:
    """Triggers ADW runs from webhook events.

    Provides async methods for triggering ADW runs in the background,
    allowing webhook handlers to respond quickly without waiting for
    run completion.

    Attributes:
        _project_dir: The project directory to run ADW in.
        _adw_command: The ADW command to execute.

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
        self._adw_command = adw_command

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
            # Build the ADW command
            cmd = self._build_command(feature_request, phases)

            # Run ADW as a background subprocess
            result = await self._run_subprocess(cmd, correlation_id)

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

    def _build_command(
        self,
        feature_request: str,
        phases: list[str] | None,
    ) -> list[str]:
        """Build the ADW CLI command.

        Args:
            feature_request: The feature to implement.
            phases: Optional phases to run. If multiple phases are specified,
                   only the first phase is used (CLI limitation).

        Returns:
            Command as list of strings for subprocess.
        """
        cmd = [self._adw_command, "run"]

        # Add phase flag if specified
        if phases:
            if len(phases) == 1:
                cmd.extend(["--phase", phases[0]])
            else:
                # CLI only supports single --phase flag
                # Use first phase and log warning about limitation
                logger.warning(
                    "Multiple phases specified but CLI only supports single phase; "
                    "using first phase only",
                    extra={
                        "requested_phases": phases,
                        "selected_phase": phases[0],
                    },
                )
                cmd.extend(["--phase", phases[0]])

        # Add the feature request (quoted for shell safety)
        cmd.append(feature_request)

        return cmd

    async def _run_subprocess(
        self,
        cmd: list[str],
        correlation_id: str,
    ) -> RunTriggerResult:
        """Run the ADW command as a subprocess.

        Launches ADW in the background without blocking on output.
        The subprocess runs detached with stdout/stderr going to
        DEVNULL to avoid pipe buffer deadlocks.

        Args:
            cmd: The command to execute.
            correlation_id: Correlation ID for logging.

        Returns:
            RunTriggerResult with subprocess details.
        """
        logger.debug(
            "Executing ADW command",
            extra={
                "correlation_id": correlation_id,
                "command": cmd,
                "cwd": str(self._project_dir),
            },
        )

        try:
            # Start the subprocess in background with output discarded
            # We redirect to DEVNULL to avoid pipe buffer deadlock:
            # if we used PIPE but didn't drain it, the child would block
            # once the ~64KB buffer fills, causing the run to hang
            process = await asyncio.to_thread(
                subprocess.Popen,
                cmd,
                cwd=self._project_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                # Detach from parent's process group so it continues
                # running even if the webhook server restarts
                start_new_session=True,
            )

            # Note: We can't capture the run_id from output anymore
            # since we redirect to DEVNULL. The run_id can be looked up
            # via `adw list-runs` or the ADW logs directory if needed.

            return RunTriggerResult(
                success=True,
                run_id=None,  # Not available without reading output
                process_id=process.pid,
            )

        except FileNotFoundError:
            return RunTriggerResult(
                success=False,
                error=f"ADW command not found: {cmd[0]}",
            )
        except OSError as e:
            return RunTriggerResult(
                success=False,
                error=f"Failed to start subprocess: {e}",
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
