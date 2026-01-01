"""ADW executors module - LLM abstraction layer.

This package provides the LLM execution abstraction:
- LLMExecutor: Protocol defining the executor interface
- ClaudeCodeExecutor: Production executor using Claude Code CLI
- MockExecutor: Testing implementation with configurable responses
- LLMResult: Result model for execution outcomes
- ToolCall: Model for tracking tool invocations
"""

from adw.executors.base import LLMExecutor
from adw.executors.claude_code import ClaudeCodeExecutor
from adw.executors.mock import MockExecutor
from adw.executors.retry import RetryExecutor
from adw.models.llm import LLMResult, ToolCall

__all__: list[str] = [
    "ClaudeCodeExecutor",
    "LLMExecutor",
    "LLMResult",
    "MockExecutor",
    "RetryExecutor",
    "ToolCall",
]
