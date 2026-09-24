"""Tests for adw.plans.authoring: the rules and errors the golden tree doesn't reach."""

from datetime import date
from pathlib import Path

import pytest

from adw.exceptions import PlanError
from adw.plans.authoring import add_final_task, add_task, init_plan


def _files(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


def test_small_risk_plan_has_no_research(tmp_path: Path) -> None:
    directory = init_plan(tmp_path, title="Small", risk="small", today=date(2026, 1, 2))

    assert _files(directory) == ["PLAN.md", "tasks"]
    assert "Created: 2026-01-02\n" in (directory / "PLAN.md").read_text()


def test_task_numbers_follow_the_highest_existing_one(tmp_path: Path) -> None:
    directory = init_plan(tmp_path, title="Gaps", risk="tiny")
    (directory / "tasks" / "TASK-001-a.md").write_text("")
    (directory / "tasks" / "TASK-003-c.md").write_text("")

    assert add_task(tmp_path, "gaps", task_type="impl", title="Next") == "TASK-004"
    assert add_final_task(tmp_path, "gaps") == "TASK-005"
    assert (directory / "tasks" / "TASK-004-next.md").is_file()


def test_init_plan_refuses_an_existing_dir(tmp_path: Path) -> None:
    directory = init_plan(tmp_path, title="Twice", risk="small")
    before = (directory / "PLAN.md").read_text()

    with pytest.raises(PlanError) as excinfo:
        init_plan(tmp_path, title="Twice", risk="medium")

    assert excinfo.value.code == "PLAN_EXISTS"
    assert (directory / "PLAN.md").read_text() == before
    assert not (directory / "RESEARCH.md").exists()


@pytest.mark.parametrize(
    ("title", "risk", "slug"),
    [
        ("Fine title", "enormous", None),
        ("!!!", "small", None),
        ("Fine title", "small", "../escape"),
        ("Fine title", "small", "archive"),
    ],
    ids=["unknown-risk", "empty-slug", "slug-with-slash", "reserved-slug"],
)
def test_init_plan_rejects_bad_input_and_writes_nothing(
    tmp_path: Path, title: str, risk: str, slug: str | None
) -> None:
    with pytest.raises(PlanError) as excinfo:
        init_plan(tmp_path, title=title, risk=risk, slug=slug)

    assert excinfo.value.code == "INVALID_PLAN"
    assert not (tmp_path / "docs").exists()


def test_adding_to_a_missing_plan_raises_plan_not_found(tmp_path: Path) -> None:
    with pytest.raises(PlanError) as excinfo:
        add_task(tmp_path, "nope", task_type="impl", title="Task")
    assert excinfo.value.code == "PLAN_NOT_FOUND"

    with pytest.raises(PlanError) as excinfo:
        add_final_task(tmp_path, "nope")
    assert excinfo.value.code == "PLAN_NOT_FOUND"


@pytest.mark.parametrize(
    ("task_type", "title", "depends", "strip_tasks_section"),
    [
        ("epic", "Task", None, False),
        ("impl", "???", None, False),
        ("impl", "Task", ["TASK-001)"], False),
        ("impl", "Task", None, True),
    ],
    ids=["unknown-type", "empty-title-slug", "bad-depends-id", "no-tasks-section"],
)
def test_add_task_rejects_bad_input_and_writes_nothing(
    tmp_path: Path,
    task_type: str,
    title: str,
    depends: list[str] | None,
    strip_tasks_section: bool,
) -> None:
    directory = init_plan(tmp_path, title="Plan", risk="tiny")
    plan_md = directory / "PLAN.md"
    if strip_tasks_section:
        plan_md.write_text(plan_md.read_text().replace("## Tasks", "## Work"))
    before = plan_md.read_text()

    with pytest.raises(PlanError) as excinfo:
        add_task(tmp_path, "plan", task_type=task_type, title=title, depends=depends)

    assert excinfo.value.code == "INVALID_PLAN"
    assert plan_md.read_text() == before
    assert list((directory / "tasks").iterdir()) == []


def test_add_final_task_needs_a_tasks_section(tmp_path: Path) -> None:
    directory = init_plan(tmp_path, title="Plan", risk="tiny")
    plan_md = directory / "PLAN.md"
    plan_md.write_text(plan_md.read_text().replace("## Tasks", "## Work"))

    with pytest.raises(PlanError) as excinfo:
        add_final_task(tmp_path, "plan")

    assert excinfo.value.code == "INVALID_PLAN"
    assert list((directory / "tasks").iterdir()) == []
