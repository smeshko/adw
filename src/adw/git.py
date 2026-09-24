"""Every git and gh subprocess in ADW goes through this module.

git() and gh() behave like subprocess.run with captured text output, plus
a timeout on every call. A command that overruns its timeout is stopped with
SIGTERM, so git can remove its lockfiles, then SIGKILL after a grace period,
and the caller gets a recoverable ADWError instead of a hang.

git stays in the terminal's process group: a Ctrl+C reaches it directly, and
credential or SSH prompts can still use the terminal.

The branch, commit and diff helpers below run through git() and gh().
"""

import logging
import re
import subprocess
from pathlib import Path

from adw.exceptions import ADWError, HookError
from adw.models.artifacts import DiffStats

logger = logging.getLogger(__name__)

# Timeout tiers, in seconds
DEFAULT_TIMEOUT = 60.0  # local plumbing
NETWORK_TIMEOUT = 300.0  # fetch, gh pr view
CHECKOUT_TIMEOUT = 300.0  # worktree remove, add -A
# Commands that run git hooks: commit, checkout, pull, push, worktree add
HOOK_TIMEOUT = 600.0

# Seconds between SIGTERM and SIGKILL
KILL_GRACE = 5.0

_SUGGESTIONS = {
    "git": (
        "A slow remote, a waiting credential or SSH prompt, or a slow hook can "
        "hold git up: check `git remote -v`, your credentials or ssh-agent and "
        "the network, remove a stale .git/index.lock if one is left, then retry"
    ),
    "gh": "Check network access and `gh auth status`, then retry",
}


def git(
    *args: str,
    cwd: Path | None = None,
    check: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    """Run git with a timeout.

    Raises:
        ADWError: GIT_TIMEOUT (recoverable) when git overruns ``timeout``.
        subprocess.CalledProcessError: On a non-zero exit when ``check`` is set.
        FileNotFoundError: When git is not installed.
    """
    return _run("git", args, cwd=cwd, check=check, timeout=timeout)


def gh(
    *args: str,
    cwd: Path | None = None,
    check: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    """Run the GitHub CLI with a timeout.

    Raises:
        ADWError: GH_TIMEOUT (recoverable) when gh overruns ``timeout``.
        subprocess.CalledProcessError: On a non-zero exit when ``check`` is set.
        FileNotFoundError: When gh is not installed.
    """
    return _run("gh", args, cwd=cwd, check=check, timeout=timeout)


def _run(
    tool: str,
    args: tuple[str, ...],
    *,
    cwd: Path | None,
    check: bool,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    cmd = [tool, *args]
    with subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as proc:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            _stop(proc)
            raise ADWError(
                f"{tool.upper()}_TIMEOUT",
                f"`{_label(tool, args)}` timed out after {timeout:g}s",
                suggestion=_SUGGESTIONS[tool],
                recoverable=True,
            ) from exc
        except BaseException:
            # KeyboardInterrupt or SystemExit from ADW's signal handlers
            _stop(proc)
            raise

    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, stdout, stderr)
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def _stop(proc: subprocess.Popen[str]) -> None:
    """Stop the process with SIGTERM, then SIGKILL after the grace period.

    Never reads the pipes afterwards: a descendant that inherited them could
    keep them open forever.
    """
    proc.terminate()
    try:
        proc.wait(timeout=KILL_GRACE)
    except subprocess.TimeoutExpired:
        pass
    finally:
        # Also reached when a second interrupt lands during the grace wait
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def _label(tool: str, args: tuple[str, ...]) -> str:
    """Return the tool plus up to two leading arguments before the first flag."""
    leading: list[str] = []
    for arg in args[:2]:
        if arg.startswith("-"):
            break
        leading.append(arg)
    return " ".join([tool, *leading])


# --- Branches ---------------------------------------------------------------

# Git allows ~256 chars; 50 keeps branch names readable in prompts, logs and CI
MAX_BRANCH_LENGTH = 50


def sanitize_branch_name(feature: str) -> str:
    """Turn a feature description into a git branch name.

    Lowercases, turns whitespace into hyphens, drops everything but
    alphanumerics and hyphens, collapses hyphens and truncates to
    MAX_BRANCH_LENGTH.

    Example:
        >>> sanitize_branch_name("Fix bug #123!")
        'fix-bug-123'
    """
    if not feature:
        return ""

    name = feature.lower()
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^a-z0-9-]", "", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")

    if len(name) > MAX_BRANCH_LENGTH:
        name = name[:MAX_BRANCH_LENGTH].rstrip("-")

    return name


def get_current_branch(*, working_dir: Path | None = None) -> str | None:
    """Return the checked-out branch, or None on a detached HEAD.

    Raises:
        HookError: GIT_BRANCH_CHECK_FAILED if git fails.
    """
    result = git("rev-parse", "--abbrev-ref", "HEAD", cwd=working_dir)

    if result.returncode != 0:
        raise HookError(
            code="GIT_BRANCH_CHECK_FAILED",
            message=f"Failed to get current branch: {result.stderr.strip()}",
            phase="post-hook",
            exit_code=result.returncode,
            stderr=result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    branch = result.stdout.strip()
    # "HEAD" is returned when in detached HEAD state
    return None if branch == "HEAD" else branch


def check_uncommitted_changes(*, working_dir: Path | None = None) -> bool:
    """Return whether the tree has staged, unstaged or untracked changes.

    Raises:
        HookError: GIT_STATUS_FAILED if git status fails.
    """
    result = git("status", "--porcelain", cwd=working_dir)

    if result.returncode != 0:
        raise HookError(
            code="GIT_STATUS_FAILED",
            message=f"Failed to check git status: {result.stderr.strip()}",
            phase="pre-hook",
            exit_code=result.returncode,
            stderr=result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    return bool(result.stdout.strip())


def create_or_switch_branch(
    branch_name: str, *, working_dir: Path | None = None
) -> None:
    """Switch to branch_name, creating it first if it doesn't exist.

    Raises:
        HookError: GIT_BRANCH_FAILED if listing or checking out fails.
    """
    result = git("branch", "--list", branch_name, cwd=working_dir)

    if result.returncode != 0:
        raise HookError(
            code="GIT_BRANCH_FAILED",
            message=f"Failed to list branches: {result.stderr.strip()}",
            phase="pre-hook",
            exit_code=result.returncode,
            stderr=result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    exists = bool(result.stdout.strip())

    # checkout runs the post-checkout hook
    if exists:
        checkout_result = git(
            "checkout", branch_name, cwd=working_dir, timeout=HOOK_TIMEOUT
        )
    else:
        checkout_result = git(
            "checkout", "-b", branch_name, cwd=working_dir, timeout=HOOK_TIMEOUT
        )

    if checkout_result.returncode != 0:
        action = "switch to" if exists else "create"
        err_msg = checkout_result.stderr.strip()
        raise HookError(
            code="GIT_BRANCH_FAILED",
            message=f"Failed to {action} branch '{branch_name}': {err_msg}",
            phase="pre-hook",
            exit_code=checkout_result.returncode,
            stderr=checkout_result.stderr,
            suggestion="Check for uncommitted changes or ensure branch name is valid",
        )


def ensure_on_branch(branch_name: str, *, working_dir: Path | None = None) -> None:
    """Make sure the repository in working_dir has branch_name checked out.

    Already on the branch, this does nothing, whatever the state of the tree.
    Otherwise it refuses to switch away from uncommitted changes, and creates
    or switches to the branch on a clean tree.

    Raises:
        HookError: GIT_BRANCH_CHECK_FAILED outside a git repository,
            GIT_UNCOMMITTED_CHANGES on a dirty tree, or GIT_BRANCH_FAILED
            if the checkout fails.
    """
    if get_current_branch(working_dir=working_dir) == branch_name:
        return

    if check_uncommitted_changes(working_dir=working_dir):
        raise HookError(
            code="GIT_UNCOMMITTED_CHANGES",
            message=(
                f"Cannot switch to branch '{branch_name}': "
                "the working tree has uncommitted changes"
            ),
            phase="run-start",
            suggestion=(
                "Commit or stash your changes, or run with worktree isolation "
                "(drop --no-worktree)"
            ),
        )

    create_or_switch_branch(branch_name, working_dir=working_dir)


def branch_exists(branch_name: str, *, working_dir: Path) -> bool:
    """Return whether branch_name exists locally.

    Raises:
        ADWError: GIT_TIMEOUT. A timed-out check must never read as "absent",
            because callers delete or recreate branches on False.
    """
    try:
        result = git("branch", "--list", branch_name, cwd=working_dir)
    except FileNotFoundError:
        return False
    return bool(result.stdout.strip())


def delete_branch(branch_name: str, *, working_dir: Path) -> bool:
    """Force-delete a local branch.

    Returns:
        True if the branch is gone (deleted, or never existed); False if git
        refused or timed out. Never raises a timeout.
    """
    try:
        if not branch_exists(branch_name, working_dir=working_dir):
            return True

        logger.info("Deleting branch", extra={"branch": branch_name})
        result = git("branch", "-D", branch_name, cwd=working_dir)
    except ADWError as e:
        logger.warning(
            "Failed to delete branch",
            extra={"branch": branch_name, "error": e.message},
        )
        return False

    if result.returncode == 0:
        logger.info("Branch deleted successfully", extra={"branch": branch_name})
        return True

    logger.warning(
        "Failed to delete branch",
        extra={"branch": branch_name, "error": result.stderr.strip()},
    )
    return False


def pr_exists(branch_name: str, *, working_dir: Path) -> bool | None:
    """Return whether an open or merged PR exists for branch_name.

    Returns:
        True or False from `gh pr view`; None when gh is missing, not
        authenticated, times out, or finds no PR.
    """
    try:
        result = gh(
            "pr",
            "view",
            branch_name,
            "--json",
            "state",
            cwd=working_dir,
            timeout=NETWORK_TIMEOUT,
        )
    except (FileNotFoundError, ADWError):
        return None

    if result.returncode != 0:
        # Could be: gh not installed, not authenticated, no PR
        return None

    return "OPEN" in result.stdout or "MERGED" in result.stdout


# --- Commits ----------------------------------------------------------------

DEFAULT_COMMIT_TEMPLATE = "[adw] {Phase}: {feature}\n\nRun: {run_id}"

# Maximum retries when a pre-commit hook modifies files
MAX_HOOK_RETRIES = 3


def validate_branch_matches(
    expected_branch: str | None,
    *,
    working_dir: Path | None = None,
) -> None:
    """Refuse to commit unless expected_branch is checked out.

    Skipped when expected_branch is None (non-worktree runs).

    Raises:
        HookError: GIT_BRANCH_MISMATCH on a detached HEAD or another branch.
    """
    if expected_branch is None:
        return

    current_branch = get_current_branch(working_dir=working_dir)

    if current_branch is None:
        raise HookError(
            code="GIT_BRANCH_MISMATCH",
            message="Cannot commit: repository is in detached HEAD state",
            phase="post-hook",
            exit_code=1,
            suggestion=f"Expected branch '{expected_branch}'. "
            f"Run 'git checkout {expected_branch}' to fix.",
        )

    if current_branch != expected_branch:
        raise HookError(
            code="GIT_BRANCH_MISMATCH",
            message=f"Cannot commit: current branch '{current_branch}' "
            f"does not match expected branch '{expected_branch}'",
            phase="post-hook",
            exit_code=1,
            suggestion=(
                f"Run 'git checkout {expected_branch}' to switch to the correct branch"
            ),
        )


def format_commit_message(phase: str, feature: str, run_id: str) -> str:
    """Fill DEFAULT_COMMIT_TEMPLATE for a phase commit.

    Example:
        >>> format_commit_message("build", "Add auth", "01HQ123")
        '[adw] Build: Add auth\\n\\nRun: 01HQ123'
    """
    return DEFAULT_COMMIT_TEMPLATE.format(
        phase=phase,
        Phase=phase.capitalize(),
        feature=feature,
        run_id=run_id,
    )


def stage_changes(*, working_dir: Path | None = None) -> list[str]:
    """Stage every change (`git add -A`) and return the staged paths.

    Raises:
        HookError: GIT_STAGE_FAILED if staging or listing fails.
    """
    # LFS clean filters and large untracked trees can make add slow
    add_result = git("add", "-A", cwd=working_dir, timeout=CHECKOUT_TIMEOUT)

    if add_result.returncode != 0:
        raise HookError(
            code="GIT_STAGE_FAILED",
            message=f"Failed to stage changes: {add_result.stderr.strip()}",
            phase="post-hook",
            exit_code=add_result.returncode,
            stderr=add_result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    diff_result = git("diff", "--cached", "--name-only", cwd=working_dir)

    if diff_result.returncode != 0:
        raise HookError(
            code="GIT_STAGE_FAILED",
            message=f"Failed to list staged files: {diff_result.stderr.strip()}",
            phase="post-hook",
            exit_code=diff_result.returncode,
            stderr=diff_result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    return [f for f in diff_result.stdout.strip().split("\n") if f]


def has_staged_changes(*, working_dir: Path | None = None) -> bool:
    """Return whether anything is staged (`git diff --cached --quiet`).

    Raises:
        HookError: GIT_DIFF_FAILED if git exits with anything but 0 or 1.
    """
    result = git("diff", "--cached", "--quiet", cwd=working_dir)

    # Exit code 0 = no changes, 1 = has changes, >1 = error
    if result.returncode == 0:
        return False
    if result.returncode == 1:
        return True
    raise HookError(
        code="GIT_DIFF_FAILED",
        message=f"Failed to check staged changes: {result.stderr.strip()}",
        phase="post-hook",
        exit_code=result.returncode,
        stderr=result.stderr,
        suggestion="Ensure you are in a git repository",
    )


def get_unstaged_modifications(*, working_dir: Path | None = None) -> list[str]:
    """Return the files modified but not staged, e.g. by a pre-commit hook.

    Raises:
        HookError: GIT_DIFF_FAILED if git diff fails.
    """
    result = git("diff", "--name-only", cwd=working_dir)

    if result.returncode != 0:
        raise HookError(
            code="GIT_DIFF_FAILED",
            message=f"Failed to check unstaged changes: {result.stderr.strip()}",
            phase="post-hook",
            exit_code=result.returncode,
            stderr=result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    return [f for f in result.stdout.strip().split("\n") if f]


def create_commit(
    phase: str,
    feature: str,
    run_id: str,
    *,
    skip_hooks: bool = False,
    working_dir: Path | None = None,
    expected_branch: str | None = None,
) -> str | None:
    """Commit the staged changes and return the commit SHA.

    Returns None when nothing is staged. When a pre-commit hook modifies
    files (e.g. a formatter), they are re-staged and the commit is retried
    or amended, up to MAX_HOOK_RETRIES times.

    Raises:
        HookError: GIT_BRANCH_MISMATCH if expected_branch isn't checked out,
            or GIT_COMMIT_FAILED if the commit fails.
    """
    validate_branch_matches(expected_branch, working_dir=working_dir)

    if not has_staged_changes(working_dir=working_dir):
        return None

    message = format_commit_message(phase=phase, feature=feature, run_id=run_id)
    commit_args = ["commit", "-m", message]
    if skip_hooks:
        commit_args.insert(1, "--no-verify")

    for attempt in range(MAX_HOOK_RETRIES):
        # Record files that are currently staged
        staged_before = set(
            git("diff", "--cached", "--name-only", cwd=working_dir)
            .stdout.strip()
            .split("\n")
        )

        commit_result = git(*commit_args, cwd=working_dir, timeout=HOOK_TIMEOUT)

        if commit_result.returncode == 0:
            # Commit succeeded - check if hooks modified any files
            modified = get_unstaged_modifications(working_dir=working_dir)
            hook_modified = [f for f in modified if f in staged_before]

            if hook_modified and attempt < MAX_HOOK_RETRIES - 1:
                # Pre-commit hook modified files - re-stage and amend
                stage_changes(working_dir=working_dir)
                amend_result = git(
                    "commit",
                    "--amend",
                    "--no-edit",
                    cwd=working_dir,
                    timeout=HOOK_TIMEOUT,
                )
                if amend_result.returncode != 0:
                    stderr = amend_result.stderr.strip()
                    raise HookError(
                        code="GIT_COMMIT_FAILED",
                        message=f"Failed to amend commit with hook changes: {stderr}",
                        phase="post-hook",
                        exit_code=amend_result.returncode,
                        stderr=amend_result.stderr,
                        suggestion="Pre-commit hook modified files but amend failed",
                    )

            sha_result = git("rev-parse", "HEAD", cwd=working_dir)

            if sha_result.returncode != 0:
                stderr = sha_result.stderr.strip()
                raise HookError(
                    code="GIT_COMMIT_FAILED",
                    message=f"Commit created but failed to get SHA: {stderr}",
                    phase="post-hook",
                    exit_code=sha_result.returncode,
                    stderr=sha_result.stderr,
                    suggestion="Commit may have succeeded - check git log",
                )

            return sha_result.stdout.strip()

        # Commit failed - check if it's due to hook modifying files
        modified = get_unstaged_modifications(working_dir=working_dir)
        hook_modified = [f for f in modified if f in staged_before]

        if hook_modified and attempt < MAX_HOOK_RETRIES - 1:
            stage_changes(working_dir=working_dir)
            continue

        raise HookError(
            code="GIT_COMMIT_FAILED",
            message=f"Failed to create commit: {commit_result.stderr.strip()}",
            phase="post-hook",
            exit_code=commit_result.returncode,
            stdout=commit_result.stdout,
            stderr=commit_result.stderr,
            suggestion="Check pre-commit hooks or commit message format",
        )

    # Should not reach here, but handle edge case
    raise HookError(
        code="GIT_COMMIT_FAILED",
        message="Commit failed after maximum retries",
        phase="post-hook",
        exit_code=1,
        suggestion="Pre-commit hooks may be continuously modifying files",
    )


# --- Diffs ------------------------------------------------------------------

# Marks a binary file in git diff output
BINARY_FILE_PATTERN = re.compile(r"Binary files .+ differ")


def has_commits(*, working_dir: Path | None = None) -> bool:
    """Return whether the repository has a commit (HEAD~1 needs one)."""
    result = git("rev-parse", "HEAD", cwd=working_dir or Path.cwd())
    return result.returncode == 0


def count_binary_files(diff_content: str) -> int:
    """Count the "Binary files ... differ" lines in a diff."""
    if not diff_content:
        return 0
    return len(BINARY_FILE_PATTERN.findall(diff_content))


def capture_diff(
    since: str = "HEAD~1",
    *,
    working_dir: Path | None = None,
) -> str:
    """Return `git diff --no-color <since>` output.

    Raises:
        HookError: GIT_DIFF_FAILED if git diff fails.
    """
    cwd = working_dir or Path.cwd()
    logger.debug("Capturing git diff", extra={"cwd": str(cwd), "since": since})

    result = git("diff", "--no-color", since, cwd=cwd)

    if result.returncode != 0:
        logger.error(
            "Git diff command failed",
            extra={
                "returncode": result.returncode,
                "stderr": result.stderr,
                "since": since,
            },
        )
        raise HookError(
            code="GIT_DIFF_FAILED",
            message=f"Git diff failed with exit code {result.returncode}",
            phase="build",
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            suggestion=f"Verify '{since}' is a valid git reference",
            recoverable=False,
        )

    return result.stdout


def capture_staged_diff(*, working_dir: Path | None = None) -> str:
    """Return `git diff --cached --no-color` output.

    Raises:
        HookError: GIT_DIFF_STAGED_FAILED if git diff fails.
    """
    cwd = working_dir or Path.cwd()
    logger.debug("Capturing staged git diff", extra={"cwd": str(cwd)})

    result = git("diff", "--cached", "--no-color", cwd=cwd)

    if result.returncode != 0:
        logger.error(
            "Git diff --cached command failed",
            extra={"returncode": result.returncode, "stderr": result.stderr},
        )
        raise HookError(
            code="GIT_DIFF_STAGED_FAILED",
            message=f"Git diff --cached failed with exit code {result.returncode}",
            phase="build",
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            suggestion="Verify you are in a valid git repository",
            recoverable=False,
        )

    return result.stdout


def truncate_diff(diff: str, max_bytes: int = 102400) -> str:
    """Truncate a diff to max_bytes at a line boundary and append a notice."""
    if not diff:
        return ""

    diff_bytes = diff.encode("utf-8")

    if len(diff_bytes) <= max_bytes:
        return diff

    total_lines = diff.count("\n")

    # Truncate to max_bytes, trying to end at a newline
    truncated_bytes = diff_bytes[:max_bytes]
    last_newline = truncated_bytes.rfind(b"\n")
    if last_newline > 0:
        truncated_bytes = truncated_bytes[: last_newline + 1]

    truncated = truncated_bytes.decode("utf-8", errors="replace")

    kept_lines = truncated.count("\n")
    omitted_lines = total_lines - kept_lines

    truncation_notice = (
        f"\n\n[TRUNCATED] Diff too large ({len(diff_bytes):,} bytes). "
        f"Showing first {kept_lines:,} lines, {omitted_lines:,} lines omitted.\n"
    )

    logger.info(
        "Truncated large diff",
        extra={
            "original_bytes": len(diff_bytes),
            "truncated_bytes": len(truncated_bytes),
            "total_lines": total_lines,
            "kept_lines": kept_lines,
            "omitted_lines": omitted_lines,
        },
    )

    return truncated + truncation_notice


def get_diff_stats(stat_output: str, diff_content: str = "") -> DiffStats:
    """Parse the summary line of `git diff --stat` into DiffStats.

    Binary files are counted from diff_content. Unparseable input gives zeros.
    """
    if not stat_output:
        return DiffStats()

    # Summary line: "N file(s) changed, M insertion(s)(+), P deletion(s)(-)"
    files_changed = 0
    insertions = 0
    deletions = 0

    files_match = re.search(r"(\d+)\s+files?\s+changed", stat_output)
    if files_match:
        files_changed = int(files_match.group(1))

    insertions_match = re.search(r"(\d+)\s+insertions?\(\+\)", stat_output)
    if insertions_match:
        insertions = int(insertions_match.group(1))

    deletions_match = re.search(r"(\d+)\s+deletions?\(-\)", stat_output)
    if deletions_match:
        deletions = int(deletions_match.group(1))

    binary_files = count_binary_files(diff_content)

    logger.debug(
        "Parsed diff stats",
        extra={
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
            "binary_files": binary_files,
        },
    )

    return DiffStats(
        files_changed=files_changed,
        insertions=insertions,
        deletions=deletions,
        binary_files=binary_files,
    )
