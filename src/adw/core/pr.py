"""Pull request creation for ADW runs.

``core.pr`` owns opening a run's PR: it pushes the run's branch, builds the
title and the Linear link, runs ``gh pr create``, and maps ``gh`` failures to
``ADWError`` codes. The ``adw pr`` command (``cli/pr.py``) and the document
extension both call :func:`create_pr`, so every path produces the same PR.

Example:
    >>> body = load_pr_description(run_dir)
    >>> url = create_pr(context, body, base="main")
"""

import logging
import re
from pathlib import Path

from adw.core.constants import PR_DESCRIPTION_ARTIFACT
from adw.exceptions import ADWError
from adw.git import HOOK_TIMEOUT, gh, git
from adw.models import PRDescription, RunContext

logger = logging.getLogger(__name__)

# Only a GitHub PR URL counts, so a stray URL in an unrelated error isn't
# mistaken for the existing PR.
_PR_URL = re.compile(r"https://\S+/pull/\d+")


def generate_pr_title(context: RunContext) -> str:
    """Generate PR title from context, using task_info.title when appropriate.

    When feature_description equals task_id (user ran with just a task ID),
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


def load_pr_description(run_dir: Path) -> str:
    """Load and validate the PR description from a run's artifacts.

    Looks in ``artifacts/document/pr_description.md``,
    then falls back to ``artifacts/pr_description.md``.

    Args:
        run_dir: Path to the run directory (.adw/runs/<run_id>).

    Returns:
        The PR description rendered as markdown.

    Raises:
        ADWError: PR_DESCRIPTION_NOT_FOUND if no description exists, or
            PR_DESCRIPTION_INVALID if it doesn't parse.
    """
    candidates = (
        run_dir / PR_DESCRIPTION_ARTIFACT,
        run_dir / "artifacts" / "pr_description.md",
    )
    pr_path = next((path for path in candidates if path.exists()), None)

    if pr_path is None:
        raise ADWError(
            code="PR_DESCRIPTION_NOT_FOUND",
            message="No PR description found in run artifacts",
            suggestion=(
                "Run the 'document' phase first to generate PR description, "
                "or ensure run completed the full pipeline"
            ),
        )

    try:
        content = pr_path.read_text(encoding="utf-8")
        return PRDescription.from_markdown(content).to_markdown()
    except ValueError as e:
        raise ADWError(
            code="PR_DESCRIPTION_INVALID",
            message=f"Failed to parse PR description: {e}",
            suggestion="Check the pr_description.md file format",
        ) from e


def create_pr(
    context: RunContext,
    body: str,
    *,
    base: str,
    draft: bool = False,
) -> str:
    """Push the run's branch and open its PR with ``gh``.

    The caller owns the body; this function owns the title, the Linear link,
    the push and the ``gh`` call, so every caller produces the same PR.

    Args:
        context: Run context; branch_name, worktree_path, task_id and
            task_info shape the push and the PR.
        body: PR body in markdown.
        base: Base branch for the PR.
        draft: If True, open the PR as a draft.

    Returns:
        URL of the created PR, or of the existing PR for this branch.

    Raises:
        ADWError: GIT_PUSH_FAILED, GH_NOT_INSTALLED, GH_TIMEOUT,
            GH_AUTH_ERROR, GH_NO_COMMITS, GH_PR_FAILED or GH_NO_URL.
    """
    if context.branch_name:
        _push_branch(context.branch_name, context.worktree_path)

    args = [
        "pr",
        "create",
        "--title",
        generate_pr_title(context),
        "--body",
        _with_linear_link(context, body),
        "--base",
        base,
    ]
    if context.branch_name:
        args.extend(["--head", context.branch_name])
    if draft:
        args.append("--draft")

    try:
        # A timeout raises GH_TIMEOUT (recoverable) from gh() itself
        result = gh(*args, timeout=60)
    except FileNotFoundError as e:
        raise ADWError(
            code="GH_NOT_INSTALLED",
            message="GitHub CLI (gh) is not installed or not on PATH",
            suggestion=(
                "Install the GitHub CLI (https://cli.github.com) "
                "or open the PR manually"
            ),
        ) from e

    if result.returncode != 0:
        outcome = _map_gh_failure(f"{result.stderr}\n{result.stdout}".strip())
        if isinstance(outcome, ADWError):
            raise outcome
        logger.info("PR already exists", extra={"pr_url": outcome})
        return outcome

    pr_url = result.stdout.strip()
    if not pr_url:
        raise ADWError(
            code="GH_NO_URL",
            message="gh pr create succeeded but returned no URL",
            suggestion="Check GitHub for the created PR",
        )

    logger.info("PR created", extra={"pr_url": pr_url})
    return pr_url


def _push_branch(branch_name: str, working_dir: Path | None) -> None:
    """Push the branch to origin with upstream tracking.

    Raises:
        ADWError: GIT_PUSH_FAILED on a non-zero exit, timeout or OS error.
    """
    suggestion = f"Check 'git remote -v', then run 'git push -u origin {branch_name}'"
    try:
        # push runs pre-push hooks
        result = git(
            "push", "-u", "origin", branch_name, cwd=working_dir, timeout=HOOK_TIMEOUT
        )
    except ADWError as e:
        # A timeout: keep adw.git's suggestion, which names credentials
        error = e.message
        suggestion = e.suggestion or suggestion
    except OSError as e:
        error = str(e)
    else:
        if result.returncode == 0:
            return
        error = result.stderr.strip() or result.stdout.strip()

    raise ADWError(
        code="GIT_PUSH_FAILED",
        message=f"Failed to push branch '{branch_name}': {error}",
        suggestion=suggestion,
    )


def _with_linear_link(context: RunContext, body: str) -> str:
    """Append the Linear task link to the body."""
    if not (context.task_id and context.task_info):
        return body
    # Team key from the identifier, e.g. "RULE-123" -> "rule"
    identifier = context.task_info.identifier
    team_key = identifier.split("-")[0].lower() if "-" in identifier else "team"
    return f"{body}\n\n---\nLinear: https://linear.app/{team_key}/issue/{identifier}"


def _map_gh_failure(output: str) -> str | ADWError:
    """Map a failed ``gh pr create`` to the existing PR's URL or an error.

    Args:
        output: gh's stderr and stdout.

    Returns:
        The existing PR's URL when gh reports it already exists, otherwise
        the ADWError to raise.
    """
    lowered = output.lower()
    if "already exists" in lowered:
        match = _PR_URL.search(output)
        if match:
            return match.group(0)
    if "auth" in lowered or "login" in lowered:
        return ADWError(
            code="GH_AUTH_ERROR",
            message="GitHub CLI authentication failed",
            suggestion="Run 'gh auth login' to authenticate",
            recoverable=True,
        )
    if "no commits" in lowered:
        return ADWError(
            code="GH_NO_COMMITS",
            message="No commits between base and head branches",
            suggestion="Ensure changes are committed before creating PR",
        )
    return ADWError(
        code="GH_PR_FAILED",
        message=f"Failed to create PR: {output}",
        suggestion="Check gh CLI output for details",
    )
