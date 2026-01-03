"""Tool call logger for security audit trail.

This module provides the ToolLogger class for logging all LLM tool calls
to a JSONL file for audit and debugging purposes.
"""

from pathlib import Path
from typing import Any

from adw.models.security import ToolCallLog


class ToolLogger:
    """Logger for LLM tool calls.
    
    Writes tool call entries to a JSONL file in the run directory.
    Each entry is a single JSON object on its own line, allowing
    for append-only writes and easy parsing.
    
    Attributes:
        run_dir: Path to the run directory.
        log_file: Path to the tools.jsonl file.
        
    Example:
        >>> logger = ToolLogger(Path(".adw/runs/abc123"))
        >>> logger.log_tool_call(ToolCallLog(
        ...     tool_name="Bash",
        ...     arguments={"command": "ls"},
        ...     result_summary="success",
        ...     duration_ms=150,
        ... ))
    """
    
    def __init__(self, run_dir: Path) -> None:
        """Initialize the tool logger.
        
        Args:
            run_dir: Path to the run directory where logs will be stored.
        """
        self.run_dir = run_dir
        self.log_file = run_dir / "tools.jsonl"
        
        # Ensure run directory exists
        self.run_dir.mkdir(parents=True, exist_ok=True)
    
    def log_tool_call(self, entry: ToolCallLog) -> None:
        """Log a tool call entry.
        
        Appends the entry as a JSON line to the tools.jsonl file.
        
        Args:
            entry: The tool call log entry to write.
        """
        # Serialize to JSON and append to file
        json_line = entry.model_dump_json()
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json_line)
            f.write("\n")
    
    def log(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result_summary: str,
        duration_ms: int,
        *,
        blocked: bool = False,
        block_reason: str | None = None,
    ) -> None:
        """Convenience method to log a tool call.
        
        Creates a ToolCallLog entry and writes it to the log file.
        
        Args:
            tool_name: Name of the tool that was called.
            arguments: Arguments passed to the tool.
            result_summary: Brief summary of the result.
            duration_ms: Duration of the call in milliseconds.
            blocked: Whether the call was blocked.
            block_reason: Reason for blocking, if applicable.
        """
        entry = ToolCallLog(
            tool_name=tool_name,
            arguments=arguments,
            result_summary=result_summary,
            duration_ms=duration_ms,
            blocked=blocked,
            block_reason=block_reason,
        )
        self.log_tool_call(entry)
    
    def get_log_path(self) -> Path:
        """Get the path to the log file.
        
        Returns:
            Path to the tools.jsonl file.
        """
        return self.log_file
    
    def read_entries(self) -> list[ToolCallLog]:
        """Read all log entries from the file.
        
        Returns:
            List of ToolCallLog entries.
        """
        if not self.log_file.exists():
            return []
        
        entries = []
        with open(self.log_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = ToolCallLog.model_validate_json(line)
                    entries.append(entry)
        
        return entries
