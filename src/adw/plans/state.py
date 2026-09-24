"""Update a plan's state in PLAN.md: task checkboxes, Status and Branch.

A port of implement-plan's mark_task_done.py, set_plan_status.py and
set_plan_branch.py. Each is one regex substitution on PLAN.md.
"""

import re
from pathlib import Path

from adw.exceptions import PlanError
from adw.plans.paths import plan_dir

VALID_STATUSES = ("draft", "ready", "in-progress", "done")
TASK_ID_RE = re.compile(r"^TASK-\d+$")
STATUS_LINE_RE = re.compile(r"^Status:\s*.*$", re.MULTILINE)
BRANCH_LINE_RE = re.compile(r"^Branch:\s*.*$", re.MULTILINE)


def mark_task_done(root: Path, slug: str, task_id: str) -> bool:
    """Tick a task's checkbox in PLAN.md.

    Returns:
        True when the box was ticked now, False when it already was.

    Raises:
        PlanError: INVALID_PLAN for an id that isn't TASK-NNN, TASK_NOT_FOUND
            when PLAN.md has no line for it, PLAN_NOT_FOUND for a missing plan.
    """
    if not TASK_ID_RE.match(task_id):
        raise PlanError("INVALID_PLAN", f"task id must match TASK-NNN, got {task_id!r}")
    plan_md, text = _read(root, slug)
    pattern = re.compile(
        rf"^(- \[)(?P<box>[ xX])(\]\s+{re.escape(task_id)}:.*)$", re.MULTILINE
    )
    match = pattern.search(text)
    if not match:
        raise PlanError("TASK_NOT_FOUND", f"task {task_id} not found in {plan_md}")
    if match.group("box").lower() == "x":
        return False
    plan_md.write_text(pattern.sub(r"\1x\3", text, count=1), encoding="utf-8")
    return True


def set_plan_status(root: Path, slug: str, status: str) -> None:
    """Set PLAN.md's Status line.

    Raises:
        PlanError: INVALID_PLAN for a status outside VALID_STATUSES or a
            PLAN.md without a Status line, PLAN_NOT_FOUND for a missing plan.
    """
    if status not in VALID_STATUSES:
        raise PlanError(
            "INVALID_PLAN",
            f"status must be one of {', '.join(VALID_STATUSES)}, got {status!r}",
        )
    plan_md, text = _read(root, slug)
    new_text, count = STATUS_LINE_RE.subn(f"Status: {status}", text, count=1)
    if count == 0:
        raise PlanError("INVALID_PLAN", f"no Status line found in {plan_md}")
    plan_md.write_text(new_text, encoding="utf-8")


def set_plan_branch(root: Path, slug: str, branch: str) -> None:
    """Record the feature branch: replace the Branch line, or add one after Status.

    Raises:
        PlanError: INVALID_PLAN when PLAN.md has neither a Branch nor a Status
            line, PLAN_NOT_FOUND for a missing plan.
    """
    plan_md, text = _read(root, slug)
    branch_line = f"Branch: {branch}"
    new_text, count = BRANCH_LINE_RE.subn(lambda _: branch_line, text, count=1)
    if count == 0:
        new_text, count = STATUS_LINE_RE.subn(
            lambda m: f"{m.group(0)}\n{branch_line}", text, count=1
        )
        if count == 0:
            raise PlanError("INVALID_PLAN", f"no Status line found in {plan_md}")
    plan_md.write_text(new_text, encoding="utf-8")


def _read(root: Path, slug: str) -> tuple[Path, str]:
    plan_md = plan_dir(root, slug) / "PLAN.md"
    if not plan_md.is_file():
        raise PlanError("PLAN_NOT_FOUND", f"plan not found: {plan_md}")
    return plan_md, plan_md.read_text(encoding="utf-8")
