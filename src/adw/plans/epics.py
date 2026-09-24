"""Link plans to epic phases and report an epic's progress.

A port of create-epic's link_plan.py and epic_status.py. An epic is
docs/artifacts/epics/<NN>-<slug>.md; each "## Phase <NN.M> — <title>" block
carries a "**Plan**:" line that points at the phase's plan.
"""

import re
from pathlib import Path

from pydantic import BaseModel

from adw.exceptions import PlanError
from adw.plans.paths import plan_dir

LINK_STATUSES = ("planned", "in-progress", "done")
EPICS_INDEX = "EPICS.md"


class EpicStatus(BaseModel):
    """An epic's Linear and project links, and its phase-completion counts.

    Attributes:
        epic: The epic's two-digit number.
        epic_slug: The epic file's stem, e.g. "04-plan-driven-runs".
        linear_issue: The epic parent issue id, or "none".
        linear_milestone: The Milestone header's value, or "none".
        project: The Project header's value, or "none".
        phases_total: The number of "## Phase" headings.
        phases_done: The number of "**Plan**:" lines with status done.
        all_phases_done: Whether there are phases and all of them are done.
    """

    epic: str
    epic_slug: str
    linear_issue: str
    linear_milestone: str
    project: str
    phases_total: int
    phases_done: int
    all_phases_done: bool


def epics_dir(root: Path) -> Path:
    """Return the directory that holds the epic files."""
    return root / "docs" / "artifacts" / "epics"


def resolve_epic_file(root: Path, token: str) -> Path | None:
    """Find an epic file from an id or a slug.

    "4", "04" and "E04" pick 04-*.md. Otherwise the token is an exact file
    name, with or without ".md", or a substring that matches one epic only.

    Returns:
        The epic file, or None when nothing, or more than one file, matches.
    """
    token = token.strip()
    if not token:
        return None
    directory = epics_dir(root)
    if match := re.fullmatch(r"[Ee]?0*(\d+)", token):
        numbered = sorted(directory.glob(f"{int(match.group(1)):02d}-*.md"))
        if numbered:
            return numbered[0]
    name = token.removesuffix(".md")
    candidate = directory / f"{name}.md"
    if candidate.is_file() and candidate.name != EPICS_INDEX:
        return candidate
    matches = [
        path
        for path in sorted(directory.glob(f"*{_glob_escape(name)}*.md"))
        if path.name != EPICS_INDEX
    ]
    return matches[0] if len(matches) == 1 else None


def link_plan(
    root: Path,
    epic: str,
    *,
    phase: str,
    plan: str,
    status: str = "planned",
) -> tuple[Path, Path]:
    """Link a plan and an epic phase, both ways.

    Sets the phase block's "**Plan**:" line to point at the plan with the
    given status, and the plan's Epic and Phase fields, plus Linear when the
    phase has a "**Linear**:" id. Running it twice changes nothing.

    Returns:
        The epic file and the plan's PLAN.md.

    Raises:
        PlanError: INVALID_PLAN for a status outside LINK_STATUSES,
            EPIC_NOT_FOUND, PLAN_NOT_FOUND, or PHASE_NOT_FOUND when the epic
            has no heading for the phase. Nothing is written on error.
    """
    if status not in LINK_STATUSES:
        raise PlanError(
            "INVALID_PLAN",
            f"status must be one of {', '.join(LINK_STATUSES)}, got {status!r}",
        )
    epic_path = _epic_file(root, epic)
    plan_md = plan_dir(root, plan) / "PLAN.md"
    if not plan_md.is_file():
        raise PlanError("PLAN_NOT_FOUND", f"plan not found: {plan_md}")
    number = re.match(r"(\d+)-", epic_path.name)
    if not number:
        raise PlanError(
            "INVALID_PLAN", f"epic filename {epic_path.name!r} is not NN-slug.md form"
        )

    epic_text = epic_path.read_text(encoding="utf-8")
    block = _phase_block(epic_text, phase)
    if block is None:
        raise PlanError(
            "PHASE_NOT_FOUND", f"phase '{phase}' heading not found in {epic_path}"
        )
    heading, body = block.group(1), block.group(2)
    title_match = re.search(r"[—-]\s+(.+?)\s*$", heading)
    phase_title = title_match.group(1).strip() if title_match else phase

    plan_line = f"**Plan**: [{plan}](../plans/{plan}/PLAN.md) · status: {status}"
    new_body, count = re.subn(
        r"^\*\*Plan\*\*:.*$", lambda _: plan_line, body, count=1, flags=re.MULTILINE
    )
    if count == 0:
        new_body = plan_line + "\n\n" + body.lstrip("\n")
    new_epic = (
        epic_text[: block.start()] + heading + new_body + epic_text[block.end() :]
    )

    linear = _phase_linear_id(heading + body)
    new_plan = _link_plan_side(
        plan_md,
        plan_md.read_text(encoding="utf-8"),
        epic_value=(
            f"{int(number.group(1)):02d} — {_epic_title(epic_text)} "
            f"([epic](../../epics/{epic_path.stem}.md))"
        ),
        phase_value=f"{phase} — {phase_title}",
        linear=linear,
    )

    epic_path.write_text(new_epic, encoding="utf-8")
    plan_md.write_text(new_plan, encoding="utf-8")
    return epic_path, plan_md


def epic_status(root: Path, epic: str) -> EpicStatus:
    """Report an epic's links and how many of its phases are done.

    Raises:
        PlanError: EPIC_NOT_FOUND when no epic file matches.
    """
    epic_path = _epic_file(root, epic)
    text = epic_path.read_text(encoding="utf-8")
    number = re.match(r"(\d+)-", epic_path.name)
    total = len(re.findall(r"^##\s+Phase\s+[\d.]+\b", text, flags=re.MULTILINE))
    done = len(
        re.findall(r"^\*\*Plan\*\*:.*status:\s*done\b", text, flags=re.MULTILINE)
    )
    return EpicStatus(
        epic=f"{int(number.group(1)):02d}" if number else "??",
        epic_slug=epic_path.stem,
        linear_issue=_header_token(text, "Linear"),
        linear_milestone=_header_token(text, "Milestone"),
        project=_header_token(text, "Project"),
        phases_total=total,
        phases_done=done,
        all_phases_done=total > 0 and done == total,
    )


def _glob_escape(text: str) -> str:
    """Escape glob metacharacters so text matches literally."""
    return re.sub(r"([*?\[])", r"[\1]", text)


def _epic_file(root: Path, epic: str) -> Path:
    epic_path = resolve_epic_file(root, epic)
    if epic_path is None:
        raise PlanError(
            "EPIC_NOT_FOUND",
            f"could not resolve epic {epic!r} under {epics_dir(root)}",
        )
    return epic_path


def _phase_block(text: str, phase: str) -> re.Match[str] | None:
    """Match a phase block: its heading line, then everything to the next "## "."""
    return re.search(
        rf"(^##\s+Phase\s+{re.escape(phase)}\b[^\n]*\n)(.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )


def _phase_linear_id(block: str) -> str:
    match = re.search(r"^\*\*Linear\*\*:\s*(.+)$", block, flags=re.MULTILINE)
    if not match:
        return "none"
    value = match.group(1).strip()
    return value.split()[0] if value and value != "none" else "none"


def _epic_title(text: str) -> str:
    match = re.search(r"^#\s+Epic\s+\d+\s+[—-]\s+(.+)$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else "epic"


def _header_token(text: str, field: str) -> str:
    match = re.search(rf"^{field}:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return "none"
    value = match.group(1).strip()
    return value.split()[0] if value and value != "none" else "none"


def _link_plan_side(
    plan_md: Path, text: str, *, epic_value: str, phase_value: str, linear: str
) -> str:
    """Set the plan's Epic, Phase and (when known) Linear fields."""

    def set_field(text: str, field: str, value: str) -> tuple[str, int]:
        line = f"{field}: {value}"
        return re.subn(
            rf"^{field}:.*$", lambda _: line, text, count=1, flags=re.MULTILINE
        )

    text, epic_count = set_field(text, "Epic", epic_value)
    text, phase_count = set_field(text, "Phase", phase_value)
    linear_count = 1
    if linear != "none":
        text, linear_count = set_field(text, "Linear", linear)

    inserts = []
    if epic_count == 0:
        inserts.append(f"Epic: {epic_value}")
    if phase_count == 0:
        inserts.append(f"Phase: {phase_value}")
    if linear_count == 0:
        inserts.append(f"Linear: {linear}")
    if inserts:
        block = "\n".join(inserts)

        def append_block(match: re.Match[str]) -> str:
            return f"{match.group(1)}\n{block}"

        for anchor in ("Created", "Status"):
            text, count = re.subn(
                rf"^({anchor}:.*)$",
                append_block,
                text,
                count=1,
                flags=re.MULTILINE,
            )
            if count:
                break
        else:
            raise PlanError(
                "INVALID_PLAN",
                f"no Status:/Created: line to anchor Epic/Phase in {plan_md}",
            )
    return text
