"""Tests for LLMExecutor Protocol definition."""

from typing import Protocol, get_type_hints

from adw.executors import LLMExecutor
from adw.models.llm import LLMResult


def test_llm_executor_is_protocol() -> None:
    """LLMExecutor is a typing.Protocol."""
    assert issubclass(type(LLMExecutor), type(Protocol))


def test_llm_executor_is_runtime_checkable() -> None:
    """LLMExecutor can be used with isinstance()."""

    # Create a minimal class that implements the protocol
    class MinimalExecutor:
        def execute(
            self,
            prompt: str,
            *,
            timeout: int | None = None,
        ) -> LLMResult:
            return LLMResult(success=True, content="test")

    executor = MinimalExecutor()
    assert isinstance(executor, LLMExecutor)


def test_llm_executor_rejects_non_conforming() -> None:
    """LLMExecutor rejects classes that don't implement execute()."""

    class BadExecutor:
        pass

    executor = BadExecutor()
    assert not isinstance(executor, LLMExecutor)


def test_llm_executor_has_execute_method() -> None:
    """LLMExecutor Protocol defines execute() method."""
    assert hasattr(LLMExecutor, "execute")


def test_llm_executor_execute_has_correct_signature() -> None:
    """LLMExecutor.execute() has correct parameter types."""
    hints = get_type_hints(LLMExecutor.execute)

    # Check return type is LLMResult
    assert hints.get("return") == LLMResult

    # Check prompt is str
    assert hints.get("prompt") is str

    # Check timeout is int | None
    assert hints.get("timeout") == (int | None)

    # Check model is str | None
    assert hints.get("model") == (str | None)
