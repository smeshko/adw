"""Integration tests for the non-worktree branch switch at run start.

The orchestrator is built through ``create_orchestrator``, so the branch
switch runs exactly as ``adw run --no-worktree`` runs it.
"""

import json
import subprocess
from pathlib import Path

import pytest

from adw.cli.bootstrap import create_orchestrator
from adw.core.context_manager import ContextManager
from adw.core.orchestrator import Orchestrator
from adw.exceptions import HookError, LLMError
from adw.executors.mock import MockExecutor

PROJECT_YAML = """\
name: branch-test
language: python
worktree:
  enabled: false
"""

# Records the branch a phase starts on
BRANCH_PROBE = 'git branch --show-current > "$ADW_ARTIFACTS_DIR/branch.txt"\n'

# Resumed runs stop after build: later phases would open a PR
DISABLED_PHASES = ("validate", "document", "ship")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def branch_project(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a committed ADW project whose plan and build pre-hooks record the branch.

    HOME (``home/``) and the run directories live inside the repository, so
    they are gitignored: run start refuses to switch branches on a dirty tree.
    """
    commands_dir = git_repo / ".adw" / "commands"
    for phase in ("plan", "build"):
        (commands_dir / phase).mkdir(parents=True)
        (commands_dir / phase / "pre.sh").write_text(BRANCH_PROBE)
    for phase in DISABLED_PHASES:
        (commands_dir / phase).mkdir(parents=True)
        (commands_dir / phase / "config.yaml").write_text("enabled: false\n")
    (git_repo / ".adw" / "project.yaml").write_text(PROJECT_YAML)
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


def _failed_plan_run(repo: Path) -> tuple[Orchestrator, str, str]:
    """Fail a non-worktree plan run, then check out the initial branch again.

    Returns:
        The orchestrator (its executor succeeds from now on), the run ID, and
        the initial branch.
    """
    initial_branch = _git(repo, "branch", "--show-current")
    orchestrator = create_orchestrator(with_progress=False)
    executor = orchestrator._phase_runner.executor  # type: ignore[attr-defined]
    assert isinstance(executor, MockExecutor)
    executor.configure_failures(
        [LLMError(code="LLM_ERROR", message="boom", recoverable=False), None]
    )
    with pytest.raises(LLMError):
        orchestrator.run_single_phase("plan", "Add login", use_worktree=False)
    (run_dir,) = (repo / ".adw" / "runs").iterdir()
    assert _git(repo, "branch", "--show-current") == "feature/add-login"
    _git(repo, "checkout", initial_branch)
    return orchestrator, run_dir.name, initial_branch


def test_resume_switches_back_to_run_branch(branch_project: Path) -> None:
    """Resuming from another branch puts the run back on its own branch."""
    orchestrator, run_id, _ = _failed_plan_run(branch_project)

    context = orchestrator.resume(run_id)

    assert context.status == "completed"
    assert _git(branch_project, "branch", "--show-current") == "feature/add-login"


def test_resume_on_dirty_tree_leaves_status_unchanged(branch_project: Path) -> None:
    """A resume that cannot switch branches fails before touching the run."""
    orchestrator, run_id, initial_branch = _failed_plan_run(branch_project)
    (branch_project / "README.md").write_text("modified")

    with pytest.raises(HookError) as exc_info:
        orchestrator.resume(run_id)

    assert exc_info.value.code == "GIT_UNCOMMITTED_CHANGES"
    assert _git(branch_project, "branch", "--show-current") == initial_branch
    runs_dir = branch_project / ".adw" / "runs"
    assert ContextManager(runs_dir).load(run_id).status == "failed"


def test_continue_from_run_switches_to_run_branch(branch_project: Path) -> None:
    """--from-run continues on the source run's branch."""
    initial_branch = _git(branch_project, "branch", "--show-current")
    orchestrator = create_orchestrator(with_progress=False)
    source = orchestrator.run_single_phase("plan", "Add login", use_worktree=False)
    _git(branch_project, "checkout", initial_branch)

    orchestrator.continue_from_run("build", source.run_id)

    run_dir = branch_project / ".adw" / "runs" / source.run_id
    branch_file = run_dir / "artifacts" / "build" / "branch.txt"
    assert branch_file.read_text().strip() == "feature/add-login"


def test_resume_backfills_branch_name(branch_project: Path) -> None:
    """A run saved without branch_name gets it derived and recorded on resume."""
    orchestrator, run_id, _ = _failed_plan_run(branch_project)
    context_file = branch_project / ".adw" / "runs" / run_id / "context.json"
    saved = json.loads(context_file.read_text())
    saved["branch_name"] = None
    context_file.write_text(json.dumps(saved))
    _git(branch_project, "branch", "-D", "feature/add-login")

    orchestrator.resume(run_id)

    assert json.loads(context_file.read_text())["branch_name"] == "feature/add-login"
    assert _git(branch_project, "branch", "--show-current") == "feature/add-login"
