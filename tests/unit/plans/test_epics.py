"""Tests for adw.plans.epics: linking plans to epic phases, epic status."""

from pathlib import Path

import pytest

from adw.exceptions import PlanError
from adw.plans.authoring import init_plan
from adw.plans.epics import epic_status, link_plan, resolve_epic_file

EPIC = """\
# Epic 07 — Golden epic

Status: planned
Created: 2026-09-23
Project: adw-next
Linear: ADW-90 (https://linear.app/x/issue/ADW-90)
Milestone: M-7

## Overview

Two phases.

## Phase 7.1 — First phase

**Plan**: _not yet created_

**Linear**: ADW-99 (https://linear.app/x/issue/ADW-99)

**Goal**: One.

---

## Phase 7.2 — Second phase

**Goal**: Two, with no Plan or Linear line.

---

<!-- PHASES -->

## Epic-level acceptance criteria

- [ ] Every phase merged
"""


@pytest.fixture
def epic_file(tmp_path: Path) -> Path:
    epics = tmp_path / "docs" / "artifacts" / "epics"
    epics.mkdir(parents=True)
    (epics / "EPICS.md").write_text("# Implementation Epics\n")
    (epics / "08-other-epic.md").write_text("# Epic 08 — Other epic\n")
    path = epics / "07-golden-epic.md"
    path.write_text(EPIC)
    return path


@pytest.fixture
def plan_md(tmp_path: Path) -> Path:
    return init_plan(tmp_path, title="Linked", risk="tiny") / "PLAN.md"


def test_link_plan_writes_both_sides_once(
    tmp_path: Path, epic_file: Path, plan_md: Path
) -> None:
    assert link_plan(tmp_path, "7", phase="7.1", plan="linked") == (
        epic_file,
        plan_md,
    )

    assert (
        "## Phase 7.1 — First phase\n\n"
        "**Plan**: [linked](../plans/linked/PLAN.md) · status: planned\n\n"
        "**Linear**: ADW-99"
    ) in epic_file.read_text()
    plan_lines = plan_md.read_text().splitlines()
    assert plan_lines[4:7] == [
        "Epic: 07 — Golden epic ([epic](../../epics/07-golden-epic.md))",
        "Phase: 7.1 — First phase",
        "Linear: ADW-99",
    ]

    epic_after, plan_after = epic_file.read_text(), plan_md.read_text()
    link_plan(tmp_path, "7", phase="7.1", plan="linked")
    assert (epic_file.read_text(), plan_md.read_text()) == (epic_after, plan_after)


def test_a_phase_without_plan_or_linear_lines(
    tmp_path: Path, epic_file: Path, plan_md: Path
) -> None:
    link_plan(tmp_path, "07", phase="7.2", plan="linked", status="in-progress")

    assert (
        "## Phase 7.2 — Second phase\n"
        "**Plan**: [linked](../plans/linked/PLAN.md) · status: in-progress\n\n"
        "**Goal**: Two"
    ) in epic_file.read_text()
    assert "\nLinear: none\n" in plan_md.read_text()


def test_a_plan_without_epic_fields_gets_them_after_created(
    tmp_path: Path, epic_file: Path, plan_md: Path
) -> None:
    text = plan_md.read_text()
    for field in ("Epic: none\n", "Phase: none\n", "Linear: none\n"):
        text = text.replace(field, "")
    plan_md.write_text(text)

    link_plan(tmp_path, "7", phase="7.1", plan="linked")

    lines = plan_md.read_text().splitlines()
    created = next(i for i, line in enumerate(lines) if line.startswith("Created:"))
    assert [line.split(":")[0] for line in lines[created + 1 : created + 4]] == [
        "Epic",
        "Phase",
        "Linear",
    ]


@pytest.mark.parametrize(
    ("epic", "phase", "plan", "status", "code"),
    [
        ("99", "7.1", "linked", "planned", "EPIC_NOT_FOUND"),
        ("7", "7.9", "linked", "planned", "PHASE_NOT_FOUND"),
        ("7", "7.1", "missing", "planned", "PLAN_NOT_FOUND"),
        ("7", "7.1", "linked", "started", "INVALID_PLAN"),
    ],
)
def test_link_plan_errors_write_nothing(
    tmp_path: Path,
    epic_file: Path,
    plan_md: Path,
    epic: str,
    phase: str,
    plan: str,
    status: str,
    code: str,
) -> None:
    before = (epic_file.read_text(), plan_md.read_text())

    with pytest.raises(PlanError) as excinfo:
        link_plan(tmp_path, epic, phase=phase, plan=plan, status=status)

    assert excinfo.value.code == code
    assert (epic_file.read_text(), plan_md.read_text()) == before


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("7", "07-golden-epic.md"),
        ("E07", "07-golden-epic.md"),
        ("07-golden-epic", "07-golden-epic.md"),
        ("07-golden-epic.md", "07-golden-epic.md"),
        ("golden", "07-golden-epic.md"),
        ("epic", None),
        ("EPICS", None),
        ("", None),
        ("99", None),
    ],
)
def test_resolve_epic_file(
    tmp_path: Path, epic_file: Path, token: str, expected: str | None
) -> None:
    resolved = resolve_epic_file(tmp_path, token)

    assert (resolved.name if resolved else None) == expected


def test_epic_status_counts_done_phases(
    tmp_path: Path, epic_file: Path, plan_md: Path
) -> None:
    link_plan(tmp_path, "7", phase="7.1", plan="linked", status="done")

    status = epic_status(tmp_path, "7")

    assert status.model_dump() == {
        "epic": "07",
        "epic_slug": "07-golden-epic",
        "linear_issue": "ADW-90",
        "linear_milestone": "M-7",
        "project": "adw-next",
        "phases_total": 2,
        "phases_done": 1,
        "all_phases_done": False,
    }

    link_plan(tmp_path, "7", phase="7.2", plan="linked", status="done")
    assert epic_status(tmp_path, "7").all_phases_done is True


def test_epic_status_of_a_missing_epic_raises(tmp_path: Path) -> None:
    with pytest.raises(PlanError) as excinfo:
        epic_status(tmp_path, "7")

    assert excinfo.value.code == "EPIC_NOT_FOUND"
