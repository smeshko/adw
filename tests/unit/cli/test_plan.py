"""Tests for the `adw plan` command group."""

import re
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from adw.cli.app import app

FIXTURES = Path(__file__).parents[2] / "fixtures" / "plans"
GOLDEN_SLUG = "add-a-dry-run-flag-to-the-importer"

# The only differences tolerated between the skill scripts' tree and ADW's.
NORMALISATIONS: list[tuple[re.Pattern[str], str]] = [
    # The creation date is today's date on both sides.
    (re.compile(r"^Created: \d{4}-\d{2}-\d{2}$", re.MULTILINE), "Created: <date>"),
]


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


def _plan(runner: CliRunner, *args: str) -> Result:
    return runner.invoke(app, ["plan", *args])


def normalise(text: str) -> str:
    """Apply every entry of NORMALISATIONS to one file's text."""
    for pattern, replacement in NORMALISATIONS:
        text = pattern.sub(replacement, text)
    return text


def _tree(directory: Path) -> dict[str, str]:
    """Map each file under directory, by relative path, to its normalised text."""
    return {
        path.relative_to(directory).as_posix(): normalise(
            path.read_text(encoding="utf-8")
        )
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


class TestAuthoring:
    """adw plan init, add-task and add-final."""

    def test_cli_scaffold_matches_skill_golden_tree(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        root = str(tmp_path)
        steps = [
            (
                ["init", "--root", root, "--risk", "medium"]
                + ["--title", "Add a --dry-run flag to the importer"],
                f"slug:    {GOLDEN_SLUG}",
            ),
            (
                ["add-task", GOLDEN_SLUG, "--root", root, "--type", "impl"]
                + ["--title", "Parse the --dry-run flag"],
                "TASK-001",
            ),
            (
                ["add-task", GOLDEN_SLUG, "--root", root, "--type", "checklist"]
                + ["--title", "Document the flag in the README"]
                + ["--depends", "TASK-001"],
                "TASK-002",
            ),
            (["add-final", GOLDEN_SLUG, "--root", root], "TASK-003"),
        ]
        for args, expected_line in steps:
            result = _plan(runner, *args)
            assert result.exit_code == 0, result.output
            assert expected_line in result.stdout.splitlines()

        written = tmp_path / "docs" / "artifacts" / "plans" / GOLDEN_SLUG
        assert _tree(written) == _tree(FIXTURES / "golden" / GOLDEN_SLUG)

    def test_init_twice_exits_1_with_the_error_on_stderr(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        args = ["init", "--root", str(tmp_path), "--title", "Twice", "--risk", "small"]
        assert _plan(runner, *args).exit_code == 0

        result = _plan(runner, *args)

        assert result.exit_code == 1
        assert result.stderr.startswith("error: plan directory already exists: ")
        assert result.stdout == ""

    def test_default_root_is_the_git_toplevel(
        self,
        runner: CliRunner,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        subdir = git_repo / "src" / "pkg"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        result = _plan(runner, "init", "--title", "From a subdir", "--risk", "tiny")

        assert result.exit_code == 0, result.output
        assert (git_repo / "docs/artifacts/plans/from-a-subdir/PLAN.md").is_file()
        assert not (subdir / "docs").exists()

    def test_default_root_outside_git_is_the_cwd(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Stop git from finding a repo above tmp_path.
        monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

        result = _plan(runner, "init", "--title", "No repo", "--risk", "tiny")

        assert result.exit_code == 0, result.output
        assert (tmp_path / "docs/artifacts/plans/no-repo/PLAN.md").is_file()
