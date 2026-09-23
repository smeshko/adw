"""Shared fixtures for CLI unit tests."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every CLI test from its own tmp_path.

    CLI commands act on cwd's .adw/ and git repo: from the checkout, a command
    such as `adw resume` would resume the checkout's real runs and create
    branches and worktrees there.
    """
    monkeypatch.chdir(tmp_path)
