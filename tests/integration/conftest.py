"""Shared fixtures for integration tests."""

import pytest

from adw.executors.claude_code import ClaudeCodeExecutor
from adw.models.config import LLMConfig


@pytest.fixture
def executor() -> ClaudeCodeExecutor:
    """Create executor with default config."""
    return ClaudeCodeExecutor(LLMConfig(path="claude"))
