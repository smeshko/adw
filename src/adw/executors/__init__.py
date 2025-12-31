"""ADW executors module - LLM abstraction layer.

This package provides the LLM execution abstraction:
- LLMExecutor: Protocol defining the executor interface
- MockExecutor: Testing implementation with configurable responses
- LLMResult: Result model for execution outcomes
- ToolCall: Model for tracking tool invocations
"""

from adw.executors.base import LLMExecutor
from adw.executors.mock import MockExecutor
from adw.models.llm import LLMResult, ToolCall

__all__: list[str] = [
    "LLMExecutor",
    "LLMResult",
    "MockExecutor",
    "ToolCall",
]
