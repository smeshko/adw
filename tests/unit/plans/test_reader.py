"""Tests for adw.plans.reader: parsing PLAN.md, listing tasks, branch lookup."""

import shutil
from pathlib import Path

import pytest

from adw.exceptions import PlanError
from adw.plans.paths import plans_dir
from adw.plans.reader import (
    list_plans,
    list_tasks,
    load_plan,
    resolve_plan_by_branch,
)

FIXTURE = Path(__file__).parents[2] / "fixtures" / "plans" / "04.1-adw-plans-module"
SLUG = "04.1-adw-plans-module"


def _write_plan(root: Path, slug: str, header: str, body: str = "") -> Path:
    directory = plans_dir(root) / slug
    directory.mkdir(parents=True)
    (directory / "PLAN.md").write_text(f"# Plan: {slug}\n\n{header}\n{body}")
    return directory


def test_load_plan_reads_a_plan_written_by_create_plan(tmp_path: Path) -> None:
    shutil.copytree(FIXTURE, plans_dir(tmp_path) / SLUG)

    plan = load_plan(tmp_path, SLUG)

    assert plan.slug == SLUG
    assert plan.title == "adw.plans: plan files in ADW"
    assert (plan.status, plan.risk, plan.created) == (
        "in-progress",
        "medium",
        "2026-09-24",
    )
    assert (plan.epic, plan.phase, plan.linear, plan.branch) == (
        "04",
        "4.1",
        "ADW-39",
        "feature/adw-39",
    )
    assert [task.id for task in plan.tasks] == [f"TASK-00{n}" for n in range(1, 8)]
    assert [task.done for task in plan.tasks] == [True] + [False] * 6
    assert plan.tasks[1].title == (
        "Parse PLAN.md into a Plan model and add list, show and tasks"
    )
    assert plan.tasks[5].depends_on == [f"TASK-00{n}" for n in range(1, 6)]
    assert plan.tasks[6].depends_on == []
    assert all(task.file is not None and task.file.is_file() for task in plan.tasks)


def test_load_plan_on_a_missing_plan_raises(tmp_path: Path) -> None:
    with pytest.raises(PlanError) as excinfo:
        load_plan(tmp_path, "nope")

    assert excinfo.value.code == "PLAN_NOT_FOUND"


def test_tasks_come_only_from_the_tasks_section(tmp_path: Path) -> None:
    _write_plan(
        tmp_path,
        "sections",
        "Status: draft",
        "## Acceptance Criteria\n\n"
        "- [ ] TASK-009: above the section\n\n"
        "## Tasks\n\n"
        "Prose between the heading and the tasks.\n\n"
        "- [x] TASK-001: First\n"
        "- [ ] TASK-002: Second (depends on TASK-001)\n"
        "- not a task line\n\n"
        "## Notes\n\n"
        "- [ ] TASK-003: below the section\n",
    )

    tasks = list_tasks(tmp_path, "sections")

    assert [(t.id, t.title, t.done, t.depends_on, t.file) for t in tasks] == [
        ("TASK-001", "First", True, [], None),
        ("TASK-002", "Second", False, ["TASK-001"], None),
    ]


def test_a_plan_without_header_fields_reads_as_unknown(tmp_path: Path) -> None:
    _write_plan(tmp_path, "bare", "", "## Tasks\n")

    plan = load_plan(tmp_path, "bare")

    assert plan.status == "unknown"
    assert (plan.risk, plan.epic, plan.phase, plan.linear, plan.branch) == (
        None,
        None,
        None,
        None,
        None,
    )


def test_list_plans_without_a_plans_dir_is_empty(tmp_path: Path) -> None:
    assert list_plans(tmp_path) == []


class TestResolvePlanByBranch:
    """The skills' slug-from-branch rule."""

    def test_a_recorded_branch_matches(self, tmp_path: Path) -> None:
        _write_plan(tmp_path, "one", "Status: in-progress\nBranch: feature/x-1")

        assert resolve_plan_by_branch(tmp_path, "feature/x-1") == "one"

    def test_a_recorded_branch_beats_a_suffix_match(self, tmp_path: Path) -> None:
        _write_plan(tmp_path, "two", "Status: draft")
        _write_plan(tmp_path, "other", "Status: in-progress\nBranch: feature/two")

        assert resolve_plan_by_branch(tmp_path, "feature/two") == "other"

    def test_the_suffix_fallback_skips_plans_with_a_branch(
        self, tmp_path: Path
    ) -> None:
        _write_plan(tmp_path, "three", "Status: in-progress\nBranch: feature/elsewhere")
        _write_plan(tmp_path, "four", "Status: draft")

        assert resolve_plan_by_branch(tmp_path, "feature/three") is None
        assert resolve_plan_by_branch(tmp_path, "feature/four") == "four"

    def test_two_recorded_matches_are_ambiguous(self, tmp_path: Path) -> None:
        _write_plan(tmp_path, "five", "Status: done\nBranch: feature/dup")
        _write_plan(tmp_path, "six", "Status: done\nBranch: feature/dup")

        with pytest.raises(PlanError) as excinfo:
            resolve_plan_by_branch(tmp_path, "feature/dup")

        assert excinfo.value.code == "AMBIGUOUS_PLAN"

    def test_archived_plans_never_match(self, tmp_path: Path) -> None:
        _write_plan(tmp_path, "archive/2026-09-01-old", "Branch: feature/old")

        assert resolve_plan_by_branch(tmp_path, "feature/old") is None
        assert resolve_plan_by_branch(tmp_path, "x/2026-09-01-old") is None
