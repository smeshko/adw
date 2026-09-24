"""Tests for the `adw plan` command group."""

import re
import shutil
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from adw.cli.app import app
from adw.plans.state import mark_task_done

FIXTURES = Path(__file__).parents[2] / "fixtures" / "plans"
GOLDEN_SLUG = "add-a-dry-run-flag-to-the-importer"
PLAN_SLUG = "04.1-adw-plans-module"

# The only differences tolerated between the skill scripts' tree and ADW's.
NORMALISATIONS: list[tuple[re.Pattern[str], str]] = [
    # The creation date is today's date on both sides.
    (re.compile(r"^Created: \d{4}-\d{2}-\d{2}$", re.MULTILINE), "Created: <date>"),
    # Final validation marks the epic phase done with ADW's own command; the
    # skill's template names a script under the user's skills directory.
    (
        re.compile(
            re.escape("python3 ~/.claude/skills/create-epic/scripts/link_plan.py")
        ),
        "adw plan link",
    ),
]


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


def _plan(runner: CliRunner, *args: str) -> Result:
    return runner.invoke(app, ["plan", *args])


def _install_fixture_plan(root: Path) -> Path:
    """Copy this repo's own create-plan plan into root's plans dir."""
    destination = root / "docs" / "artifacts" / "plans" / PLAN_SLUG
    shutil.copytree(FIXTURES / PLAN_SLUG, destination)
    return destination


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


class TestReading:
    """adw plan list, tasks and show."""

    def test_list_prints_active_plans_and_skips_archived_ones(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        plans = tmp_path / "docs" / "artifacts" / "plans"
        for slug, text in [
            ("b-plan", "# Plan: Second plan\n\nStatus: ready\n"),
            ("a-plan", "# Plan: First plan\n\nRisk: small\n"),
            ("archive/2026-09-01-old", "# Plan: Old\n\nStatus: done\n"),
        ]:
            (plans / slug).mkdir(parents=True)
            (plans / slug / "PLAN.md").write_text(text)
        (plans / "notes").mkdir()
        (plans / "README.md").write_text("not a plan")

        result = _plan(runner, "list", "--root", str(tmp_path))

        assert result.exit_code == 0, result.output
        assert result.stdout == (
            "a-plan\tunknown\tFirst plan\nb-plan\tready\tSecond plan\n"
        )

    def test_tasks_prints_one_row_per_task(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _install_fixture_plan(tmp_path)

        result = _plan(runner, "tasks", PLAN_SLUG, "--root", str(tmp_path))

        assert result.exit_code == 0, result.output
        rows = [line.split("\t") for line in result.stdout.splitlines()]
        assert [row[:2] for row in rows] == [["TASK-001", "done"]] + [
            [f"TASK-00{n}", "pending"] for n in range(2, 8)
        ]
        assert rows[0] == [
            "TASK-001",
            "done",
            f"docs/artifacts/plans/{PLAN_SLUG}/tasks/"
            "TASK-001-bundle-the-plan-templates-and-port-plan-authoring.md",
            "Bundle the plan templates and port plan authoring",
        ]

    def test_show_prints_key_value_lines(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _install_fixture_plan(tmp_path)

        result = _plan(runner, "show", PLAN_SLUG, "--root", str(tmp_path))

        assert result.exit_code == 0, result.output
        assert result.stdout.splitlines() == [
            f"slug={PLAN_SLUG}",
            "title=adw.plans: plan files in ADW",
            "status=in-progress",
            "risk=medium",
            "epic=04",
            "phase=4.1",
            "linear=ADW-39",
            "branch=feature/adw-39",
            "created=2026-09-24",
            f"dir=docs/artifacts/plans/{PLAN_SLUG}",
            "tasks=1/7",
        ]

    def test_tasks_and_mark_task_done_round_trip(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        plan_md = _install_fixture_plan(tmp_path) / "PLAN.md"
        original = plan_md.read_text()

        def task_states() -> dict[str, str]:
            result = _plan(runner, "tasks", PLAN_SLUG, "--root", str(tmp_path))
            assert result.exit_code == 0, result.output
            rows = [line.split("\t") for line in result.stdout.splitlines()]
            return {row[0]: row[1] for row in rows}

        assert task_states()["TASK-002"] == "pending"

        assert mark_task_done(tmp_path, PLAN_SLUG, "TASK-002") is True

        assert task_states() == {"TASK-001": "done", "TASK-002": "done"} | {
            f"TASK-00{n}": "pending" for n in range(3, 8)
        }
        changed = [
            (before, after)
            for before, after in zip(
                original.splitlines(), plan_md.read_text().splitlines(), strict=True
            )
            if before != after
        ]
        assert changed == [
            (
                "- [ ] TASK-002: Parse PLAN.md into a Plan model and add list, "
                "show and tasks (depends on TASK-001)",
                "- [x] TASK-002: Parse PLAN.md into a Plan model and add list, "
                "show and tasks (depends on TASK-001)",
            )
        ]
        ticked = plan_md.read_bytes()

        assert mark_task_done(tmp_path, PLAN_SLUG, "TASK-002") is False
        assert plan_md.read_bytes() == ticked

    @pytest.mark.parametrize("command", ["show", "tasks"])
    def test_a_missing_plan_exits_1(
        self, runner: CliRunner, tmp_path: Path, command: str
    ) -> None:
        result = _plan(runner, command, "nope", "--root", str(tmp_path))

        assert result.exit_code == 1
        assert result.stderr.startswith("error: plan not found: ")


class TestLink:
    """adw plan link."""

    @pytest.fixture
    def root(self, tmp_path: Path) -> Path:
        epics = tmp_path / "docs" / "artifacts" / "epics"
        epics.mkdir(parents=True)
        (epics / "04-plan-driven-runs.md").write_text(
            "# Epic 04 — Plan-driven runs\n\n"
            "## Phase 4.1 — adw.plans\n\n**Plan**: _not yet created_\n"
        )
        _install_fixture_plan(tmp_path)
        return tmp_path

    def test_link_prints_what_it_linked(self, runner: CliRunner, root: Path) -> None:
        result = _plan(
            runner,
            *["link", "04", "--phase", "4.1", "--plan", PLAN_SLUG],
            *["--status", "done", "--root", str(root)],
        )

        assert result.exit_code == 0, result.output
        assert result.stdout.splitlines() == [
            f"linked plan '{PLAN_SLUG}' <-> 04-plan-driven-runs phase 4.1 "
            "(status: done)",
            "epic_file=docs/artifacts/epics/04-plan-driven-runs.md",
            f"plan_file=docs/artifacts/plans/{PLAN_SLUG}/PLAN.md",
        ]
        epic_text = (root / "docs/artifacts/epics/04-plan-driven-runs.md").read_text()
        assert (
            f"**Plan**: [{PLAN_SLUG}](../plans/{PLAN_SLUG}/PLAN.md) · status: done"
            in epic_text
        )

    def test_link_to_an_unknown_phase_exits_1(
        self, runner: CliRunner, root: Path
    ) -> None:
        result = _plan(
            runner,
            *["link", "04", "--phase", "4.9", "--plan", PLAN_SLUG, "--root", str(root)],
        )

        assert result.exit_code == 1
        assert result.stderr.startswith("error: phase '4.9' heading not found in ")
