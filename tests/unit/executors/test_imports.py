"""Tests for executor package structure and imports."""


def test_can_import_llm_executor_protocol() -> None:
    """LLMExecutor protocol can be imported from executors."""
    from adw.executors import LLMExecutor

    assert LLMExecutor is not None


def test_can_import_mock_executor() -> None:
    """MockExecutor can be imported from executors."""
    from adw.executors import MockExecutor

    assert MockExecutor is not None


def test_can_import_llm_result() -> None:
    """LLMResult model can be imported from executors."""
    from adw.executors import LLMResult

    assert LLMResult is not None


def test_can_import_tool_call() -> None:
    """ToolCall model can be imported from executors."""
    from adw.executors import ToolCall

    assert ToolCall is not None
