"""Core run trigger logic for starting ADW runs.

Starts the runs requested by the dashboard's New Run form.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RunTriggerResult:
    """Result of triggering an ADW run.

    Attributes:
        success: Whether the run was successfully triggered.
        run_id: The ADW run ID if available.
        error: Error message if not successful.
        process_id: The subprocess PID if launched in background.
    """

    success: bool
    run_id: str | None = None
    error: str | None = None
    process_id: int | None = None


class RunTrigger:
    """Triggers ADW runs as background subprocesses.

    Used by the dashboard's New Run. Spawns ADW as a detached subprocess
    so the caller can return immediately.

    Attributes:
        _adw_command: The ADW CLI command to execute.
    """

    def __init__(self, adw_command: str = "adw") -> None:
        self._adw_command = adw_command

    def _build_command(
        self,
        feature_request: str,
        phases: list[str] | None,
    ) -> list[str]:
        """Build the ADW CLI command."""
        cmd = [self._adw_command, "run"]

        if phases:
            if len(phases) > 1:
                logger.warning(
                    "Multiple phases specified but CLI only supports single phase; "
                    "using first phase only",
                    extra={"requested_phases": phases, "selected_phase": phases[0]},
                )
            cmd.extend(["--phase", phases[0]])

        cmd.append(feature_request)
        return cmd

    async def start_run(
        self,
        project_path: str,
        feature: str,
        phases: list[str] | None = None,
    ) -> RunTriggerResult:
        """Start an ADW run as a background subprocess.

        Args:
            project_path: Directory to run ADW in.
            feature: The feature description to implement.
            phases: Optional list of phases to run.

        Returns:
            RunTriggerResult with success status and process details.
        """
        cwd = Path(project_path)
        cmd = self._build_command(feature, phases)

        logger.info(
            "Starting ADW run",
            extra={
                "command": cmd,
                "cwd": str(cwd),
                "feature": feature[:100],
            },
        )

        try:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            return RunTriggerResult(
                success=True,
                run_id=None,
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
