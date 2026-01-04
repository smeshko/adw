"""Git diff capture module for ADW.

This module provides functions for capturing git diffs as artifacts,
parsing diff statistics, and handling large diff truncation.

The captured diffs can be used for:
- Build phase artifacts
- PR description generation
- Code review context
"""

import logging
import re
import subprocess
from pathlib import Path

from adw.exceptions import HookError
from adw.models.artifacts import DiffStats

logger = logging.getLogger(__name__)

# Pattern to detect binary file markers in git diff output
BINARY_FILE_PATTERN = re.compile(r"Binary files .+ differ")


def has_commits(*, working_dir: Path | None = None) -> bool:
    """Check if the repository has any commits.

    Used to handle the initial commit edge case where HEAD~1 doesn't exist.

    Args:
        working_dir: Directory to run git command in (default: current dir)

    Returns:
        True if the repository has at least one commit, False otherwise.

    Example:
        >>> if has_commits():
        ...     diff = capture_diff(since="HEAD~1")
        ... else:
        ...     diff = capture_staged_diff()
    """
    cwd = working_dir if working_dir is not None else Path.cwd()

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    return result.returncode == 0


def count_binary_files(diff_content: str) -> int:
    """Count binary files detected in git diff output.

    Binary files are noted in git diff with "Binary files ... differ" lines.

    Args:
        diff_content: Raw git diff output

    Returns:
        Number of binary files detected in the diff
    """
    if not diff_content:
        return 0

    return len(BINARY_FILE_PATTERN.findall(diff_content))


def capture_diff(
    since: str = "HEAD~1",
    *,
    working_dir: Path | None = None,
) -> str:
    """Capture git diff output since a given commit.

    Executes `git diff` and returns the output as a string.
    Uses --no-color to avoid ANSI escape codes in the output.

    Args:
        since: Git reference to diff against (default: HEAD~1)
        working_dir: Directory to run git command in (default: current dir)

    Returns:
        The raw diff output as a string (may be empty if no changes)

    Raises:
        HookError: If git diff command fails

    Example:
        >>> diff = capture_diff()  # Diff since last commit
        >>> diff = capture_diff(since="HEAD~3")  # Diff since 3 commits ago
        >>> diff = capture_diff(since="main")  # Diff since main branch
    """
    cmd = ["git", "diff", "--no-color", since]

    cwd = working_dir if working_dir is not None else Path.cwd()

    logger.debug(
        "Capturing git diff",
        extra={"command": " ".join(cmd), "cwd": str(cwd), "since": since},
    )

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )

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


def capture_staged_diff(
    *,
    working_dir: Path | None = None,
) -> str:
    """Capture git diff for staged (cached) changes.

    Executes `git diff --cached` to get changes that have been
    staged but not yet committed. Useful when no commits were
    made during the build phase.

    Args:
        working_dir: Directory to run git command in (default: current dir)

    Returns:
        The raw diff output for staged changes (may be empty)

    Raises:
        HookError: If git diff command fails

    Example:
        >>> staged = capture_staged_diff()
        >>> if staged:
        ...     print("Staged changes found")
    """
    cmd = ["git", "diff", "--cached", "--no-color"]

    cwd = working_dir if working_dir is not None else Path.cwd()

    logger.debug(
        "Capturing staged git diff",
        extra={"command": " ".join(cmd), "cwd": str(cwd)},
    )

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    if result.returncode != 0:
        logger.error(
            "Git diff --cached command failed",
            extra={
                "returncode": result.returncode,
                "stderr": result.stderr,
            },
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
    """Truncate a diff if it exceeds max_bytes while preserving structure.

    Large diffs are truncated to prevent memory issues and keep
    artifacts manageable. The function attempts to preserve diff
    file headers when truncating.

    Args:
        diff: The raw diff content
        max_bytes: Maximum size in bytes (default: 100KB)

    Returns:
        The diff, possibly truncated with a notice appended

    Example:
        >>> large_diff = "x" * 200000
        >>> result = truncate_diff(large_diff, max_bytes=1024)
        >>> "[TRUNCATED]" in result
        True
    """
    if not diff:
        return ""

    diff_bytes = diff.encode("utf-8")

    if len(diff_bytes) <= max_bytes:
        return diff

    # Count total lines for the truncation notice
    total_lines = diff.count("\n")

    # Truncate to max_bytes, trying to end at a newline
    truncated_bytes = diff_bytes[:max_bytes]

    # Find the last newline to avoid cutting in the middle of a line
    last_newline = truncated_bytes.rfind(b"\n")
    if last_newline > 0:
        truncated_bytes = truncated_bytes[: last_newline + 1]

    truncated = truncated_bytes.decode("utf-8", errors="replace")

    # Calculate how many lines we're keeping
    kept_lines = truncated.count("\n")
    omitted_lines = total_lines - kept_lines

    # Build truncation notice
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
    """Parse git diff --stat output into DiffStats model.

    Extracts file count, insertions, deletions, and binary file count from
    the summary line of git diff --stat output and the raw diff content.

    Args:
        stat_output: Output from `git diff --stat`
        diff_content: Raw diff output (optional, for binary file detection)

    Returns:
        DiffStats with parsed values (all 0 if parsing fails)

    Example:
        >>> stat = '''
        ...  src/main.py | 10 +++++++---
        ...  2 files changed, 7 insertions(+), 3 deletions(-)
        ... '''
        >>> stats = get_diff_stats(stat)
        >>> stats.files_changed
        2
        >>> stats.insertions
        7
    """
    if not stat_output:
        return DiffStats()

    # Look for the summary line at the end
    # Format: "N file(s) changed, M insertion(s)(+), P deletion(s)(-)"
    # The numbers are optional if zero

    files_changed = 0
    insertions = 0
    deletions = 0

    # Match patterns like "2 files changed" or "1 file changed"
    files_match = re.search(r"(\d+)\s+files?\s+changed", stat_output)
    if files_match:
        files_changed = int(files_match.group(1))

    # Match patterns like "9 insertions(+)" or "1 insertion(+)"
    insertions_match = re.search(r"(\d+)\s+insertions?\(\+\)", stat_output)
    if insertions_match:
        insertions = int(insertions_match.group(1))

    # Match patterns like "4 deletions(-)" or "1 deletion(-)"
    deletions_match = re.search(r"(\d+)\s+deletions?\(-\)", stat_output)
    if deletions_match:
        deletions = int(deletions_match.group(1))

    # Count binary files from raw diff content
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
