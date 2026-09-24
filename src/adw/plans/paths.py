"""Where plans live, and how titles become slugs."""

import re
from pathlib import Path

from adw.exceptions import PlanError

ARCHIVE_DIR_NAME = "archive"


def plans_dir(root: Path) -> Path:
    """Return the directory that holds every plan under a project root."""
    return root / "docs" / "artifacts" / "plans"


def plan_dir(root: Path, slug: str) -> Path:
    """Return a plan's directory.

    Raises:
        PlanError: INVALID_PLAN when the slug is empty, reserved for the
            archive, starts with a dot, or contains a path separator.
    """
    if (
        not slug
        or slug == ARCHIVE_DIR_NAME
        or slug.startswith(".")
        or "/" in slug
        or "\\" in slug
    ):
        raise PlanError("INVALID_PLAN", f"invalid plan slug: {slug!r}")
    return plans_dir(root) / slug


def slugify(text: str) -> str:
    """Lowercase text and join its runs of letters and digits with dashes."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
