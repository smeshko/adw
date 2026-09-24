"""The plan templates bundled in adw/defaults/plans/.

They are copies of the plan skills' reference templates. The one deliberate
difference: final validation marks the epic phase done with `adw plan link`.
"""

from importlib.resources import files

from adw.exceptions import PlanError


def read_template(name: str) -> str:
    """Return a bundled plan template's text.

    Raises:
        PlanError: INVALID_PLAN when no template has that name.
    """
    resource = files("adw") / "defaults" / "plans" / name
    if "/" in name or not resource.is_file():
        raise PlanError("INVALID_PLAN", f"unknown plan template: {name!r}")
    return resource.read_text(encoding="utf-8")
