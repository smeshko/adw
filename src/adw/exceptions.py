"""ADW exception hierarchy.

Every ADW error carries a code, a message, an optional suggestion and a
recoverable flag, which the CLI renders as an error panel.
"""


class ADWError(Exception):
    """Base exception for all ADW errors.

    Attributes:
        code: A unique error code (e.g., "CONFIG_NOT_FOUND").
        message: A human-readable error message.
        suggestion: An optional actionable suggestion for resolution.
        recoverable: Whether the operation can be retried.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize an ADWError.

        Args:
            code: Unique error code (e.g., "HOOK_FAILED").
            message: Human-readable error message.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried.
        """
        self.code = code
        self.message = message
        self.suggestion = suggestion
        self.recoverable = recoverable
        super().__init__(self.message)

    def __str__(self) -> str:
        """Format error for user-friendly display.

        Returns:
            Formatted error string suitable for Rich Panel display.
        """
        parts = [f"[{self.code}] {self.message}"]
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return "\n".join(parts)


class ConfigError(ADWError):
    """Exception for configuration-related errors.

    Used for issues with configuration files, missing settings,
    or invalid configuration values.

    Common error codes:
    - CONFIG_NOT_FOUND: Configuration file doesn't exist
    - INVALID_CONFIG: Configuration file has invalid content
    """


class HookError(ADWError):
    """Exception for hook script execution failures.

    Used when pre-hooks or post-hooks fail during phase execution.
    Includes additional context about the hook execution.

    Common error codes:
    - HOOK_FAILED: Hook script exited with non-zero status
    - HOOK_TIMEOUT: Hook script exceeded timeout
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        phase: str,
        exit_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
        duration_ms: int | None = None,
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize a HookError.

        Args:
            code: Unique error code (e.g., "HOOK_FAILED").
            message: Human-readable error message.
            phase: The phase where the hook failed (e.g., "build").
            exit_code: The exit code of the hook script, if available.
            stdout: Captured stdout from the hook execution.
            stderr: Captured stderr from the hook execution.
            duration_ms: Execution duration in milliseconds (for debugging).
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried (default False).
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )
        self.phase = phase
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms


class LLMError(ADWError):
    """Exception for LLM-related errors.

    Used for issues with Claude Code or other LLM interactions.
    """


class StateError(ADWError):
    """Exception for state persistence and loading errors.

    Used for issues with run state, context files, and snapshots.

    Common error codes:
    - CONTEXT_CORRUPTED: State file is corrupted or invalid
    - SNAPSHOT_FAILED: Failed to create or load state snapshot
    - RUN_NOT_FOUND: Specified run ID doesn't exist
    """


class WorktreeError(ADWError):
    """Exception for worktree operation failures.

    Used when git worktree creation, removal, or management fails, and when
    a run cannot get ports or a concurrent-run slot.

    Common error codes:
    - BRANCH_EXISTS: The target branch already exists
    - WORKTREE_PATH_EXISTS: The worktree directory already exists
    - WORKTREE_NOT_FOUND: The worktree doesn't exist
    - WORKTREE_HAS_CHANGES: Worktree has uncommitted changes
    - PORT_ALLOCATION_FAILED: No free port slot after the allowed attempts
    - MAX_CONCURRENT_REACHED: The concurrent-run limit is reached
    """


class TaskError(ADWError):
    """Exception for task management errors.

    Used when interactions with external task management systems fail,
    such as fetching task info, updating status, or resolving task IDs.

    Common error codes:
    - TASK_NOT_FOUND: Requested task doesn't exist
    - TASK_FETCH_FAILED: Failed to fetch task information
    - TASK_UPDATE_FAILED: Failed to update task status
    - NO_TASK_MANAGER: No task manager is configured
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        task_id: str | None = None,
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize a TaskError.

        Args:
            code: Unique error code (e.g., "TASK_NOT_FOUND").
            message: Human-readable error message.
            task_id: The task ID related to the error, if applicable.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried (default False).
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )
        self.task_id = task_id


class SecurityError(ADWError):
    """Exception for security-related blocking.

    Used when a dangerous command or file access is blocked by the
    security interceptor. Includes rich context for user feedback.

    Common error codes:
    - DANGEROUS_COMMAND_BLOCKED: A shell command matched a blocked pattern
    - DANGEROUS_FILE_ACCESS: A file access matched a blocked pattern
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        pattern_matched: str | None = None,
        tool_name: str | None = None,
        alternatives: list[str] | None = None,
        override_instruction: str | None = None,
        severity: str = "warning",
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
        """Initialize a SecurityError.

        Args:
            code: Unique error code (e.g., "DANGEROUS_COMMAND_BLOCKED").
            message: Human-readable error message.
            pattern_matched: The regex pattern that triggered the block.
            tool_name: The tool that was blocked (e.g., "Bash", "Write").
            alternatives: List of safe alternative commands or approaches.
            override_instruction: How to bypass the block if needed.
            severity: Severity level ("critical", "warning", "info").
            suggestion: Optional actionable next step (inherited from ADWError).
            recoverable: Whether the operation can be retried (default False).
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )
        self.pattern_matched = pattern_matched
        self.tool_name = tool_name
        self.alternatives = alternatives if alternatives is not None else []
        self.override_instruction = override_instruction
        self.severity = severity

    def __str__(self) -> str:
        """Format error for user-friendly display.

        Returns:
            Formatted error string with all security context.
        """
        parts = [f"[{self.code}] {self.message}"]

        if self.alternatives:
            parts.append("Alternatives:")
            for alt in self.alternatives:
                parts.append(f"  - {alt}")

        if self.override_instruction:
            parts.append(f"Override: {self.override_instruction}")

        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")

        return "\n".join(parts)
