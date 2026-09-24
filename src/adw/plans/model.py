"""A plan as parsed from its PLAN.md."""

from pathlib import Path

from pydantic import BaseModel, Field


class PlanTask(BaseModel):
    """One checkbox line of a plan's "## Tasks" section.

    Attributes:
        id: The task id, e.g. "TASK-003".
        title: The title, without the "(depends on …)" suffix.
        done: Whether the box is ticked.
        depends_on: Ids from the "(depends on …)" suffix.
        file: The matching tasks/TASK-NNN-*.md file, if there is one.
    """

    id: str
    title: str
    done: bool
    depends_on: list[str] = Field(default_factory=list)
    file: Path | None = None


class Plan(BaseModel):
    """A plan directory's PLAN.md: its header fields and its tasks.

    Header fields hold the first token of their value, so `epic` is "04" and
    `phase` is "4.1" rather than the display text after them. A field that is
    missing or reads "none" is None.

    Attributes:
        slug: The plan directory's name.
        path: The plan directory.
        title: The text after "# Plan:", or "" when there is none.
        status: draft, ready, in-progress or done; "unknown" when missing.
        risk: tiny, small, medium, large or high.
        epic: The linked epic's number.
        phase: The linked epic phase's id.
        linear: The phase's Linear issue id.
        branch: The feature branch that implement-plan recorded.
        created: The creation date, YYYY-MM-DD.
        tasks: The "## Tasks" checkbox lines, in order.
    """

    slug: str
    path: Path
    title: str = ""
    status: str = "unknown"
    risk: str | None = None
    epic: str | None = None
    phase: str | None = None
    linear: str | None = None
    branch: str | None = None
    created: str | None = None
    tasks: list[PlanTask] = Field(default_factory=list)
