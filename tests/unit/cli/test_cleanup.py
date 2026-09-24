"""Tests for `adw cleanup`."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from adw.cli.app import app
from adw.models.context import RunContext

RUN_ID = "01HQTEST123456789012345678"
BRANCH = f"adw/{RUN_ID}"


def _write_context(project: Path) -> None:
    run_dir = project / ".adw" / "runs" / RUN_ID
    run_dir.mkdir(parents=True)
    context = RunContext(
        run_id=RUN_ID,
        feature_description="Add auth",
        current_phase="build",
        started_at=datetime.now(UTC),
        use_worktree=True,
        # The worktree is already gone
        worktree_path=project / "trees" / RUN_ID,
        branch_name=BRANCH,
    )
    (run_dir / "context.json").write_text(context.model_dump_json(indent=2))


def test_cleanup_deletes_branch_when_worktree_is_gone(git_repo: Path) -> None:
    subprocess.run(
        ["git", "branch", BRANCH], cwd=git_repo, check=True, capture_output=True
    )
    _write_context(git_repo)

    result = CliRunner().invoke(app, ["cleanup", RUN_ID, "--delete-branch", "--force"])

    assert result.exit_code == 0, result.output
    assert "Branch deleted" in result.output
    branches = subprocess.run(
        ["git", "branch", "--list", BRANCH],
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert branches.stdout.strip() == ""
