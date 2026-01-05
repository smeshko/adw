"""Hook runner for executing shell scripts.

This module provides the HookRunner class for executing pre-hook and
post-hook shell scripts with timeout support and output capture.

Timeout Hierarchy:
    1. timeout parameter passed to run_hook() - highest priority
    2. config.timeout_seconds from HookConfig
    3. DEFAULT_HOOK_TIMEOUT constant - fallback default
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from adw.exceptions import HookError
from adw.hooks.environment import build_hook_environment
from adw.models import HookConfig, HookResult, RunContext

if TYPE_CHECKING:
    from adw.models.worktree import PortAllocation

logger = logging.getLogger(__name__)

# Default timeout for hook execution in seconds (1 minute)
DEFAULT_HOOK_TIMEOUT = 60


class HookRunner:
    """Executes shell hook scripts with timeout and output capture.

    The HookRunner provides a synchronous interface for running pre-hook
    and post-hook shell scripts, while internally using asyncio for
    non-blocking subprocess execution with timeout support.

    Attributes:
        config: Hook configuration containing shell path and timeout settings

    Example:
        >>> runner = HookRunner(HookConfig(shell="/bin/bash", timeout_seconds=60))
        >>> result = runner.run_hook(
        ...     Path("/project/commands/plan/pre-hook.sh"),
        ...     context,
        ...     "plan",
        ... )
        >>> print(result.stdout)
        'Environment prepared successfully'
    """

    def __init__(self, config: HookConfig) -> None:
        """Initialize the HookRunner with configuration.

        Args:
            config: Hook configuration containing shell and timeout settings
        """
        self.config = config

    def _resolve_timeout(self, timeout: int | None) -> int:
        """Resolve timeout using 3-tier hierarchy.

        Resolution order:
            1. Explicit timeout parameter - highest priority
            2. config.timeout_seconds from HookConfig
            3. DEFAULT_HOOK_TIMEOUT constant - fallback default

        Args:
            timeout: Optional timeout override in seconds.

        Returns:
            Resolved timeout in seconds.
        """
        if timeout is not None:
            return timeout
        if self.config.timeout_seconds:
            return self.config.timeout_seconds
        return DEFAULT_HOOK_TIMEOUT

    def run_hook(
        self,
        hook_path: Path,
        context: RunContext,
        phase: str,
        *,
        hook_type: Literal["pre", "post"] = "pre",
        timeout: int | None = None,
        artifacts_dir: Path | None = None,
        context_file: Path | None = None,
        working_dir: Path | None = None,
        port_allocation: "PortAllocation | None" = None,
    ) -> HookResult:
        """Execute a hook script and capture its output.

        This method provides a synchronous interface while internally using
        asyncio for non-blocking execution with timeout support.

        Args:
            hook_path: Path to the hook script file
            context: Current run context for environment variables
            phase: The current phase name (e.g., "plan", "build")
            hook_type: Type of hook ("pre" or "post")
            timeout: Optional timeout override in seconds (uses config default if None)
            artifacts_dir: Optional path to artifacts directory for ADW_ARTIFACTS_DIR
            context_file: Optional path to context file for ADW_CONTEXT_FILE
            working_dir: Working directory for hook execution (defaults to project root)
            port_allocation: Optional port allocation for ADW_BACKEND_PORT/ADW_FRONTEND_PORT

        Returns:
            HookResult with captured stdout, stderr, exit code, and timing

        Raises:
            HookError: If the hook fails (non-zero exit) or times out
        """
        return asyncio.run(
            self._execute_hook(
                hook_path=hook_path,
                context=context,
                phase=phase,
                hook_type=hook_type,
                timeout=timeout,
                artifacts_dir=artifacts_dir,
                context_file=context_file,
                working_dir=working_dir,
                port_allocation=port_allocation,
            )
        )

    async def _execute_hook(
        self,
        hook_path: Path,
        context: RunContext,
        phase: str,
        hook_type: Literal["pre", "post"],
        timeout: int | None,
        artifacts_dir: Path | None,
        context_file: Path | None,
        working_dir: Path | None,
        port_allocation: "PortAllocation | None",
    ) -> HookResult:
        """Internal async implementation of hook execution.

        Args:
            hook_path: Path to the hook script file
            context: Current run context
            phase: Current phase name
            hook_type: Type of hook
            timeout: Timeout in seconds (None uses config default)
            artifacts_dir: Optional artifacts directory path
            context_file: Optional context file path
            working_dir: Working directory (defaults to current directory)
            port_allocation: Optional port allocation for environment variables

        Returns:
            HookResult on successful execution

        Raises:
            HookError: On execution failure or timeout
        """
        # Resolve timeout using 3-tier hierarchy
        effective_timeout = self._resolve_timeout(timeout)

        # Build environment variables
        env = build_hook_environment(
            context,
            phase,
            artifacts_dir=artifacts_dir,
            context_file=context_file,
            port_allocation=port_allocation,
        )

        # Use provided working directory or default to current directory
        cwd = working_dir if working_dir is not None else Path.cwd()

        start_time = time.monotonic()

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            self.config.shell,
            str(hook_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd,
        )

        try:
            # Wait for completion with timeout
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=effective_timeout,
            )
        except TimeoutError:
            # Kill the process on timeout
            process.kill()
            await process.wait()

            duration_ms = int((time.monotonic() - start_time) * 1000)

            logger.warning(
                "Hook execution timed out",
                extra={
                    "hook_path": str(hook_path),
                    "hook_type": hook_type,
                    "phase": phase,
                    "timeout": effective_timeout,
                    "duration_ms": duration_ms,
                },
            )

            raise HookError(
                code="HOOK_TIMEOUT",
                message=f"Hook timed out after {effective_timeout}s",
                phase=phase,
                exit_code=None,
                stdout="",
                stderr="",
                duration_ms=duration_ms,
                suggestion=f"Increase timeout or optimize {hook_type}-hook script",
                recoverable=False,
            ) from None

        duration_ms = int((time.monotonic() - start_time) * 1000)
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = process.returncode or 0

        # Check for non-zero exit code
        if exit_code != 0:
            raise HookError(
                code="HOOK_FAILED",
                message=f"Hook script exited with code {exit_code}",
                phase=phase,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                suggestion=f"Check {hook_type}-hook script at {hook_path}",
                recoverable=False,
            )

        return HookResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
            hook_type=hook_type,
        )


def find_hook(command_dir: Path, hook_type: Literal["pre", "post"]) -> Path | None:
    """Find a hook script in the command directory.

    Searches for hook scripts with or without .sh extension.
    Returns None if no hook is found (which is not an error).

    Args:
        command_dir: Directory to search for hooks
        hook_type: Type of hook to find ("pre" or "post")

    Returns:
        Path to the hook script if found, None otherwise

    Example:
        >>> hook = find_hook(Path("/project/commands/plan"), "pre")
        >>> if hook:
        ...     runner.run_hook(hook, context, "plan")
    """
    # Check with .sh extension first, then without
    for ext in [".sh", ""]:
        hook_path = command_dir / f"{hook_type}-hook{ext}"
        if hook_path.exists() and hook_path.is_file():
            return hook_path

    return None
