"""CLI evidence capture for terminal output.

This module provides the CLICaptureStrategy class for executing CLI commands
and capturing their output during the Verify phase of evidence gathering.
"""

import subprocess
import time
from datetime import UTC, datetime

from adw.models.evidence import CommandConfig, CommandResult


class CLICaptureStrategy:
    """Strategy for capturing CLI terminal output as evidence.

    Executes commands and captures stdout, stderr, exit code, and timing
    information for evidence gathering during the Verify phase.

    Example:
        >>> strategy = CLICaptureStrategy()
        >>> result = strategy.execute_command("adw --version", timeout=30)
        >>> result.success
        True
        >>> result.stdout
        'adw version 1.0.0'
    """

    def execute_command(
        self,
        cmd: str,
        timeout: int,
        name: str | None = None,
    ) -> CommandResult:
        """Execute a command and capture its output.

        Runs the command using subprocess with shell=True, capturing
        stdout, stderr, exit code, and duration.

        Args:
            cmd: The shell command to execute
            timeout: Maximum execution time in seconds
            name: Optional config name for evidence file naming

        Returns:
            CommandResult with captured output and metadata

        Note:
            Timeout exceptions are handled gracefully and result in
            exit_code=-1 and success=False rather than raising.
        """
        start_time = time.monotonic()
        executed_at = datetime.now(UTC)

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = time.monotonic() - start_time

            return CommandResult(
                command=cmd,
                name=name,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                success=result.returncode == 0,
                executed_at=executed_at,
            )

        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start_time

            return CommandResult(
                command=cmd,
                name=name,
                exit_code=-1,
                stdout="",
                stderr="Command timed out",
                duration_seconds=duration,
                success=False,
                executed_at=executed_at,
            )

    def execute_command_config(self, config: CommandConfig) -> CommandResult:
        """Execute a command from a CommandConfig.

        Convenience method that extracts command and timeout from
        a CommandConfig instance.

        Args:
            config: Configuration for the command to execute

        Returns:
            CommandResult with captured output and metadata
        """
        return self.execute_command(config.cmd, config.timeout, config.name)
