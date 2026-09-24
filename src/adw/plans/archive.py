"""Archive a merged plan: move it under plans/archive/ and repair its links.

The file move ports archive-plan's archive_plan.sh; its git and GitHub steps
(the merged-PR check, checkout, pull and branch delete) stay with the caller.
The script leaves relative links broken, because the plan moves one level
deeper; archive_plan repairs them.
"""

import os
import re
import shutil
from datetime import date
from pathlib import Path

from adw.exceptions import PlanError
from adw.plans.epics import epics_dir
from adw.plans.paths import ARCHIVE_DIR_NAME, plan_dir, plans_dir

# Code is matched first, so a link-shaped string inside a fenced block or an
# inline code span is left alone; only the "link" group is repaired.
CODE_OR_LINK_RE = re.compile(
    r"(?P<fenced>^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)[ \t]*$)"
    r"|(?P<inline>``[^\n]+?``|`[^`\n]+`)"
    r"|(?P<link>\]\((?P<target>[^)\s]+)\))",
    re.MULTILINE | re.DOTALL,
)
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def archive_plan(root: Path, slug: str, merged_on: date) -> Path:
    """Move a plan to plans/archive/<merged_on>-<slug>/ and repair its links.

    The name gets "-2", "-3" and so on when it is taken. In the moved
    Markdown files, a relative link that pointed outside the plan dir is
    recomputed from the new location. Epic links into the plan dir move to
    the archive.

    Args:
        root: Project root.
        slug: The plan's slug.
        merged_on: The date its PR merged.

    Returns:
        The archived plan directory.

    Raises:
        PlanError: INVALID_PLAN for an unusable slug, PLAN_NOT_FOUND when the
            plan has no PLAN.md.
    """
    source = plan_dir(root, slug)
    if not (source / "PLAN.md").is_file():
        raise PlanError("PLAN_NOT_FOUND", f"plan not found: {source / 'PLAN.md'}")

    archive_root = plans_dir(root) / ARCHIVE_DIR_NAME
    base = f"{merged_on.isoformat()}-{slug}"
    destination = archive_root / base
    suffix = 2
    while destination.exists():
        destination = archive_root / f"{base}-{suffix}"
        suffix += 1
    archive_root.mkdir(parents=True, exist_ok=True)
    shutil.move(source, destination)

    for markdown in sorted(destination.rglob("*.md")):
        old_file = source / markdown.relative_to(destination)
        text = markdown.read_text(encoding="utf-8")
        repaired = _repair_links(text, old_file.parent, markdown.parent, source)
        if repaired != text:
            markdown.write_text(repaired, encoding="utf-8")

    for epic in sorted(epics_dir(root).glob("*.md")):
        text = epic.read_text(encoding="utf-8")
        repointed = text.replace(
            f"](../plans/{slug}/",
            f"](../plans/{ARCHIVE_DIR_NAME}/{destination.name}/",
        )
        if repointed != text:
            epic.write_text(repointed, encoding="utf-8")
    return destination


def _repair_links(text: str, old_dir: Path, new_dir: Path, old_plan: Path) -> str:
    """Recompute relative link targets that pointed outside old_plan."""
    plan_root = os.path.normpath(old_plan)

    def repair(match: re.Match[str]) -> str:
        target = match.group("target")
        if target is None or target.startswith(("/", "#")) or SCHEME_RE.match(target):
            return match.group(0)
        path, hash_sign, anchor = target.partition("#")
        resolved = os.path.normpath(os.path.join(old_dir, path))
        if os.path.commonpath([resolved, plan_root]) == plan_root:
            return match.group(0)
        new_path = Path(os.path.relpath(resolved, new_dir)).as_posix()
        return f"]({new_path}{hash_sign}{anchor})"

    return CODE_OR_LINK_RE.sub(repair, text)
