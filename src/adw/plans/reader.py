"""Read plans: parse PLAN.md, list plans and tasks, find a branch's plan.

A port of implement-plan's list_plans.py and list_tasks.py, and of the
slug-from-branch rule that review-plan's resolve_plan.py and archive-plan
share.
"""

import re
from pathlib import Path

from adw.exceptions import PlanError
from adw.plans.model import Plan, PlanTask
from adw.plans.paths import ARCHIVE_DIR_NAME, plan_dir, plans_dir

TITLE_RE = re.compile(r"#\s+Plan:\s+(.+)")
HEADER_FIELD_RE = re.compile(
    r"^(Status|Branch|Risk|Epic|Phase|Linear|Created):\s*(.*)$"
)
TASK_LINE_RE = re.compile(
    r"^- \[(?P<box>[ xX])\]\s+(?P<id>TASK-\d+):\s+(?P<title>.+?)"
    r"(?:\s+\(depends on (?P<depends>[^)]+)\))?\s*$"
)
TASK_FILE_RE = re.compile(r"(TASK-\d+)-")


def load_plan(root: Path, slug: str) -> Plan:
    """Parse a plan's PLAN.md.

    Raises:
        PlanError: PLAN_NOT_FOUND when the plan has no PLAN.md.
    """
    return _parse(plan_dir(root, slug))


def list_plans(root: Path) -> list[Plan]:
    """Return every plan under root, sorted by slug, archived ones excluded."""
    directory = plans_dir(root)
    if not directory.is_dir():
        return []
    return [
        _parse(child)
        for child in sorted(directory.iterdir())
        if child.name != ARCHIVE_DIR_NAME and (child / "PLAN.md").is_file()
    ]


def list_tasks(root: Path, slug: str) -> list[PlanTask]:
    """Return a plan's tasks in "## Tasks" order.

    Raises:
        PlanError: PLAN_NOT_FOUND when the plan has no PLAN.md.
    """
    return load_plan(root, slug).tasks


def resolve_plan_by_branch(root: Path, branch: str) -> str | None:
    """Return the slug of the plan implemented on a branch.

    A plan whose Branch field equals the branch wins. Failing that, a plan
    with no Branch field whose slug is the branch's last path segment.

    Returns:
        The slug, or None when no plan matches.

    Raises:
        PlanError: AMBIGUOUS_PLAN when two plans match at the same step.
    """
    plans = list_plans(root)
    recorded = [plan.slug for plan in plans if plan.branch == branch]
    if not recorded:
        recorded = [
            plan.slug
            for plan in plans
            if plan.branch is None and branch.endswith("/" + plan.slug)
        ]
    if len(recorded) > 1:
        raise PlanError(
            "AMBIGUOUS_PLAN",
            f"multiple plans match branch '{branch}': {', '.join(recorded)}",
        )
    return recorded[0] if recorded else None


def _parse(directory: Path) -> Plan:
    plan_md = directory / "PLAN.md"
    if not plan_md.is_file():
        raise PlanError("PLAN_NOT_FOUND", f"plan not found: {plan_md}")
    lines = plan_md.read_text(encoding="utf-8").splitlines()

    title = ""
    fields: dict[str, str] = {}
    for line in lines:
        if line.startswith("## "):
            break
        if not title and (match := TITLE_RE.match(line)):
            title = match.group(1).strip()
        elif match := HEADER_FIELD_RE.match(line):
            tokens = match.group(2).split()
            if tokens and tokens[0] != "none":
                fields.setdefault(match.group(1).lower(), tokens[0])

    return Plan(
        slug=directory.name,
        path=directory,
        title=title,
        status=fields.get("status", "unknown"),
        risk=fields.get("risk"),
        epic=fields.get("epic"),
        phase=fields.get("phase"),
        linear=fields.get("linear"),
        branch=fields.get("branch"),
        created=fields.get("created"),
        tasks=_parse_tasks(lines, directory / "tasks"),
    )


def _parse_tasks(lines: list[str], tasks_dir: Path) -> list[PlanTask]:
    files: dict[str, Path] = {}
    for path in sorted(tasks_dir.glob("TASK-*.md")):
        if match := TASK_FILE_RE.match(path.name):
            files[match.group(1)] = path

    tasks: list[PlanTask] = []
    in_section = False
    for line in lines:
        if line.startswith("## Tasks"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and (match := TASK_LINE_RE.match(line)):
            depends = match.group("depends")
            tasks.append(
                PlanTask(
                    id=match.group("id"),
                    title=match.group("title").strip(),
                    done=match.group("box").lower() == "x",
                    depends_on=[d.strip() for d in depends.split(",")]
                    if depends
                    else [],
                    file=files.get(match.group("id")),
                )
            )
    return tasks
