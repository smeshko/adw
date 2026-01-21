"""PR creation command for ADW CLI.

This module provides the pr command that allows users to create
a GitHub PR directly from a completed run.

ISS-026: Base branch is configurable via git.base_branch in project.yaml.
Defaults to 'staging' if not configured.

Examples:
    adw pr 01HQXK5P3Z...              # Create PR from run
    adw pr 01HQXK5P3Z... --draft      # Create as draft PR
"""

import logging
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from adw.cli.bootstrap import get_runs_dir
from adw.core.context_manager import ContextManager
from adw.core.run_lookup import RunLookup
from adw.exceptions import ConfigError
from adw.models import PRDescription, RunContext

logger = logging.getLogger(__name__)

console = Console()


def check_gh_available() -> bool:
    """Check if GitHub CLI (gh) is available in PATH.

    Uses shutil.which to detect if gh is installed and accessible.

    Returns:
        True if gh CLI is available, False otherwise.

    Example:
        >>> if check_gh_available():
        ...     print("gh CLI ready")
    """
    return shutil.which("gh") is not None


def check_git_remote() -> tuple[bool, str]:
    """Check if git remote exists for the current repository.

    Runs `git remote -v` to check for configured remotes.

    Returns:
        Tuple of (has_remote, remote_url).
        If has_remote is True, remote_url contains the origin URL.
        If has_remote is False, remote_url is empty.

    Example:
        >>> has_remote, url = check_git_remote()
        >>> if has_remote:
        ...     print(f"Remote: {url}")
    """
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return False, ""

        # Parse first remote URL (format: "origin  git@... (fetch)")
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    return True, parts[1]
        return False, ""
    except subprocess.TimeoutExpired:
        return False, ""
    except Exception:
        return False, ""


def push_branch_to_remote(
    branch_name: str,
    *,
    working_dir: Path | None = None,
) -> tuple[bool, str]:
    """Push a branch to the remote repository.

    Pushes the specified branch to origin with --set-upstream flag to
    establish tracking. This is required before creating a PR via gh CLI.

    ISS-032: Added to support worktree-based PR creation where the
    feature branch is created locally and needs to be pushed before
    the PR can be created.

    Args:
        branch_name: Name of the branch to push.
        working_dir: Optional working directory for git command.

    Returns:
        Tuple of (success, error_message).
        If success, error_message is empty.

    Example:
        >>> ok, err = push_branch_to_remote("feature/add-auth")
        >>> if not ok:
        ...     print(f"Push failed: {err}")
    """
    cmd = ["git", "push", "-u", "origin", branch_name]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # Allow more time for large pushes
            cwd=working_dir,
        )

        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip()
            return False, error

        return True, ""

    except subprocess.TimeoutExpired:
        return False, "Push timed out after 120 seconds"
    except Exception as e:
        return False, str(e)


def check_gh_authenticated() -> tuple[bool, str]:
    """Check if gh CLI is authenticated.

    Runs `gh auth status` to verify authentication.

    Returns:
        Tuple of (is_authenticated, error_message).
        If authenticated, error_message is empty.

    Example:
        >>> ok, err = check_gh_authenticated()
        >>> if not ok:
        ...     print(f"Auth failed: {err}")
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, ""
        # Extract useful error message
        error = result.stderr.strip() or result.stdout.strip()
        return False, error
    except subprocess.TimeoutExpired:
        return False, "Authentication check timed out"
    except Exception as e:
        return False, str(e)


def create_pr_via_gh(
    title: str,
    body: str,
    *,
    base: str = "staging",
    head_branch: str | None = None,
    draft: bool = False,
    no_open: bool = False,
) -> str:
    """Create a PR using the gh CLI.

    ISS-026: Base branch is configurable, defaults to 'staging'.

    Args:
        title: PR title.
        body: PR body/description in markdown.
        base: Base branch for the PR (default: 'staging').
        head_branch: Head branch for the PR. If provided, explicitly
            specifies the branch with changes. If None, uses current branch.
        draft: If True, create as draft PR.
        no_open: If True, don't open browser after creation.

    Returns:
        URL of the created PR.

    Raises:
        ConfigError: If gh command fails or returns no URL.

    Example:
        >>> url = create_pr_via_gh("Add login", "## Summary\\n...",
        ...                        base="develop", head_branch="adw/01HQ123")
        >>> print(f"Created: {url}")
    """

    cmd = [
        "gh",
        "pr",
        "create",
        "--title",
        title,
        "--body",
        body,
        "--base",
        base,
    ]

    # ISS-025: Explicitly specify head branch if provided
    if head_branch:
        cmd.extend(["--head", head_branch])

    if draft:
        cmd.append("--draft")

    # Note: gh pr create by default does NOT open browser (it just prints URL).
    # The no_open parameter is provided for API completeness but has no effect
    # since browser opening is not the default behavior.
    _ = no_open  # Explicitly acknowledge the parameter (no-op)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip()

            # Check for common auth errors
            if "auth" in error.lower() or "login" in error.lower():
                raise ConfigError(
                    code="GH_AUTH_ERROR",
                    message="GitHub CLI authentication failed",
                    suggestion="Run 'gh auth login' to authenticate",
                    recoverable=True,
                )

            # Check for no commits error
            if "no commits" in error.lower():
                raise ConfigError(
                    code="GH_NO_COMMITS",
                    message="No commits between base and head branches",
                    suggestion="Ensure changes are committed before creating PR",
                    recoverable=False,
                )

            raise ConfigError(
                code="GH_PR_FAILED",
                message=f"Failed to create PR: {error}",
                suggestion="Check gh CLI output for details",
                recoverable=False,
            )

        # gh pr create outputs the PR URL
        pr_url = result.stdout.strip()
        if not pr_url:
            raise ConfigError(
                code="GH_NO_URL",
                message="gh pr create succeeded but returned no URL",
                suggestion="Check GitHub for the created PR",
                recoverable=False,
            )

        return pr_url

    except subprocess.TimeoutExpired as e:
        raise ConfigError(
            code="GH_TIMEOUT",
            message="PR creation timed out after 60 seconds",
            suggestion="Check network connection and try again",
            recoverable=True,
        ) from e


class AutoPRResult:
    """Result of automatic PR creation attempt.

    Attributes:
        success: Whether PR was successfully created.
        pr_url: URL of created PR (if success).
        reason: Reason for skipping/failure (if not success).
        suggestion: Suggestion for user (if not success).
    """

    def __init__(
        self,
        *,
        success: bool,
        pr_url: str = "",
        reason: str = "",
        suggestion: str = "",
    ) -> None:
        """Initialize AutoPRResult.

        Args:
            success: Whether PR was created.
            pr_url: URL of created PR.
            reason: Reason for failure.
            suggestion: Suggestion for user.
        """
        self.success = success
        self.pr_url = pr_url
        self.reason = reason
        self.suggestion = suggestion


def can_auto_create_pr() -> tuple[bool, str]:
    """Check if automatic PR creation is possible.

    Verifies all prerequisites for automatic PR creation:
    1. Git remote exists
    2. gh CLI is available
    3. gh CLI is authenticated

    Returns:
        Tuple of (can_create, reason).
        If can_create is True, reason is empty.
        If can_create is False, reason explains why.

    Example:
        >>> can_create, reason = can_auto_create_pr()
        >>> if not can_create:
        ...     print(f"Cannot auto-create PR: {reason}")
    """
    # Check git remote
    has_remote, _ = check_git_remote()
    if not has_remote:
        return False, "No git remote configured"

    # Check gh CLI
    if not check_gh_available():
        return False, "GitHub CLI (gh) not installed"

    # Check gh authentication
    authenticated, auth_error = check_gh_authenticated()
    if not authenticated:
        return False, f"GitHub CLI not authenticated: {auth_error}"

    return True, ""


def auto_create_pr(
    run_id: str,
    context: "RunContext",
    runs_dir: Path,
) -> AutoPRResult:
    """Automatically create a PR after successful run completion.

    This function attempts to create a PR using the generated PR description.
    It does not raise exceptions for failures - instead returns an AutoPRResult
    indicating what happened. This allows the run to complete even if PR
    creation fails.

    ISS-026: Base branch is read from git.base_branch in project.yaml config,
    with 'staging' as the default. Uses context.branch_name as the explicit
    head branch to ensure PR is created from the correct branch.

    Args:
        run_id: ID of the completed run.
        context: RunContext with feature description and branch_name.
        runs_dir: Path to runs directory.

    Returns:
        AutoPRResult indicating success/failure and details.

    Example:
        >>> result = auto_create_pr(run_id, context, runs_dir)
        >>> if result.success:
        ...     print(f"PR created: {result.pr_url}")
        ... else:
        ...     print(f"Skipped: {result.reason}")
    """
    # Check prerequisites
    can_create, reason = can_auto_create_pr()
    if not can_create:
        suggestion = ""
        if "remote" in reason.lower():
            suggestion = "Push to a remote repository first"
        elif "installed" in reason.lower():
            suggestion = "Install GitHub CLI: brew install gh"
        elif "authenticated" in reason.lower():
            suggestion = "Run 'gh auth login' to authenticate"

        return AutoPRResult(
            success=False,
            reason=reason,
            suggestion=suggestion,
        )

    # Load PR description
    run_dir = runs_dir / run_id
    try:
        pr_desc = _load_pr_description(run_dir)
    except ConfigError as e:
        return AutoPRResult(
            success=False,
            reason=e.message,
            suggestion=e.suggestion or "Ensure document phase completed",
        )

    # Generate PR title (Story 12.6: PR-Task Linking, ISS-037: task_info.title fallback)
    pr_title = _generate_pr_title(context)

    # Convert to markdown
    pr_body = pr_desc.to_markdown()

    # Add Linear task link to PR body (Story 12.6: PR-Task Linking)
    if context.task_id and context.task_info:
        # Get team key from task_info.identifier (e.g., "RULE-123" -> "rule")
        identifier = context.task_info.identifier
        team_key = identifier.split("-")[0].lower() if "-" in identifier else "team"
        task_url = f"https://linear.app/{team_key}/issue/{identifier}"
        pr_body = f"{pr_body}\n\n---\nLinear: {task_url}"

    # Get base branch from config (ISS-026: defaults to staging)
    base_branch = _get_base_branch(run_dir)

    # Push branch to remote before creating PR (ISS-032)
    # This is required when using worktrees since the feature branch is
    # created locally and needs to be pushed before gh pr create can work
    if context.branch_name:
        push_ok, push_error = push_branch_to_remote(
            context.branch_name,
            working_dir=context.worktree_path,
        )
        if not push_ok:
            return AutoPRResult(
                success=False,
                reason=f"Failed to push branch: {push_error}",
                suggestion="Check git remote configuration and try 'git push' manually",
            )

    # Create the PR
    try:
        pr_url = create_pr_via_gh(
            pr_title,
            pr_body,
            base=base_branch,
            head_branch=context.branch_name,
            draft=False,
            no_open=True,
        )

        # Store PR URL in run artifacts
        _store_pr_url(context, pr_url, runs_dir)

        return AutoPRResult(success=True, pr_url=pr_url)

    except ConfigError as e:
        return AutoPRResult(
            success=False,
            reason=e.message,
            suggestion=e.suggestion or "Check gh CLI output for details",
        )


def display_manual_instructions(
    description: str,
    title: str,
    base: str,
) -> None:
    """Display instructions for manual PR creation.

    Shows the PR description and GitHub URL pattern for users
    who don't have gh CLI installed.

    Args:
        description: Markdown PR description.
        title: Suggested PR title.
        base: Suggested base branch.

    Example:
        >>> display_manual_instructions("## Summary\\n...", "Add login", "main")
    """
    console.print()
    console.print(
        Panel(
            "[yellow]GitHub CLI (gh) not found[/]\n\n"
            "To create a PR automatically, install gh:\n"
            "  • macOS: [cyan]brew install gh[/]\n"
            "  • Linux: [cyan]sudo apt install gh[/] or [cyan]sudo dnf install gh[/]\n"
            "  • Windows: [cyan]winget install GitHub.cli[/]\n\n"
            "After installing, run [cyan]gh auth login[/] to authenticate.",
            title="Manual PR Creation Required",
            border_style="yellow",
        )
    )

    console.print()
    console.print("[bold]Suggested PR Title:[/]")
    console.print(f"  {title}")

    console.print()
    console.print("[bold]Base Branch:[/]")
    console.print(f"  {base}")

    console.print()
    console.print("[bold]PR Description (copy this):[/]")
    console.print()

    # Show description with syntax highlighting
    syntax = Syntax(description, "markdown", theme="monokai", word_wrap=True)
    console.print(Panel(syntax, border_style="dim"))

    console.print()
    console.print("[dim]To create the PR manually:[/]")
    console.print("  1. Push your branch to GitHub")
    console.print("  2. Go to your repository on GitHub")
    console.print("  3. Click 'Compare & pull request'")
    console.print("  4. Paste the description above")
    console.print()


def _get_pr_description_path(run_dir: Path) -> Path | None:
    """Find the PR description artifact in a run directory.

    Args:
        run_dir: Path to the run directory.

    Returns:
        Path to pr_description.md if found, None otherwise.
    """
    # Check in artifacts/document/ (Story 9.4 location)
    artifact_path = run_dir / "artifacts" / "document" / "pr_description.md"
    if artifact_path.exists():
        return artifact_path

    # Fallback: check artifacts root
    fallback_path = run_dir / "artifacts" / "pr_description.md"
    if fallback_path.exists():
        return fallback_path

    return None


def _load_pr_description(run_dir: Path) -> PRDescription:
    """Load PR description from run artifacts.

    Args:
        run_dir: Path to the run directory.

    Returns:
        Parsed PRDescription model.

    Raises:
        ConfigError: If PR description not found or invalid.
    """
    pr_path = _get_pr_description_path(run_dir)

    if not pr_path:
        raise ConfigError(
            code="PR_DESCRIPTION_NOT_FOUND",
            message="No PR description found in run artifacts",
            suggestion=(
                "Run the 'document' phase first to generate PR description, "
                "or ensure run completed the full pipeline"
            ),
            recoverable=False,
        )

    try:
        content = pr_path.read_text(encoding="utf-8")
        return PRDescription.from_markdown(content)
    except ValueError as e:
        raise ConfigError(
            code="PR_DESCRIPTION_INVALID",
            message=f"Failed to parse PR description: {e}",
            suggestion="Check the pr_description.md file format",
            recoverable=False,
        ) from e


def _get_base_branch(run_dir: Path) -> str:
    """Get the base branch for PR creation.

    ISS-026: Reads git.base_branch from project.yaml config.
    Falls back to 'staging' if not configured.

    Args:
        run_dir: Path to the run directory (.adw/runs/<run_id>).

    Returns:
        Base branch name from config, or 'staging' as default.
    """
    from adw.config.loader import ConfigLoader

    # .adw/runs/<id> -> project root
    project_root = run_dir.parent.parent.parent

    try:
        loader = ConfigLoader(project_root)
        if loader.has_project_config:
            config = loader.load()
            if config.git.base_branch:
                return config.git.base_branch
    except Exception:
        # Config loading failed - use default
        pass

    return "staging"


def _generate_pr_title(context: RunContext) -> str:
    """Generate PR title from context, using task_info.title when appropriate.

    ISS-037: When feature_description equals task_id (user ran with just a task ID),
    use task_info.title from Linear to create a meaningful PR title.

    Title generation logic:
    1. If feature_description == task_id and task_info.title exists:
       → "{task_id}: {task_info.title}"
    2. If feature_description == task_id but no task_info:
       → "{task_id}" (no redundant duplication)
    3. If feature_description != task_id and task_id exists:
       → "{task_id}: {feature_description}"
    4. If no task_id:
       → "{feature_description}"

    Args:
        context: RunContext with feature_description, task_id, and task_info.

    Returns:
        PR title string, truncated to 72 chars if necessary.
    """
    pr_title = context.feature_description

    if context.task_id and context.feature_description == context.task_id:
        # Feature description is just the task ID - try task title from Linear
        task_title = (
            context.task_info.title.strip()
            if context.task_info and context.task_info.title
            else ""
        )
        if task_title:
            pr_title = f"{context.task_id}: {task_title}"
            logger.info(
                "Using task title from Linear: %s - %s",
                context.task_id,
                task_title,
            )
        else:
            # Fallback to just the task ID (no redundant duplication)
            pr_title = context.task_id
            logger.debug("No task title available, using task ID: %s", context.task_id)
    elif context.task_id:
        # Normal case: prefix with task ID
        pr_title = f"{context.task_id}: {context.feature_description}"

    if len(pr_title) > 72:
        pr_title = pr_title[:69] + "..."

    return pr_title


def _store_pr_url(context: RunContext, pr_url: str, runs_dir: Path) -> RunContext:
    """Store PR URL in run context.

    Updates the run context with the PR URL and saves it.

    Args:
        context: Current run context.
        pr_url: URL of the created PR.
        runs_dir: Path to runs directory.

    Returns:
        Updated RunContext with PR URL in artifacts.
    """
    context_manager = ContextManager(runs_dir)

    # Add PR URL to artifacts under 'pr' key
    new_artifacts = dict(context.artifacts)
    if "pr" not in new_artifacts:
        new_artifacts["pr"] = []
    new_artifacts["pr"].append(pr_url)

    updated_context = context.model_copy(update={"artifacts": new_artifacts})
    context_manager.save(updated_context)

    return updated_context


def pr(
    run_id: str | None = typer.Argument(
        None,
        help="Run ID to create PR from (defaults to most recent completed)",
    ),
    draft: bool = typer.Option(
        False,
        "--draft",
        "-d",
        help="Create as draft PR",
    ),
    no_open: bool = typer.Option(
        False,
        "--no-open",
        help="Don't open browser after creation (gh default is to open)",
    ),
) -> None:
    """Create a GitHub PR from a completed run.

    Uses the PR description generated during the document phase
    to create a pull request via the gh CLI.

    If gh is not available, displays the PR description for
    manual copy-paste.

    ISS-026: Base branch is read from git.base_branch in project.yaml config.
    Defaults to 'staging' if not configured.

    Examples:
        adw pr                         # Most recent completed run
        adw pr 01HQXK5P3Z...           # Specific run
        adw pr --draft                 # Create as draft PR
    """
    runs_dir = get_runs_dir()
    lookup = RunLookup(runs_dir)

    # Find the run
    if run_id:
        context = lookup.find_by_id(run_id)
        if not context:
            console.print(
                Panel(
                    f"[red]Run not found:[/] {run_id}\n\n"
                    "[dim]Use 'adw list' to see available runs[/]",
                    title="[red]RUN_NOT_FOUND[/]",
                    border_style="red",
                )
            )
            raise typer.Exit(1)
    else:
        # Find most recent completed run
        context = lookup.find_most_recent()
        if not context:
            console.print("[yellow]No runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
            raise typer.Exit(1)

    # Check run is complete
    if context.status not in ("completed",):
        console.print(
            Panel(
                f"[red]Run is not complete[/]\n\n"
                f"Run ID: {context.run_id}\n"
                f"Status: [yellow]{context.status}[/]\n\n"
                "PR creation requires a completed run with all phases finished.",
                title="[red]RUN_NOT_COMPLETE[/]",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Load PR description from artifacts
    run_dir = runs_dir / context.run_id
    try:
        pr_desc = _load_pr_description(run_dir)
    except ConfigError as e:
        console.print(
            Panel(
                f"[red]{e.message}[/]\n\n[dim]Suggestion:[/] {e.suggestion}",
                title=f"[red]{e.code}[/]",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None

    # ISS-026: Base branch from config (defaults to staging)
    base_branch = _get_base_branch(run_dir)

    # Generate PR title (ISS-037: use helper for consistent title generation)
    pr_title = _generate_pr_title(context)

    # Convert to markdown
    pr_body = pr_desc.to_markdown()

    # Check if gh is available
    if not check_gh_available():
        display_manual_instructions(pr_body, pr_title, base_branch)
        raise typer.Exit(0)

    # Check gh authentication
    authenticated, auth_error = check_gh_authenticated()
    if not authenticated:
        console.print(
            Panel(
                f"[red]GitHub CLI not authenticated[/]\n\n"
                f"{auth_error}\n\n"
                "[dim]Run 'gh auth login' to authenticate[/]",
                title="[red]GH_AUTH_ERROR[/]",
                border_style="red",
            )
        )
        # Still show manual instructions as fallback
        display_manual_instructions(pr_body, pr_title, base_branch)
        raise typer.Exit(1)

    # Push branch to remote before creating PR (ISS-032)
    if context.branch_name:
        console.print(f"[dim]Pushing branch:[/] {context.branch_name}")
        push_ok, push_error = push_branch_to_remote(
            context.branch_name,
            working_dir=context.worktree_path,
        )
        if not push_ok:
            console.print(
                Panel(
                    f"[red]Failed to push branch[/]\n\n{push_error}\n\n"
                    "[dim]Try 'git push' manually[/]",
                    title="[red]GIT_PUSH_FAILED[/]",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

    # Create the PR
    console.print(f"[bold]Creating PR from run:[/] {context.run_id}")
    console.print(f"[dim]Base branch:[/] {base_branch}")
    if draft:
        console.print("[dim]Mode:[/] Draft PR")
    console.print()

    try:
        # ISS-026: Use base_branch from config and explicit head branch from context
        pr_url = create_pr_via_gh(
            pr_title,
            pr_body,
            base=base_branch,
            head_branch=context.branch_name,
            draft=draft,
            no_open=no_open,
        )

        # Store PR URL in run artifacts
        _store_pr_url(context, pr_url, runs_dir)

        console.print(
            Panel(
                f"[green]PR created successfully![/]\n\n{pr_url}",
                title="[green]✓ Pull Request Created[/]",
                border_style="green",
            )
        )

    except ConfigError as e:
        console.print(
            Panel(
                f"[red]{e.message}[/]\n\n[dim]Suggestion:[/] {e.suggestion}",
                title=f"[red]{e.code}[/]",
                border_style="red",
            )
        )
        # Show manual instructions as fallback
        console.print()
        console.print("[yellow]Falling back to manual instructions:[/]")
        display_manual_instructions(pr_body, pr_title, base_branch)
        raise typer.Exit(1) from None
