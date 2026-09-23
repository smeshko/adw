"""Shared fixtures for dashboard unit tests."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every dashboard test from its own tmp_path.

    The dashboard reads and writes cwd's .adw/ and git repo: from the
    checkout, it would act on the checkout's real runs.
    """
    monkeypatch.chdir(tmp_path)
