"""Archive a merged plan: move it under plans/archive/ and repair its links.

The file move ports archive-plan's archive_plan.sh; its git and GitHub steps
(the merged-PR check, checkout, pull and branch delete) stay with the caller.
The script leaves relative links broken, because the plan moves one level
deeper; archive_plan repairs them.
"""

import os
import re
import shutil
from contextlib import suppress
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

    The archive is built as a copy, swapped in with a rename, and the source
    is dropped last. Epics are rewritten atomically. If any step raises, the
    copy is removed and the epics are restored, so the plan stays where it
    was and a retry starts clean; if an epic can't be restored, the copy is
    kept so its link still resolves, and the error's notes name the epic.
    A hard kill mid-way is recovered through git: every file this touches
    is tracked, so restore the plans and epics dirs and retry.

    Args:
        root: Project root.
        slug: The plan's slug.
        merged_on: The date its PR merged.

    Returns:
        The archived plan directory.

    Raises:
        PlanError: INVALID_PLAN for an unusable slug, PLAN_NOT_FOUND when the
            plan has no PLAN.md.
        OSError: A read or write failed; nothing was changed.
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
    staging = archive_root / f".{destination.name}.tmp"
    discarded = archive_root / f".{destination.name}.old"
    epics = _repointed_epics(root, slug, destination.name)

    archive_root.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(discarded, ignore_errors=True)
    try:
        shutil.copytree(source, staging)
        for markdown in sorted(staging.rglob("*.md")):
            relative = markdown.relative_to(staging)
            text = markdown.read_text(encoding="utf-8")
            repaired = _repair_links(
                text,
                (source / relative).parent,
                (destination / relative).parent,
                source,
            )
            if repaired != text:
                markdown.write_text(repaired, encoding="utf-8")
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    replaced: list[Path] = []
    try:
        for epic, (_, repointed) in epics.items():
            _write_atomically(epic, repointed)
            replaced.append(epic)
        source.rename(discarded)
    except BaseException as error:
        unrestored = []
        for epic in replaced:
            try:
                _write_atomically(epic, epics[epic][0])
            except OSError:
                unrestored.append(epic.name)
        if unrestored:
            error.add_note(
                f"could not restore {', '.join(unrestored)}, which still link to "
                f"{destination}; that copy is kept. Restore them from git."
            )
        else:
            shutil.rmtree(destination, ignore_errors=True)
        raise
    shutil.rmtree(discarded, ignore_errors=True)
    return destination


def _write_atomically(path: Path, text: str) -> None:
    """Replace a file's text in one step, so a failure leaves the old text."""
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    except BaseException:
        with suppress(OSError):
            temporary.unlink()
        raise


def _repointed_epics(
    root: Path, slug: str, archived_name: str
) -> dict[Path, tuple[str, str]]:
    """Map each epic that links into the plan to its (original, repointed) text."""
    epics: dict[Path, tuple[str, str]] = {}
    for epic in sorted(epics_dir(root).glob("*.md")):
        text = epic.read_text(encoding="utf-8")
        repointed = text.replace(
            f"](../plans/{slug}/",
            f"](../plans/{ARCHIVE_DIR_NAME}/{archived_name}/",
        )
        if repointed != text:
            epics[epic] = (text, repointed)
    return epics


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
