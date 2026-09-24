"""Tests for adw.plans.state: ticking tasks, setting status and branch."""

from pathlib import Path

import pytest

from adw.exceptions import PlanError
from adw.plans.authoring import init_plan
from adw.plans.state import mark_task_done, set_plan_branch, set_plan_status


def _plan(root: Path, tasks: str = "") -> Path:
    directory = init_plan(root, title="State", risk="tiny")
    plan_md = directory / "PLAN.md"
    plan_md.write_text(plan_md.read_text() + tasks)
    return plan_md


def test_mark_task_done_anchors_the_id_on_its_colon(tmp_path: Path) -> None:
    plan_md = _plan(tmp_path, "\n- [ ] TASK-20: Twenty\n- [ ] TASK-2: Two\n")

    assert mark_task_done(tmp_path, "state", "TASK-2") is True

    text = plan_md.read_text()
    assert "- [ ] TASK-20: Twenty\n" in text
    assert "- [x] TASK-2: Two\n" in text


@pytest.mark.parametrize(
    ("slug", "task_id", "code"),
    [
        ("state", "task-1", "INVALID_PLAN"),
        ("state", "TASK-9", "TASK_NOT_FOUND"),
        ("nope", "TASK-1", "PLAN_NOT_FOUND"),
    ],
    ids=["malformed-id", "missing-task", "missing-plan"],
)
def test_mark_task_done_errors_leave_plan_md_unchanged(
    tmp_path: Path, slug: str, task_id: str, code: str
) -> None:
    plan_md = _plan(tmp_path, "\n- [ ] TASK-1: One\n")
    before = plan_md.read_text()

    with pytest.raises(PlanError) as excinfo:
        mark_task_done(tmp_path, slug, task_id)

    assert excinfo.value.code == code
    assert plan_md.read_text() == before


def test_set_plan_status_replaces_the_status_line(tmp_path: Path) -> None:
    plan_md = _plan(tmp_path)

    set_plan_status(tmp_path, "state", "in-progress")

    assert "\nStatus: in-progress\n" in plan_md.read_text()
    assert "Status: draft" not in plan_md.read_text()


def test_set_plan_branch_inserts_after_status_then_replaces(tmp_path: Path) -> None:
    plan_md = _plan(tmp_path)

    set_plan_branch(tmp_path, "state", "feature/one")
    lines = plan_md.read_text().splitlines()
    assert lines[lines.index("Status: draft") + 1] == "Branch: feature/one"

    set_plan_branch(tmp_path, "state", "feature/two")
    text = plan_md.read_text()
    assert "Status: draft\nBranch: feature/two\n" in text
    assert "feature/one" not in text


@pytest.mark.parametrize(
    ("status", "strip_status_line"),
    [("finished", False), ("done", True)],
    ids=["unknown-status", "no-status-line"],
)
def test_set_plan_status_errors(
    tmp_path: Path, status: str, strip_status_line: bool
) -> None:
    plan_md = _plan(tmp_path)
    if strip_status_line:
        plan_md.write_text(plan_md.read_text().replace("Status: draft\n", ""))
    before = plan_md.read_text()

    with pytest.raises(PlanError) as excinfo:
        set_plan_status(tmp_path, "state", status)

    assert excinfo.value.code == "INVALID_PLAN"
    assert plan_md.read_text() == before


def test_set_plan_branch_needs_a_status_line(tmp_path: Path) -> None:
    plan_md = _plan(tmp_path)
    plan_md.write_text(plan_md.read_text().replace("Status: draft\n", ""))

    with pytest.raises(PlanError) as excinfo:
        set_plan_branch(tmp_path, "state", "feature/x")

    assert excinfo.value.code == "INVALID_PLAN"
    assert "Branch:" not in plan_md.read_text()
