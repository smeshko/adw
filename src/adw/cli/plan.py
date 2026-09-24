"""`adw plan`: read and write plan directories from the shell.

Prompts call these commands through Bash, so the output is plain text in the
plan skills' shapes: tab-separated rows or `key: value` lines. Errors go to
stderr as `error: <message>`, with exit code 1.
"""

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer

from adw.exceptions import PlanError
from adw.plans.authoring import (
    RESEARCH_REQUIRED,
    add_final_task,
    add_task,
    init_plan,
)
from adw.plans.reader import list_plans, load_plan

plan_app = typer.Typer(
    name="plan",
    help="Read and write plan directories under docs/artifacts/plans/",
)

RootOption = Annotated[
    Path | None,
    typer.Option(
        "--root",
        help="Project root. Defaults to the git toplevel, else the current directory.",
    ),
]


def _root(root: Path | None) -> Path:
    """Resolve --root, else the cwd's git toplevel, else the cwd."""
    if root is not None:
        return root.resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd().resolve()
    return Path(result.stdout.strip())


@contextmanager
def _plan_errors() -> Iterator[None]:
    """Turn a PlanError into `error: <message>` on stderr and exit code 1."""
    try:
        yield
    except PlanError as e:
        typer.echo(f"error: {e.message}", err=True)
        raise typer.Exit(1) from None


@plan_app.command("init")
def init_command(
    title: str = typer.Option(..., "--title", help="Plan title"),
    risk: str = typer.Option(
        ..., "--risk", help="One of: tiny, small, medium, large, high"
    ),
    slug: str | None = typer.Option(
        None, "--slug", help="Override the slug derived from the title"
    ),
    root: RootOption = None,
) -> None:
    """Create a plan: PLAN.md, tasks/, and RESEARCH.md for medium risk and up."""
    with _plan_errors():
        directory = init_plan(_root(root), title=title, risk=risk, slug=slug)
    research = (
        "RESEARCH.md created"
        if risk in RESEARCH_REQUIRED
        else "skipped (risk below medium)"
    )
    typer.echo(f"created: {directory}")
    typer.echo(f"slug:    {directory.name}")
    typer.echo(f"risk:    {risk}")
    typer.echo(f"research: {research}")


@plan_app.command("add-task")
def add_task_command(
    slug: str = typer.Argument(..., help="Plan slug"),
    task_type: str = typer.Option(
        ..., "--type", help="impl (RED/GREEN/REFACTOR) or checklist"
    ),
    title: str = typer.Option(..., "--title", help="Task title"),
    depends: str | None = typer.Option(
        None, "--depends", help="Comma-separated task ids, e.g. TASK-001,TASK-002"
    ),
    root: RootOption = None,
) -> None:
    """Add the next task file and its checkbox line; print its id."""
    depends_on = [d.strip() for d in depends.split(",")] if depends else None
    with _plan_errors():
        task_id = add_task(
            _root(root), slug, task_type=task_type, title=title, depends=depends_on
        )
    typer.echo(task_id)


@plan_app.command("add-final")
def add_final_command(
    slug: str = typer.Argument(..., help="Plan slug"),
    root: RootOption = None,
) -> None:
    """Add the final-validation task; print its id."""
    with _plan_errors():
        task_id = add_final_task(_root(root), slug)
    typer.echo(task_id)


@plan_app.command("list")
def list_command(root: RootOption = None) -> None:
    """Print each plan as slug, status and title, tab-separated."""
    for plan in list_plans(_root(root)):
        typer.echo(f"{plan.slug}\t{plan.status}\t{plan.title}")


@plan_app.command("tasks")
def tasks_command(
    slug: str = typer.Argument(..., help="Plan slug"),
    root: RootOption = None,
) -> None:
    """Print each task as id, done|pending, file and title, tab-separated."""
    project_root = _root(root)
    with _plan_errors():
        plan = load_plan(project_root, slug)
    for task in plan.tasks:
        state = "done" if task.done else "pending"
        file = task.file.relative_to(project_root).as_posix() if task.file else ""
        typer.echo(f"{task.id}\t{state}\t{file}\t{task.title}")


@plan_app.command("show")
def show_command(
    slug: str = typer.Argument(..., help="Plan slug"),
    root: RootOption = None,
) -> None:
    """Print a plan's header fields and task count as key=value lines."""
    project_root = _root(root)
    with _plan_errors():
        plan = load_plan(project_root, slug)
    fields = {
        "slug": plan.slug,
        "title": plan.title,
        "status": plan.status,
        "risk": plan.risk,
        "epic": plan.epic,
        "phase": plan.phase,
        "linear": plan.linear,
        "branch": plan.branch,
        "created": plan.created,
        "dir": plan.path.relative_to(project_root).as_posix(),
        "tasks": f"{sum(task.done for task in plan.tasks)}/{len(plan.tasks)}",
    }
    for key, value in fields.items():
        typer.echo(f"{key}={'none' if value is None else value}")
