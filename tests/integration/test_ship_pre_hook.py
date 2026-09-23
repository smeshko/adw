"""Integration tests for the ship phase pre.sh hook.

The hook runs in an isolated git repository with a recording fake `gh` first
on PATH, so no real GitHub call is made.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import adw

if TYPE_CHECKING:
    from tests.conftest import FakeGh

PRE_HOOK = Path(adw.__file__).parent / "defaults" / "commands" / "ship" / "pre.sh"

PR_JSON = json.dumps(
    {
        "number": 5,
        "url": "https://github.com/o/r/pull/5",
        "state": "OPEN",
        "mergeable": "MERGEABLE",
        "title": "t",
    }
)

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="ship/pre.sh parses gh output with jq"
)


@pytest.fixture
def feature_repo(git_repo: Path, fake_gh: "FakeGh") -> Path:
    """Check out a feature branch and make the fake gh answer with an open PR."""
    subprocess.run(
        ["git", "checkout", "-b", "feature/x"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    fake_gh.reply(stdout=PR_JSON)
    return git_repo


def _run_pre_hook(
    repo: Path, artifacts_dir: Path, env_overrides: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "ADW_PR_URL"}
    env.update({"ADW_ARTIFACTS_DIR": str(artifacts_dir), **env_overrides})
    return subprocess.run(
        ["/bin/bash", str(PRE_HOOK)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _pr_view_refs(fake_gh: "FakeGh") -> list[str]:
    return [argv[2] for argv in fake_gh.calls() if argv[:2] == ["pr", "view"]]


def test_pre_hook_looks_up_pr_by_url(
    feature_repo: Path, fake_gh: "FakeGh", tmp_path_factory: pytest.TempPathFactory
) -> None:
    """With ADW_PR_URL set, the hook looks the run's PR up by its URL."""
    artifacts_dir = tmp_path_factory.mktemp("artifacts")

    result = _run_pre_hook(
        feature_repo,
        artifacts_dir,
        {"ADW_PR_URL": "https://github.com/o/r/pull/5"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert _pr_view_refs(fake_gh) == ["https://github.com/o/r/pull/5"]
    pre_hook_vars = json.loads((artifacts_dir / "pre_hook_vars.json").read_text())
    assert pre_hook_vars["pr_number"] == "5"


def test_pre_hook_falls_back_to_branch(
    feature_repo: Path, fake_gh: "FakeGh", tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Without ADW_PR_URL, the hook looks the PR up by the current branch."""
    artifacts_dir = tmp_path_factory.mktemp("artifacts")

    result = _run_pre_hook(feature_repo, artifacts_dir, {})

    assert result.returncode == 0, result.stdout + result.stderr
    assert _pr_view_refs(fake_gh) == ["feature/x"]
