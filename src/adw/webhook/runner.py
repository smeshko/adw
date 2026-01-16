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

        except Exception as e:
            logger.exception(
                "Exception while triggering ADW run",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
            )
            return RunTriggerResult(
                success=False,
                error=f"Exception: {e}",
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
            phases: Optional phases to run.

        Returns:
            Command as list of strings for subprocess.
        """
        cmd = [self._adw_command, "run"]

        # Add phase flags if specified
        if phases:
            # Multiple phases means we run them all
            # For single phase, use --phase flag
            if len(phases) == 1:
                cmd.extend(["--phase", phases[0]])
            # For multiple phases, run full pipeline
            # (ADW will run all phases anyway)

        # Add the feature request (quoted for shell safety)
        cmd.append(feature_request)

        return cmd

    async def _run_subprocess(
        self,
        cmd: list[str],
        correlation_id: str,
    ) -> RunTriggerResult:
        """Run the ADW command as a subprocess.

        Launches ADW in the background and captures initial output
        to extract the run ID.

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
            # Start the subprocess - use Popen for background execution
            # We use asyncio.to_thread to avoid blocking the event loop
            process = await asyncio.to_thread(
                subprocess.Popen,
                cmd,
                cwd=self._project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Try to read initial output to get run ID
            # We read a few lines without blocking indefinitely
            run_id: str | None = None

            try:
                # Set a short timeout to get initial output
                # without blocking the webhook response
                import select

                if process.stdout:
                    # Use select for non-blocking read on Unix
                    # This may not work on Windows, so wrap in try/except
                    readable, _, _ = select.select([process.stdout], [], [], 1.0)
                    if readable:
                        line = process.stdout.readline()
                        # Look for run ID in output (format: "Run ID: 01HQXK...")
                        if "Run ID:" in line or "run_id" in line.lower():
                            # Extract run ID - it's a ULID (26 chars)
                            import re

                            match = re.search(r"([0-9A-Z]{26})", line)
                            if match:
                                run_id = match.group(1)

            except Exception:
                # Non-blocking read failed - that's okay
                # The process is still running in background
                pass

            return RunTriggerResult(
                success=True,
                run_id=run_id,
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


def trigger_from_params(
    params: RunParams,
    project_dir: Path | str | None = None,
) -> RunTriggerResult:
    """Trigger an ADW run from extracted RunParams.

    Convenience function to trigger a run using the RunParams model
    extracted from a webhook event.

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
