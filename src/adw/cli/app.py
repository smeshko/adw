"""Main Typer CLI application for ADW."""

from datetime import UTC, datetime
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from ulid import ULID

from adw.cli.bootstrap import create_log_manager, create_orchestrator
from adw.cli.dry_run import DryRunDisplay
from adw.cli.init import init as init_impl
from adw.cli.list import list_runs
from adw.cli.logs import logs_app
from adw.cli.pr import pr as pr_command
from adw.cli.register import register as register_command
from adw.cli.resume import resume as resume_command
from adw.cli.run_display import RunDisplay
from adw.cli.status import status as status_command
from adw.cli.validators import validate_phase
from adw.cli.webhook import webhook_app
from adw.commands.template import escape_feature_description
from adw.config.loader import ConfigLoader
from adw.exceptions import ADWError, ConfigError
from adw.models.config import ProjectConfig
from adw.models.logging import Verbosity
from adw.models.task import TaskInfo
from adw.task_managers import InputResolver, InputType, TaskManagerFactory

console = Console()
app = typer.Typer(
    name="adw",
    help="Agentic Development Workflow SDK",
    add_completion=True,
)


@app.command(name="init")
def init(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration",
    ),
    language: str | None = typer.Option(
        None,
        "--language",
        "-l",
        help="Override detected language (python, javascript, go, rust, etc.)",
    ),
    wizard: bool = typer.Option(
        False,
        "--wizard",
        "-w",
        help="Force wizard mode, skip initial prompt",
    ),
    no_interactive: bool = typer.Option(
        False,
        "--no-interactive",
        "-n",
        help="Force minimal mode, no prompts",
    ),
) -> None:
    """Initialize ADW in the current directory.

    Creates .adw/ directory with project configuration.
    Auto-detects project type and sets appropriate defaults.

    Examples:
        adw init                    # Auto-detect and initialize (prompts for mode)
        adw init --force            # Reinitialize existing project
        adw init --language python  # Override detection
        adw init --wizard           # Force interactive wizard mode
        adw init --no-interactive   # Force minimal setup, no prompts
    """
    # Check mutually exclusive flags
    if wizard and no_interactive:
        console.print(
            "[red]Error:[/] --wizard and --no-interactive are mutually exclusive."
        )
        raise typer.Exit(1)

    try:
        init_impl(
            force=force,
            language=language,
            wizard=wizard,
            no_interactive=no_interactive,
        )
    except ConfigError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1) from None


def _load_env_file() -> None:
    """Load environment variables from .adw/.env if it exists.

    This enables per-project credential configuration for task managers
    (e.g., LINEAR_API_KEY, LINEAR_TEAM_ID) without requiring global
    shell environment variables.

    The file is loaded silently - no error if it doesn't exist.
    Existing environment variables are NOT overwritten (dotenv default).
    """
    env_path = Path.cwd() / ".adw" / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Show errors only (minimal output)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed output including debug info"
    ),
    trace: bool = typer.Option(
        False, "--trace", help="Show all output including trace-level debugging"
    ),
) -> None:
    """Agentic Development Workflow SDK CLI."""
    # Load environment from .adw/.env before any command runs (ISS-028)
    _load_env_file()

    # Handle mutual exclusivity of verbosity flags
    verbosity_flags = sum([quiet, verbose, trace])
    if verbosity_flags > 1:
        console.print(
            "[red]Error:[/] Verbosity flags are mutually exclusive. "
            "Use only one of: --quiet, --verbose, --trace"
        )
        raise typer.Exit(1)

    # Determine verbosity level
    if quiet:
        verbosity = Verbosity.QUIET
    elif trace:
        verbosity = Verbosity.TRACE
    elif verbose:
        verbosity = Verbosity.VERBOSE
    else:
        verbosity = Verbosity.NORMAL

    # Store verbosity in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbosity"] = verbosity

    if version:
        from adw import __version__

        console.print(f"adw version {__version__}")
        raise typer.Exit()


@app.command()
def run(
    ctx: typer.Context,
    feature: str = typer.Argument(
        ...,
        help="Feature description to implement",
        metavar="FEATURE_DESCRIPTION",
    ),
    phase: str | None = typer.Option(
        None,
        "--phase",
        "-p",
        help="Execute single phase only (plan, build, validate, document)",
        callback=validate_phase,
    ),
    from_run: str | None = typer.Option(
        None,
        "--from-run",
        "-f",
        help="Load artifacts from this run ID (required for phases after plan)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would happen without executing",
    ),
    allow_dangerous: bool = typer.Option(
        False,
        "--allow-dangerous",
        help="Allow dangerous LLM tool calls (log warnings instead of blocking)",
    ),
    no_worktree: bool = typer.Option(
        False,
        "--no-worktree",
        help="Run in current directory instead of isolated worktree (Story 10.1)",
    ),
    task_id: bool = typer.Option(
        False,
        "--task-id",
        help="Force input to be interpreted as task ID (error if not recognized)",
    ),
    no_task_manager: bool = typer.Option(
        False,
        "--no-task-manager",
        help="Ignore task manager, treat input as literal feature string",
    ),
) -> None:
    """Run the agentic development workflow.

    Execute the full pipeline or a single phase.

    Examples:
        # Full pipeline
        adw run "Add user authentication"

        # Single phase (plan doesn't need --from-run)
        adw run --phase plan "Add login"

        # Single phase with artifacts from previous run
        adw run --phase build --from-run 01HQXK5P3Z7V "Add login"

        # Dry run to see what would happen
        adw run "Add login" --dry-run

        # Allow dangerous operations (log warnings instead of blocking)
        adw run "Add login" --allow-dangerous

        # View real-time LLM output (run in separate terminal)
        adw logs follow <run_id>

        # Run without worktree isolation (in current directory)
        adw run "Quick fix" --no-worktree

        # Task manager integration (Story 12.4)
        adw run RULE-123                    # Auto-detect as task ID
        adw run RULE-123 --task-id          # Force task ID interpretation
        adw run RULE-123 --no-task-manager  # Force feature string
    """
    # Validate feature description is not empty (Story 6.1)
    if not feature.strip():
        console.print("[red]Error:[/] Feature description cannot be empty")
        raise typer.Exit(code=1)

    # Validate mutually exclusive task manager flags (Story 12.4)
    if task_id and no_task_manager:
        console.print(
            "[red]Error:[/] --task-id and --no-task-manager are mutually exclusive"
        )
        raise typer.Exit(code=1)

    # Load config for task manager configuration (Story 12.8)

    task_manager_config = None
    try:
        config = ConfigLoader().load()
        task_manager_config = config.task_manager
    except ConfigError:
        # No config or invalid - use default
        pass

    # Resolve input: task ID vs feature string (Story 12.4 Task 4)
    # Creates a task manager with config and uses InputResolver to auto-detect
    # When --no-task-manager is used, bypass config entirely to avoid initialization
    # errors (e.g., missing LINEAR_API_KEY) even when user doesn't want task manager
    task_type_to_use = (
        "none"
        if no_task_manager
        else (task_manager_config.type if task_manager_config else "none")
    )
    task_manager = TaskManagerFactory().create(
        task_type=task_type_to_use,
        config=task_manager_config if not no_task_manager else None,
    )
    resolver = InputResolver(task_manager)
    try:
        resolved = resolver.resolve(
            feature,
            force_task_id=task_id,
            force_feature=no_task_manager,
        )
    except ValueError as e:
        # --task-id was used but input doesn't match pattern
        console.print(f"[red]Error:[/] {e}")
        console.print(
            "[dim]Suggestion:[/] Remove --task-id to treat as feature description, "
            "or use a valid task ID"
        )
        raise typer.Exit(code=1) from None

    # Fetch task info to get internal UUID for issue closing and labels
    # (Story 12.8, ISS-033)
    task_uuid: str | None = None
    task_info: TaskInfo | None = None
    if resolved.type == InputType.TASK_ID and resolved.task_id:
        console.print(f"[dim]Resolved as task ID:[/] {resolved.task_id}")
        try:
            task_info = task_manager.fetch_task(resolved.task_id)
            task_uuid = task_info.id  # Internal UUID for issue closing
            console.print(f"[dim]Task:[/] {task_info.title}")
        except Exception as e:
            # Non-blocking - continue without task_info/task_uuid, but warn user
            console.print(
                f"[yellow]Warning:[/] Failed to fetch task '{resolved.task_id}': {e}"
            )
            console.print(
                "[dim]Continuing without task context. "
                "The LLM will only see the task ID, not its contents.[/]"
            )
            task_info = None
        if not task_id:  # Auto-detected, not forced
            console.print(
                "[dim]Tip:[/] Use --no-task-manager if you meant this "
                "as a feature description"
            )
    # Note: Feature strings don't need logging - that's the default expectation

    # Escape special characters for template safety (Story 6.1 Task 5)
    # Note: safe_feature will be used when templates need the escaped version
    _ = escape_feature_description(feature)

    # Generate run ID and timestamp (Story 6.1)
    run_id = str(ULID())
    started_at = datetime.now(UTC)

    # Show run header using RunDisplay (UX-12, Story 6.1)
    run_display = RunDisplay(console)
    run_display.show_run_header(
        run_id=run_id,
        feature=feature,
        started_at=started_at,
    )

    if dry_run:
        # Load config for dry-run preview (Story UX-FIX-ISS-002)
        dry_run_config: ProjectConfig | None
        try:
            dry_run_config = ConfigLoader().load()
        except ConfigError:
            dry_run_config = None

        # Determine runs directory for artifact lookup
        runs_dir = Path.cwd() / ".adw" / "runs"

        # Show detailed dry-run preview
        dry_run_display = DryRunDisplay(console)
        dry_run_display.show_execution_preview(
            feature=feature,
            phase=phase,
            from_run=from_run,
            config=dry_run_config,
            runs_dir=runs_dir if runs_dir.exists() else None,
        )
        return

    # Get verbosity from context (Story 7.2)
    verbosity = Verbosity.NORMAL
    if ctx.obj:
        verbosity = ctx.obj.get("verbosity", Verbosity.NORMAL)

    # Calculate run directory for file logging
    runs_dir = Path.cwd() / ".adw" / "runs"
    run_dir = runs_dir / run_id

    # Create log manager with file transports (Story 7.2, ISS-003, ISS-006 fix)
    # This wires up Python logging to LogManager, so all logging.getLogger() calls
    # in ADW modules flow through to live.log for debugging via `adw logs follow`
    create_log_manager(console, verbosity=verbosity, run_dir=run_dir)

    try:
        # Pass task_manager and task_info for StatusSyncService/LabelManager
        orchestrator = create_orchestrator(
            console,
            allow_dangerous=allow_dangerous,
            run_id=run_id,
            task_manager=task_manager,
            task_info=task_info,
        )

        if phase:
            # Validate --from-run requirement for non-plan phases (Story 5.4)
            if phase != "plan" and from_run is None:
                console.print(
                    f"[red]Error:[/] Phase '{phase}' requires artifacts "
                    "from previous phases"
                )
                console.print(
                    "[dim]Suggestion:[/] Use --from-run <run_id> to specify source run"
                )
                raise typer.Exit(1)

            # Single phase execution (Story 5.4, Story 10.1: pass use_worktree flag)
            context = orchestrator.run_single_phase(
                phase, feature, from_run, run_id=run_id, use_worktree=not no_worktree
            )
            console.print(
                f"[green]✓[/] Single phase '{phase}' completed: {context.run_id}"
            )
        else:
            # Full pipeline execution (Story 10.1: pass use_worktree flag)
            # (Story 12.8: pass task_uuid for issue closing)
            context = orchestrator.run(
                feature,
                run_id=run_id,
                use_worktree=not no_worktree,
                task_uuid=task_uuid,
            )
            console.print(f"[green]✓[/] Run completed: {context.run_id}")

    except ConfigError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1) from None
    except ADWError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1) from None
    except RuntimeError as e:
        # PhaseRunner not set - infrastructure not ready
        console.print(f"[red]Error:[/] {e}")
        console.print("[dim]Suggestion:[/] Ensure phase commands are in .adw/commands/")
        raise typer.Exit(1) from None


@app.command()
def abort(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to abort",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Abort without confirmation",
    ),
) -> None:
    """Abort a running execution.

    The run must be in 'running' status to be aborted.
    Use --force to skip the confirmation prompt.

    Examples:
        adw abort 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw abort 01HQXK5P3Z7V8R2M4N6T9W1Y3C --force
    """
    from adw.cli.abort import abort_command

    try:
        abort_command(run_id=run_id, force=force)
    except ConfigError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1) from None


# Register the resume command (Story 6.2)
app.command()(resume_command)

# Register the status command (Story 6.3)
app.command()(status_command)

# Register the list command (Story 6.4)
# Note: We use name="list" since list_runs avoids Python keyword conflict
app.command(name="list")(list_runs)

# Register the logs subapp (Story 7.5)
app.add_typer(logs_app, name="logs")

# Register the pr command (Story 9.5)
app.command()(pr_command)

# Register the register command (Story 16.1)
app.command()(register_command)

# Register the webhook subapp (Story 13.1)
app.add_typer(webhook_app, name="webhook")


@app.command()
def cleanup(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to clean up",
    ),
    delete_branch: bool = typer.Option(
        False,
        "--delete-branch",
        "-b",
        help="Also delete the adw/<run_id> branch after removing worktree",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force cleanup without confirmation (required if worktree has changes)",
    ),
) -> None:
    """Clean up worktree and optionally branch for a run.

    Removes the worktree directory created for a run. By default, preserves
    the branch for debugging or later PR creation.

    Use --delete-branch to also remove the branch. Branches with existing
    PRs or unpushed commits will be preserved unless --force is used.

    Examples:
        adw cleanup 01HQXK5P3Z7V8R2M4N6T9W1Y3C
        adw cleanup 01HQXK5P3Z7V8R2M4N6T9W1Y3C --delete-branch
        adw cleanup 01HQXK5P3Z7V8R2M4N6T9W1Y3C --force --delete-branch
    """
    from adw.cli.cleanup import cleanup_command

    try:
        cleanup_command(run_id=run_id, delete_branch=delete_branch, force=force)
    except ConfigError as e:
        console.print(f"[red]Error:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1) from None


@app.command(name="cleanup-orphans")
def cleanup_orphans(
    delete_branch: bool = typer.Option(
        False,
        "--delete-branch",
        "-b",
        help="Also delete the adw/<run_id> branch for each orphaned worktree",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt and force remove even with uncommitted changes",
    ),
) -> None:
    """Find and remove orphaned worktrees.

    Scans for worktrees that don't have corresponding active lock files
    (from crashed or killed runs) and removes them after confirmation.

    Examples:
        adw cleanup-orphans
        adw cleanup-orphans --delete-branch
        adw cleanup-orphans --force
    """
    from adw.cli.cleanup import cleanup_orphans_command

    cleanup_orphans_command(delete_branch=delete_branch, force=force)
