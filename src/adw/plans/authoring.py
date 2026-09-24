"""Write new plans: PLAN.md, RESEARCH.md and task files.

A port of create-plan's init_plan.py, add_task.py and add_final_task.py.
Each template substitution replaces the first occurrence only, as the scripts
do, so ADW writes the same bytes for the same inputs.
"""

import datetime
import re
from pathlib import Path

from adw.exceptions import PlanError
from adw.plans.paths import plan_dir, slugify
from adw.plans.templates import read_template

VALID_RISKS = ("tiny", "small", "medium", "large", "high")
RESEARCH_REQUIRED = frozenset({"medium", "large", "high"})
TASK_TEMPLATES = {
    "impl": "template-task-implementation.md",
    "checklist": "template-task-checklist.md",
}
TASK_ID_RE = re.compile(r"^TASK-\d+$")


def init_plan(
    root: Path,
    *,
    title: str,
    risk: str,
    slug: str | None = None,
    today: datetime.date | None = None,
) -> Path:
    """Create a plan directory with PLAN.md, tasks/, and RESEARCH.md for medium+.

    Args:
        root: Project root.
        title: Plan title; the slug derives from it unless given.
        risk: One of VALID_RISKS.
        slug: Overrides the derived slug.
        today: The Created date; defaults to today.

    Returns:
        The new plan directory.

    Raises:
        PlanError: INVALID_PLAN for an unknown risk or an unusable slug,
            PLAN_EXISTS when the directory exists.
    """
    if risk not in VALID_RISKS:
        raise PlanError(
            "INVALID_PLAN",
            f"risk must be one of {', '.join(VALID_RISKS)}, got {risk!r}",
        )
    slug = slug or slugify(title)
    if not slug:
        raise PlanError("INVALID_PLAN", f"could not derive slug from title {title!r}")
    directory = plan_dir(root, slug)
    if directory.exists():
        raise PlanError("PLAN_EXISTS", f"plan directory already exists: {directory}")

    created = (today or datetime.date.today()).isoformat()
    plan = read_template("template-plan.md")
    plan = plan.replace("<title>", title, 1)
    plan = plan.replace("draft | ready | in-progress | done", "draft", 1)
    plan = plan.replace("tiny | small | medium | large | high", risk, 1)
    plan = plan.replace("YYYY-MM-DD", created, 1)

    directory.mkdir(parents=True)
    (directory / "tasks").mkdir()
    (directory / "PLAN.md").write_text(plan, encoding="utf-8")
    if risk in RESEARCH_REQUIRED:
        research = read_template("template-research.md").replace(
            "<plan-title>", title, 1
        )
        (directory / "RESEARCH.md").write_text(research, encoding="utf-8")
    return directory


def add_task(
    root: Path,
    slug: str,
    *,
    task_type: str,
    title: str,
    depends: list[str] | None = None,
) -> str:
    """Add the next TASK-NNN file and append its checkbox line to PLAN.md.

    Args:
        root: Project root.
        slug: The plan's slug.
        task_type: "impl" (RED/GREEN/REFACTOR) or "checklist".
        title: Task title; the file name derives from it.
        depends: Ids of the tasks this one depends on.

    Returns:
        The new task's id.

    Raises:
        PlanError: PLAN_NOT_FOUND for a missing plan; INVALID_PLAN for an
            unknown type, an unusable title, a malformed dependency id, or a
            PLAN.md without a "## Tasks" section.
    """
    template = TASK_TEMPLATES.get(task_type)
    if template is None:
        raise PlanError(
            "INVALID_PLAN",
            f"task type must be one of {', '.join(TASK_TEMPLATES)}, got {task_type!r}",
        )
    title_slug = slugify(title)
    if not title_slug:
        raise PlanError(
            "INVALID_PLAN",
            f"could not derive a filename slug from title {title!r}",
        )
    for task_id in depends or []:
        if not TASK_ID_RE.match(task_id):
            raise PlanError(
                "INVALID_PLAN", f"dependency must match TASK-NNN, got {task_id!r}"
            )
    depends_text = ",".join(depends) if depends else None

    directory, plan_text = _existing_plan(root, slug)
    tasks_dir = directory / "tasks"
    task_id = f"TASK-{next_task_number(tasks_dir):03d}"

    body = read_template(template)
    body = body.replace("TASK-00X", task_id, 1)
    body = body.replace("<title>", title, 1)
    body = body.replace("TASK-00Y | None", depends_text or "None", 1)

    line = f"- [ ] {task_id}: {title}"
    if depends_text:
        line += f" (depends on {depends_text})"
    _write_task(directory, tasks_dir / f"{task_id}-{title_slug}.md", body)
    _append_task_line(directory / "PLAN.md", plan_text, line)
    return task_id


def add_final_task(root: Path, slug: str) -> str:
    """Add the final-validation task file and its checkbox line.

    Returns:
        The final-validation task's id, the next sequential number.

    Raises:
        PlanError: PLAN_NOT_FOUND for a missing plan, INVALID_PLAN for a
            PLAN.md without a "## Tasks" section.
    """
    directory, plan_text = _existing_plan(root, slug)
    tasks_dir = directory / "tasks"
    task_id = f"TASK-{next_task_number(tasks_dir):03d}"

    body = read_template("template-task-final-validation.md")
    body = body.replace("TASK-00N", task_id, 1)
    body = body.replace("<plan-slug>", slug, 1)

    _write_task(directory, tasks_dir / f"{task_id}-final-validation.md", body)
    _append_task_line(
        directory / "PLAN.md", plan_text, f"- [ ] {task_id}: Final Validation"
    )
    return task_id


def next_task_number(tasks_dir: Path) -> int:
    """Return one more than the highest TASK-NNN number in tasks_dir, or 1."""
    numbers = [
        int(match.group(1))
        for path in tasks_dir.glob("TASK-*.md")
        if (match := re.match(r"TASK-(\d+)-", path.name))
    ]
    return max(numbers) + 1 if numbers else 1


def _existing_plan(root: Path, slug: str) -> tuple[Path, str]:
    """Return a plan's directory and PLAN.md text, checked for "## Tasks"."""
    directory = plan_dir(root, slug)
    plan_md = directory / "PLAN.md"
    if not plan_md.is_file():
        raise PlanError("PLAN_NOT_FOUND", f"plan directory does not exist: {directory}")
    text = plan_md.read_text(encoding="utf-8")
    if "## Tasks" not in text:
        raise PlanError("INVALID_PLAN", f"'## Tasks' section not found in {plan_md}")
    return directory, text


def _write_task(directory: Path, task_path: Path, body: str) -> None:
    (directory / "tasks").mkdir(exist_ok=True)
    task_path.write_text(body, encoding="utf-8")


def _append_task_line(plan_md: Path, text: str, line: str) -> None:
    """Append a task line, after a blank line unless a task line precedes it."""
    text = text.rstrip() + "\n"
    last_line = text.rstrip("\n").rsplit("\n", 1)[-1]
    separator = "" if last_line.lstrip().startswith("- [") else "\n"
    plan_md.write_text(f"{text}{separator}{line}\n", encoding="utf-8")
