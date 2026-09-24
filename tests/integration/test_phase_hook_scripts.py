"""Integration tests for the bundled build and document post-hook scripts.

Each script runs in a throwaway directory: the build post-hook once
auto-committed whatever was dirty in its cwd.
"""

import os
import subprocess
from pathlib import Path

import adw

COMMANDS_DIR = Path(adw.__file__).parent / "defaults" / "commands"


def _run_script(
    script: Path, cwd: Path, env_overrides: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(script)],
        cwd=cwd,
        env={**os.environ, **env_overrides},
        capture_output=True,
        text=True,
        check=False,
    )


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def test_build_post_hook_extracts_story_and_leaves_changes_uncommitted(
    git_repo: Path, tmp_path: Path
) -> None:
    """build/post.sh extracts the story output and commits nothing."""
    (git_repo / ".adw").mkdir()
    (git_repo / ".adw" / "project.yaml").write_text("name: demo\nlanguage: python\n")
    (git_repo / ".gitignore").write_text("home/\nartifacts/\n")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-m", "Add ADW config")
    commits_before = _git(git_repo, "log", "--oneline").count("\n")
    (git_repo / "src.py").write_text("print('hi')\n")
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    llm_output = (
        "Work done.\n"
        "# UPDATED STORY OUTPUT\n"
        "Story body line\n"
        "# END STORY OUTPUT\n"
        "Trailing text\n"
    )

    result = _run_script(
        COMMANDS_DIR / "build" / "post.sh",
        git_repo,
        {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_ARTIFACTS_DIR": str(artifacts_dir),
            "ADW_FEATURE": "Add login",
            "ADW_RUN_ID": "run-123",
            "ADW_PHASE": "build",
        },
    )

    assert result.returncode == 0, result.stderr
    assert (artifacts_dir / "build_output.md").read_text() == "Story body line\n"
    assert "src.py" in _git(git_repo, "status", "--porcelain")
    assert _git(git_repo, "log", "--oneline").count("\n") == commits_before


def test_document_post_hook_keeps_extension_pr_description(tmp_path: Path) -> None:
    """document/post.sh leaves the pr_description.md DocumentExtension stored."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "pr_description.md").write_text("from extension")
    llm_output = "Docs updated.\n\n## Summary\n\nShell-extracted body\n"

    result = _run_script(
        COMMANDS_DIR / "document" / "post.sh",
        tmp_path,
        {
            "ADW_LLM_OUTPUT": llm_output,
            "ADW_ARTIFACTS_DIR": str(artifacts_dir),
            "ADW_PHASE": "document",
        },
    )

    assert result.returncode == 0, result.stderr
    assert (artifacts_dir / "pr_description.md").read_text() == "from extension"
    assert (artifacts_dir / "document_output.md").exists()
