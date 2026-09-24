"""Tests for adw.plans.archive: moving a merged plan and repairing its links."""

import os
import re
from datetime import date
from pathlib import Path

import pytest

from adw.exceptions import PlanError
from adw.plans.archive import archive_plan
from adw.plans.authoring import init_plan
from adw.plans.paths import plans_dir

MERGED = date(2026, 9, 24)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A project with an epic, a linked plan "p", and a sibling plan "p-2"."""
    (tmp_path / "AGENTS.md").write_text("# Agents\n")
    epics = tmp_path / "docs" / "artifacts" / "epics"
    epics.mkdir(parents=True)
    (epics / "04-x.md").write_text(
        "## Phase 4.1 — X\n\n"
        "**Plan**: [p](../plans/p/PLAN.md) · status: done\n\n"
        "## Phase 4.2 — Y\n\n"
        "**Plan**: [p-2](../plans/p-2/PLAN.md) · status: planned\n"
    )
    init_plan(tmp_path, title="Sibling", risk="tiny", slug="p-2")

    plan = init_plan(tmp_path, title="P", risk="medium", slug="p")
    plan_md = plan / "PLAN.md"
    plan_md.write_text(
        plan_md.read_text().replace(
            "Epic: none", "Epic: 04 — X ([epic](../../epics/04-x.md))"
        )
        + "\n[research](./RESEARCH.md) [goal](#goal) "
        "[site](https://example.com/a/../b) [task](tasks/TASK-001-a.md)\n"
    )
    research = plan / "RESEARCH.md"
    research.write_text(research.read_text() + "\n[agents](../../../../AGENTS.md)\n")
    (plan / "tasks" / "TASK-001-a.md").write_text(
        "[plan](../PLAN.md) [epic](../../../epics/04-x.md#phase-41)\n"
        "![sibling](../../p-2/PLAN.md)\n"
    )
    return tmp_path


def _links(path: Path) -> list[str]:
    return LINK_RE.findall(path.read_text())


def test_archive_moves_the_plan_under_its_merge_date(root: Path) -> None:
    destination = archive_plan(root, "p", MERGED)

    assert destination == plans_dir(root) / "archive" / "2026-09-24-p"
    assert (destination / "PLAN.md").is_file()
    assert not (plans_dir(root) / "p").exists()


def test_a_taken_name_gets_a_numeric_suffix(root: Path) -> None:
    archive_plan(root, "p", MERGED)
    init_plan(root, title="P again", risk="tiny", slug="p")
    second = archive_plan(root, "p", MERGED)
    init_plan(root, title="P thrice", risk="tiny", slug="p")
    third = archive_plan(root, "p", MERGED)

    assert (second.name, third.name) == ("2026-09-24-p-2", "2026-09-24-p-3")


def test_links_that_leave_the_plan_dir_are_repaired(root: Path) -> None:
    destination = archive_plan(root, "p", MERGED)

    assert _links(destination / "PLAN.md") == [
        "../../../epics/04-x.md",
        "./RESEARCH.md",
        "#goal",
        "https://example.com/a/../b",
        "tasks/TASK-001-a.md",
    ]
    assert _links(destination / "RESEARCH.md") == ["../../../../../AGENTS.md"]
    assert _links(destination / "tasks" / "TASK-001-a.md") == [
        "../PLAN.md",
        "../../../../epics/04-x.md#phase-41",
        "../../../p-2/PLAN.md",
    ]


def test_every_relative_link_resolves_after_the_move(root: Path) -> None:
    destination = archive_plan(root, "p", MERGED)

    for md in destination.rglob("*.md"):
        for target in _links(md):
            if target.startswith("#") or "://" in target:
                continue
            path = target.split("#", 1)[0]
            assert (md.parent / path).resolve().exists(), (md, target)


def test_links_inside_code_are_left_alone(root: Path) -> None:
    code = (
        "Format: `([epic](../../epics/<NN>-<slug>.md))` and "
        "``[a](../../x.md)``\n\n"
        "```md\n[fenced](../../epics/04-x.md)\n```\n\n"
        "~~~\n[tilde](../../epics/04-x.md)\n~~~\n"
    )
    research = plans_dir(root) / "p" / "RESEARCH.md"
    research.write_text(research.read_text() + code)

    destination = archive_plan(root, "p", MERGED)

    text = (destination / "RESEARCH.md").read_text()
    assert text.endswith(code)
    assert "[agents](../../../../../AGENTS.md)" in text


def test_the_epic_points_at_the_archived_plan(root: Path) -> None:
    archive_plan(root, "p", MERGED)

    epic = (root / "docs/artifacts/epics/04-x.md").read_text()
    assert "**Plan**: [p](../plans/archive/2026-09-24-p/PLAN.md) · status: done" in epic
    assert "**Plan**: [p-2](../plans/p-2/PLAN.md) · status: planned" in epic


def _snapshot(root: Path) -> dict[str, bytes]:
    docs = root / "docs"
    return {
        path.relative_to(docs).as_posix(): path.read_bytes()
        for path in sorted(docs.rglob("*"))
        if path.is_file()
    }


@pytest.mark.parametrize(
    "failing_file",
    ["RESEARCH.md", ".04-x.md.tmp"],
    ids=["rewriting-the-plan", "repointing-the-epic"],
)
def test_a_failed_write_leaves_everything_as_it_was(
    root: Path, monkeypatch: pytest.MonkeyPatch, failing_file: str
) -> None:
    before = _snapshot(root)
    original_write_text = Path.write_text
    failures = []

    def write_text_failing_once(self: Path, data: str, **kwargs: object) -> int:
        if self.name == failing_file and not failures:
            failures.append(self)
            raise OSError(28, "No space left on device")
        return original_write_text(self, data, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", write_text_failing_once)

    with pytest.raises(OSError, match="No space left"):
        archive_plan(root, "p", MERGED)

    assert failures, "the injected failure never fired"
    assert _snapshot(root) == before
    assert not (plans_dir(root) / "archive").exists() or not any(
        (plans_dir(root) / "archive").iterdir()
    )

    monkeypatch.setattr(Path, "write_text", original_write_text)
    destination = archive_plan(root, "p", MERGED)
    assert destination.name == "2026-09-24-p"


def test_an_epic_that_cannot_be_restored_keeps_the_archive(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    epics = root / "docs" / "artifacts" / "epics"
    (epics / "05-y.md").write_text("**Plan**: [p](../plans/p/PLAN.md)\n")
    source_before = {
        path.relative_to(plans_dir(root)).as_posix(): path.read_bytes()
        for path in (plans_dir(root) / "p").rglob("*")
        if path.is_file()
    }
    original_replace = os.replace
    calls = []

    def replace_then_fail(src: str, dst: str) -> None:
        calls.append(dst)
        if len(calls) > 1:
            raise OSError(5, "Input/output error")
        original_replace(src, dst)

    monkeypatch.setattr(os, "replace", replace_then_fail)

    with pytest.raises(OSError, match="Input/output error") as excinfo:
        archive_plan(root, "p", MERGED)

    destination = plans_dir(root) / "archive" / "2026-09-24-p"
    assert (destination / "PLAN.md").is_file()
    assert "04-x.md" in " ".join(excinfo.value.__notes__)
    assert "../plans/archive/2026-09-24-p/PLAN.md" in (epics / "04-x.md").read_text()
    assert (epics / "05-y.md").read_text() == "**Plan**: [p](../plans/p/PLAN.md)\n"
    assert not list(epics.glob(".*.tmp"))
    assert {
        path.relative_to(plans_dir(root)).as_posix(): path.read_bytes()
        for path in (plans_dir(root) / "p").rglob("*")
        if path.is_file()
    } == source_before


@pytest.mark.parametrize(
    ("slug", "code"),
    [("missing", "PLAN_NOT_FOUND"), ("archive", "INVALID_PLAN")],
)
def test_archive_errors_move_nothing(root: Path, slug: str, code: str) -> None:
    before = sorted(p.as_posix() for p in plans_dir(root).rglob("*"))

    with pytest.raises(PlanError) as excinfo:
        archive_plan(root, slug, MERGED)

    assert excinfo.value.code == code
    assert sorted(p.as_posix() for p in plans_dir(root).rglob("*")) == before
