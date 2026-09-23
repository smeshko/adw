"""Integration tests for failing and retrying a phase.

These tests build the real orchestrator through ``create_orchestrator`` in an
isolated git repository, so ``llm.retry`` travels from ``project.yaml`` to the
orchestrator's retry loop exactly as it does in production.
"""

import subprocess
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from adw.cli.bootstrap import create_orchestrator
from adw.exceptions import LLMError
from adw.executors.mock import MockExecutor

PROJECT_YAML = """\
name: retry-test
language: python
test_command: "true"
worktree:
  enabled: false
llm:
  retry:
    max_retries: 4
    base_delay_seconds: 0.5
    multiplier: 3
    max_delay_seconds: 1.0
"""


def _recoverable_error() -> LLMError:
    return LLMError(
        code="CLAUDE_EXIT_NONZERO",
        message="Claude Code exited with code 1",
        recoverable=True,
    )


@pytest.fixture
def retry_project(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[MagicMock]:
    """Set up a committed ADW project with a non-default retry config.

    HOME (``home/``) and the run directories live inside the repository, so
    they are gitignored: ``plan/pre.sh`` refuses to run on a dirty tree.

    Yields:
        The patched orchestrator ``time.sleep``.
    """
    (git_repo / ".adw").mkdir()
    (git_repo / ".adw" / "project.yaml").write_text(PROJECT_YAML)
    (git_repo / ".gitignore").write_text("home/\nbin/\n.adw/runs/\n")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add ADW config"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    monkeypatch.chdir(git_repo)
    with patch("adw.core.orchestrator.time.sleep") as mock_sleep:
        yield mock_sleep


def test_mock_executor_fails_twice_then_succeeds(retry_project: MagicMock) -> None:
    """Two recoverable failures are retried with the project's backoff."""
    orchestrator = create_orchestrator(with_progress=False)
    executor = orchestrator._phase_runner.executor  # type: ignore[attr-defined]
    assert isinstance(executor, MockExecutor)
    executor.configure_failures([_recoverable_error(), _recoverable_error(), None])

    context = orchestrator.run_single_phase("plan", "noop feature", use_worktree=False)

    assert context.status == "completed"
    assert executor.call_count == 3
    assert retry_project.call_args_list == [call(0.5), call(1.0)]
