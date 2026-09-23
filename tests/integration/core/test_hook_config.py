"""Integration test for project.yaml hook settings reaching the hook runner.

The orchestrator is built through ``create_orchestrator`` in an isolated git
repository, so ``hooks.timeout_seconds`` travels from ``project.yaml`` to the
post-hook exactly as it does in production.
"""

import subprocess
import time
from pathlib import Path

import pytest

from adw.cli.bootstrap import create_orchestrator
from adw.exceptions import HookError

PROJECT_YAML = """\
name: hook-config-test
language: python
worktree:
  enabled: false
hooks:
  timeout_seconds: 1
"""


@pytest.fixture
def slow_hook_project(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a committed ADW project whose plan post-hook sleeps for 10 s.

    HOME (``home/``) and the run directories live inside the repository, so
    they are gitignored to keep the tree clean.
    """
    commands_dir = git_repo / ".adw" / "commands" / "plan"
    commands_dir.mkdir(parents=True)
    (git_repo / ".adw" / "project.yaml").write_text(PROJECT_YAML)
    (commands_dir / "post.sh").write_text("exec sleep 10\n")
    (git_repo / ".gitignore").write_text("home/\n.adw/runs/\n")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add ADW config"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    monkeypatch.chdir(git_repo)
    return git_repo


def test_project_hook_timeout_stops_post_hook(slow_hook_project: Path) -> None:
    """hooks.timeout_seconds from project.yaml stops a slow post-hook (B10)."""
    orchestrator = create_orchestrator(with_progress=False)

    start = time.monotonic()
    with pytest.raises(HookError) as exc_info:
        orchestrator.run_single_phase("plan", "timeout check", use_worktree=False)
    elapsed = time.monotonic() - start

    assert exc_info.value.code == "HOOK_TIMEOUT"
    assert elapsed < 5
