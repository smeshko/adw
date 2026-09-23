"""Integration tests for the non-worktree branch switch at run start.

The orchestrator is built through ``create_orchestrator``, so the branch
switch runs exactly as ``adw run --no-worktree`` runs it.
"""

import json
import subprocess
from pathlib import Path

import pytest

from adw.cli.bootstrap import create_orchestrator
from adw.exceptions import HookError

PROJECT_YAML = """\
name: branch-test
language: python
worktree:
  enabled: false
"""

# Records the branch the plan phase starts on
BRANCH_PROBE = 'git branch --show-current > "$ADW_ARTIFACTS_DIR/branch.txt"\n'


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def branch_project(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a committed ADW project with a plan pre-hook that records the branch.

    HOME (``home/``) and the run directories live inside the repository, so
    they are gitignored: run start refuses to switch branches on a dirty tree.
    """
    commands_dir = git_repo / ".adw" / "commands" / "plan"
    commands_dir.mkdir(parents=True)
    (git_repo / ".adw" / "project.yaml").write_text(PROJECT_YAML)
    (commands_dir / "pre.sh").write_text(BRANCH_PROBE)
    (git_repo / ".gitignore").write_text("home/\n.adw/runs/\n")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-m", "Add ADW config")
    monkeypatch.chdir(git_repo)
    return git_repo


def test_non_worktree_run_switches_branch_before_plan(branch_project: Path) -> None:
    """A non-worktree run is on its feature branch before the plan phase runs."""
    orchestrator = create_orchestrator(with_progress=False)

    context = orchestrator.run_single_phase("plan", "Add login", use_worktree=False)

    run_dir = branch_project / ".adw" / "runs" / context.run_id
    branch_file = run_dir / "artifacts" / "plan" / "branch.txt"
    assert branch_file.read_text().strip() == "feature/add-login"
    assert _git(branch_project, "branch", "--show-current") == "feature/add-login"
    saved = json.loads((run_dir / "context.json").read_text())
    assert saved["branch_name"] == "feature/add-login"


def test_non_worktree_run_outside_git_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-worktree run outside git fails before creating a run."""
    (tmp_path / ".adw").mkdir()
    (tmp_path / ".adw" / "project.yaml").write_text(PROJECT_YAML)
    monkeypatch.chdir(tmp_path)
    orchestrator = create_orchestrator(with_progress=False)

    with pytest.raises(HookError) as exc_info:
        orchestrator.run_single_phase("plan", "Add login", use_worktree=False)

    assert exc_info.value.code == "GIT_BRANCH_CHECK_FAILED"
    runs_dir = tmp_path / ".adw" / "runs"
    assert not runs_dir.exists() or not any(runs_dir.iterdir())
